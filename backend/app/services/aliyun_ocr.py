"""
阿里云 OCR 服务封装 - 使用 DashScope Qwen-VL 多模态能力
"""
import base64
from typing import Optional, Tuple, List
from app.core.config import settings
from app.core.logger import app_logger as logger
import dashscope
from dashscope import MultiModalConversation

# 导入手写提示模块
from app.services.handwriting_hints import HANDWRITING_HINTS_FOR_VL


class AliyunOCRService:
    """阿里云 OCR 服务 (基于 DashScope Qwen-VL)"""
    
    def __init__(self):
        """初始化 OCR 服务"""
        dashscope.api_key = settings.ALIYUN_ACCESS_KEY_ID
        logger.info("OCR 服务初始化完成 (使用 DashScope Qwen-VL)")
    
    async def recognize_general(
        self,
        image_data: bytes = None,
        image_url: str = None
    ) -> str:
        """
        通用文字识别 (使用 Qwen-VL 多模态模型)
        
        Args:
            image_data: 图片字节数据
            image_url: 图片URL（二选一）
            
        Returns:
            str: 识别的文字内容
        """
        try:
            # 构建图片输入
            if image_data:
                # 将字节数据转为 base64 data URI
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                image_input = f"data:image/jpeg;base64,{image_base64}"
            elif image_url:
                image_input = image_url
            else:
                raise ValueError("必须提供 image_data 或 image_url")
            
            # 构建多模态消息
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": image_input},
                        {"text": "请识别这张图片中的所有内容。如果包含表格或列表，请直接输出为 Markdown 表格格式。如果是键值对（如表单），也请整理为 Markdown 表格。保持原有内容的完整性。"}
                    ]
                }
            ]
            
            # 调用 Qwen-VL 模型
            response = MultiModalConversation.call(
                model=settings.ALIYUN_VL_MODEL,
                messages=messages
            )
            
            if response.status_code == 200:
                # 提取识别结果
                content = response.output.choices[0].message.content
                if isinstance(content, list):
                    # 可能返回列表格式
                    text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
                    result_text = "\n".join(text_parts)
                else:
                    result_text = str(content)
                
                logger.info(f"OCR 识别成功，提取文本长度: {len(result_text)}")
                return result_text
            else:
                logger.error(f"OCR 识别失败: {response.code} - {response.message}")
                raise Exception(f"OCR 识别失败: {response.message}")
                
        except Exception as e:
            logger.error(f"OCR 识别异常: {str(e)}")
            raise
    
    async def recognize_handwriting(
        self,
        image_data: bytes = None,
        image_url: str = None
    ) -> str:
        """
        手写文字识别 (使用 Qwen-VL 多模态模型)
        
        Args:
            image_data: 图片字节数据
            image_url: 图片URL
            
        Returns:
            str: 识别的手写文字
        """
        try:
            # 构建图片输入
            if image_data:
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                image_input = f"data:image/jpeg;base64,{image_base64}"
            elif image_url:
                image_input = image_url
            else:
                raise ValueError("必须提供 image_data 或 image_url")
            
            # 构建多模态消息 (专门针对手写体)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": image_input},
                        {"text": "请识别这张图片中的手写文字。请仔细辨认每个字，直接输出识别到的文字内容，保持原有格式，不要添加任何解释。"}
                    ]
                }
            ]
            
            response = MultiModalConversation.call(
                model=settings.ALIYUN_VL_MODEL,
                messages=messages
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if isinstance(content, list):
                    text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
                    result_text = "\n".join(text_parts)
                else:
                    result_text = str(content)
                
                logger.info(f"手写识别成功，提取文本长度: {len(result_text)}")
                return result_text
            else:
                logger.error(f"手写识别失败: {response.code}")
                raise Exception(f"手写识别失败: {response.message}")
                
        except Exception as e:
            logger.error(f"手写识别异常: {str(e)}")
            raise

    async def recognize_order_handwriting(
        self,
        image_data: bytes = None,
        image_url: str = None
    ) -> Tuple[str, List[str]]:
        """
        手写订单识别 (带手写简化字提示)
        
        专门用于识别手写的食品/商品订单，包含手写简化字识别指南。
        
        Args:
            image_data: 图片字节数据
            image_url: 图片URL
            
        Returns:
            Tuple[str, List[str]]: (识别结果文本, 识别备注列表)
        """
        try:
            # 构建图片输入
            if image_data:
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                image_input = f"data:image/jpeg;base64,{image_base64}"
            elif image_url:
                image_input = image_url
            else:
                raise ValueError("必须提供 image_data 或 image_url")
            
            # 构建带手写提示的 prompt
            prompt = f"""请识别这张图片中的手写订单内容。

{HANDWRITING_HINTS_FOR_VL}

【输出要求】
1. 如果内容是表格形式，请输出为 Markdown 表格
2. 如果是列表/清单形式，也请整理为 Markdown 表格（列: 序号, 商品名称, 数量, 单价, 备注）
3. 请根据上述手写简化字指南进行识别，将简写转换为标准字
4. 如有无法确定的字，请在【识别备注】中说明

【输出格式】
先输出识别结果（Markdown表格），然后另起一行输出：
【识别备注】无 或 【识别备注】xxx

示例：
| 序号 | 产品名称 | 数量 | 单价 |
|-----|---------|------|-----|
| 1 | 早餐大包 | 10 | 2 |

【识别备注】第1行"早餐"原文疑似简写"早歺"
"""
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": image_input},
                        {"text": prompt}
                    ]
                }
            ]
            
            response = MultiModalConversation.call(
                model=settings.ALIYUN_VL_MODEL,
                messages=messages
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if isinstance(content, list):
                    text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
                    result_text = "\n".join(text_parts)
                else:
                    result_text = str(content)
                
                # 解析识别备注
                notes = []
                if "【识别备注】" in result_text:
                    parts = result_text.split("【识别备注】")
                    result_text = parts[0].strip()
                    if len(parts) > 1:
                        note_text = parts[1].strip()
                        if note_text and note_text != "无":
                            notes = [note_text]
                
                logger.info(f"订单手写识别成功，文本长度: {len(result_text)}, 备注数: {len(notes)}")
                return result_text, notes
            else:
                logger.error(f"订单手写识别失败: {response.code}")
                raise Exception(f"订单手写识别失败: {response.message}")
                
        except Exception as e:
            logger.error(f"订单手写识别异常: {str(e)}")
            raise

    async def detect_content_type(
        self,
        image_data: bytes = None,
        image_url: str = None
    ) -> str:
        """
        检测图片内容类型（手写/打印/混合）
        
        Args:
            image_data: 图片字节数据
            image_url: 图片URL
            
        Returns:
            str: 'handwriting' | 'printed' | 'mixed'
        """
        try:
            if image_data:
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                image_input = f"data:image/jpeg;base64,{image_base64}"
            elif image_url:
                image_input = image_url
            else:
                raise ValueError("必须提供 image_data 或 image_url")
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": image_input},
                        {"text": "请判断这张图片中的文字是手写体还是打印体。只需回答一个词：handwriting（手写）、printed（打印）或 mixed（混合）。"}
                    ]
                }
            ]
            
            response = MultiModalConversation.call(
                model=settings.ALIYUN_VL_MODEL,
                messages=messages
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if isinstance(content, list):
                    text = content[0].get("text", "").lower() if content else ""
                else:
                    text = str(content).lower()
                
                if "handwriting" in text or "手写" in text:
                    return "handwriting"
                elif "printed" in text or "打印" in text:
                    return "printed"
                else:
                    return "mixed"
            else:
                logger.warning(f"内容类型检测失败，默认为 mixed")
                return "mixed"
                
        except Exception as e:
            logger.warning(f"内容类型检测异常: {str(e)}, 默认为 mixed")
            return "mixed"


# 全局单例
ocr_service = AliyunOCRService()
