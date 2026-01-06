"""
WebSocket 连接管理器
"""
from fastapi import WebSocket
from typing import Dict, Set, Optional
from app.core.logger import app_logger as logger
import asyncio

class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 使用 Dict 存储: client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # 同时保留 Set 兼容旧逻辑（虽然主要用 Dict）
        self._all_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """接受连接并注册 client_id"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self._all_connections.add(websocket)
        logger.info(f"WebSocket 连接建立: {client_id}, 当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, client_id: Optional[str] = None):
        """断开连接"""
        if client_id and client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # 尝试从 value 中移除（如果是未知 client_id 的情况）
        if websocket in self._all_connections:
            self._all_connections.remove(websocket)
            
        logger.info(f"WebSocket 连接断开: {client_id}, 当前连接数: {len(self.active_connections)}")
    
    async def send_message(self, websocket: WebSocket, message: dict):
        """发送消息到单个连接"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
            
    async def send_to_client(self, client_id: str, message: dict):
        """发送消息到指定 client_id"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await self.send_message(websocket, message)
        else:
            # logger.debug(f"Client {client_id} not connected, skipping message")
            pass
    
    async def broadcast(self, message: dict):
        """广播消息"""
        for connection in self._all_connections:
            await self.send_message(connection, message)

# 全局单例
manager = ConnectionManager()

