"""
通用辅助函数
"""
import uuid
import base64
from datetime import datetime
from typing import Dict, Any
import Levenshtein


def generate_uuid() -> str:
    """生成 UUID"""
    return str(uuid.uuid4())


def generate_trace_id() -> str:
    """生成追踪ID"""
    return f"trace_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def snake_to_camel(snake_str: str) -> str:
    """snake_case 转 camelCase"""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_to_snake(camel_str: str) -> str:
    """camelCase 转 snake_case"""
    import re
    return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()


def keys_to_camel(data: Any) -> Any:
    """递归转换字典键为 camelCase"""
    if isinstance(data, dict):
        return {snake_to_camel(k): keys_to_camel(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [keys_to_camel(item) for item in data]
    else:
        return data


def keys_to_snake(data: Any) -> Any:
    """递归转换字典键为 snake_case"""
    if isinstance(data, dict):
        return {camel_to_snake(k): keys_to_snake(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [keys_to_snake(item) for item in data]
    else:
        return data


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度（Levenshtein距离）
    返回 0.0 - 1.0 之间的相似度分数
    """
    if not text1 or not text2:
        return 0.0
    
    distance = Levenshtein.distance(text1, text2)
    max_len = max(len(text1), len(text2))
    
    if max_len == 0:
        return 1.0
    
    similarity = 1.0 - (distance / max_len)
    return max(0.0, min(1.0, similarity))


def encode_image_to_base64(image_path: str) -> str:
    """将图片文件编码为 base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def decode_base64_to_bytes(base64_str: str) -> bytes:
    """将 base64 字符串解码为字节"""
    return base64.b64decode(base64_str)


def format_timestamp(dt: datetime = None) -> str:
    """格式化时间戳为 ISO 8601"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def validate_confidence(score: float) -> float:
    """验证并规范化置信度分数"""
    return max(0.0, min(1.0, float(score)))

