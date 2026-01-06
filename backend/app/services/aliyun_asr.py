
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
            # 简化处理：开发阶段如果没有配置有效的 Key，直接返回 Mock 结果
            if not self.app_key or "your_" in self.app_key:
                logger.warning("ALIYUN_ASR_APP_KEY 未配置，使用 Mock 结果")
                return self._mock_asr_result(audio_data)

            # 这里使用简化的一句话识别 API
            # 实际生产环境建议使用官方 SDK
            
            import httpx
            
            # 构建请求
            url = f"https://{self.endpoint}/stream/v1/asr"
            
            # 使用 Token 服务获取 Token，或者这里假设已经有有效 Token
            token = await self._get_token()
            
            headers = {
                "Content-Type": f"audio/{format}",
                "X-NLS-Token": token
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
                    logger.error(f"ASR 识别失败: {response.status_code} - {response.text}")
                    # 如果调用失败（可能是 Token 问题），也降级到 Mock
                    logger.warning("ASR 调用失败，降级使用 Mock")
                    return self._mock_asr_result(audio_data)
                    
        except Exception as e:
            logger.error(f"ASR 识别异常: {str(e)}")
            # 开发阶段返回 Mock 数据
            logger.warning("返回 Mock ASR 结果")
            return self._mock_asr_result(audio_data)
