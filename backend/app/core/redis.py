"""
Redis 客户端管理器
"""
import redis.asyncio as redis
from typing import Optional
from app.core.config import settings
from app.core.logger import app_logger as logger

class RedisManager:
    """Redis 连接管理器"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        
    async def init_redis(self):
        """初始化 Redis 连接"""
        try:
            self._redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD or None,
                db=settings.REDIS_DB,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0
            )
            await self._redis.ping()
            logger.info(f"Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._redis = None

    async def close(self):
        """关闭连接"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")
            
    @property
    def client(self) -> Optional[redis.Redis]:
        """获取 Redis 客户端"""
        return self._redis

    async def get(self, key: str) -> Optional[str]:
        if not self._redis: return None
        try:
            return await self._redis.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
            
    async def set(self, key: str, value: str, ex: int = None) -> bool:
        if not self._redis: return False
        try:
            await self._redis.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

# 全局单例
redis_manager = RedisManager()
