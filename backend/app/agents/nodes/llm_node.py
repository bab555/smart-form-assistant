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
                logger.debug(f"[LLM] Raw row before mapping: {row}")
                # 统一标准化（虽然 Prompt 已经要求了字段，但再做一次兜底）
                normalized_row = map_row_to_template(row)
                logger.debug(f"[LLM] After mapping: {normalized_row}")
                yield normalized_row
            
    except Exception as e:
        logger.error(f"[LLM] Format failed: {str(e)}")
        yield {"_error": str(e)}


async def _extract_unstructured(text: str) -> List[Dict[str, Any]]:
    """
    非结构化文本提取
    
    使用 Turbo 模型按基础模板表头提取
    【重要】只做原样提取，不做任何校正
    """
    logger.info("[LLM] Using unstructured extraction (Turbo)")
    
    prompt = UNSTRUCTURED_EXTRACTION_PROMPT.format(text=text[:6000])
    
    # 系统提示词：让模型自己理解内容
    system_content = """你是智能数据提取助手。请阅读文本，理解其中的商品信息。

你的任务是找出文本中的商品，并提取：
- 识别商品 = 商品的名字（如：海天老抽、白醋、味事达、土豆、鸡蛋等）
- 规格 = 容量/重量描述（如：500ml、1.9L、2.7kg）
- 单位 = 计量单位（如：瓶、箱、斤、袋）
- 数量 = 购买数目

输出 JSON 数组：[{"序号": "", "识别商品": "", "规格": "", "单位": "", "数量": 0, "备注": ""}]

关键：识别商品填的是商品名字（如"海天老抽"），不是规格或单位。"""
    
    # 使用 Turbo 模型（快速）
    response = await llm_service.call_turbo_model(
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )
    
    logger.info(f"[LLM] Raw response: {response[:500]}...")  # 添加调试日志
    
    # 解析响应
    rows = _parse_json_response(response)
    
    # 检查并警告空的识别商品
    empty_count = sum(1 for r in rows if not r.get("识别商品"))
    if empty_count > 0:
        logger.warning(f"[LLM] {empty_count}/{len(rows)} rows have empty 识别商品!")
    
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

