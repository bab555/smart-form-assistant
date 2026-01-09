"""
工具模块

分层设计：
- fast_tools: 程序直接执行的工具（加速，不经过 LLM）
- agent_tools: LLM 调用的工具（推理，后处理）
"""
from .fast_tools import FastTools, fast_tools
from .agent_tools import AgentTools, AGENT_TOOL_DEFINITIONS

__all__ = [
    "FastTools",
    "fast_tools",
    "AgentTools", 
    "AGENT_TOOL_DEFINITIONS",
]

