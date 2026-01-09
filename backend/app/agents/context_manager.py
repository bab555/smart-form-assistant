"""
会话上下文管理器

功能：
1. 管理用户会话状态
2. 维护对话历史
3. 跟踪待确认的操作
4. 支持多轮对话
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import asyncio

from app.core.logger import app_logger as logger


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


@dataclass
class Message:
    """对话消息"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    intent: Optional[str] = None
    tool_call: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class PendingAction:
    """待确认的操作"""
    action_type: str
    params: Dict[str, Any]
    missing_params: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.expires_at:
            # 默认 5 分钟过期
            self.expires_at = self.created_at + timedelta(minutes=5)
    
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


class ConversationContext:
    """
    单个会话的上下文
    
    管理一个用户的对话状态
    """
    
    def __init__(self, client_id: str, max_history: int = 20):
        self.client_id = client_id
        self.max_history = max_history
        
        # 对话历史
        self.history: List[Message] = []
        
        # 待确认的操作
        self.pending_action: Optional[PendingAction] = None
        
        # 当前状态
        self.current_table_id: Optional[str] = None
        self.current_row_index: Optional[int] = None
        self.current_col_key: Optional[str] = None
        
        # 上一个意图（用于上下文推断）
        self.last_intent: Optional[str] = None
        self.last_tool: Optional[str] = None
        
        # 用户偏好/记忆
        self.preferences: Dict[str, Any] = {}
        
        # 会话元数据
        self.created_at = datetime.now()
        self.last_active = datetime.now()
    
    def add_message(
        self,
        role: MessageRole,
        content: str,
        intent: str = None,
        tool_call: Dict = None,
        **metadata
    ):
        """添加消息"""
        msg = Message(
            role=role,
            content=content,
            intent=intent,
            tool_call=tool_call,
            metadata=metadata
        )
        self.history.append(msg)
        self.last_active = datetime.now()
        
        # 更新状态
        if intent:
            self.last_intent = intent
        if tool_call and tool_call.get("tool"):
            self.last_tool = tool_call.get("tool")
        
        # 限制历史长度
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def add_user_message(self, content: str, intent: str = None, **kwargs):
        """添加用户消息"""
        self.add_message(MessageRole.USER, content, intent, **kwargs)
    
    def add_agent_message(self, content: str, tool_call: Dict = None, **kwargs):
        """添加 Agent 消息"""
        self.add_message(MessageRole.AGENT, content, tool_call=tool_call, **kwargs)
    
    def get_recent_messages(self, n: int = 5) -> List[Message]:
        """获取最近 n 条消息"""
        return self.history[-n:]
    
    def get_context_for_llm(self, n: int = 5) -> str:
        """
        生成给 LLM 的对话上下文
        """
        recent = self.get_recent_messages(n)
        lines = []
        
        for msg in recent:
            role = "用户" if msg.role == MessageRole.USER else "助手"
            lines.append(f"{role}: {msg.content}")
        
        return "\n".join(lines)
    
    def get_context_summary(self) -> str:
        """
        生成上下文摘要（用于 System Prompt）
        """
        parts = []
        
        if self.current_table_id:
            parts.append(f"当前表格: {self.current_table_id}")
        if self.current_row_index is not None:
            parts.append(f"当前行: 第{self.current_row_index + 1}行")
        if self.last_intent:
            parts.append(f"上一个意图: {self.last_intent}")
        if self.pending_action:
            parts.append(f"待确认操作: {self.pending_action.action_type}")
        
        return "; ".join(parts) if parts else "无特殊上下文"
    
    # ========== 待确认操作管理 ==========
    
    def set_pending_action(
        self,
        action_type: str,
        params: Dict[str, Any],
        missing_params: List[str]
    ):
        """设置待确认的操作"""
        self.pending_action = PendingAction(
            action_type=action_type,
            params=params,
            missing_params=missing_params
        )
        logger.debug(f"[Context] 设置待确认操作: {action_type}, 缺失参数: {missing_params}")
    
    def update_pending_params(self, updates: Dict[str, Any]) -> bool:
        """
        更新待确认操作的参数
        
        Returns:
            是否所有必需参数都已填充
        """
        if not self.pending_action:
            return False
        
        self.pending_action.params.update(updates)
        
        # 移除已填充的缺失参数
        for key in updates:
            if key in self.pending_action.missing_params:
                self.pending_action.missing_params.remove(key)
        
        return len(self.pending_action.missing_params) == 0
    
    def confirm_pending_action(self) -> Optional[Dict]:
        """
        确认并返回待执行的操作
        """
        if not self.pending_action:
            return None
        
        if self.pending_action.is_expired():
            self.pending_action = None
            return None
        
        action = {
            "action_type": self.pending_action.action_type,
            "params": self.pending_action.params
        }
        self.pending_action = None
        return action
    
    def cancel_pending_action(self) -> bool:
        """取消待确认的操作"""
        if self.pending_action:
            self.pending_action = None
            return True
        return False
    
    def has_pending_action(self) -> bool:
        """是否有待确认的操作"""
        if self.pending_action and not self.pending_action.is_expired():
            return True
        self.pending_action = None
        return False
    
    # ========== 状态更新 ==========
    
    def set_current_table(self, table_id: str):
        """设置当前表格"""
        self.current_table_id = table_id
    
    def set_current_cell(self, row_index: int, col_key: str = None):
        """设置当前单元格"""
        self.current_row_index = row_index
        if col_key:
            self.current_col_key = col_key
    
    def clear_selection(self):
        """清除选择状态"""
        self.current_row_index = None
        self.current_col_key = None
    
    def to_dict(self) -> Dict:
        """导出为字典"""
        return {
            "client_id": self.client_id,
            "current_table_id": self.current_table_id,
            "current_row_index": self.current_row_index,
            "last_intent": self.last_intent,
            "has_pending": self.has_pending_action(),
            "message_count": len(self.history),
        }


class ContextManager:
    """
    全局上下文管理器
    
    管理所有用户的会话上下文
    """
    
    def __init__(self, max_contexts: int = 1000, context_ttl_minutes: int = 60):
        self.contexts: Dict[str, ConversationContext] = {}
        self.max_contexts = max_contexts
        self.context_ttl = timedelta(minutes=context_ttl_minutes)
        
        # 启动清理任务
        self._cleanup_task = None
    
    def get_context(self, client_id: str) -> ConversationContext:
        """
        获取或创建会话上下文
        """
        if client_id not in self.contexts:
            self.contexts[client_id] = ConversationContext(client_id)
            logger.debug(f"[ContextManager] 创建新上下文: {client_id}")
        
        ctx = self.contexts[client_id]
        ctx.last_active = datetime.now()
        return ctx
    
    def remove_context(self, client_id: str):
        """移除会话上下文"""
        if client_id in self.contexts:
            del self.contexts[client_id]
            logger.debug(f"[ContextManager] 移除上下文: {client_id}")
    
    def cleanup_expired(self):
        """清理过期的上下文"""
        now = datetime.now()
        expired = []
        
        for client_id, ctx in self.contexts.items():
            if now - ctx.last_active > self.context_ttl:
                expired.append(client_id)
        
        for client_id in expired:
            del self.contexts[client_id]
        
        if expired:
            logger.info(f"[ContextManager] 清理 {len(expired)} 个过期上下文")
        
        # 如果超过最大数量，移除最旧的
        if len(self.contexts) > self.max_contexts:
            sorted_contexts = sorted(
                self.contexts.items(),
                key=lambda x: x[1].last_active
            )
            to_remove = len(self.contexts) - self.max_contexts
            for client_id, _ in sorted_contexts[:to_remove]:
                del self.contexts[client_id]
            logger.info(f"[ContextManager] 移除 {to_remove} 个最旧上下文")
    
    async def start_cleanup_loop(self, interval_seconds: int = 300):
        """启动定期清理循环"""
        while True:
            await asyncio.sleep(interval_seconds)
            self.cleanup_expired()
    
    def stats(self) -> Dict:
        """统计信息"""
        return {
            "total_contexts": len(self.contexts),
            "max_contexts": self.max_contexts,
        }


# 全局单例
context_manager = ContextManager()

