"""
表单操作技能 - 提供给 Agent 操作前端表格的能力
"""
from typing import List, Dict, Any
from langchain.tools import tool
from app.core.logger import app_logger as logger
import json


@tool
def update_table(rows: str) -> str:
    """
    更新整个表格数据
    
    Args:
        rows: 表格行数据（JSON 字符串）
    
    Returns:
        str: 操作结果
    """
    try:
        logger.info(f"表格更新工具被调用")
        
        # 这里只是返回一个指令，实际更新由前端 WebSocket 处理
        result = {
            "action": "update_table",
            "data": json.loads(rows) if isinstance(rows, str) else rows
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"表格更新失败: {str(e)}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def update_cell(row_index: int, key: str, value: Any, confidence: float = 1.0) -> str:
    """
    更新单个单元格
    
    Args:
        row_index: 行索引
        key: 字段键
        value: 新值
        confidence: 置信度
    
    Returns:
        str: 操作指令
    """
    try:
        logger.info(f"单元格更新工具被调用: row={row_index}, key={key}, value={value}")
        
        result = {
            "action": "update_cell",
            "rowIndex": row_index,
            "key": key,
            "value": value,
            "confidence": confidence
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"单元格更新失败: {str(e)}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@tool
def mark_ambiguous(row_index: int, key: str, candidates: List[str]) -> str:
    """
    标记单元格为歧义状态
    
    Args:
        row_index: 行索引
        key: 字段键
        candidates: 候选值列表
    
    Returns:
        str: 操作指令
    """
    try:
        logger.info(f"歧义标记工具被调用: row={row_index}, key={key}, candidates={candidates}")
        
        result = {
            "action": "mark_ambiguous",
            "rowIndex": row_index,
            "key": key,
            "candidates": candidates
        }
        
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"歧义标记失败: {str(e)}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# 导出工具列表
FORM_TOOLS = [update_table, update_cell, mark_ambiguous]
