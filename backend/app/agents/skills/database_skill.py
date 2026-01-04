"""
数据库检索技能 - 向量检索封装为 LangChain Tool
"""
from typing import Optional, List, Dict, Any
from langchain.tools import tool
from app.services.knowledge_base import vector_store
from app.core.logger import app_logger as logger


@tool
async def lookup_standard_entity(query: str, category: Optional[str] = None) -> str:
    """
    在知识库中查找标准实体名称
    
    Args:
        query: 查询文本（可能是 OCR 识别的错误文本）
        category: 类别筛选（product/customer/unit/supplier）
    
    Returns:
        str: 标准化后的实体名称和候选列表（JSON 格式）
    """
    try:
        logger.info(f"数据库技能被调用: query={query}, category={category}")
        
        # 调用向量检索
        results = await vector_store.search(query, top_k=5, category=category)
        
        if not results:
            return f'{{"standard_text": "{query}", "confidence": 0.0, "candidates": []}}'
        
        # 获取最佳匹配
        best_match = results[0]
        standard_text = best_match['text']
        confidence = best_match['combined_score']
        
        # 获取候选列表
        candidates = [r['text'] for r in results[:3]]
        
        # 返回 JSON 格式结果
        result = {
            "standard_text": standard_text,
            "confidence": round(confidence, 2),
            "candidates": candidates,
            "is_ambiguous": confidence < 0.85 and len(candidates) > 1
        }
        
        import json
        logger.info(f"数据库技能返回: {result}")
        return json.dumps(result, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"数据库技能执行失败: {str(e)}")
        return f'{{"error": "{str(e)}"}}'


@tool
async def calibrate_text_batch(texts: List[str], category: Optional[str] = None) -> str:
    """
    批量校准文本
    
    Args:
        texts: 文本列表
        category: 类别筛选
    
    Returns:
        str: 校准结果（JSON 格式）
    """
    try:
        logger.info(f"批量校准被调用: 共 {len(texts)} 条")
        
        results = []
        for text in texts:
            calibrated, confidence, is_amb, candidates = await vector_store.calibrate_text(
                text, category=category
            )
            results.append({
                "original": text,
                "calibrated": calibrated,
                "confidence": round(confidence, 2),
                "is_ambiguous": is_amb,
                "candidates": candidates
            })
        
        import json
        return json.dumps(results, ensure_ascii=False)
        
    except Exception as e:
        logger.error(f"批量校准失败: {str(e)}")
        return f'{{"error": "{str(e)}"}}'


# 导出工具列表
DATABASE_TOOLS = [lookup_standard_entity, calibrate_text_batch]

