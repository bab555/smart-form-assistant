"""
WebSocket 端点 (极简版)

原则：
- 只做连接管理和消息路由
- 不在这里写业务逻辑
- 业务逻辑在 Graph 节点中
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
from app.core.logger import app_logger as logger
from app.core.connection_manager import manager
from app.core.protocol import EventType
from app.utils.helpers import generate_trace_id


router = APIRouter()


@router.websocket("/agent")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None)
):
    """
    主 WebSocket 端点
    
    职责：
    1. 建立连接，发送 connection_ack
    2. 路由消息到对应处理器
    3. 处理断连
    """
    # 生成或使用提供的 client_id
    actual_client_id = client_id or f"client_{generate_trace_id()[:8]}"
    
    # 建立连接
    connected = await manager.connect(websocket, actual_client_id)
    if not connected:
        return
    
    try:
        while True:
            # 接收消息
            raw_data = await websocket.receive_text()
            
            try:
                message = json.loads(raw_data)
                msg_type = message.get("type", "")
                
                # 路由消息
                if msg_type == "ping":
                    # 心跳 (虽然我们说不需要主动心跳，但保留兼容)
                    await websocket.send_json({"type": "pong"})
                
                elif msg_type == "sync_state":
                    # 前端同步画布状态
                    # 后端可以据此恢复上下文（可选）
                    tables = message.get("data", {}).get("tables", {})
                    logger.info(f"[WS] Received sync_state from {actual_client_id}, tables: {len(tables)}")
                    # 目前只记录，不做处理
                
                elif msg_type == "chat":
                    # 对话消息 -> 转发给 Chat Handler
                    await handle_chat(actual_client_id, message)
                
                else:
                    # 未知消息类型，忽略
                    logger.debug(f"[WS] Unknown message type: {msg_type}")
                    
            except json.JSONDecodeError:
                logger.warning(f"[WS] Invalid JSON from {actual_client_id}")
    
    except WebSocketDisconnect:
        manager.disconnect(actual_client_id)
    
    except Exception as e:
        logger.error(f"[WS] Error for {actual_client_id}: {str(e)}")
        manager.disconnect(actual_client_id)


async def handle_chat(client_id: str, message: dict):
    """
    处理对话消息
    
    调用 Agent Graph 的对话分支
    """
    data = message.get("data", {})
    content = data.get("content", "")
    context = data.get("context", {})  # 当前画布快照
    
    logger.info(f"[WS] Chat from {client_id}: {content[:50]}...")
    
    if not content.strip():
        return
    
    # 提取表格上下文（用于咨询分析）
    table_context = None
    if context:
        # 尝试获取当前表格数据（兼容两种字段名）
        current_table_id = context.get("activeTableId") or context.get("currentTableId")
        tables = context.get("tables", {})
        
        if current_table_id and current_table_id in tables:
            # 获取当前选中的表格
            table = tables[current_table_id]
            table_context = {
                "id": current_table_id,
                "title": table.get("title", "表格"),
                "rows": table.get("rows", []),
                "schema": table.get("schema", []),
                "metadata": table.get("metadata", {}),
            }
            logger.debug(f"[WS] Chat with table context: {current_table_id}, rows={len(table_context['rows'])}")
        elif tables:
            # 没有选中的表格，使用第一个有数据的表格
            for tid, table in tables.items():
                if table.get("rows"):
                    table_context = {
                        "id": tid,
                        "title": table.get("title", "表格"),
                        "rows": table.get("rows", []),
                        "schema": table.get("schema", []),
                        "metadata": table.get("metadata", {}),
                    }
                    logger.debug(f"[WS] Chat using first table: {tid}, rows={len(table_context['rows'])}")
                    break
    
    # 调用 Agent Graph 处理对话
    try:
        from app.agents.graph import run_task
        import asyncio
        
        task_id = generate_trace_id()
        
        # 异步执行，不阻塞 WebSocket
        asyncio.create_task(
            run_task(
                task_id=task_id,
                client_id=client_id,
                task_type="chat",
                text_content=content,
                table_context=table_context,  # 传递表格上下文
            )
        )
    except Exception as e:
        logger.error(f"[WS] Chat handler error: {str(e)}")
        await manager.send(client_id, EventType.CHAT_MESSAGE, {
            "role": "agent",
            "content": f"处理失败: {str(e)}",
            "content_type": "text"
        })
