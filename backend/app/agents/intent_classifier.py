"""
意图分类器 (重构版)

特点：
1. 规则优先，LLM 兜底
2. 支持上下文感知
3. 支持多轮对话
4. 细粒度意图分类
"""
import re
from typing import Tuple, Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass

from app.core.logger import app_logger as logger


class Intent(str, Enum):
    """意图类型"""
    
    # === 操作类 (需要工具调用) ===
    MODIFY = "modify"           # 修改: "把XX改成YY"
    ADD = "add"                 # 添加: "添加一行", "加上XX"
    DELETE = "delete"           # 删除: "删掉XX", "移除第X行"
    CREATE_TABLE = "create_table"  # 创建表格
    
    # === 查询类 ===
    QUERY_PRODUCT = "query_product"    # 商品查询: "有没有XX"
    QUERY_TABLE = "query_table"        # 表格查询: "第几行是什么"
    CALCULATE = "calculate"            # 计算统计: "总共多少", "平均XX"
    
    # === 提取类 (通常由文件触发) ===
    EXTRACT = "extract"         # 数据提取
    
    # === 确认类 (多轮对话) ===
    CONFIRM = "confirm"         # 确认: "是的", "对", "好的"
    REJECT = "reject"           # 否定: "不是", "取消", "算了"
    SUPPLEMENT = "supplement"   # 补充信息: 回答之前的问题
    
    # === 对话类 ===
    GREETING = "greeting"       # 打招呼
    HELP = "help"               # 帮助
    CHAT = "chat"               # 闲聊
    
    # === 特殊 ===
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """意图分类结果"""
    intent: Intent
    confidence: float           # 0-1
    matched_rule: Optional[str] # 匹配的规则
    extracted_params: Dict[str, Any]  # 提取的参数
    needs_clarification: bool   # 是否需要澄清
    clarification_question: Optional[str]  # 澄清问题


# ========== 规则定义 ==========

# 修改操作规则
MODIFY_PATTERNS = [
    (r"把(.+?)(?:的)?(.+?)(?:改|修改|更改|换|变)(?:成|为|作)?(.+)", 0.95, ["target", "field", "value"]),
    (r"将(.+?)(?:的)?(.+?)(?:改|修改|更改)(?:成|为)?(.+)", 0.95, ["target", "field", "value"]),
    (r"(?:把|将)?第(\d+)行(?:的)?(.+?)(?:改|修改|换)(?:成|为)?(.+)", 0.95, ["row", "field", "value"]),
    (r"(?:修改|更改|改)(?:一下)?(.+?)(?:为|成)?(.+)", 0.85, ["field", "value"]),
    (r"(.+?)(?:改|换)(?:成|为)(.+)", 0.80, ["field", "value"]),
]

# 添加操作规则
ADD_PATTERNS = [
    (r"(?:添加|新增|加|增加)(?:一)?(?:行|条|个)(?:数据|记录)?[,，]?(.+)?", 0.95, ["data"]),
    (r"(?:补充|加上|录入)(?:一下)?(.+)", 0.85, ["data"]),
    (r"(?:新建|创建)(?:一)?(?:行|条)(.+)?", 0.85, ["data"]),
]

# 删除操作规则
DELETE_PATTERNS = [
    (r"(?:删除|删掉|移除|去掉|清除)第(\d+)行", 0.95, ["row"]),
    (r"(?:删除|删掉|移除|去掉)(?:最后)?(?:一)?行", 0.90, []),
    (r"(?:把|将)?第(\d+)行(?:删除|删掉|移除|去掉)", 0.95, ["row"]),
    (r"(?:删除|删掉|移除)(.+)", 0.80, ["target"]),
]

# 创建表格规则
CREATE_TABLE_PATTERNS = [
    (r"(?:新建|创建|建|开)(?:一个|一张)?(?:新)?(?:的)?表(?:格)?", 0.95, []),
    (r"(?:帮我)?(?:建|创建|新建)(?:一个)?(.+?)(?:表|单)", 0.90, ["title"]),
]

# 查询商品规则
QUERY_PRODUCT_PATTERNS = [
    (r"(?:有没有|有无|有)(?:这个)?(.+?)(?:这个)?(?:商品|产品)?(?:吗|没)?", 0.90, ["query"]),
    (r"(?:查|搜|找|查询|搜索)(?:一下)?(.+?)(?:商品|产品)?", 0.85, ["query"]),
    (r"(.+?)(?:是什么|什么意思|什么价格|多少钱)", 0.80, ["query"]),
]

# 计算统计规则
CALCULATE_PATTERNS = [
    (r"(?:总共|合计|一共|总计)(?:是)?(?:多少)?(?:钱|金额)?", 0.95, []),
    (r"(?:算|计算|统计)(?:一下)?(?:总|合计)?(?:金额|价格|数量)?", 0.90, []),
    (r"(?:这个|这张)?(?:订单|表|表格)?(?:总共|一共)?多少(?:钱|行)?", 0.85, []),
    (r"(?:帮我)?(?:算|计算)(?:一下)?(.+)", 0.80, ["field"]),
]

# 确认规则
CONFIRM_PATTERNS = [
    (r"^(?:是的?|对的?|好的?|可以|行|没错|确认|确定|嗯|ok|OK|yes|Yes)$", 0.98, []),
    (r"^(?:对|是|好|行|嗯)$", 0.95, []),
]

# 否定规则
REJECT_PATTERNS = [
    (r"^(?:不是|不对|不要|不用|取消|算了|没有|不|否|no|No|NO)$", 0.98, []),
    (r"(?:取消|算了|不用了|不要了)", 0.90, []),
]

# 打招呼规则
GREETING_PATTERNS = [
    (r"^(?:你好|您好|hi|Hi|HI|hello|Hello|嗨|哈喽)$", 0.98, []),
    (r"(?:早上好|下午好|晚上好|早安|晚安)", 0.95, []),
]

# 帮助规则
HELP_PATTERNS = [
    (r"(?:怎么用|怎么操作|如何使用|帮助|help|功能|能做什么)", 0.90, []),
    (r"(?:你能|你可以|你会)(?:做什么|干什么)", 0.85, []),
]


class IntentClassifier:
    """
    意图分类器
    
    支持规则匹配和上下文感知
    """
    
    def __init__(self):
        # 编译正则表达式
        self.patterns = {
            Intent.MODIFY: [(re.compile(p, re.IGNORECASE), c, g) for p, c, g in MODIFY_PATTERNS],
            Intent.ADD: [(re.compile(p, re.IGNORECASE), c, g) for p, c, g in ADD_PATTERNS],
            Intent.DELETE: [(re.compile(p, re.IGNORECASE), c, g) for p, c, g in DELETE_PATTERNS],
            Intent.CREATE_TABLE: [(re.compile(p, re.IGNORECASE), c, g) for p, c, g in CREATE_TABLE_PATTERNS],
            Intent.QUERY_PRODUCT: [(re.compile(p, re.IGNORECASE), c, g) for p, c, g in QUERY_PRODUCT_PATTERNS],
            Intent.CALCULATE: [(re.compile(p, re.IGNORECASE), c, g) for p, c, g in CALCULATE_PATTERNS],
            Intent.CONFIRM: [(re.compile(p, re.IGNORECASE), c, g) for p, c, g in CONFIRM_PATTERNS],
            Intent.REJECT: [(re.compile(p, re.IGNORECASE), c, g) for p, c, g in REJECT_PATTERNS],
            Intent.GREETING: [(re.compile(p, re.IGNORECASE), c, g) for p, c, g in GREETING_PATTERNS],
            Intent.HELP: [(re.compile(p, re.IGNORECASE), c, g) for p, c, g in HELP_PATTERNS],
        }
    
    def classify(
        self,
        text: str,
        context: Optional[Dict] = None
    ) -> IntentResult:
        """
        分类用户意图
        
        Args:
            text: 用户输入
            context: 上下文信息 {
                "has_pending_action": bool,
                "pending_action_type": str,
                "missing_params": List[str],
                "last_intent": str,
                "current_table_id": str,
            }
            
        Returns:
            IntentResult
        """
        text = text.strip()
        context = context or {}
        
        # 1. 检查是否是对待确认操作的回应
        if context.get("has_pending_action"):
            # 检查确认/否定
            for pattern, confidence, _ in self.patterns[Intent.CONFIRM]:
                if pattern.search(text):
                    return IntentResult(
                        intent=Intent.CONFIRM,
                        confidence=confidence,
                        matched_rule="confirm_pending",
                        extracted_params={},
                        needs_clarification=False,
                        clarification_question=None
                    )
            
            for pattern, confidence, _ in self.patterns[Intent.REJECT]:
                if pattern.search(text):
                    return IntentResult(
                        intent=Intent.REJECT,
                        confidence=confidence,
                        matched_rule="reject_pending",
                        extracted_params={},
                        needs_clarification=False,
                        clarification_question=None
                    )
            
            # 可能是补充信息
            missing_params = context.get("missing_params", [])
            if missing_params:
                extracted = self._try_extract_missing_params(text, missing_params)
                if extracted:
                    return IntentResult(
                        intent=Intent.SUPPLEMENT,
                        confidence=0.85,
                        matched_rule="supplement_params",
                        extracted_params=extracted,
                        needs_clarification=False,
                        clarification_question=None
                    )
        
        # 2. 规则匹配
        best_result = None
        best_confidence = 0
        
        for intent, patterns in self.patterns.items():
            for pattern, confidence, groups in patterns:
                match = pattern.search(text)
                if match and confidence > best_confidence:
                    # 提取参数
                    params = {}
                    for i, group_name in enumerate(groups):
                        if i + 1 <= len(match.groups()) and match.group(i + 1):
                            params[group_name] = match.group(i + 1).strip()
                    
                    best_result = IntentResult(
                        intent=intent,
                        confidence=confidence,
                        matched_rule=pattern.pattern,
                        extracted_params=params,
                        needs_clarification=False,
                        clarification_question=None
                    )
                    best_confidence = confidence
        
        if best_result:
            # 检查是否需要澄清（缺少关键参数）
            best_result = self._check_clarification_needed(best_result)
            logger.debug(f"[Intent] 规则匹配: {best_result.intent.value} ({best_result.confidence:.2f})")
            return best_result
        
        # 3. 关键词检测（兜底）
        keyword_result = self._keyword_fallback(text)
        if keyword_result:
            logger.debug(f"[Intent] 关键词匹配: {keyword_result.intent.value}")
            return keyword_result
        
        # 4. 默认为闲聊
        logger.debug(f"[Intent] 默认闲聊")
        return IntentResult(
            intent=Intent.CHAT,
            confidence=0.5,
            matched_rule=None,
            extracted_params={},
            needs_clarification=False,
            clarification_question=None
        )
    
    def _try_extract_missing_params(
        self,
        text: str,
        missing_params: List[str]
    ) -> Dict[str, Any]:
        """
        尝试从文本中提取缺失的参数
        """
        extracted = {}
        
        for param in missing_params:
            if param == "row" or param == "row_index":
                # 提取行号
                match = re.search(r"第?(\d+)行?", text)
                if match:
                    extracted["row_index"] = int(match.group(1)) - 1  # 转为 0-based
                elif text in ["第一行", "首行"]:
                    extracted["row_index"] = 0
                elif text in ["最后一行", "末行"]:
                    extracted["row_index"] = -1
            
            elif param == "field" or param == "col_key":
                # 提取字段名（常见字段）
                field_keywords = {
                    "商品": "商品名称", "商品名": "商品名称", "名称": "商品名称",
                    "数量": "数量", "数目": "数量",
                    "单价": "单价", "价格": "单价",
                    "单位": "单位",
                    "金额": "金额", "总价": "金额",
                }
                for kw, field in field_keywords.items():
                    if kw in text:
                        extracted["col_key"] = field
                        break
            
            elif param == "value":
                # 提取值（可能是数字或文本）
                # 先尝试提取数字
                num_match = re.search(r"(\d+(?:\.\d+)?)", text)
                if num_match:
                    extracted["value"] = float(num_match.group(1))
                else:
                    # 作为文本
                    extracted["value"] = text
        
        return extracted
    
    def _check_clarification_needed(self, result: IntentResult) -> IntentResult:
        """
        检查是否需要澄清
        """
        intent = result.intent
        params = result.extracted_params
        
        if intent == Intent.MODIFY:
            # 修改操作需要: 行号, 字段, 值
            missing = []
            if "row" not in params and "row_index" not in params and "target" not in params:
                missing.append("row_index")
            if "field" not in params and "col_key" not in params:
                missing.append("col_key")
            if "value" not in params:
                missing.append("value")
            
            if missing:
                result.needs_clarification = True
                if "row_index" in missing:
                    result.clarification_question = "请问是修改哪一行？"
                elif "col_key" in missing:
                    result.clarification_question = "请问是修改哪个字段？"
                else:
                    result.clarification_question = "请问要修改成什么值？"
        
        elif intent == Intent.DELETE:
            if "row" not in params and "row_index" not in params:
                result.needs_clarification = True
                result.clarification_question = "请问要删除哪一行？"
        
        return result
    
    def _keyword_fallback(self, text: str) -> Optional[IntentResult]:
        """
        关键词兜底检测
        """
        text_lower = text.lower()
        
        # 修改类关键词
        modify_keywords = ["改", "修改", "更改", "换成", "变成"]
        if any(kw in text_lower for kw in modify_keywords):
            return IntentResult(
                intent=Intent.MODIFY,
                confidence=0.6,
                matched_rule="keyword_modify",
                extracted_params={},
                needs_clarification=True,
                clarification_question="请问您想修改什么？"
            )
        
        # 添加类关键词
        add_keywords = ["添加", "新增", "加一", "补充"]
        if any(kw in text_lower for kw in add_keywords):
            return IntentResult(
                intent=Intent.ADD,
                confidence=0.6,
                matched_rule="keyword_add",
                extracted_params={},
                needs_clarification=True,
                clarification_question="请问要添加什么数据？"
            )
        
        # 删除类关键词
        delete_keywords = ["删除", "删掉", "移除", "去掉"]
        if any(kw in text_lower for kw in delete_keywords):
            return IntentResult(
                intent=Intent.DELETE,
                confidence=0.6,
                matched_rule="keyword_delete",
                extracted_params={},
                needs_clarification=True,
                clarification_question="请问要删除哪一行？"
            )
        
        # 查询类关键词
        query_keywords = ["有没有", "查一下", "搜索", "找"]
        if any(kw in text_lower for kw in query_keywords):
            return IntentResult(
                intent=Intent.QUERY_PRODUCT,
                confidence=0.6,
                matched_rule="keyword_query",
                extracted_params={},
                needs_clarification=True,
                clarification_question="请问要查询什么商品？"
            )
        
        # 计算类关键词
        calc_keywords = ["总共", "合计", "多少钱", "算一下"]
        if any(kw in text_lower for kw in calc_keywords):
            return IntentResult(
                intent=Intent.CALCULATE,
                confidence=0.7,
                matched_rule="keyword_calculate",
                extracted_params={},
                needs_clarification=False,
                clarification_question=None
            )
        
        return None


# ========== 兼容旧接口 ==========

# 全局分类器实例
_classifier = IntentClassifier()


async def classify_intent(
    text: str,
    task_type: str = None,
    use_llm: bool = False,
) -> Tuple[Intent, float]:
    """
    兼容旧接口的分类函数
    """
    # 文件提取任务
    if task_type == "extract":
        return Intent.EXTRACT, 1.0
    
    result = _classifier.classify(text)
    return result.intent, result.confidence


def get_agent_for_intent(intent: Intent) -> str:
    """
    根据意图获取对应的处理节点
    """
    routing = {
        # 操作类 → action_agent
        Intent.MODIFY: "action_agent",
        Intent.ADD: "action_agent",
        Intent.DELETE: "action_agent",
        Intent.CREATE_TABLE: "action_agent",
        
        # 查询类 → query_agent (或 fast_query)
        Intent.QUERY_PRODUCT: "query_agent",
        Intent.QUERY_TABLE: "query_agent",
        Intent.CALCULATE: "calculate_agent",
        
        # 提取类
        Intent.EXTRACT: "extract_agent",
        
        # 确认类
        Intent.CONFIRM: "confirm_handler",
        Intent.REJECT: "reject_handler",
        Intent.SUPPLEMENT: "supplement_handler",
        
        # 对话类
        Intent.GREETING: "chat_agent",
        Intent.HELP: "help_agent",
        Intent.CHAT: "chat_agent",
        
        Intent.UNKNOWN: "chat_agent",
    }
    return routing.get(intent, "chat_agent")


# 导出分类器实例
intent_classifier = _classifier
