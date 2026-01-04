"""
阿里云 OCR 服务封装 - 使用 DashScope Qwen-VL 多模态能力
"""
import base64
from typing import Optional
from app.core.config import settings
from app.core.logger import app_logger as logger
import dashscope
from dashscope import MultiModalConversation


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
                        {"text": "请识别这张图片中的所有文字内容。请直接输出识别到的文字，保持原有格式和换行，不要添加任何解释或说明。"}
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


# 全局单例
ocr_service = AliyunOCRService()
