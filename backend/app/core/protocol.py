"""
通信协议定义 (Protocol Definition)
定义前后端 WebSocket 通信的标准消息格式和事件类型。

原则：
- 前端 CanvasStore 是唯一权威数据源 (SoT)
- 后端是无状态执行器，不持久化业务数据
- 事件仅用于推送结果，不用于驱动前端业务逻辑分支
"""
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class EventType(str, Enum):
    """WebSocket 事件类型"""
    
    # 连接管理
    CONNECTION_ACK = "connection_ack"      # 连接确认
    SYNC_STATE = "sync_state"              # 前端同步画布快照给后端
    
    # 任务状态 (仅用于日志/调试，不驱动UI)
    TASK_START = "task_start"              # 任务开始
    TASK_FINISH = "task_finish"            # 任务完成
    NODE_START = "node_start"              # 节点开始 (可选)
    NODE_FINISH = "node_finish"            # 节点完成 (可选)
    
    # 数据更新 (核心)
    ROW_COMPLETE = "row_complete"          # 行级流式：追加一行
    TABLE_REPLACE = "table_replace"        # 全量替换表格
    TABLE_CREATE = "table_create"          # 创建新表格
    TABLE_DELETE = "table_delete"          # 删除表格
    CELL_UPDATE = "cell_update"            # 更新单个单元格
    
    # 校对建议
    CALIBRATION_NOTE = "calibration_note"  # 校对建议
    
    # 对话
    CHAT_MESSAGE = "chat_message"          # 对话消息
    
    # 异常
    ERROR = "error"                        # 错误


class WebSocketMessage(BaseModel):
    """标准 WebSocket 消息包"""
    type: EventType
    client_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: Dict[str, Any] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "client_id": self.client_id,
            "timestamp": self.timestamp,
            "data": self.data
        }


# ========== 具体 Payload 类型定义 ==========

class ConnectionAckPayload(BaseModel):
    """连接确认"""
    status: str = "connected"


class TaskStartPayload(BaseModel):
    """任务开始"""
    task_id: str
    task_type: str  # "extract" | "audio" | "chat"


class TaskFinishPayload(BaseModel):
    """任务完成"""
    task_id: str
    success: bool = True
    message: Optional[str] = None


class RowCompletePayload(BaseModel):
    """行级流式：一行数据完成"""
    table_id: str
    row: Dict[str, Any]  # 完整的一行数据


class TableReplacePayload(BaseModel):
    """全量替换表格"""
    table_id: str
    rows: List[Dict[str, Any]]
    schema: Optional[List[Dict[str, Any]]] = None  # 可选：表头定义
    metadata: Optional[Dict[str, Any]] = None      # 可选：表单头信息


class TableCreatePayload(BaseModel):
    """创建新表格"""
    table_id: str
    title: str
    schema: List[Dict[str, Any]]  # 表头定义
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    position: Dict[str, int] = Field(default_factory=lambda: {"x": 100, "y": 100})
    metadata: Optional[Dict[str, Any]] = None


class CellUpdatePayload(BaseModel):
    """更新单个单元格"""
    table_id: str
    row_index: int
    col_key: str
    value: Any


class CalibrationNotePayload(BaseModel):
    """校对建议"""
    table_id: str
    row_index: int
    note: str
    severity: str = "warning"  # "info" | "warning" | "error"


class ChatMessagePayload(BaseModel):
    """对话消息"""
    role: str  # "user" | "agent" | "system"
    content: str
    content_type: str = "text"  # "text" | "markdown"


class ErrorPayload(BaseModel):
    """错误"""
    code: int
    message: str
    details: Optional[Dict[str, Any]] = None


# ========== 辅助函数 ==========

def create_message(
    event_type: EventType,
    client_id: str,
    data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """创建标准消息"""
    return WebSocketMessage(
        type=event_type,
        client_id=client_id,
        data=data or {}
    ).to_dict()

