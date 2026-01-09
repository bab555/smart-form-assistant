"""
阿里云 OCR OpenAPI SDK（优先方案 - Tea SDK）

使用官方 Tea SDK（alibabacloud_ocr_api20210707），与文档示例一致，避免 CommonRequest 参数不匹配问题。
参考：
- API 概览（文字识别/2021-07-07）：https://help.aliyun.com/zh/ocr/developer-reference/api-ocr-api-2021-07-07-overview
"""

from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.core.logger import app_logger as logger


class AliyunOCROpenAPISDK:
    """
    使用 alibabacloud_ocr_api20210707 Tea SDK 调用 OCR OpenAPI
    """

    def __init__(self):
        if settings.ALIYUN_ACCESS_KEY_ID.startswith("sk-"):
            raise ValueError("ALIYUN_ACCESS_KEY_ID 看起来是 sk-（DashScope），传统 OCR OpenAPI 需要 LTAI... 形式的 AccessKeyId")
        if not settings.ALIYUN_ACCESS_KEY_SECRET:
            raise ValueError("未配置 ALIYUN_ACCESS_KEY_SECRET（传统 OCR OpenAPI 必填）")

        # 延迟导入：避免依赖没装导致启动失败
        from alibabacloud_tea_openapi import models as open_api_models  # type: ignore
        from alibabacloud_ocr_api20210707.client import Client as OcrClient  # type: ignore

        cfg = open_api_models.Config(
            access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
            access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET,
        )
        # 默认公网接入：ocr-api.cn-hangzhou.aliyuncs.com
        cfg.endpoint = settings.ALIYUN_OCR_ENDPOINT
        self.client = OcrClient(cfg)

    def recognize_printed(self, image_data: Optional[bytes] = None, image_url: Optional[str] = None) -> tuple[str, float, float]:
        """
        印刷体 OCR：优先 RecognizeGeneral（通用文字识别）。

        Returns:
            (text, avg_confidence, low_confidence_ratio):
            - text: 识别文本
            - avg_confidence: 平均置信度 (0-100)
            - low_confidence_ratio: 低置信度(<75)字数占比 (0.0-1.0)
        """
        from alibabacloud_ocr_api20210707 import models as ocr_models  # type: ignore
        from alibabacloud_tea_util import models as util_models  # type: ignore

        if not image_data and not image_url:
            raise ValueError("image_data 与 image_url 至少提供一个")

        runtime = util_models.RuntimeOptions()

        # 根据 settings.OCR_OPENAPI_ACTION 动态选择
        action = settings.OCR_OPENAPI_ACTION
        
        if action == "RecognizeAdvanced":
            req = ocr_models.RecognizeAdvancedRequest()
            if image_url:
                req.url = image_url
            if image_data:
                req.body = image_data
            
            logger.info("[OCR SDK] Using RecognizeAdvanced (High Precision)")
            resp = self.client.recognize_advanced_with_options(req, runtime)
            
        else:
            req = ocr_models.RecognizeGeneralRequest()
            if image_url:
                req.url = image_url
            if image_data:
                req.body = image_data
                
            logger.info("[OCR SDK] Using RecognizeGeneral (Standard)")
            resp = self.client.recognize_general_with_options(req, runtime)

        # resp.body.data 通常是结构化结果
        body = getattr(resp, "body", None)
        data = getattr(body, "data", None) if body is not None else None

        import json
        data_dict = {}

        if data:
            if isinstance(data, str):
                try:
                    data_dict = json.loads(data)
                except:
                    data_dict = {"content": data}
            elif hasattr(data, "to_map"):
                data_dict = data.to_map()
            else:
                try:
                    data_dict = dict(data)
                except:
                    data_dict = getattr(data, "__dict__", {})

        text = ""
        avg_prob = 0.0
        low_conf_ratio = 0.0
        
        if data_dict:
            # 1. 获取文本内容
            text = (
                data_dict.get("content") or 
                data_dict.get("Content") or 
                ""
            )
            
            # 2. 计算平均置信度 & 低置信度占比
            words_info = (
                data_dict.get("prism_wordsInfo") or 
                data_dict.get("PrismWordsInfo") or 
                data_dict.get("prism_words_info") or 
                []
            )
            
            if words_info and isinstance(words_info, list):
                total_prob = 0
                count = 0
                low_conf_count = 0
                LOW_CONF_THRESHOLD = 75.0  # 低于此分数视为存疑
                
                for w in words_info:
                    prob = 0
                    if isinstance(w, dict):
                        prob = w.get("prob", 0) or w.get("Prob", 0)
                    else:
                        prob = getattr(w, "prob", 0) or getattr(w, "Prob", 0)
                    
                    try:
                        prob = float(prob)
                    except:
                        prob = 0.0
                        
                    total_prob += prob
                    if prob < LOW_CONF_THRESHOLD:
                        low_conf_count += 1
                    count += 1
                
                if count > 0:
                    avg_prob = total_prob / count
                    low_conf_ratio = low_conf_count / count
                    logger.info(f"[OCR SDK] Stats: avg_prob={avg_prob:.1f}, low_conf_ratio={low_conf_ratio:.2%}, total_words={count}")
            
            if not text:
                try:
                    text = str(data)
                except Exception:
                    text = ""

        return (text or "").strip(), avg_prob, low_conf_ratio


_sdk_client: Optional[AliyunOCROpenAPISDK] = None


def get_ocr_openapi_sdk() -> AliyunOCROpenAPISDK:
    global _sdk_client
    if _sdk_client is None:
        _sdk_client = AliyunOCROpenAPISDK()
        logger.info("✅ OCR OpenAPI SDK 初始化完成（印刷体快路径）")
    return _sdk_client


