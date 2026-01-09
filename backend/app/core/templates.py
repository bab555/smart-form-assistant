"""
基础表格模板定义

用途：
1. 新建表格时的默认 schema
2. 非结构化文本提取时的目标字段
3. 校对时的标准字段映射
"""
from typing import List, Dict, Any


# ========== 基础模板（标准订单格式） ==========

DEFAULT_SCHEMA: List[Dict[str, str]] = [
    {"key": "序号", "title": "序号", "type": "text"},
    {"key": "识别商品", "title": "识别商品", "type": "text"},
    {"key": "订单商品", "title": "订单商品", "type": "text"},
    {"key": "规格", "title": "规格", "type": "text"},
    {"key": "单位", "title": "单位", "type": "text"},
    {"key": "数量", "title": "数量", "type": "number"},
    {"key": "备注", "title": "备注", "type": "text"},
]

# 基础模板的表头（用于 LLM 提取）
# 注意：订单商品是后端校对生成的，不需要提取
DEFAULT_HEADERS = ["序号", "识别商品", "规格", "单位", "数量", "备注"]

# 字段别名映射（OCR 可能识别出的不同写法）
FIELD_ALIASES = {
    "序号": ["序号", "编号", "行号", "index", "no", "no.", "#"],
    "识别商品": ["识别商品", "品名", "商品名", "商品名称", "名称", "产品", "产品名", "品种", "货物", "物品", "商品"],
    "订单商品": ["订单商品", "校对商品", "标准商品", "规范商品", "匹配商品"],
    "数量": ["数量", "数目", "件数", "个数", "份数", "qty", "quantity", "count"],
    "单位": ["单位", "计量单位", "unit", "uom"],
    "规格": ["规格", "规格型号", "型号", "大小", "尺寸", "包装", "spec", "specification"],
    "备注": ["备注", "说明", "注释", "note", "comment", "remark", "remarks"],
    "单价": ["单价", "价格", "单位价格", "单位价", "price", "unit_price"], # 保留别名，用于后续扩展
    "总价": ["总价", "金额", "总金额", "小计", "合计", "total", "amount", "total_price"], # 同上
}


# ========== 空行模板 ==========

def create_empty_row() -> Dict[str, Any]:
    """创建一个空行（基于基础模板）"""
    return {
        "序号": "",
        "识别商品": "",
        "订单商品": "",
        "规格": "",
        "单位": "",
        "数量": "",
        "备注": "",
    }


# ========== 字段匹配 ==========

def normalize_field_name(field: str) -> str:
    """
    将字段名标准化为基础模板的字段名
    
    Args:
        field: 原始字段名
        
    Returns:
        标准化后的字段名，如果无法匹配则返回原字段名
    """
    field_stripped = field.strip()
    field_lower = field_stripped.lower()
    
    # 精确匹配（中文直接比较，英文忽略大小写）
    for standard_name, aliases in FIELD_ALIASES.items():
        # 直接匹配标准名
        if field_stripped == standard_name:
            return standard_name
        # 匹配别名列表
        for alias in aliases:
            if field_stripped == alias or field_lower == alias.lower():
                return standard_name
    
    # 模糊匹配（包含关系）
    # 注意：这里不要用过短/过泛的别名（例如“商品”）做包含匹配，否则会把“订单商品”误归为“识别商品”，
    # 导致在 map_row_to_template 时用空的“订单商品”覆盖“识别商品”。
    generic_aliases = {"商品", "产品", "物品", "货物"}
    for standard_name, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if not alias:
                continue
            if alias in generic_aliases:
                continue
            if len(alias) < 3:
                continue
            if alias in field_stripped or alias.lower() in field_lower:
                return standard_name
                
    return field


def map_row_to_template(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    将一行数据映射到基础模板的字段
    
    Args:
        row: 原始行数据
        
    Returns:
        映射后的行数据
    """
    from app.core.logger import app_logger as logger
    
    mapped = create_empty_row()
    
    for key, value in row.items():
        normalized = normalize_field_name(key)
        logger.debug(f"[Map] '{key}' -> '{normalized}' (in mapped: {normalized in mapped})")
        if normalized in mapped:
            mapped[normalized] = value
        else:
            logger.warning(f"[Map] Field '{key}' (normalized: '{normalized}') not in schema, ignored")
    
    return mapped


# ========== LLM 提示词模板 ==========

# 提取提示词：让模型自己理解内容含义
EXTRACTION_PROMPT = """请阅读以下文本，找出其中的**商品信息**。

你需要理解文本内容，识别出：
- 哪些是**商品名称**（如：海天老抽、白醋、酱油、生抽、味事达、料酒、土豆、白菜、鸡蛋等食品/物品的名字）
- 哪些是**规格**（如：500ml、1.9L、2.7千克 等容量/重量描述）
- 哪些是**单位**（如：瓶、箱、桶、斤、袋、个 等计量单位）
- 哪些是**数量**（购买的数目）

文本内容：
{text}

请输出 JSON 数组，每个商品一条记录：
```json
[
  {{"序号": "1", "识别商品": "海天老抽", "规格": "1.9L", "单位": "瓶", "数量": 5, "备注": ""}},
  {{"序号": "2", "识别商品": "白醋", "规格": "500ml", "单位": "瓶", "数量": 3, "备注": ""}}
]
```

注意：
1. "识别商品"填的是具体商品名字（如"海天老抽"、"白醋"），不是"商品名称"这四个字
2. 如果某信息找不到，留空 ""
3. 数量是数字，找不到填 0
4. 只输出 JSON，不要解释"""


# 手写体校对提示词：基于候选列表推断
HANDWRITING_CALIBRATION_PROMPT = """你是商品名称校对专家。用户手写的商品名可能有错别字或简写，请根据候选列表推断最可能的商品。

【识别结果】{recognized_name}
【候选商品】
{candidates}

【任务】
1. 分析"识别结果"与每个候选的相似度（考虑：字形相似、读音相近、常见简写）
2. 选择最可能的 1-3 个结果

【输出格式】
如果能确定匹配，输出：{{"match": "匹配的商品名", "confidence": "高/中/低"}}
如果有多个可能，输出：{{"candidates": ["候选1", "候选2"], "confidence": "低"}}
如果完全无法匹配，输出：{{"match": null, "note": "未找到匹配商品"}}

只输出 JSON。"""


# 保留旧名称兼容
UNSTRUCTURED_EXTRACTION_PROMPT = EXTRACTION_PROMPT


