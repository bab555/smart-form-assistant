"""
阿里云 DashScope LLM 服务封装
"""
import dashscope
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logger import app_logger as logger


class AliyunLLMService:
    """阿里云大语言模型服务"""
    
    def __init__(self):
        """初始化服务"""
        dashscope.api_key = settings.ALIYUN_ACCESS_KEY_ID
        logger.info("阿里云 LLM 服务初始化完成")
    
    async def call_main_model(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        调用主控大模型（Qwen-Max）
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            str: 模型回复内容
        """
        try:
            response = dashscope.Generation.call(
                model=settings.ALIYUN_LLM_MODEL_MAIN,
                messages=messages,
                result_format='message',
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                logger.debug(f"主控模型返回: {content[:100]}...")
                return content
            else:
                logger.error(f"主控模型调用失败: {response.code} - {response.message}")
                raise Exception(f"LLM调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"主控模型调用异常: {str(e)}")
            raise
    
    async def call_calibration_model(
        self,
        prompt: str,
        temperature: float = 0.3
    ) -> str:
        """
        调用校对模型（Qwen-Turbo）- 快速推理
        
        Args:
            prompt: 提示词
            temperature: 温度参数（较低以保证稳定性）
            
        Returns:
            str: 模型回复
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            
            response = dashscope.Generation.call(
                model=settings.ALIYUN_LLM_MODEL_CALIBRATION,
                messages=messages,
                result_format='message',
                temperature=temperature,
                max_tokens=500,
                stream=False
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                logger.debug(f"校对模型返回: {content[:100]}...")
                return content
            else:
                logger.error(f"校对模型调用失败: {response.code}")
                raise Exception(f"校对模型调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"校对模型调用异常: {str(e)}")
            raise
    
    async def call_vl_model(
        self,
        image_url: str,
        prompt: str = "请识别图片中的文字内容，保持原有格式"
    ) -> str:
        """
        调用视觉语言模型（Qwen-VL）
        
        Args:
            image_url: 图片URL或base64
            prompt: 提示词
            
        Returns:
            str: 识别结果
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": image_url},
                        {"text": prompt}
                    ]
                }
            ]
            
            response = dashscope.MultiModalConversation.call(
                model=settings.ALIYUN_VL_MODEL,
                messages=messages
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content[0]["text"]
                logger.info(f"VL模型识别成功，内容长度: {len(content)}")
                return content
            else:
                logger.error(f"VL模型调用失败: {response.code}")
                raise Exception(f"VL模型调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"VL模型调用异常: {str(e)}")
            raise
    
    async def get_embedding(
        self,
        text: str,
        text_type: str = "query"
    ) -> List[float]:
        """
        获取文本嵌入向量
        
        Args:
            text: 输入文本
            text_type: 文本类型（query/document）
            
        Returns:
            List[float]: 嵌入向量
        """
        try:
            response = dashscope.TextEmbedding.call(
                model=settings.ALIYUN_EMBEDDING_MODEL,
                input=text,
                text_type=text_type
            )
            
            if response.status_code == 200:
                embedding = response.output['embeddings'][0]['embedding']
                logger.debug(f"获取嵌入向量成功，维度: {len(embedding)}")
                return embedding
            else:
                logger.error(f"嵌入向量调用失败: {response.code}")
                raise Exception(f"嵌入向量调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"嵌入向量调用异常: {str(e)}")
            raise
    
    async def batch_get_embeddings(
        self,
        texts: List[str],
        text_type: str = "document"
    ) -> List[List[float]]:
        """
        批量获取文本嵌入向量
        
        Args:
            texts: 文本列表
            text_type: 文本类型
            
        Returns:
            List[List[float]]: 嵌入向量列表
        """
        embeddings = []
        
        # 批量处理，每批25条
        batch_size = 25
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            try:
                response = dashscope.TextEmbedding.call(
                    model=settings.ALIYUN_EMBEDDING_MODEL,
                    input=batch,
                    text_type=text_type
                )
                
                if response.status_code == 200:
                    batch_embeddings = [emb['embedding'] for emb in response.output['embeddings']]
                    embeddings.extend(batch_embeddings)
                    logger.debug(f"批量嵌入 {len(batch)} 条文本成功")
                else:
                    logger.error(f"批量嵌入失败: {response.code}")
                    raise Exception(f"批量嵌入失败: {response.message}")
                    
            except Exception as e:
                logger.error(f"批量嵌入异常: {str(e)}")
                raise
        
        return embeddings


# 全局单例
llm_service = AliyunLLMService()

