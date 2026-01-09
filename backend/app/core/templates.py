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
    field_lower = field.lower().strip()
    
    for standard_name, aliases in FIELD_ALIASES.items():
        if field_lower == standard_name:
            return standard_name
        for alias in aliases:
            if alias.lower() == field_lower: # 精确匹配优先
                return standard_name
    
    # 模糊匹配
    for standard_name, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias.lower() in field_lower:
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
    mapped = create_empty_row()
    
    for key, value in row.items():
        normalized = normalize_field_name(key)
        # 即使 normalized 是 "单价" 或 "总价"，如果 Schema 里没这俩字段，也会被忽略吗？
        # mapped 是基于 create_empty_row 的，如果 Schema 只有 品名/数量... 
        # 那么 "单价" 不会进去。
        # 但为了保留数据，我们可以允许动态扩充，或者严格遵守 Schema。
        # 根据 Phase 2.1 需求："固定 Schema"，所以这里只保留 Schema 内字段。
        if normalized in mapped:
            mapped[normalized] = value
    
    return mapped


# ========== LLM 提示词模板 ==========

UNSTRUCTURED_EXTRACTION_PROMPT = """你是一个订单录入助手。请从以下文本中提取订单商品信息。

目标字段（严格按此顺序提取）：
- 序号：如有编号提取，无则留空
- 识别商品：商品名称（原始识别结果）
- 规格：商品规格描述
- 单位：计量单位（如斤、个、箱）
- 数量：数量数值
- 备注：其他附加信息

文本内容：
{text}

请输出 JSON 数组，每个商品一个对象：
```json
[
  {{"序号": "1", "识别商品": "土豆", "规格": "大", "单位": "斤", "数量": 50, "备注": "要新鲜的"}},
  ...
]
```

规则：
1. 如果某字段找不到，留空字符串 ""
2. 数量尽量转为数字
3. 如果有多个商品，提取所有
4. 只输出 JSON，不要解释"""


