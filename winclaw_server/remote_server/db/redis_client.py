"""Redis 客户端

用于会话存储、Token 黑名单、消息缓存等。
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Any
import asyncio

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端封装"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        prefix: str = "winclaw:"
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.prefix = prefix
        self._client = None
        self._enabled = False
    
    async def initialize(self) -> bool:
        """初始化 Redis 连接"""
        try:
            import redis.asyncio as redis
            
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=True
            )
            
            # 测试连接
            await self._client.ping()
            self._enabled = True
            logger.info(f"Redis 连接成功: {self.host}:{self.port}")
            return True
            
        except ImportError:
            logger.warning("redis 库未安装，将使用内存缓存")
            self._enabled = False
            return False
            
        except Exception as e:
            logger.warning(f"Redis 连接失败: {e}，将使用内存缓存")
            self._enabled = False
            return False
    
    def _key(self, key: str) -> str:
        """添加前缀"""
        return f"{self.prefix}{key}"
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        if not self._enabled or not self._client:
            return None
        try:
            return await self._client.get(self._key(key))
        except Exception as e:
            logger.warning(f"Redis get 失败: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None
    ) -> bool:
        """设置值"""
        if not self._enabled or not self._client:
            return False
        try:
            await self._client.set(self._key(key), value, ex=ex)
            return True
        except Exception as e:
            logger.warning(f"Redis set 失败: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除键"""
        if not self._enabled or not self._client:
            return False
        try:
            await self._client.delete(self._key(key))
            return True
        except Exception as e:
            logger.warning(f"Redis delete 失败: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self._enabled or not self._client:
            return False
        try:
            return await self._client.exists(self._key(key)) > 0
        except Exception as e:
            logger.warning(f"Redis exists 失败: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        if not self._enabled or not self._client:
            return False
        try:
            return await self._client.expire(self._key(key), seconds)
        except Exception as e:
            logger.warning(f"Redis expire 失败: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        if not self._enabled or not self._client:
            return -1
        try:
            return await self._client.ttl(self._key(key))
        except Exception as e:
            logger.warning(f"Redis ttl 失败: {e}")
            return -1
    
    # ========== 会话管理 ==========
    
    async def set_session(self, session_id: str, data: dict, ttl: int = 3600):
        """存储会话数据"""
        await self.set(
            f"session:{session_id}",
            json.dumps(data),
            ex=ttl
        )
    
    async def get_session(self, session_id: str) -> Optional[dict]:
        """获取会话数据"""
        data = await self.get(f"session:{session_id}")
        if data:
            return json.loads(data)
        return None
    
    async def delete_session(self, session_id: str):
        """删除会话"""
        await self.delete(f"session:{session_id}")
    
    # ========== Token 黑名单 ==========
    
    async def add_token_to_blacklist(self, token: str, expires_in: int):
        """将 Token 加入黑名单"""
        await self.set(f"blacklist:{token}", "1", ex=expires_in)
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """检查 Token 是否在黑名单中"""
        return await self.exists(f"blacklist:{token}")
    
    # ========== 用户在线状态 ==========
    
    async def set_user_online(self, user_id: str, ttl: int = 300):
        """设置用户在线状态"""
        await self.set(f"online:{user_id}", datetime.now().isoformat(), ex=ttl)
    
    async def is_user_online(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return await self.exists(f"online:{user_id}")
    
    async def get_online_users(self) -> list:
        """获取所有在线用户"""
        if not self._enabled or not self._client:
            return []
        try:
            keys = await self._client.keys(self._key("online:*"))
            return [k.split(":")[-1] for k in keys]
        except Exception as e:
            logger.warning(f"获取在线用户失败: {e}")
            return []
    
    # ========== 消息缓存 ==========
    
    async def cache_message(self, message_id: str, data: dict, ttl: int = 3600):
        """缓存消息"""
        await self.set(f"message:{message_id}", json.dumps(data), ex=ttl)
    
    async def get_cached_message(self, message_id: str) -> Optional[dict]:
        """获取缓存的消息"""
        data = await self.get(f"message:{message_id}")
        if data:
            return json.loads(data)
        return None
    
    # ========== 速率限制 ==========
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window: int = 60
    ) -> tuple[bool, int]:
        """
        检查速率限制
        
        Args:
            key: 限制键（如用户ID或IP）
            limit: 窗口内最大请求数
            window: 窗口大小（秒）
            
        Returns:
            (是否允许, 剩余请求数)
        """
        if not self._enabled or not self._client:
            return True, limit
        
        try:
            redis_key = self._key(f"ratelimit:{key}")
            current = await self._client.get(redis_key)
            
            if current is None:
                await self._client.set(redis_key, "1", ex=window)
                return True, limit - 1
            
            current = int(current)
            if current >= limit:
                ttl = await self._client.ttl(redis_key)
                return False, 0
            
            await self._client.incr(redis_key)
            return True, limit - current - 1
            
        except Exception as e:
            logger.warning(f"速率限制检查失败: {e}")
            return True, limit
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()


# 全局 Redis 客户端
_redis: Optional[RedisClient] = None


def get_redis() -> Optional[RedisClient]:
    """获取 Redis 客户端"""
    return _redis


async def init_redis(config: dict) -> RedisClient:
    """初始化 Redis"""
    global _redis
    
    _redis = RedisClient(
        host=config.get("host", "localhost"),
        port=config.get("port", 6379),
        password=config.get("password"),
        db=config.get("db", 0)
    )
    
    await _redis.initialize()
    
    return _redis


# ========== 内存缓存后备 ==========

class MemoryCache:
    """内存缓存（Redis 不可用时使用）"""
    
    def __init__(self):
        self._data: dict = {}
        self._expiry: dict = {}
    
    def _clean_expired(self):
        """清理过期数据"""
        now = datetime.now().timestamp()
        expired = [k for k, v in self._expiry.items() if v < now]
        for k in expired:
            self._data.pop(k, None)
            self._expiry.pop(k, None)
    
    async def get(self, key: str) -> Optional[str]:
        self._clean_expired()
        return self._data.get(key)
    
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        self._data[key] = value
        if ex:
            self._expiry[key] = datetime.now().timestamp() + ex
    
    async def delete(self, key: str):
        self._data.pop(key, None)
        self._expiry.pop(key, None)
    
    async def exists(self, key: str) -> bool:
        self._clean_expired()
        return key in self._data


_memory_cache = MemoryCache()
