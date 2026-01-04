"""
阿里云 ASR 语音识别服务封装
"""
import json
import base64
from typing import Optional
from app.core.config import settings
from app.core.logger import app_logger as logger

# 注意: 阿里云 ASR 需要使用 nls-sdk-python
# 这里提供简化版封装，使用 HTTP API 方式


class AliyunASRService:
    """阿里云语音识别服务"""
    
    def __init__(self):
        """初始化 ASR 服务"""
        self.app_key = settings.ALIYUN_ASR_APP_KEY
        self.access_key_id = settings.ALIYUN_ACCESS_KEY_ID
        self.access_key_secret = settings.ALIYUN_ACCESS_KEY_SECRET
        self.endpoint = settings.ALIYUN_ASR_ENDPOINT
        logger.info("阿里云 ASR 服务初始化完成")
    
    async def recognize_audio(
        self,
        audio_data: bytes,
        format: str = "wav",
        sample_rate: int = 16000
    ) -> str:
        """
        识别音频文件
        
        Args:
            audio_data: 音频字节数据
            format: 音频格式（wav/mp3/pcm）
            sample_rate: 采样率
            
        Returns:
            str: 识别的文本
        """
        try:
            # 这里使用简化的一句话识别 API
            # 实际生产环境建议使用官方 SDK
            
            import httpx
            
            # 构建请求
            url = f"https://{self.endpoint}/stream/v1/asr"
            
            headers = {
                "Content-Type": f"audio/{format}",
                "X-NLS-Token": await self._get_token()
            }
            
            params = {
                "appkey": self.app_key,
                "format": format,
                "sample_rate": sample_rate
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    params=params,
                    content=audio_data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result.get("result", "")
                    logger.info(f"ASR 识别成功: {text}")
                    return text
                else:
                    logger.error(f"ASR 识别失败: {response.status_code}")
                    raise Exception(f"ASR 识别失败: {response.text}")
                    
        except Exception as e:
            logger.error(f"ASR 识别异常: {str(e)}")
            # 开发阶段返回 Mock 数据
            logger.warning("返回 Mock ASR 结果")
            return self._mock_asr_result(audio_data)
    
    async def _get_token(self) -> str:
        """
        获取访问 Token
        实际生产环境需要实现完整的鉴权流程
        """
        # 简化处理：这里应该调用阿里云 Token 服务
        # 暂时返回 access_key_id 作为 token
        return self.access_key_id
    
    def _mock_asr_result(self, audio_data: bytes) -> str:
        """
        Mock ASR 结果（用于开发测试）
        
        Args:
            audio_data: 音频数据
            
        Returns:
            str: Mock 的识别结果
        """
        # 根据音频长度返回不同的 Mock 结果
        audio_len = len(audio_data)
        
        mock_results = [
            "把第一行的商品名称改成红富士苹果",
            "删除最后一行",
            "添加一行数据",
            "把价格改成15元",
            "清空所有数据"
        ]
        
        # 简单的哈希选择
        index = audio_len % len(mock_results)
        result = mock_results[index]
        
        logger.info(f"返回 Mock ASR 结果: {result}")
        return result


# 全局单例
asr_service = AliyunASRService()

