"""JWT 处理器

处理 JWT Token 的生成、验证和解码。
支持 RS256 和 HS256 算法。
"""

from datetime import datetime, timedelta
from typing import Optional, Any
import logging

from jose import JWTError, jwt

logger = logging.getLogger(__name__)


class JWTHandler:
    """JWT Token 处理器"""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "RS256",
        expires_minutes: int = 15,
        refresh_expires_days: int = 7,
        public_key: Optional[str] = None
    ):
        """
        初始化 JWT 处理器
        
        Args:
            secret_key: 密钥（RS256 为私钥 PEM，HS256 为密钥字符串）
            algorithm: 算法，支持 "RS256" 或 "HS256"
            expires_minutes: Access Token 过期时间（分钟）
            refresh_expires_days: Refresh Token 过期时间（天）
            public_key: 公钥 PEM（RS256 模式下用于验证签名，不提供则从私钥提取）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expires_minutes = expires_minutes
        self.refresh_expires_days = refresh_expires_days
        
        # RS256 模式下，确定验证用的公钥
        if algorithm == "RS256":
            if public_key:
                self.verify_key = public_key
            else:
                # 从私钥提取公钥
                self.verify_key = self._extract_public_key(secret_key)
        else:
            # HS256 使用相同的密钥
            self.verify_key = secret_key
    
    def _extract_public_key(self, private_key_pem: str) -> str:
        """
        从私钥 PEM 中提取公钥
        
        Args:
            private_key_pem: 私钥 PEM 字符串
            
        Returns:
            公钥 PEM 字符串
        """
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend
            
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None,
                backend=default_backend()
            )
            public_key = private_key.public_key()
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            logger.debug("已从私钥提取公钥用于 JWT 验证")
            return public_pem.decode('utf-8')
        except Exception as e:
            logger.warning(f"从私钥提取公钥失败: {e}，将使用私钥验证（不推荐）")
            return private_key_pem
    
    def create_access_token(
        self,
        user_id: str,
        device_fingerprint: Optional[str] = None,
        additional_claims: Optional[dict] = None
    ) -> str:
        """
        创建访问令牌
        
        Args:
            user_id: 用户ID
            device_fingerprint: 设备指纹（可选，用于设备绑定）
            additional_claims: 额外的声明
            
        Returns:
            JWT Token 字符串
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.expires_minutes)
        
        payload = {
            "sub": user_id,
            "type": "access",
            "iat": now,
            "exp": expire
        }
        
        if device_fingerprint:
            payload["device"] = device_fingerprint
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"为用户 {user_id} 创建访问令牌，过期时间: {expire}")
        return token
    
    def create_refresh_token(
        self,
        user_id: str,
        device_fingerprint: Optional[str] = None
    ) -> str:
        """
        创建刷新令牌
        
        Args:
            user_id: 用户ID
            device_fingerprint: 设备指纹
            
        Returns:
            Refresh Token 字符串
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_expires_days)
        
        payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": expire
        }
        
        if device_fingerprint:
            payload["device"] = device_fingerprint
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"为用户 {user_id} 创建刷新令牌，过期时间: {expire}")
        return token
    
    def create_token_pair(
        self,
        user_id: str,
        device_fingerprint: Optional[str] = None
    ) -> dict[str, Any]:
        """
        创建令牌对（访问令牌 + 刷新令牌）
        
        Returns:
            包含 access_token、refresh_token、expires_in 等信息的字典
        """
        access_token = self.create_access_token(user_id, device_fingerprint)
        refresh_token = self.create_refresh_token(user_id, device_fingerprint)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.expires_minutes * 60  # 秒
        }
    
    def verify_token(
        self,
        token: str,
        expected_type: str = "access"
    ) -> Optional[dict]:
        """
        验证并解码令牌
        
        Args:
            token: JWT Token 字符串
            expected_type: 期望的令牌类型（"access" 或 "refresh"）
            
        Returns:
            解码后的 payload，验证失败返回 None
        """
        try:
            # RS256 使用公钥验证，HS256 使用密钥验证
            payload = jwt.decode(token, self.verify_key, algorithms=[self.algorithm])
            
            # 检查令牌类型
            if payload.get("type") != expected_type:
                logger.warning(f"令牌类型不匹配: 期望 {expected_type}, 实际 {payload.get('type')}")
                return None
            
            # 检查过期
            exp = payload.get("exp")
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                logger.warning("令牌已过期")
                return None
            
            return payload
            
        except JWTError as e:
            logger.warning(f"令牌验证失败: {e}")
            return None
    
    def decode_token(self, token: str) -> Optional[dict]:
        """
        解码令牌（不验证过期时间）
        
        Args:
            token: JWT Token 字符串
            
        Returns:
            解码后的 payload，解码失败返回 None
        """
        try:
            # 使用 options 跳过过期验证，RS256 使用公钥验证
            payload = jwt.decode(
                token,
                self.verify_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
            return payload
        except JWTError as e:
            logger.warning(f"令牌解码失败: {e}")
            return None
    
    def get_user_id(self, token: str) -> Optional[str]:
        """
        从令牌中提取用户ID
        
        Args:
            token: JWT Token 字符串
            
        Returns:
            用户ID，提取失败返回 None
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("sub")
        return None
    
    def get_device_fingerprint(self, token: str) -> Optional[str]:
        """
        从令牌中提取设备指纹
        
        Args:
            token: JWT Token 字符串
            
        Returns:
            设备指纹，不存在返回 None
        """
        payload = self.verify_token(token)
        if payload:
            return payload.get("device")
        return None
    
    def is_token_expired(self, token: str) -> bool:
        """
        检查令牌是否已过期
        
        Args:
            token: JWT Token 字符串
            
        Returns:
            True 表示已过期
        """
        payload = self.decode_token(token)
        if not payload:
            return True
        
        exp = payload.get("exp")
        if not exp:
            return True
        
        return datetime.utcfromtimestamp(exp) < datetime.utcnow()
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        获取令牌过期时间
        
        Args:
            token: JWT Token 字符串
            
        Returns:
            过期时间，获取失败返回 None
        """
        payload = self.decode_token(token)
        if payload:
            exp = payload.get("exp")
            if exp:
                return datetime.utcfromtimestamp(exp)
        return None
