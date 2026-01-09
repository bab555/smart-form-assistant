"""
手写简化字映射与提示模块

用于提高 VL 模型对手写订单的识别准确率
"""

from typing import Dict, List, Tuple

# ============================================================
# 手写简化字映射表
# ============================================================

# 简化字 -> 可能的实际字
SIMPLIFIED_CHAR_MAP: Dict[str, List[str]] = {
    # 餐饮相关高频简写
    "歺": ["餐"],
    "饣": ["饭", "饺", "饼", "馒", "馄", "饮"],
    "氵": ["汤", "汁", "油", "酒", "海", "洋"],
    "扌": ["打", "拌", "拍", "捞", "搅"],
    "艹": ["菜", "草", "蔬", "蒜", "葱", "芹", "莴", "茄", "荷"],
    "钅": ["锅", "铁", "锡", "铝"],
    "亻": ["份", "做", "作"],
    "纟": ["红", "绿", "紫", "纯", "细", "绞"],
    "火": ["炒", "炖", "烧", "烤", "煮", "煎", "炸"],
    "月": ["肉", "肥", "腿", "腰", "肚", "肠"],
    
    # 形似字（容易混淆）
    "与": ["歺"],      # "与" 形似 "歺"
    "鸡": ["包"],      # 潦草时相似
    "角": ["鱼"],      # 连笔时相似
    "内": ["肉"],      # 缺两点
    "夂": ["冬"],
    "乚": ["乙", "已"],
}

# 反向映射：实际字 -> 可能的简写形式
ACTUAL_TO_SIMPLIFIED: Dict[str, List[str]] = {}
for simplified, actuals in SIMPLIFIED_CHAR_MAP.items():
    for actual in actuals:
        if actual not in ACTUAL_TO_SIMPLIFIED:
            ACTUAL_TO_SIMPLIFIED[actual] = []
        ACTUAL_TO_SIMPLIFIED[actual].append(simplified)


# ============================================================
# 常见手写混淆对
# ============================================================

CONFUSION_PAIRS: List[Tuple[str, str, str]] = [
    # (容易误识别的字, 实际可能是, 说明)
    ("与", "歺", "在食品订单中，'与'形状的字大概率是'歺'(餐)"),
    ("鸡", "包", "潦草手写时'包'可能被识别为'鸡'"),
    ("鱼", "角", "连笔的'鱼'可能被识别为'角'"),
    ("大", "太", "手写'太'的点可能不明显"),
    ("未", "末", "横的长短区分"),
    ("己", "已", "开口程度"),
    ("干", "千", "第一横的长度"),
    ("土", "士", "横的长短"),
    ("日", "曰", "宽窄比例"),
    ("贝", "见", "手写简化"),
]


# ============================================================
# 订单领域常见词汇
# ============================================================

COMMON_ORDER_WORDS = [
    # 餐类
    "早餐", "午餐", "晚餐", "夜宵", "加餐",
    # 主食
    "米饭", "面条", "馒头", "包子", "饺子", "馄饨", "面包", "烧饼",
    "大包", "小包", "肉包", "菜包", "豆沙包", "奶黄包",
    # 菜品
    "炒菜", "炖菜", "凉菜", "热菜", "汤菜",
    "青菜", "白菜", "菠菜", "芹菜", "生菜", "油菜",
    "猪肉", "牛肉", "羊肉", "鸡肉", "鱼肉", "虾仁",
    "豆腐", "鸡蛋", "土豆", "番茄", "茄子", "黄瓜",
    # 汤类
    "米汤", "菜汤", "肉汤", "骨汤", "紫菜汤", "蛋花汤",
    # 饮品
    "豆浆", "牛奶", "果汁", "茶水", "饮料", "矿泉水",
    # 单位
    "份", "碗", "盘", "杯", "瓶", "个", "块", "斤", "两",
]


# ============================================================
# VL 模型提示文本
# ============================================================

HANDWRITING_HINTS_FOR_VL = """
【手写简化字识别指南】

在手写订单中，以下简化写法非常常见，请特别注意：

1. 高频简写字：
   - "歺" = "餐"（极简写法，只保留左上部分）
   - "饣" = 食字旁，常见于：饭、饺、饼、馒头、馄饨
   - "氵" = 三点水，常见于：汤、汁、油、酒
   - "艹" = 草字头，常见于：菜、葱、蒜、芹菜
   - "火" 旁 = 炒、炖、烧、烤、煮、煎

2. 形似字注意（按食品订单语境优先判断）：
   - 形似 "与" 的字 → 大概率是 "歺"（餐）
   - 形似 "鸡" 的潦草字 → 可能是 "包"
   - 形似 "内" 少两点 → 可能是 "肉"
   
3. 常见订单词汇参考：
   早餐、午餐、晚餐、大包、小包、馒头、饺子、面条、米饭、
   炒菜、青菜、猪肉、鸡蛋、豆腐、土豆、番茄、豆浆、牛奶...

4. 识别原则：
   - 优先往食品/商品名方向理解
   - 遇到无法确定的字，结合上下文推断
   - 如 "早歺大包" 应识别为 "早餐大包"
"""


# ============================================================
# 辅助函数
# ============================================================

def get_possible_corrections(char: str) -> List[str]:
    """
    获取某个字可能的正确形式
    
    Args:
        char: 识别出的字符
        
    Returns:
        可能的正确字符列表
    """
    return SIMPLIFIED_CHAR_MAP.get(char, [])


def get_possible_simplifications(char: str) -> List[str]:
    """
    获取某个字可能的简写形式
    
    Args:
        char: 标准字符
        
    Returns:
        可能的简写形式列表
    """
    return ACTUAL_TO_SIMPLIFIED.get(char, [])


def analyze_text_for_hints(text: str) -> List[Dict]:
    """
    分析文本中可能的简写字
    
    Args:
        text: OCR 识别结果文本
        
    Returns:
        可能的简写字分析结果
    """
    hints = []
    
    for i, char in enumerate(text):
        corrections = get_possible_corrections(char)
        if corrections:
            hints.append({
                "position": i,
                "original": char,
                "possible": corrections,
                "context": text[max(0, i-2):min(len(text), i+3)]
            })
    
    return hints


def enhance_ocr_result(text: str) -> Tuple[str, List[str]]:
    """
    尝试增强 OCR 结果（基于简写映射）
    
    Args:
        text: 原始 OCR 结果
        
    Returns:
        (增强后文本, 修改说明列表)
    """
    result = list(text)
    changes = []
    
    for i, char in enumerate(text):
        corrections = get_possible_corrections(char)
        if corrections and len(corrections) == 1:
            # 只有一个可能的校正，自动替换
            old_char = char
            new_char = corrections[0]
            result[i] = new_char
            changes.append(f"'{old_char}' → '{new_char}'")
    
    return ''.join(result), changes


# ============================================================
# 校对阈值配置
# ============================================================

class CalibrationThresholds:
    """校对置信度阈值配置"""
    
    # 高置信度：直接确认
    HIGH = 0.85
    
    # 中等置信度：给出建议
    MEDIUM = 0.6
    
    # 低置信度：列出候选
    LOW = 0.4
    
    # 极低置信度：提示手动校对
    MINIMUM = 0.3
    
    @classmethod
    def get_level(cls, score: float) -> str:
        """
        根据分数获取置信度等级
        
        Args:
            score: 置信度分数 0-1
            
        Returns:
            等级: 'high', 'medium', 'low', 'none'
        """
        if score >= cls.HIGH:
            return 'high'
        elif score >= cls.MEDIUM:
            return 'medium'
        elif score >= cls.LOW:
            return 'low'
        else:
            return 'none'

