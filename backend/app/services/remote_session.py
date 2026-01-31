"""
远端 API Session 管理

负责：
1. 管理与远端 shian360 API 的 HTTP Session
2. 用户登录状态维护
3. 本地 Token 生成（用于"记住登录"功能）
"""

import asyncio
import hashlib
import secrets
import time
import json
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import httpx

from app.core.logger import app_logger as logger
from app.core.redis import redis_manager

# 远端 API 基础 URL
REMOTE_API_BASE = "https://api.szst.zjcqq.com/order_tool"


@dataclass
class UserSession:
    """用户会话"""
    user_type: str  # purchaser / supplier
    user_id: str
    genus_id: str  # 学校ID 或 配送商ID
    name: str
    access_token: str  # 远端返回的 token
    local_token: str  # 本地生成的 token（用于记住登录）
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_type": self.user_type,
            "user_id": self.user_id,
            "genus_id": self.genus_id,
            "name": self.name,
            "access_token": self.access_token,
            "local_token": self.local_token,
            "created_at": self.created_at,
            "last_active": self.last_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSession':
        return cls(
            user_type=data.get("user_type", ""),
            user_id=data.get("user_id", ""),
            genus_id=data.get("genus_id", ""),
            name=data.get("name", ""),
            access_token=data.get("access_token", ""),
            local_token=data.get("local_token", ""),
            created_at=data.get("created_at", time.time()),
            last_active=data.get("last_active", time.time())
        )


class RemoteSessionManager:
    """远端 Session 管理器 (Redis 版)"""
    
    def __init__(self):
        self._lock = asyncio.Lock()
    
    def _generate_local_token(self, username: str) -> str:
        """生成本地 token"""
        random_part = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        raw = f"{username}:{timestamp}:{random_part}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    async def _save_session(self, session: UserSession, ex: int = 86400):
        """保存会话到 Redis"""
        key = f"session:{session.local_token}"
        await redis_manager.set(key, json.dumps(session.to_dict()), ex=ex)
        
    async def get_session(self, token: str) -> Optional[UserSession]:
        """获取会话"""
        key = f"session:{token}"
        raw = await redis_manager.get(key)
        if not raw:
            return None
        
        try:
            data = json.loads(raw)
            session = UserSession.from_dict(data)
            # 更新活跃时间 (每次获取都刷新过期时间)
            session.last_active = time.time()
            # 异步刷新 Redis 过期时间，不等待
            asyncio.create_task(redis_manager.set(key, json.dumps(session.to_dict()), ex=86400))
            return session
        except Exception as e:
            logger.error(f"[RemoteSession] Failed to parse session: {e}")
            return None

    async def login(self, username: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        用户登录
        """
        logger.info(f"[RemoteSession] Login attempt for user: {username}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                logger.debug(f"[RemoteSession] Sending login request to {REMOTE_API_BASE}/login.php")
                response = await client.post(
                    f"{REMOTE_API_BASE}/login.php",
                    params={"op": "set"},
                    data={"username": username, "password": password}
                )
                
                try:
                    result = response.json()
                except Exception as e:
                    logger.error(f"[RemoteSession] Failed to parse JSON: {response.text[:200]}...")
                    return False, None, f"远端响应异常: {str(e)}"
    
                if result.get("code") != 0:
                    msg = result.get("msg") or result.get("message") or "登录失败"
                    logger.warning(f"[RemoteSession] Login failed for {username}: {msg}")
                    return False, None, msg
                
                data = result.get("data", {})
                
                # 生成本地 token
                local_token = self._generate_local_token(username)
                
                # 创建会话
                session = UserSession(
                    user_type=data.get("type", ""),
                    user_id=data.get("user_id", ""),
                    genus_id=data.get("genus_id", ""),
                    name=data.get("name", ""),
                    access_token=data.get("access_token", ""),
                    local_token=local_token,
                )
                
                # 保存到 Redis
                await self._save_session(session)
                
                logger.info(f"[RemoteSession] User logged in successfully: {session.name} ({session.user_type})")
                
                return True, {
                    "userType": session.user_type,
                    "userId": session.user_id,
                    "genusId": session.genus_id,
                    "name": session.name,
                    "token": local_token,
                }, None
                
            except Exception as e:
                logger.error(f"[RemoteSession] Login exception: {e}", exc_info=True)
                return False, None, f"系统错误: {str(e)}"
    
    async def login_by_token(self, remote_token: str) -> Optional[Dict[str, Any]]:
        """SSO 登录"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{REMOTE_API_BASE}/login.php",
                    params={"op": "set"},
                    data={"access_token": remote_token}
                )
                
                try:
                    result = response.json()
                except Exception:
                    return None
    
                if result.get("code") != 0:
                    return None
                
                data = result.get("data", {})
                user_id = data.get("user_id", "")
                
                if not user_id:
                    return None
    
                local_token = self._generate_local_token(f"sso_{user_id}")
                
                session = UserSession(
                    user_type=data.get("type", ""),
                    user_id=user_id,
                    genus_id=data.get("genus_id", ""),
                    name=data.get("name", ""),
                    access_token=remote_token,
                    local_token=local_token,
                )
                
                await self._save_session(session)
                
                return {
                    "userType": session.user_type,
                    "userId": session.user_id,
                    "genusId": session.genus_id,
                    "name": session.name,
                    "token": local_token,
                }
                
            except Exception as e:
                logger.error(f"[RemoteSession] SSO Login error: {e}")
                return None

    async def logout(self, token: str) -> bool:
        """用户登出"""
        session = await self.get_session(token)
        if session:
            # 删除 Redis Key
            await redis_manager.client.delete(f"session:{token}")
            
            # 尝试调用远端登出 (不等待结果)
            async def remote_logout():
                async with httpx.AsyncClient(timeout=5.0) as client:
                    try:
                        await client.post(
                            f"{REMOTE_API_BASE}/login.php",
                            params={"op": "out"},
                            data={"access_token": session.access_token}
                        )
                    except:
                        pass
            
            asyncio.create_task(remote_logout())
            return True
        return False
    
    async def request(
        self, 
        token: str, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
        json_body: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """代理请求到远端 API"""
        session = await self.get_session(token)
        if not session:
            return None
        
        try:
            url = f"{REMOTE_API_BASE}{endpoint}"
            req_params = params or {}
            
            # 注入 access_token
            if session.access_token:
                req_params["access_token"] = session.access_token

            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=req_params)
                else:
                    if json_body is not None:
                        if session.access_token:
                            json_body["access_token"] = session.access_token
                        response = await client.post(url, params=req_params, json=json_body)
                    else:
                        req_data = data or {}
                        if session.access_token:
                            req_data["access_token"] = session.access_token
                        response = await client.post(url, params=req_params, data=req_data)
                
                return response.json()
            
        except Exception as e:
            logger.error(f"[RemoteSession] Request error: {e}")
            return None
    
    async def cleanup_expired(self, max_age: int = 86400):
        """清理过期会话 (Redis 自动过期，无需手动清理)"""
        pass

# 全局单例
remote_session_manager = RemoteSessionManager()

