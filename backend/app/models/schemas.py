"""
数据模型定义 - 与前端总控文档保持一致
"""
from typing import Any, Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


# ==================== 错误码定义 ====================
class ErrorCode(str, Enum):
    """业务错误码枚举"""
    SUCCESS = "200"
    INVALID_INPUT = "4001"
    AMBIGUOUS_INTENT = "4002"
    OCR_FAILED = "5001"
    SKILL_EXECUTION_ERROR = "5002"
    CALIBRATION_FAILED = "5003"


# ==================== 基础表单项 ====================
class FormItem(BaseModel):
    """表单项 - 前后端交换的最小单元"""
    key: str = Field(..., description="字段唯一标识")
    label: str = Field(..., description="显示名称")
    value: Any = Field(..., description="实际值")
    original_text: Optional[str] = Field(None, description="OCR/ASR原始文本")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="置信度")
    is_ambiguous: bool = Field(False, description="是否有歧义")
    candidates: Optional[List[str]] = Field(None, description="候选值列表")
    data_type: Literal['string', 'number', 'date', 'enum'] = Field('string', description="数据类型")

    class Config:
        json_schema_extra = {
            "example": {
                "key": "product_name",
                "label": "商品名称",
                "value": "红富士苹果",
                "original_text": "红富土苹果",
                "confidence": 0.85,
                "is_ambiguous": True,
                "candidates": ["红富士苹果", "红富土苹果"],
                "data_type": "string"
            }
        }


# ==================== 识别请求 ====================
class RecognitionRequest(BaseModel):
    """识别请求模型"""
    request_id: str = Field(..., description="请求唯一ID")
    input_type: Literal['image_handwriting', 'image_print', 'audio_command'] = Field(..., description="输入类型")
    file_url: Optional[str] = Field(None, description="文件URL或base64")
    template_id: Optional[str] = Field(None, description="表单模板ID")


# ==================== 标准响应封套 ====================
class StandardResponse(BaseModel):
    """标准API响应封装"""
    code: int = Field(200, description="业务状态码")
    message: str = Field("success", description="提示信息")
    data: Any = Field(None, description="实际载荷")
    trace_id: str = Field(..., description="链路追踪ID")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "识别成功",
                "data": {"rows": []},
                "trace_id": "uuid-v4"
            }
        }


# ==================== 表单模板 ====================
class FormTemplate(BaseModel):
    """表单模板"""
    template_id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    columns: List[dict] = Field(..., description="字段定义列表")


# ==================== WebSocket 消息 ====================
class WSMessageType(str, Enum):
    """WebSocket 消息类型"""
    AGENT_THOUGHT = "agent_thought"
    STEP_START = "step_start"
    STEP_END = "step_end"
    STEP_LOG = "step_log"
    TOOL_ACTION = "tool_action"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    PONG = "pong"
    HUMAN_INPUT_REQUIRED = "human_input_required"


class WebSocketMessage(BaseModel):
    """WebSocket 消息"""
    type: WSMessageType = Field(..., description="消息类型")
    content: str = Field(..., description="消息内容")
    data: Optional[dict] = Field(None, description="附加数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


# ==================== Agent 状态 ====================
class AgentStep(str, Enum):
    """Agent 工作流步骤"""
    IDLE = "idle"
    OCR = "ocr"
    CALIBRATION = "calibration"
    QUERY = "query"
    FILL = "fill"
    WAITING = "waiting"


# ==================== 图片识别请求 ====================
class ImageRecognitionRequest(BaseModel):
    """图片识别请求"""
    template_id: Optional[str] = Field(None, description="模板ID")


# ==================== 语音识别请求 ====================
class AudioRecognitionRequest(BaseModel):
    """语音识别请求"""
    command: Optional[str] = Field(None, description="预识别的命令文本")


# ==================== 表单提交请求 ====================
class FormSubmitRequest(BaseModel):
    """表单提交请求"""
    template_id: str = Field(..., description="模板ID")
    rows: List[List[FormItem]] = Field(..., description="表格数据")
    user_id: Optional[str] = Field(None, description="用户ID")


# ==================== 知识库同步请求 ====================
class KnowledgeSyncRequest(BaseModel):
    """知识库同步请求"""
    source: Literal['mysql', 'api', 'file'] = Field('mysql', description="数据源类型")
    category: Optional[str] = Field(None, description="知识类别")
    force_rebuild: bool = Field(False, description="是否强制重建索引")
