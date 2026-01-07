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
    
    这里可以调用 Agent Graph 的对话分支
    """
    content = message.get("data", {}).get("content", "")
    context = message.get("data", {}).get("context", {})  # 当前画布快照
    
    logger.info(f"[WS] Chat from {client_id}: {content[:50]}...")
    
    # TODO: 调用 Agent Graph 处理对话
    # 目前先返回一个简单的回复
    await manager.send(client_id, EventType.CHAT_MESSAGE, {
        "role": "agent",
        "content": f"收到您的消息：{content}（Agent 功能开发中）",
        "content_type": "text"
    })
