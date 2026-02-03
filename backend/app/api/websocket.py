"""
WebSocket 端点 (流式适配版)
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import os
import aiofiles
from pathlib import Path
from app.core.logger import app_logger as logger
from app.core.connection_manager import manager
from app.core.protocol import EventType
from app.utils.helpers import generate_trace_id
from app.core.simple_agent import SimpleAgent
from app.services.knowledge_base import vector_store
from app.services.preference_store import preference_store
from app.services.remote_session import remote_session_manager

router = APIRouter()
agent = SimpleAgent()

@router.websocket("/agent")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None)
):
    # generate_trace_id() 以 "trace_20..." 开头，切前8位会导致 id 冲突；取最后的随机段
    trace_suffix = generate_trace_id().split("_")[-1]
    actual_client_id = client_id or f"client_{trace_suffix}"
    
    # 获取用户 ID（如果已登录）
    user_id = "anonymous"
    if token:
        session = await remote_session_manager.get_session(token)
        if session:
            user_id = session.user_id
            logger.info(f"[WS] Authenticated user: {user_id} ({session.name})")

    connected = await manager.connect(websocket, actual_client_id)
    if not connected: return
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                message = json.loads(raw_data)
                msg_type = message.get("type", "")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "chat":
                    # 将 user_id 注入到 message context 中，或者作为参数传递
                    await handle_chat_stream(actual_client_id, message, user_id)
                elif msg_type == "apply_order_product":
                    await handle_apply_order_product(actual_client_id, message)
                else:
                    pass # 忽略其他类型
                    
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(actual_client_id)
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
        manager.disconnect(actual_client_id)

async def handle_chat_stream(client_id: str, message: dict, user_id: str = "anonymous"):
    """处理对话流"""
    data = message.get("data", {})
    content = data.get("content", "")
    context = data.get("context", {})
    attachments = data.get("attachments", [])

    # customer guard（兜底）：未选客户不允许任何操作（含聊天/上传）
    customer_id = None
    try:
        active_id = context.get("activeTableId")
        tables_ctx = context.get("tables") or {}
        meta = (tables_ctx.get(active_id, {}) or {}).get("metadata") or {}
        customer_id = meta.get("customerId") or meta.get("customer_id")
    except Exception:
        customer_id = None

    # 注意：不再强制要求选择客户，用户可以先上传文件识别，后续再选择客户
    # customer_id 可能为空，这是允许的
    
    # 1. 准备文件
    file_bytes = None
    filename = None
    if attachments:
        file_info = attachments[0]
        raw_path = file_info.get("path") or file_info.get("file_path")
        filename = file_info.get("name")
        if raw_path:
            try:
                p = Path(raw_path)
                # 兼容：前端/旧接口可能传相对路径（如 "uploads\\xxx.xlsx"）
                if not p.is_absolute():
                    backend_root = Path(__file__).resolve().parents[2]
                    p = (backend_root / p).resolve()

                exists = p.exists()
                logger.info(f"[WS] Attachment resolve: raw={raw_path}, resolved={str(p)}, exists={exists}, cwd={os.getcwd()}")
                if exists:
                    async with aiofiles.open(p, 'rb') as f:
                        file_bytes = await f.read()
                    logger.info(f"[WS] Attachment read: name={filename}, bytes={len(file_bytes or b'')}")
                else:
                    logger.warning(f"[WS] Attachment missing on disk: {str(p)}")
            except Exception as e:
                logger.error(f"[WS] Attachment read failed: raw={raw_path}, err={e}")

    # 2. 调用 Agent 生成器
    try:
        # 发送任务开始信号
        await manager.send(client_id, EventType.TASK_START, {"table_id": None})
        
        async for event in agent.process_request(content, context, file_bytes, filename, user_id=user_id):
            event_type = event.get("type")
            
            if event_type == "tool_call":
                # 直接转发工具调用
                await manager.send(client_id, EventType.TOOL_CALL, {
                    "tool": event["tool"],
                    "params": event["params"]
                })
            
            elif event_type == "thinking":
                # 推送思考过程 (前端需支持该事件类型，或复用 CHAT_MESSAGE 带标记)
                # 这里我们复用 CHAT_MESSAGE 但标记 is_thinking
                await manager.send(client_id, EventType.CHAT_MESSAGE, {
                    "role": "agent",
                    "content": event["content"],
                    "content_type": "text",
                    "is_thinking": True # 前端用来渲染灰色折叠区
                })
            
            elif event_type == "message_delta":
                # 增量消息
                await manager.send(client_id, EventType.CHAT_MESSAGE, {
                    "role": "agent",
                    "content": event["content"],
                    "content_type": "text",
                    "is_delta": True # 前端累加显示
                })
                
            elif event_type == "message":
                # 完整消息
                await manager.send(client_id, EventType.CHAT_MESSAGE, {
                    "role": "agent",
                    "content": event["content"],
                    "content_type": "text"
                })
                
            elif event_type == "state":
                await manager.send(client_id, EventType.AGENT_STATE, {"state": event["state"]})

        # 发送任务结束信号
        await manager.send(client_id, EventType.TASK_FINISH, {"table_id": None})
        await manager.send(client_id, EventType.AGENT_STATE, {"state": "idle"})
        
    except Exception as e:
        logger.error(f"Agent Stream Error: {e}")
        await manager.send(client_id, EventType.CHAT_MESSAGE, {
            "role": "agent",
            "content": f"处理出错: {str(e)}",
            "content_type": "text"
        })
        # 出错也要发送结束信号
        await manager.send(client_id, EventType.TASK_FINISH, {"table_id": None})
        await manager.send(client_id, EventType.AGENT_STATE, {"state": "idle"})


async def handle_apply_order_product(client_id: str, message: dict):
    """
    行内“替换为订单商品”动作（A/B/C）

    data:
      - table_id: str
      - row_index: int
      - mode: 'A'|'B'|'C'
      - recognized: str (识别商品)
      - selected: str (radio 选中候选，可空)
      - order_value: str (订单商品单元格当前值，可空/手动输入)
      - customer_id: str (可选；兜底从 context.tables 取)
      - context: { activeTableId, tables } (可选；用于兜底)
    """
    data = message.get("data", {}) or {}
    table_id = data.get("table_id")
    row_index = data.get("row_index")
    mode = data.get("mode")
    recognized = (data.get("recognized") or "").strip()
    selected = (data.get("selected") or "").strip()
    # 注意：订单商品列不允许手动输入。若未选候选，则回退使用“识别商品”进行匹配。
    # order_value 仅作为兼容字段保留（前端仍会传），后端不依赖它。
    _order_value_compat = (data.get("order_value") or "").strip()

    if mode == "C":
        return

    # customer guard（兜底）
    customer_id = (data.get("customer_id") or "").strip()
    if not customer_id:
        ctx = data.get("context") or {}
        try:
            active_id = ctx.get("activeTableId")
            tables_ctx = ctx.get("tables") or {}
            meta = (tables_ctx.get(active_id, {}) or {}).get("metadata") or {}
            customer_id = (meta.get("customerId") or meta.get("customer_id") or "").strip()
        except Exception:
            customer_id = ""

    if not customer_id:
        await manager.send(client_id, EventType.CHAT_MESSAGE, {
            "role": "agent",
            "content": "请先选择客户",
            "content_type": "text"
        })
        return

    if table_id is None or row_index is None:
        await manager.send(client_id, EventType.ERROR, {"message": "apply_order_product 缺少 table_id/row_index"})
        return

    try:
        row_index = int(row_index)
    except Exception:
        await manager.send(client_id, EventType.ERROR, {"message": "row_index 必须是整数"})
        return

    # 规则：若未选择“订单商品”候选，则直接读取“识别商品”作为匹配输入
    final_name = selected or recognized
    if not final_name:
        await manager.send(client_id, EventType.CHAT_MESSAGE, {
            "role": "agent",
            "content": "请先填写或修改“识别商品”，或在“订单商品”中选择一个候选",
            "content_type": "text"
        })
        return

    # 查库：优先精确名称；否则校对一次（用于把识别商品归一到标准商品）
    product = vector_store.product_index.get_by_name(final_name)
    if not product:
        cal = vector_store.product_index.calibrate(final_name)
        if cal.match_type == "not_found" or not cal.product:
            # 明确提示：库中不存在该商品（用户可修改识别商品后再点替换）
            await manager.send(client_id, EventType.CHAT_MESSAGE, {
                "role": "agent",
                "content": "商品库中不存在该商品，请修改“识别商品”后再点击替换",
                "content_type": "text"
            })
            # 同时把订单商品列标记为 not_found 提示
            for key, value in [
                ("订单商品", "商品库中不存在该商品，请修改识别商品"),
                ("__order_status", "not_found"),
                ("__order_candidates", []),
                ("__order_selected", ""),
            ]:
                await manager.send(client_id, EventType.TOOL_CALL, {
                    "tool": "update_cell",
                    "params": {"table_id": table_id, "row_index": row_index, "key": key, "value": value},
                })
            return
        product = cal.product
        final_name = cal.calibrated

    # A：储存偏好（识别商品 -> 订单商品），按 customerId 维度
    # 注意：识别商品可能是用户手动修改后的值，以当前 recognized 为准
    if mode == "A" and recognized and final_name:
        await preference_store.set(customer_id, recognized, final_name)

    # 统一写回：订单商品 + 规格/单位盖章覆盖；数量不动
    # 用户需求：同时也覆盖“识别商品”列
    updates = [
        ("识别商品", final_name),
        ("订单商品", final_name),
        ("规格", product.spec or ""),
        ("单位", product.unit or ""),
        ("__order_status", "exact"),
        ("__order_candidates", []),
        ("__order_selected", ""),
        ("__goods_id", product.id or ""),  # 存储商品ID
    ]

    for key, value in updates:
        await manager.send(client_id, EventType.TOOL_CALL, {
            "tool": "update_cell",
            "params": {
                "table_id": table_id,
                "row_index": row_index,
                "key": key,
                "value": value
            }
        })
