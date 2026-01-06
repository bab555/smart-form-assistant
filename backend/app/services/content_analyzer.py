"""
内容分析服务
- 判断图片是否包含手写内容（严格模式）
- 判断内容类型（表格/文章）
- 匹配相关 Skills
"""
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import re

from app.core.logger import app_logger as logger
from app.services.aliyun_llm import llm_service
from app.services.skill_registry import skill_registry


class SourceType(str, Enum):
    """内容来源类型"""
    EXCEL = "excel"           # Excel 文件
    WORD = "word"             # Word 文件
    PRINTED = "printed"       # 打印体图片
    HANDWRITTEN = "handwritten"  # 包含手写内容
    MIXED = "mixed"           # 混合（打印+手写）


class ContentType(str, Enum):
    """内容结构类型"""
    TABLE = "table"           # 表格数据
    ARTICLE = "article"       # 连续文章
    MIXED = "mixed"           # 混合内容
    OTHER = "other"           # 其他


@dataclass
class ContentAnalysisResult:
    """内容分析结果"""
    source_type: SourceType           # 来源类型
    content_type: ContentType         # 内容类型
    has_handwriting: bool             # 是否包含手写
    matched_skills: List[str]         # 匹配到的 Skill IDs
    should_calibrate: bool            # 是否需要校准
    analysis_reason: str              # 分析原因说明
    is_article: bool = False          # 是否为纯文章


class ContentAnalyzer:
    """内容分析器"""
    
    def __init__(self):
        pass
    
    async def analyze_image_source(self, image_data: bytes) -> Tuple[bool, str]:
        """
        分析图片是否包含手写内容（严格模式）
        
        返回：(has_handwriting, reason)
        - has_handwriting: 只要有任何手写内容就返回 True
        - reason: 判断原因
        """
        logger.info("[ContentAnalyzer] 分析图片是否包含手写内容...")
        
        try:
            # 使用 Qwen-VL 分析图片
            prompt = """请仔细分析这张图片，判断图片中是否包含**任何手写内容**。

判断标准（严格模式）：
1. 如果图片中有任何手写文字、手写数字、手写签名、手写标注，都算作"包含手写"
2. 即使大部分是打印体，只要有一处手写内容，也返回"包含手写"
3. 只有100%确定全部是打印体/电子文字时，才返回"不包含手写"

请以 JSON 格式返回（只输出JSON，不要其他文字）：
{
  "has_handwriting": true/false,
  "confidence": 0.0-1.0,
  "reason": "判断原因说明",
  "handwriting_locations": ["如有手写，描述位置"]
}"""
            
            result = await llm_service.call_multimodal_model(
                image_data=image_data,
                prompt=prompt
            )
            
            # 解析结果
            try:
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = json.loads(result)
                
                has_handwriting = data.get("has_handwriting", False)
                reason = data.get("reason", "分析完成")
                
                logger.info(f"[ContentAnalyzer] 手写判断结果: {has_handwriting}, 原因: {reason}")
                return has_handwriting, reason
                
            except json.JSONDecodeError:
                # 解析失败时，保守处理：假设可能有手写
                logger.warning("[ContentAnalyzer] 手写判断 JSON 解析失败，保守返回 True")
                return True, "分析结果解析失败，保守判断为可能包含手写"
                
        except Exception as e:
            logger.error(f"[ContentAnalyzer] 手写判断异常: {str(e)}")
            # 异常时保守处理
            return True, f"分析异常，保守判断: {str(e)}"
    
    async def analyze_content_type(self, ocr_text: str) -> Tuple[ContentType, bool, str]:
        """
        分析 OCR 文本的内容类型
        
        返回：(content_type, is_article, reason)
        """
        logger.info("[ContentAnalyzer] 分析内容类型...")
        
        try:
            prompt = f"""请分析以下 OCR 识别的文本内容，判断其结构类型：

OCR 文本：
{ocr_text[:2000]}  # 限制长度

判断标准：
1. **table（表格数据）**: 包含明显的表格结构，有行列关系，如订单、清单、报表等
2. **article（连续文章）**: 是完整的文章、论文、报告等连续文本，没有明显表格结构
3. **mixed（混合内容）**: 既有表格也有文章段落
4. **other（其他）**: 无法归类

请以 JSON 格式返回（只输出JSON）：
{{
  "content_type": "table/article/mixed/other",
  "is_article": true/false,
  "reason": "判断原因"
}}"""
            
            messages = [
                {"role": "system", "content": "你是文档分析专家。"},
                {"role": "user", "content": prompt}
            ]
            
            result = await llm_service.call_main_model(messages, temperature=0.3)
            
            try:
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = json.loads(result)
                
                content_type = ContentType(data.get("content_type", "table"))
                is_article = data.get("is_article", False)
                reason = data.get("reason", "分析完成")
                
                logger.info(f"[ContentAnalyzer] 内容类型: {content_type}, 是否文章: {is_article}")
                return content_type, is_article, reason
                
            except (json.JSONDecodeError, ValueError):
                return ContentType.TABLE, False, "解析失败，默认为表格"
                
        except Exception as e:
            logger.error(f"[ContentAnalyzer] 内容类型分析异常: {str(e)}")
            return ContentType.TABLE, False, f"分析异常: {str(e)}"
    
    async def match_skills(self, ocr_text: str) -> Tuple[List[str], str]:
        """
        使用主控模型匹配相关 Skills
        
        返回：(matched_skill_ids, reason)
        """
        logger.info("[ContentAnalyzer] 匹配相关 Skills...")
        
        # 确保 skill_registry 已初始化
        skill_registry.initialize()
        
        # 获取 Skills 摘要
        skills_summary = skill_registry.get_skills_summary()
        
        try:
            prompt = f"""请分析以下识别的文本内容，判断与哪些校准技能相关。

{skills_summary}

---

识别的文本内容：
{ocr_text[:1500]}

---

判断标准：
1. 分析文本内容涉及的领域和数据类型
2. 匹配与内容相关的校准技能
3. 如果内容与任何技能都不相关（如电脑配置、电子产品等非农产品领域），返回空列表

请以 JSON 格式返回（只输出JSON）：
{{
  "matched_skills": ["skill_id1", "skill_id2"],
  "reason": "匹配原因说明",
  "is_relevant": true/false
}}"""
            
            messages = [
                {"role": "system", "content": "你是智能表单助手，负责分析内容与校准技能的相关性。"},
                {"role": "user", "content": prompt}
            ]
            
            result = await llm_service.call_main_model(messages, temperature=0.3)
            
            try:
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = json.loads(result)
                
                matched_skills = data.get("matched_skills", [])
                reason = data.get("reason", "匹配完成")
                
                # 验证 skill_ids 是否有效
                valid_skills = [
                    sid for sid in matched_skills 
                    if skill_registry.get_skill(sid) is not None
                ]
                
                logger.info(f"[ContentAnalyzer] 匹配到 Skills: {valid_skills}")
                return valid_skills, reason
                
            except json.JSONDecodeError:
                # 解析失败，尝试关键词匹配
                logger.warning("[ContentAnalyzer] LLM 匹配解析失败，使用关键词匹配")
                matched = skill_registry.match_skills_by_keywords(ocr_text)
                return matched, "使用关键词匹配"
                
        except Exception as e:
            logger.error(f"[ContentAnalyzer] Skill 匹配异常: {str(e)}")
            # 异常时使用关键词匹配作为备选
            matched = skill_registry.match_skills_by_keywords(ocr_text)
            return matched, f"异常后使用关键词匹配: {str(e)}"
    
    async def full_analysis(
        self,
        source_type: SourceType,
        image_data: Optional[bytes] = None,
        ocr_text: Optional[str] = None
    ) -> ContentAnalysisResult:
        """
        完整内容分析流程
        
        Args:
            source_type: 已知的来源类型（Excel/Word/图片）
            image_data: 图片数据（仅图片类型需要）
            ocr_text: OCR 文本（用于内容分析和 Skill 匹配）
        
        Returns:
            ContentAnalysisResult
        """
        logger.info(f"[ContentAnalyzer] 开始完整分析，来源类型: {source_type}")
        
        # 默认值
        has_handwriting = False
        content_type = ContentType.TABLE
        is_article = False
        matched_skills: List[str] = []
        should_calibrate = False
        reasons: List[str] = []
        
        # 1. Excel/Word 直接跳过校准
        if source_type in [SourceType.EXCEL, SourceType.WORD]:
            logger.info(f"[ContentAnalyzer] {source_type} 类型，跳过校准")
            return ContentAnalysisResult(
                source_type=source_type,
                content_type=ContentType.TABLE,
                has_handwriting=False,
                matched_skills=[],
                should_calibrate=False,
                analysis_reason=f"{source_type} 文件，无需校准",
                is_article=False
            )
        
        # 2. 图片类型：判断手写
        if image_data:
            has_handwriting, hw_reason = await self.analyze_image_source(image_data)
            reasons.append(f"手写判断: {hw_reason}")
            
            if has_handwriting:
                source_type = SourceType.HANDWRITTEN
            else:
                source_type = SourceType.PRINTED
        
        # 3. 分析内容类型
        if ocr_text:
            content_type, is_article, ct_reason = await self.analyze_content_type(ocr_text)
            reasons.append(f"内容类型: {ct_reason}")
        
        # 4. 如果是文章，不需要校准
        if is_article or content_type == ContentType.ARTICLE:
            logger.info("[ContentAnalyzer] 检测到文章内容，跳过校准")
            return ContentAnalysisResult(
                source_type=source_type,
                content_type=content_type,
                has_handwriting=has_handwriting,
                matched_skills=[],
                should_calibrate=False,
                analysis_reason="检测到连续文章内容，不适合表格提取",
                is_article=True
            )
        
        # 5. 打印体不需要校准
        if not has_handwriting:
            logger.info("[ContentAnalyzer] 打印体内容，跳过校准")
            return ContentAnalysisResult(
                source_type=source_type,
                content_type=content_type,
                has_handwriting=False,
                matched_skills=[],
                should_calibrate=False,
                analysis_reason="打印体/电子文字，无需校准",
                is_article=False
            )
        
        # 6. 手写内容：匹配 Skills
        if ocr_text:
            matched_skills, skill_reason = await self.match_skills(ocr_text)
            reasons.append(f"Skill匹配: {skill_reason}")
        
        # 7. 决定是否校准
        should_calibrate = len(matched_skills) > 0
        
        if not should_calibrate:
            reasons.append("无匹配的校准技能，跳过校准")
        else:
            reasons.append(f"将使用 {matched_skills} 进行校准")
        
        return ContentAnalysisResult(
            source_type=source_type,
            content_type=content_type,
            has_handwriting=has_handwriting,
            matched_skills=matched_skills,
            should_calibrate=should_calibrate,
            analysis_reason=" | ".join(reasons),
            is_article=is_article
        )


# 全局单例
content_analyzer = ContentAnalyzer()

