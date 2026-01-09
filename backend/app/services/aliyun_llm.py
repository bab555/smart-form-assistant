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
    
    async def call_turbo_model(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        """
        调用 Turbo 模型（Qwen-Turbo）- 支持 messages 格式
        
        用于快速推理任务，如数据提取、结构化等
        
        Args:
            messages: 对话消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            str: 模型回复
        """
        try:
            response = dashscope.Generation.call(
                model=settings.ALIYUN_LLM_MODEL_CALIBRATION,  # 使用 Turbo 模型
                messages=messages,
                result_format='message',
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                logger.debug(f"Turbo 模型返回: {content[:100]}...")
                return content
            else:
                logger.error(f"Turbo 模型调用失败: {response.code}")
                raise Exception(f"Turbo 模型调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"Turbo 模型调用异常: {str(e)}")
            raise
    
    async def call_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        调用主控模型（带 Function Calling）
        
        Args:
            messages: 对话消息列表
            tools: 工具定义列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            Dict: {
                "content": str,  # 文本回复（可能为空）
                "tool_calls": List[Dict] or None  # 工具调用列表
            }
        """
        try:
            response = dashscope.Generation.call(
                model=settings.ALIYUN_LLM_MODEL_MAIN,
                messages=messages,
                tools=tools,
                result_format='message',
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            if response.status_code == 200:
                choice = response.output.choices[0]
                message = choice.message
                
                result = {
                    "content": message.content or "",
                    "tool_calls": None
                }
                
                # 检查是否有工具调用
                if hasattr(message, 'tool_calls') and message.tool_calls:
                    result["tool_calls"] = [
                        {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                        for tc in message.tool_calls
                    ]
                    logger.info(f"主控模型调用工具: {[tc['name'] for tc in result['tool_calls']]}")
                
                return result
            else:
                logger.error(f"主控模型(tools)调用失败: {response.code} - {response.message}")
                raise Exception(f"LLM调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"主控模型(tools)调用异常: {str(e)}")
            raise
    
    async def call_vl_model(
        self,
        image_url: Optional[str] = None,
        prompt: str = "请识别图片中的文字内容，保持原有格式",
        image_data: Optional[bytes] = None
    ) -> str:
        """
        调用视觉语言模型（Qwen-VL）
        
        Args:
            image_url: 图片URL
            prompt: 提示词
            image_data: 图片二进制数据（如果提供，将优先使用，转为base64）
            
        Returns:
            str: 识别结果
        """
        try:
            content_list = []
            
            if image_data:
                import base64
                base64_str = base64.b64encode(image_data).decode('utf-8')
                # 默认使用 png 格式头，大多数情况下通用
                final_image_url = f"data:image/png;base64,{base64_str}"
                content_list.append({"image": final_image_url})
            elif image_url:
                content_list.append({"image": image_url})
            else:
                raise ValueError("必须提供 image_url 或 image_data")
                
            content_list.append({"text": prompt})
            
            messages = [
                {
                    "role": "user",
                    "content": content_list
                }
            ]
            
            response = dashscope.MultiModalConversation.call(
                model=settings.ALIYUN_VL_MODEL,
                messages=messages
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if isinstance(content, list):
                    # 处理返回列表的情况
                    text_content = ""
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            text_content += item["text"]
                elif isinstance(content, dict):
                     text_content = content.get("text", "")
                else:
                    text_content = str(content) # 可能是纯字符串或者对象列表的第一个元素的 text 属性，视 SDK 版本
                    # 针对旧版 SDK 或特定返回结构的防御性处理
                    if hasattr(response.output.choices[0].message.content[0], "text"):
                         text_content = response.output.choices[0].message.content[0]["text"]

                # 清洗 Markdown 代码块
                text_content = text_content.replace("```json", "").replace("```", "").strip()
                
                logger.info(f"VL模型识别成功，内容长度: {len(text_content)}")
                return text_content
            else:
                logger.error(f"VL模型调用失败: {response.code} - {response.message}")
                raise Exception(f"VL模型调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"VL模型调用异常: {str(e)}")
            raise

    async def call_multimodal_model(self, image_data: bytes, prompt: str) -> str:
        """
        调用多模态模型（content_analyzer 专用别名）
        """
        return await self.call_vl_model(image_data=image_data, prompt=prompt)
    
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

