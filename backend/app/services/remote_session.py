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
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import httpx

from app.core.logger import app_logger as logger

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
    http_client: httpx.AsyncClient = field(default=None, repr=False)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


class RemoteSessionManager:
    """远端 Session 管理器"""
    
    def __init__(self):
        # local_token -> UserSession
        self._sessions: Dict[str, UserSession] = {}
        self._lock = asyncio.Lock()
    
    def _generate_local_token(self, username: str) -> str:
        """生成本地 token"""
        random_part = secrets.token_hex(16)
        timestamp = str(int(time.time()))
        raw = f"{username}:{timestamp}:{random_part}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    async def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        用户登录
        
        Returns:
            成功返回用户信息，失败返回 None
        """
        # 创建新的 HTTP Client（带 Cookie 支持）
        client = httpx.AsyncClient(timeout=30.0)
        
        try:
            # 调用远端登录接口
            response = await client.post(
                f"{REMOTE_API_BASE}/login.php",
                params={"op": "set"},
                data={"username": username, "password": password}
            )
            
            result = response.json()
            logger.info(f"[RemoteSession] Login response: {result}")
            
            if result.get("code") != 0:
                await client.aclose()
                return None
            
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
                http_client=client,
            )
            
            async with self._lock:
                self._sessions[local_token] = session
            
            logger.info(f"[RemoteSession] User logged in: {session.name} ({session.user_type})")
            
            return {
                "userType": session.user_type,
                "userId": session.user_id,
                "genusId": session.genus_id,
                "name": session.name,
                "token": local_token,
            }
            
        except Exception as e:
            logger.error(f"[RemoteSession] Login error: {e}")
            await client.aclose()
            return None
    
    async def login_by_token(self, remote_token: str) -> Optional[Dict[str, Any]]:
        """
        SSO 登录：使用远端 access_token 换取用户信息
        
        注意：需要远端 API 支持通过 token 获取用户信息
        """
        # 创建新的 HTTP Client
        client = httpx.AsyncClient(timeout=30.0)
        
        try:
            # SSO 登录：直接调用远端 login.php，但参数改为 access_token
            # 根据用户需求：
            # 1. 接口不变 (login.php?op=set)
            # 2. Body 从 {username, password} 改为 {access_token: token}
            
            response = await client.post(
                f"{REMOTE_API_BASE}/login.php",
                params={"op": "set"},
                data={"access_token": remote_token}
            )
            
            try:
                result = response.json()
                logger.info(f"[RemoteSession] SSO Login response: {result}")
            except Exception as json_err:
                logger.error(f"[RemoteSession] SSO Login JSON error: {json_err}, text: {response.text}")
                await client.aclose()
                return None

            if result.get("code") != 0:
                logger.warning(f"[RemoteSession] SSO Login failed: {result.get('message')}")
                await client.aclose()
                return None
            
            data = result.get("data", {})
            
            # 提取用户信息（兼容之前的结构）
            # 注意：实际 API 返回字段可能不同，这里假设与普通登录返回一致
            user_type = data.get("type", "")
            user_id = data.get("user_id", "")
            
            if not user_id:
                logger.error("[RemoteSession] SSO Login successful but no user_id returned")
                await client.aclose()
                return None

            # 生成本地 token
            # 注意：SSO 场景下，我们可以直接用传入的 token 作为 key，或者重新生成
            # 为了安全和一致性，我们还是生成一个新的 local_token
            local_token = self._generate_local_token(f"sso_{user_id}")
            
            # 创建会话
            session = UserSession(
                user_type=user_type,
                user_id=user_id,
                genus_id=data.get("genus_id", ""),
                name=data.get("name", ""),
                access_token=remote_token, # 保存传入的 token
                local_token=local_token,
                http_client=client,
            )
            
            async with self._lock:
                self._sessions[local_token] = session
            
            logger.info(f"[RemoteSession] SSO Login success: {session.name} ({session.user_type})")
            
            return {
                "userType": session.user_type,
                "userId": session.user_id,
                "genusId": session.genus_id,
                "name": session.name,
                "token": local_token,
            }
            
        except Exception as e:
            logger.error(f"[RemoteSession] SSO Login error: {e}")
            await client.aclose()
            return None

    async def logout(self, token: str) -> bool:
        """用户登出"""
        async with self._lock:
            session = self._sessions.pop(token, None)
        
        if session:
            try:
                # 调用远端登出接口
                await session.http_client.post(
                    f"{REMOTE_API_BASE}/login.php",
                    params={"op": "out"}
                )
            except Exception as e:
                logger.warning(f"[RemoteSession] Logout remote error: {e}")
            finally:
                await session.http_client.aclose()
            
            logger.info(f"[RemoteSession] User logged out: {session.name}")
            return True
        
        return False
    
    def get_session(self, token: str) -> Optional[UserSession]:
        """获取会话"""
        session = self._sessions.get(token)
        if session:
            session.last_active = time.time()
        return session
    
    async def request(
        self, 
        token: str, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        代理请求到远端 API
        
        Args:
            token: 本地 token
            method: HTTP 方法 (GET/POST)
            endpoint: 接口路径（如 /index.php）
            params: Query 参数
            data: POST Body
        
        Returns:
            远端 API 响应
        """
        session = self.get_session(token)
        if not session:
            return None
        
        try:
            url = f"{REMOTE_API_BASE}{endpoint}"
            
            # 确保 POST 请求携带 access_token（远端 API 需要此参数进行鉴权）
            if data is None:
                data = {}
            if session.access_token:
                data["access_token"] = session.access_token
            
            if method.upper() == "GET":
                response = await session.http_client.get(url, params=params)
            else:
                response = await session.http_client.post(url, params=params, data=data)
            
            return response.json()
            
        except Exception as e:
            logger.error(f"[RemoteSession] Request error: {e}")
            return None
    
    async def cleanup_expired(self, max_age: int = 86400):
        """清理过期会话（默认24小时）"""
        now = time.time()
        expired_tokens = []
        
        async with self._lock:
            for token, session in self._sessions.items():
                if now - session.last_active > max_age:
                    expired_tokens.append(token)
        
        for token in expired_tokens:
            await self.logout(token)
        
        if expired_tokens:
            logger.info(f"[RemoteSession] Cleaned up {len(expired_tokens)} expired sessions")


# 全局单例
remote_session_manager = RemoteSessionManager()

