"""
阿里云 DashScope LLM 服务封装
"""
import dashscope
from typing import List, Dict, Any, Optional, AsyncGenerator
from app.core.config import settings
from app.core.logger import app_logger as logger


class AliyunLLMService:
    """阿里云大语言模型服务"""
    
    def __init__(self):
        """初始化服务"""
        # DashScope 使用 sk-...（百炼 API Key）
        api_key = settings.DASHSCOPE_API_KEY
        if not api_key and settings.ALIYUN_ACCESS_KEY_ID.startswith("sk-"):
            # 兼容旧配置：如果用户仍把 sk-... 放在 ALIYUN_ACCESS_KEY_ID
            api_key = settings.ALIYUN_ACCESS_KEY_ID

        if not api_key:
            logger.warning("⚠️ 未配置 DASHSCOPE_API_KEY（sk-...），DashScope LLM 调用将不可用")
        dashscope.api_key = api_key
        logger.info("阿里云 LLM 服务初始化完成")

    async def warmup(self) -> None:
        """
        启动预热：提前完成依赖加载/首个请求的握手开销
        """
        if not dashscope.api_key: return

        try:
            # 轻量 warmup
            await self.call_main_model(
                messages=[{"role": "user", "content": "ping"}],
                temperature=0.0,
                max_tokens=1,
            )
            logger.info("✅ LLM 模型预热完成")
        except Exception as e:
            logger.warning(f"⚠️ LLM 模型预热失败（忽略）: {str(e)}")
    
    # ================= 标准非流式调用 =================

    async def call_main_model(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """调用主控大模型（Qwen-Max）"""
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
                return content
            else:
                logger.error(f"主控模型调用失败: {response.code} - {response.message}")
                raise Exception(f"LLM调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"主控模型调用异常: {str(e)}")
            raise
    
    async def call_calibration_model(self, prompt: str, temperature: float = 0.3) -> str:
        """调用校对模型"""
        try:
            messages = [{"role": "user", "content": prompt}]
            response = dashscope.Generation.call(
                model=settings.ALIYUN_LLM_MODEL_CALIBRATION,
                messages=messages,
                result_format='message',
                temperature=temperature,
                stream=False
            )
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise Exception(f"Calibration Error: {response.message}")
        except Exception as e:
            logger.error(f"Calibration Exception: {e}")
            raise

    async def call_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """调用主控模型（带 Function Calling）"""
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
                    "content": getattr(message, "content", "") or "",
                    "tool_calls": None
                }
                
                # 安全获取 tool_calls
                raw_tool_calls = None
                try:
                    raw_tool_calls = getattr(message, 'tool_calls', None)
                except Exception:
                    if isinstance(message, dict):
                        raw_tool_calls = message.get('tool_calls')

                if raw_tool_calls:
                    parsed_tool_calls = []
                    for tc in raw_tool_calls:
                        if isinstance(tc, dict):
                            func = tc.get("function", {})
                            parsed_tool_calls.append({
                                "name": func.get("name", ""),
                                "arguments": func.get("arguments", {})
                            })
                        else:
                            # 对象格式
                            try:
                                func = getattr(tc, 'function', None)
                                if func:
                                    parsed_tool_calls.append({
                                        "name": getattr(func, 'name', ""),
                                        "arguments": getattr(func, 'arguments', {})
                                    })
                            except Exception:
                                pass

                    result["tool_calls"] = parsed_tool_calls
                
                return result
            else:
                logger.error(f"Tool Call Failed: {response.code} - {response.message}")
                raise Exception(f"LLM调用失败: {response.message}")
                
        except Exception as e:
            logger.error(f"Tool Call Exception: {str(e)}")
            raise
    
    async def call_vl_model(
        self,
        image_url: Optional[str] = None,
        prompt: str = "请识别图片中的文字内容，保持原有格式",
        image_data: Optional[bytes] = None
    ) -> str:
        """调用视觉语言模型（Qwen-VL）"""
        try:
            content_list = []
            if image_data:
                import base64
                base64_str = base64.b64encode(image_data).decode('utf-8')
                final_image_url = f"data:image/png;base64,{base64_str}"
                content_list.append({"image": final_image_url})
            elif image_url:
                content_list.append({"image": image_url})
            else:
                raise ValueError("必须提供 image_url 或 image_data")
                
            content_list.append({"text": prompt})
            
            messages = [{"role": "user", "content": content_list}]
            
            response = dashscope.MultiModalConversation.call(
                model=settings.ALIYUN_VL_MODEL,
                messages=messages
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if isinstance(content, list):
                    text_content = ""
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            text_content += item["text"]
                elif isinstance(content, dict):
                     text_content = content.get("text", "")
                else:
                    text_content = str(content)
                    if hasattr(response.output.choices[0].message.content[0], "text"):
                         text_content = response.output.choices[0].message.content[0]["text"]

                # 清洗
                text_content = text_content.replace("```json", "").replace("```", "").strip()
                return text_content
            else:
                raise Exception(f"VL Failed: {response.message}")
                
        except Exception as e:
            logger.error(f"VL Exception: {str(e)}")
            raise

    # ================= 新增：DashScope 原生流式调用 =================

    async def stream_chat_with_thinking(
        self,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        thinking_budget: int = 50
    ) -> AsyncGenerator[Dict, None]:
        """
        流式对话 (支持 Thinking + Content + Tools)
        
        策略：
        - 流式输出 thinking 和 content
        - 收集 tool_calls，在流式结束时通过 finish 事件一次性返回
        - 上层只需一次调用，无需双重请求
        """
        try:
            # 构造参数
            kwargs = {
                "model": settings.ALIYUN_LLM_MODEL_MAIN,
                "messages": messages,
                "result_format": "message",
                "stream": True,
                "incremental_output": True,
            }
            
            # 只有部分模型支持 enable_thinking
            if thinking_budget > 0:
                kwargs["enable_thinking"] = True
                kwargs["thinking_budget"] = thinking_budget
            
            if tools:
                kwargs["tools"] = tools

            logger.info(f"[Stream] 调用参数: model={kwargs.get('model')}, enable_thinking={kwargs.get('enable_thinking')}, tools={bool(tools)}")
            
            responses = dashscope.Generation.call(**kwargs)

            # 增量累积：tool_calls 按 index 分组累积 arguments
            tool_calls_accumulator: Dict[int, Dict] = {}  # index -> {id, name, arguments}
            finish_reason = None
            chunk_count = 0

            for response in responses:
                chunk_count += 1
                if response.status_code != 200:
                    logger.error(f"Stream Error: {response.code} - {response.message}")
                    yield {"type": "error", "content": response.message}
                    continue

                choice = response.output.choices[0]
                message = choice.message
                finish_reason = choice.finish_reason
                
                # 调试：打印前3个chunk的完整message结构
                if chunk_count <= 3:
                    try:
                        if hasattr(message, '__dict__'):
                            msg_dict = {k: v for k, v in vars(message).items() if not k.startswith('_')}
                        else:
                            msg_dict = dict(message) if isinstance(message, dict) else str(message)
                        logger.info(f"[Stream] Chunk {chunk_count} message: {msg_dict}")
                    except Exception as e:
                        logger.info(f"[Stream] Chunk {chunk_count} message (raw): {message}, error: {e}")
                
                # message 可能是对象或字典，统一处理
                def safe_get(obj, key, default=None):
                    if isinstance(obj, dict):
                        return obj.get(key, default)
                    return getattr(obj, key, default)
                
                reasoning_content = safe_get(message, "reasoning_content") or ""
                content_str = safe_get(message, "content") or ""

                # 严格按照官方文档逻辑判断
                # 1. 思考过程：reasoning_content 不为空 且 content 为空
                if reasoning_content and not content_str:
                    logger.info(f"[Stream] Got reasoning: {reasoning_content[:50]}...")
                    yield {"type": "thinking", "content": reasoning_content}
                
                # 2. 回复过程：content 不为空
                elif content_str:
                    yield {"type": "content", "content": content_str}
                
                # 3. 工具调用 (保持原逻辑)
                tc_list = safe_get(message, "tool_calls")
                if tc_list:
                    for tc in tc_list:
                        if isinstance(tc, dict):
                            idx = tc.get("index", 0)
                            tc_id = tc.get("id", "")
                            func = tc.get("function", {})
                            func_name = func.get("name", "")
                            func_args = func.get("arguments", "")
                        else:
                            idx = getattr(tc, "index", 0)
                            tc_id = getattr(tc, "id", "")
                            func = getattr(tc, "function", None)
                            func_name = getattr(func, "name", "") if func else ""
                            func_args = getattr(func, "arguments", "") if func else ""
                        
                        # 累积
                        if idx not in tool_calls_accumulator:
                            tool_calls_accumulator[idx] = {"id": tc_id, "name": func_name, "arguments": ""}
                        if tc_id:
                            tool_calls_accumulator[idx]["id"] = tc_id
                        if func_name:
                            tool_calls_accumulator[idx]["name"] = func_name
                        if func_args:
                            tool_calls_accumulator[idx]["arguments"] += func_args

            logger.info(f"[Stream] 完成: chunks={chunk_count}, finish_reason={finish_reason}, accumulated_tools={tool_calls_accumulator}")

            # 流式结束：返回 finish 事件，包含完整的 tool_calls
            parsed_tools = []
            for idx in sorted(tool_calls_accumulator.keys()):
                tc_data = tool_calls_accumulator[idx]
                if tc_data.get("name"):
                    parsed_tools.append({
                        "name": tc_data["name"],
                        "arguments": tc_data.get("arguments", "")
                    })
            
            if parsed_tools:
                logger.info(f"[Stream] 解析后工具: {parsed_tools}")

            yield {
                "type": "finish",
                "finish_reason": finish_reason,
                "tool_calls": parsed_tools if parsed_tools else None
            }

        except Exception as e:
            logger.error(f"Stream Chat Exception: {e}")
            yield {"type": "error", "content": str(e)}

    async def stream_extraction(self, prompt: str, system_prompt: str) -> AsyncGenerator[str, None]:
        """
        流式提取 (用于文件/文本解析)
        强制输出 JSON Lines
        """
        try:
            responses = dashscope.Generation.call(
                model=settings.ALIYUN_LLM_MODEL_MAIN,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                result_format="message",
                stream=True,
                incremental_output=True,
                temperature=0.1 # 低温，保证 JSON 格式
            )

            for response in responses:
                if response.status_code == 200:
                    content = response.output.choices[0].message.content
                    if content:
                        yield content
                else:
                    logger.error(f"Extraction Stream Error: {response.message}")
                    
        except Exception as e:
            logger.error(f"Extraction Exception: {e}")
            raise

    # 兼容性别名
    async def call_multimodal_model(self, image_data: bytes, prompt: str) -> str:
        return await self.call_vl_model(image_data=image_data, prompt=prompt)
    
    async def get_embedding(self, text: str, text_type: str = "query") -> List[float]:
        try:
            response = dashscope.TextEmbedding.call(
                model=settings.ALIYUN_EMBEDDING_MODEL,
                input=text,
                text_type=text_type
            )
            if response.status_code == 200:
                return response.output['embeddings'][0]['embedding']
            else:
                raise Exception(f"Embedding Error: {response.message}")
        except Exception as e:
            logger.error(f"Embedding Exception: {str(e)}")
            raise
    
    async def batch_get_embeddings(self, texts: List[str], text_type: str = "document") -> List[List[float]]:
        embeddings = []
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
                else:
                    raise Exception(f"Batch Embedding Error: {response.message}")
            except Exception as e:
                logger.error(f"Batch Embedding Exception: {str(e)}")
                raise
        return embeddings

llm_service = AliyunLLMService()
