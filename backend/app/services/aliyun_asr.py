"""
DashScope 语音识别服务

使用阿里云 DashScope 的 qwen3-asr-flash-realtime 模型
基于 WebSocket 实时流式识别
"""
import base64
import json
import asyncio
from typing import Optional
import websockets
from app.core.config import settings
from app.core.logger import app_logger as logger


class DashScopeASRService:
    """DashScope 实时语音识别服务 (WebSocket)"""
    
    def __init__(self):
        """初始化 ASR 服务"""
        # DashScope 使用 sk-...（百炼 API Key）
        self.api_key = settings.DASHSCOPE_API_KEY or (settings.ALIYUN_ACCESS_KEY_ID if settings.ALIYUN_ACCESS_KEY_ID.startswith("sk-") else "")
        self.model = settings.ALIYUN_ASR_MODEL
        self.base_url = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        logger.info(f"DashScope ASR 服务初始化完成，模型: {self.model}")
    
    async def recognize_audio(
        self,
        audio_data: bytes,
        format: str = "pcm",
        sample_rate: int = 16000,
        language: str = "zh"
    ) -> str:
        """
        识别音频数据
        
        Args:
            audio_data: 音频字节数据（PCM 格式最佳）
            format: 音频格式（pcm/wav/webm）
            sample_rate: 采样率，默认 16000
            language: 语言，默认中文
            
        Returns:
            str: 识别的文本
        """
        if not self.api_key:
            logger.error("ALIYUN_ACCESS_KEY_ID 未配置")
            return "语音识别服务未配置"
        
        url = f"{self.base_url}?model={self.model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        recognized_text = ""
        
        try:
            async with websockets.connect(url, extra_headers=headers) as ws:
                logger.info(f"[ASR] WebSocket 已连接")
                
                # 1. 发送会话配置（启用服务端 VAD）
                session_update = {
                    "event_id": "event_session",
                    "type": "session.update",
                    "session": {
                        "modalities": ["text"],
                        "input_audio_format": format,
                        "sample_rate": sample_rate,
                        "input_audio_transcription": {
                            "language": language,
                        },
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.2,
                            "silence_duration_ms": 800
                        }
                    }
                }
                await ws.send(json.dumps(session_update))
                logger.debug(f"[ASR] 发送会话配置")
                
                # 2. 分块发送音频数据
                chunk_size = 3200  # 每次发送 3200 字节（100ms 的 16kHz PCM）
                total_chunks = (len(audio_data) + chunk_size - 1) // chunk_size
                
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i + chunk_size]
                    encoded_chunk = base64.b64encode(chunk).decode('utf-8')
                    
                    audio_event = {
                        "event_id": f"event_audio_{i}",
                        "type": "input_audio_buffer.append",
                        "audio": encoded_chunk
                    }
                    await ws.send(json.dumps(audio_event))
                    
                    # 模拟实时发送，但可以加快
                    await asyncio.sleep(0.01)
                
                logger.info(f"[ASR] 音频数据发送完成，共 {total_chunks} 块")
                
                # 3. 发送提交信号
                commit_event = {
                    "event_id": "event_commit",
                    "type": "input_audio_buffer.commit"
                }
                await ws.send(json.dumps(commit_event))
                
                # 4. 接收识别结果
                timeout = 10  # 10秒超时
                start_time = asyncio.get_event_loop().time()
                
                while True:
                    try:
                        # 设置接收超时
                        remaining = timeout - (asyncio.get_event_loop().time() - start_time)
                        if remaining <= 0:
                            logger.warning("[ASR] 接收超时")
                            break
                        
                        message = await asyncio.wait_for(ws.recv(), timeout=remaining)
                        data = json.loads(message)
                        event_type = data.get("type", "")
                        
                        logger.debug(f"[ASR] 收到事件: {event_type}")
                        
                        # 处理转写结果
                        if event_type == "conversation.item.input_audio_transcription.completed":
                            transcript = data.get("transcript", "")
                            if transcript:
                                recognized_text = transcript
                                logger.info(f"[ASR] 识别完成: {recognized_text}")
                            break
                        
                        # 处理增量转写
                        elif event_type == "conversation.item.input_audio_transcription.delta":
                            delta = data.get("delta", "")
                            recognized_text += delta
                        
                        # 处理错误
                        elif event_type == "error":
                            error_msg = data.get("error", {}).get("message", "未知错误")
                            logger.error(f"[ASR] 服务端错误: {error_msg}")
                            return f"语音识别错误: {error_msg}"
                        
                        # 会话结束
                        elif event_type == "session.closed":
                            break
                            
                    except asyncio.TimeoutError:
                        logger.warning("[ASR] 接收消息超时")
                        break
                
                return recognized_text.strip() if recognized_text else "无法识别语音内容"
                
        except websockets.exceptions.ConnectionClosed as e:
            logger.error(f"[ASR] WebSocket 连接关闭: {e}")
            return "语音识别连接断开"
        except Exception as e:
            logger.error(f"[ASR] 识别异常: {str(e)}")
            return f"语音识别出错: {str(e)}"
    
    async def recognize_audio_file(self, file_path: str) -> str:
        """
        识别音频文件（从文件路径）
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            str: 识别的文本
        """
        with open(file_path, 'rb') as f:
            audio_data = f.read()
        
        # 根据文件扩展名确定格式
        ext = file_path.split('.')[-1].lower()
        format_map = {
            'wav': 'wav',
            'pcm': 'pcm',
            'mp3': 'mp3',
            'webm': 'webm',
        }
        audio_format = format_map.get(ext, 'pcm')
        
        return await self.recognize_audio(audio_data, format=audio_format)


# 全局单例
asr_service = DashScopeASRService()
