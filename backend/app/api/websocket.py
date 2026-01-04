"""
WebSocket 处理 - 实时推送 Agent 思考过程
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio
from app.core.logger import app_logger as logger
from app.agents.graph import agent_graph, AgentState
from app.utils.helpers import generate_trace_id
from datetime import datetime, timezone


router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """接受连接"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket 连接建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开连接"""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket 连接断开，当前连接数: {len(self.active_connections)}")
    
    async def send_message(self, websocket: WebSocket, message: dict):
        """发送消息到单个客户端"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")
    
    async def broadcast(self, message: dict):
        """广播消息到所有客户端"""
        for connection in self.active_connections:
            await self.send_message(connection, message)


manager = ConnectionManager()

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.websocket("/agent")
async def websocket_agent_endpoint(websocket: WebSocket):
    """
    Agent WebSocket 端点 - 实时推送处理进度
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            logger.info(f"收到 WebSocket 消息: {data[:100]}...")
            
            try:
                message = json.loads(data)
                message_type = message.get('type')
                
                if message_type == 'ping':
                    # 心跳响应
                    await manager.send_message(websocket, {"type": "pong", "timestamp": _iso_now()})
                
                elif message_type == 'process_image':
                    # 处理图片（流式推送进度）
                    await handle_image_stream(websocket, message)
                
                elif message_type == 'process_audio':
                    # 处理音频（流式推送进度）
                    await handle_audio_stream(websocket, message)
                
                else:
                    logger.warning(f"未知消息类型: {message_type}")
                    await manager.send_message(websocket, {
                        "type": "error",
                        "code": 4001,
                        "message": f"未知消息类型: {message_type}",
                        "timestamp": _iso_now(),
                    })
                    
            except json.JSONDecodeError:
                logger.error("JSON 解析失败")
                await manager.send_message(websocket, {
                    "type": "error",
                    "code": 4001,
                    "message": "消息格式错误",
                    "timestamp": _iso_now(),
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("客户端主动断开连接")
    
    except Exception as e:
        logger.error(f"WebSocket 错误: {str(e)}")
        manager.disconnect(websocket)


async def handle_image_stream(websocket: WebSocket, message: dict):
    """
    处理图片识别（流式推送）
    
    Args:
        websocket: WebSocket 连接
        message: 客户端消息
    """
    trace_id = generate_trace_id()
    
    try:
        # 发送开始消息 (扁平化结构匹配前端)
        await manager.send_message(websocket, {
            "type": "step_start",
            "content": "开始处理图片",
            "step": "ocr",
            "status": "running",
            "trace_id": trace_id,
            "timestamp": _iso_now(),
        })
        
        # 模拟处理流程
        steps = [
            {"step": "ocr", "message": "正在执行 OCR 识别..."},
            {"step": "calibrating", "message": "正在校准数据..."},
            {"step": "filling", "message": "正在填充表格..."},
        ]
        
        for step_info in steps:
            # 发送步骤开始
            await manager.send_message(websocket, {
                "type": "step_start",
                "content": step_info["message"],
                "step": step_info["step"],
                "status": "running",
                "timestamp": _iso_now(),
            })
            
            # 模拟处理延迟
            await asyncio.sleep(0.5)
            
            # 发送步骤完成
            await manager.send_message(websocket, {
                "type": "step_end",
                "content": f"{step_info['message']} 完成",
                "step": step_info["step"],
                "status": "success",
                "timestamp": _iso_now(),
            })
        
        # 发送完成消息
        await manager.send_message(websocket, {
            "type": "agent_thought",
            "content": "图片处理完成，数据已填充到表格",
            "step": "idle",
            "trace_id": trace_id,
            "timestamp": _iso_now(),
        })
        
    except Exception as e:
        logger.error(f"处理图片流失败: {str(e)}")
        await manager.send_message(websocket, {
            "type": "error",
            "code": 5002,
            "message": f"处理失败: {str(e)}",
            "timestamp": _iso_now(),
        })


async def handle_audio_stream(websocket: WebSocket, message: dict):
    """
    处理语音命令（流式推送）
    
    Args:
        websocket: WebSocket 连接
        message: 客户端消息
    """
    trace_id = generate_trace_id()
    
    try:
        # 发送开始消息
        await manager.send_message(websocket, {
            "type": "step_start",
            "content": "开始处理语音",
            "step": "ocr",
            "status": "running",
            "trace_id": trace_id,
            "timestamp": _iso_now(),
        })
        
        # 模拟 ASR
        await asyncio.sleep(0.5)
        await manager.send_message(websocket, {
            "type": "step_end",
            "content": "语音识别完成",
            "step": "ocr",
            "status": "success",
            "text": "把第一行的商品名称改成红富士苹果",
            "timestamp": _iso_now(),
        })
        
        # 模拟意图识别
        await manager.send_message(websocket, {
            "type": "step_start",
            "content": "正在理解您的指令...",
            "step": "calibrating",
            "status": "running",
            "timestamp": _iso_now(),
        })
        
        await asyncio.sleep(0.3)
        
        # 发送工具调用 (关键修复: tool_call -> tool_action, args -> params)
        await manager.send_message(websocket, {
            "type": "tool_action",
            "content": "调用表格更新工具",
            "tool": "update_cell",
            "params": {
                "rowIndex": 0,  # 前端是 camelCase (useFormStore 逻辑可能需要检查，但通常 JS 传参习惯 camelCase)
                "key": "product_name",
                "value": "红富士苹果"
            },
            "timestamp": _iso_now(),
        })
        
        # 发送完成消息
        await manager.send_message(websocket, {
            "type": "agent_thought",
            "content": "已将第1行的商品名称改为红富士苹果",
            "step": "idle",
            "trace_id": trace_id,
            "timestamp": _iso_now(),
        })
        
    except Exception as e:
        logger.error(f"处理音频流失败: {str(e)}")
        await manager.send_message(websocket, {
            "type": "error",
            "code": 5002,
            "message": f"处理失败: {str(e)}",
            "timestamp": _iso_now(),
        })
