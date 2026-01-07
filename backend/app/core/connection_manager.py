"""
WebSocket 连接管理器 (极简版)

原则：
- 无状态：不保留业务数据，只管理连接
- 极简：只做 connect/disconnect/send
- 前端是 SoT：后端不缓存消息，断连即丢
"""
from fastapi import WebSocket
from typing import Dict, Optional
from app.core.logger import app_logger as logger
from app.core.protocol import EventType, create_message
import json


class ConnectionManager:
    """极简 WebSocket 连接管理器"""
    
    def __init__(self):
        # client_id -> WebSocket
        self.connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """
        接受连接并发送 connection_ack
        返回 True 表示连接成功
        """
        try:
            await websocket.accept()
            self.connections[client_id] = websocket
            logger.info(f"[WS] Connected: {client_id} (total: {len(self.connections)})")
            
            # 发送连接确认
            await self.send(client_id, EventType.CONNECTION_ACK, {
                "status": "connected"
            })
            return True
        except Exception as e:
            logger.error(f"[WS] Connect failed: {client_id} - {str(e)}")
            return False
    
    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.connections:
            del self.connections[client_id]
            logger.info(f"[WS] Disconnected: {client_id} (total: {len(self.connections)})")
    
    def is_connected(self, client_id: str) -> bool:
        """检查客户端是否在线"""
        return client_id in self.connections
    
    async def send(self, client_id: str, event_type: EventType, data: Dict = None) -> bool:
        """
        发送消息到指定客户端
        返回 True 表示发送成功
        """
        if client_id not in self.connections:
            logger.debug(f"[WS] Client not connected: {client_id}")
            return False
        
        try:
            websocket = self.connections[client_id]
            message = create_message(event_type, client_id, data)
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"[WS] Send failed to {client_id}: {str(e)}")
            # 发送失败，清理连接
            self.disconnect(client_id)
            return False
    
    async def send_raw(self, client_id: str, message: Dict) -> bool:
        """发送原始消息（已格式化的）"""
        if client_id not in self.connections:
            return False
        
        try:
            websocket = self.connections[client_id]
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"[WS] Send raw failed to {client_id}: {str(e)}")
            self.disconnect(client_id)
            return False
    
    async def broadcast(self, event_type: EventType, data: Dict = None):
        """广播消息给所有连接"""
        for client_id in list(self.connections.keys()):
            await self.send(client_id, event_type, data)
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.connections)


# 全局单例
manager = ConnectionManager()
