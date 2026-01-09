"""
LLM Node - 文本格式化为 JSON

功能：
- 统一使用 Turbo 模型按固定 Schema 提取订单数据
- 支持任意格式的文本输入（OCR 结果、Word 文本、用户聊天）
"""
import json
import re
from typing import List, Dict, Any, AsyncGenerator
from app.core.logger import app_logger as logger
from app.services.aliyun_llm import llm_service
from app.core.templates import (
    DEFAULT_HEADERS,
    map_row_to_template,
    UNSTRUCTURED_EXTRACTION_PROMPT,
)


async def format_to_json(
    text: str,
    stream: bool = True,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    将文本格式化为 JSON
    
    统一使用 Turbo 模型按固定 Schema 提取，无论输入格式如何
    
    Args:
        text: 待提取的文本（OCR 结果、Word 文本等）
        stream: 是否流式输出（保留参数，当前未使用）
    
    Yields:
        每行解析出的 JSON 对象（已标准化为固定 Schema）
    """
    if not text or not text.strip():
        logger.warning("[LLM] Empty text, nothing to format")
        return
    
    logger.info(f"[LLM] Formatting text, length: {len(text)}")
    
    try:
        # 直接使用 Turbo 按 Schema 提取
        raw_rows = await _extract_unstructured(text)
        
        for row in raw_rows:
            if row:
                # 统一标准化（虽然 Prompt 已经要求了字段，但再做一次兜底）
                normalized_row = map_row_to_template(row)
                yield normalized_row
            
    except Exception as e:
        logger.error(f"[LLM] Format failed: {str(e)}")
        yield {"_error": str(e)}


async def _extract_unstructured(text: str) -> List[Dict[str, Any]]:
    """
    非结构化文本提取
    
    使用 Turbo 模型按基础模板表头提取
    """
    logger.info("[LLM] Using unstructured extraction (Turbo)")
    
    prompt = UNSTRUCTURED_EXTRACTION_PROMPT.format(text=text[:4000])
    
    # 使用 Turbo 模型（快速）
    response = await llm_service.call_turbo_model(
        messages=[
            {"role": "system", "content": f"你是数据提取专家。只提取以下字段：{', '.join(DEFAULT_HEADERS)}。只输出 JSON 数组。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )
    
    # 解析响应
    rows = _parse_json_response(response)
    
    logger.info(f"[LLM] Extraction completed: {len(rows)} rows")
    return rows


def _parse_json_response(response: str) -> List[Dict[str, Any]]:
    """解析 JSON 数组响应"""
    response = response.strip()
    
    # 移除 markdown 代码块
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        if end > start:
            response = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end > start:
            response = response[start:end].strip()
    
    # 尝试解析 JSON 数组
    try:
        data = json.loads(response)
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
        elif isinstance(data, dict):
            if "rows" in data:
                return data["rows"]
            return [data]
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 JSON 数组
    match = re.search(r'\[[\s\S]*?\]', response)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return [row for row in data if isinstance(row, dict)]
        except json.JSONDecodeError:
            pass
    
    # 尝试按行解析 JSONL
    rows = []
    for line in response.split('\n'):
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except json.JSONDecodeError:
                continue
    
    return rows

