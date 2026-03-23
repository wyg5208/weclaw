"""RSA 处理器

处理 RSA 密钥对的生成、加密和解密。
用于安全传输 JWT Token。
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class RSAHandler:
    """RSA 密钥处理器"""
    
    def __init__(
        self,
        private_key_path: Optional[Path] = None,
        public_key_path: Optional[Path] = None,
        key_size: int = 2048
    ):
        """
        初始化 RSA 处理器
        
        Args:
            private_key_path: 私钥文件路径
            public_key_path: 公钥文件路径
            key_size: 密钥长度（位），默认 2048
        """
        self.key_size = key_size
        self._private_key = None
        self._public_key = None
        
        # 尝试加载或生成密钥
        if private_key_path and private_key_path.exists():
            self._load_private_key(private_key_path)
        elif public_key_path and public_key_path.exists():
            self._load_public_key(public_key_path)
        else:
            # 尝试从默认路径加载
            self._try_load_default_keys()
        
        # 如果没有密钥，生成新的
        if self._private_key is None and self._public_key is None:
            logger.info("未找到 RSA 密钥，生成新的密钥对")
            self._generate_keypair()
            
            # 保存到文件
            if private_key_path:
                self._save_keys(private_key_path, public_key_path)
    
    def _try_load_default_keys(self):
        """尝试从默认路径加载密钥"""
        default_private = Path("keys/private.pem")
        default_public = Path("keys/public.pem")
        
        if default_private.exists():
            self._load_private_key(default_private)
        elif default_public.exists():
            self._load_public_key(default_public)
    
    def _load_private_key(self, path: Path):
        """加载私钥"""
        try:
            with open(path, "rb") as f:
                self._private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )
            self._public_key = self._private_key.public_key()
            logger.info(f"已加载私钥: {path}")
        except Exception as e:
            logger.error(f"加载私钥失败: {e}")
    
    def _load_public_key(self, path: Path):
        """加载公钥"""
        try:
            with open(path, "rb") as f:
                self._public_key = serialization.load_pem_public_key(
                    f.read(),
                    backend=default_backend()
                )
            logger.info(f"已加载公钥: {path}")
        except Exception as e:
            logger.error(f"加载公钥失败: {e}")
    
    def _generate_keypair(self):
        """生成 RSA 密钥对"""
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()
        logger.info(f"已生成 {self.key_size} 位 RSA 密钥对")
    
    def _save_keys(self, private_path: Path, public_path: Path):
        """保存密钥到文件"""
        # 确保目录存在
        private_path.parent.mkdir(parents=True, exist_ok=True)
        public_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存私钥
        if self._private_key:
            private_pem = self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(private_path, "wb") as f:
                f.write(private_pem)
            logger.info(f"私钥已保存到: {private_path}")
        
        # 保存公钥
        if self._public_key:
            public_pem = self._public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            with open(public_path, "wb") as f:
                f.write(public_pem)
            logger.info(f"公钥已保存到: {public_path}")
    
    def get_private_key_pem(self) -> str:
        """获取私钥 PEM 格式字符串"""
        if not self._private_key:
            raise ValueError("私钥未加载")
        
        private_pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return private_pem.decode("utf-8")
    
    def get_public_key_pem(self) -> str:
        """获取公钥 PEM 格式字符串"""
        if not self._public_key:
            raise ValueError("公钥未加载")
        
        public_pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_pem.decode("utf-8")
    
    def encrypt(self, plaintext: str, public_key_pem: Optional[str] = None) -> str:
        """
        使用 RSA 公钥加密数据
        
        Args:
            plaintext: 要加密的明文
            public_key_pem: 公钥 PEM 字符串（不提供则使用自己的公钥）
            
        Returns:
            Base64 编码的密文
        """
        import base64
        
        # 获取公钥
        if public_key_pem:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode("utf-8"),
                backend=default_backend()
            )
        else:
            public_key = self._public_key
        
        if not public_key:
            raise ValueError("公钥未加载")
        
        # 加密
        ciphertext = public_key.encrypt(
            plaintext.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(ciphertext).decode("utf-8")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        使用 RSA 私钥解密数据
        
        Args:
            ciphertext: Base64 编码的密文
            
        Returns:
            解密后的明文
        """
        import base64
        
        if not self._private_key:
            raise ValueError("私钥未加载")
        
        # 解密
        plaintext = self._private_key.decrypt(
            base64.b64decode(ciphertext),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return plaintext.decode("utf-8")
    
    def encrypt_for_user(self, data: str, user_public_key: str) -> str:
        """
        使用用户的公钥加密数据（用于向用户发送加密数据）
        
        Args:
            data: 要加密的数据
            user_public_key: 用户公钥 PEM 字符串
            
        Returns:
            Base64 编码的密文
        """
        return self.encrypt(data, user_public_key)
    
    def has_private_key(self) -> bool:
        """检查是否加载了私钥"""
        return self._private_key is not None
    
    def has_public_key(self) -> bool:
        """检查是否加载了公钥"""
        return self._public_key is not None


def generate_keypair(
    private_key_path: Path,
    public_key_path: Path,
    key_size: int = 2048
) -> Tuple[str, str]:
    """
    生成并保存 RSA 密钥对
    
    Args:
        private_key_path: 私钥保存路径
        public_key_path: 公钥保存路径
        key_size: 密钥长度
        
    Returns:
        (私钥 PEM 字符串, 公钥 PEM 字符串)
    """
    handler = RSAHandler(private_key_path, public_key_path, key_size)
    return handler.get_private_key_pem(), handler.get_public_key_pem()
