"""
DashScope 语音识别服务 (Paraformer)

使用阿里云 DashScope 的 Paraformer 模型进行语音识别
与 LLM 服务使用相同的 API Key
"""
import base64
import httpx
from typing import Optional
from app.core.config import settings
from app.core.logger import app_logger as logger


class DashScopeASRService:
    """DashScope Paraformer 语音识别服务"""
    
    def __init__(self):
        """初始化 ASR 服务"""
        self.api_key = settings.DASHSCOPE_API_KEY
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/asr/transcription"
        logger.info("DashScope ASR 服务初始化完成")
    
    async def recognize_audio(
        self,
        audio_data: bytes,
        format: str = "webm",
        sample_rate: int = 16000
    ) -> str:
        """
        识别音频文件
        
        Args:
            audio_data: 音频字节数据
            format: 音频格式（webm/wav/mp3/pcm）
            sample_rate: 采样率
            
        Returns:
            str: 识别的文本
        """
        if not self.api_key:
            logger.error("DASHSCOPE_API_KEY 未配置")
            return "语音识别服务未配置"
        
        try:
            # 将音频数据转换为 base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 使用 DashScope 的实时语音识别 API
            # 参考: https://help.aliyun.com/zh/dashscope/developer-reference/paraformer-real-time-speech-recognition
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            # 使用一句话识别模型
            payload = {
                "model": "paraformer-v2",
                "input": {
                    "audio": audio_base64,
                    "format": format,
                    "sample_rate": sample_rate,
                },
                "parameters": {
                    "language_hints": ["zh", "en"],  # 支持中英文
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 解析结果
                    output = result.get("output", {})
                    
                    # 实时识别返回格式
                    if "sentence" in output:
                        text = output["sentence"].get("text", "")
                    # 异步识别返回格式
                    elif "results" in output:
                        results = output["results"]
                        if results:
                            text = results[0].get("text", "")
                        else:
                            text = ""
                    # 直接文本格式
                    elif "text" in output:
                        text = output["text"]
                    else:
                        text = str(output)
                    
                    logger.info(f"ASR 识别成功: {text}")
                    return text.strip() if text else "无法识别语音内容"
                else:
                    error_msg = response.text
                    logger.error(f"ASR 识别失败: {response.status_code} - {error_msg}")
                    
                    # 尝试解析错误信息
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("message", error_msg)
                    except:
                        pass
                    
                    return f"语音识别失败: {error_msg}"
                    
        except httpx.TimeoutException:
            logger.error("ASR 识别超时")
            return "语音识别超时，请重试"
        except Exception as e:
            logger.error(f"ASR 识别异常: {str(e)}")
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
            'mp3': 'mp3',
            'webm': 'webm',
            'ogg': 'ogg',
            'pcm': 'pcm',
        }
        audio_format = format_map.get(ext, 'wav')
        
        return await self.recognize_audio(audio_data, format=audio_format)


# 全局单例
asr_service = DashScopeASRService()
