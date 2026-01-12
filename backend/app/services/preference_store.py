import asyncio
import json
from pathlib import Path
from typing import Optional, Dict

from app.core.logger import app_logger as logger


class PreferenceStore:
    """
    识别商品 -> 订单商品 偏好映射表

    说明：
    - 以 customer_id 维度隔离（未来接入真实客户ID后直接复用）
    - 当前 customer_id 为空时，落到 "__global__"
    """

    def __init__(self, path: str = "./data/preferences.json"):
        self.path = Path(path)
        self.path.parent.mkdir(exist_ok=True)
        self._lock = asyncio.Lock()
        self._cache: Dict[str, Dict[str, str]] = {}
        self._loaded = False

    async def _load(self) -> None:
        if self._loaded:
            return
        async with self._lock:
            if self._loaded:
                return
            try:
                if self.path.exists():
                    raw = self.path.read_text(encoding="utf-8")
                    data = json.loads(raw) if raw.strip() else {}
                    if isinstance(data, dict):
                        # 期望：{customer_id: {recognized: order_product}}
                        self._cache = {
                            str(k): v for k, v in data.items() if isinstance(v, dict)
                        }
                self._loaded = True
            except Exception as e:
                logger.warning(f"[PreferenceStore] load failed, ignore: {e}")
                self._cache = {}
                self._loaded = True

    def _normalize_customer_id(self, customer_id: Optional[str]) -> str:
        cid = (customer_id or "").strip()
        return cid if cid else "__global__"

    async def get(self, customer_id: Optional[str], recognized: str) -> Optional[str]:
        await self._load()
        cid = self._normalize_customer_id(customer_id)
        key = (recognized or "").strip()
        if not key:
            return None
        return self._cache.get(cid, {}).get(key)

    async def set(self, customer_id: Optional[str], recognized: str, order_product: str) -> None:
        await self._load()
        cid = self._normalize_customer_id(customer_id)
        r = (recognized or "").strip()
        o = (order_product or "").strip()
        if not r or not o:
            return
        async with self._lock:
            self._cache.setdefault(cid, {})[r] = o
            try:
                self.path.write_text(json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                logger.warning(f"[PreferenceStore] save failed, ignore: {e}")


preference_store = PreferenceStore()


