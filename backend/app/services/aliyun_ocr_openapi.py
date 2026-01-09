"""
阿里云 OCR OpenAPI (文字识别/2021-07-07) - RPC 签名调用

用于印刷体快速 OCR（通常比 VL-OCR 更快），参考官方文档：
https://help.aliyun.com/zh/ocr/developer-reference/api-ocr-api-2021-07-07-overview
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.logger import app_logger as logger


def _percent_encode(s: str) -> str:
    # Aliyun RPC percent-encode: space -> %20, * -> %2A, ~ keep
    return quote(s, safe="~")


def _sign(params: Dict[str, str], access_key_secret: str) -> str:
    # 1) sort params
    sorted_items = sorted(params.items(), key=lambda x: x[0])
    canonicalized = "&".join(f"{_percent_encode(k)}={_percent_encode(v)}" for k, v in sorted_items)
    string_to_sign = f"POST&%2F&{_percent_encode(canonicalized)}"

    key = (access_key_secret + "&").encode("utf-8")
    msg = string_to_sign.encode("utf-8")
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


class AliyunOCROpenAPI:
    """
    传统 OCR OpenAPI 客户端（RPC 签名）
    """

    def __init__(self):
        self.endpoint = settings.ALIYUN_OCR_ENDPOINT
        self.access_key_id = settings.ALIYUN_ACCESS_KEY_ID
        self.access_key_secret = settings.ALIYUN_ACCESS_KEY_SECRET

    async def recognize_printed(self, image_data: bytes, action: Optional[str] = None) -> str:
        """
        印刷体 OCR（默认 RecognizeGeneral）
        """
        if not self.access_key_secret or self.access_key_id.startswith("sk-"):
            raise ValueError(
                "传统 OCR OpenAPI 需要阿里云 AccessKeyId/AccessKeySecret（非 sk-）。"
                "请在 .env 中配置 ALIYUN_ACCESS_KEY_ID=LTAI... 与 ALIYUN_ACCESS_KEY_SECRET=..."
            )

        action = action or settings.OCR_OPENAPI_ACTION

        params: Dict[str, str] = {
            "Format": "JSON",
            "Version": "2021-07-07",
            "AccessKeyId": self.access_key_id,
            "SignatureMethod": "HMAC-SHA1",
            "SignatureVersion": "1.0",
            "SignatureNonce": str(uuid.uuid4()),
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Action": action,
            # 根据官方错误提示 imageUrlOrBodyEmpty：需要 Url 或 Body
            # 这里走 Body（base64 字符串），避免公网 URL 依赖
            "Body": base64.b64encode(image_data).decode("utf-8"),
        }

        params["Signature"] = _sign(params, self.access_key_secret)

        url = f"https://{self.endpoint}/"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, data=params)
            resp.raise_for_status()
            data: Dict[str, Any] = resp.json()

        # 尽量兼容不同返回结构
        # 常见：{"Data":{"Content":"..."}} 或 {"Data":{"content":"..."}} 或 prism_wordsInfo 列表
        content = ""
        if isinstance(data.get("Data"), dict):
            d = data["Data"]
            content = d.get("Content") or d.get("content") or ""
            if not content:
                words = d.get("PrismWordsInfo") or d.get("prism_wordsInfo") or d.get("prismWordsInfo")
                if isinstance(words, list):
                    content = "\n".join(w.get("Word", "") or w.get("word", "") for w in words if isinstance(w, dict))
        elif "Content" in data:
            content = str(data.get("Content") or "")
        elif "content" in data:
            content = str(data.get("content") or "")

        if not content:
            # 最后兜底：返回整包（便于排查）
            logger.warning(f"[OpenAPI OCR] Unexpected response shape, keys={list(data.keys())}")
            content = json.dumps(data, ensure_ascii=False)

        return content.strip()


# 全局单例
ocr_openapi = AliyunOCROpenAPI()


