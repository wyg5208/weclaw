"""用户模型

定义用户数据结构和用户配置。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


@dataclass
class UserSettings:
    """用户配置"""
    theme: str = "auto"  # "light" | "dark" | "auto"
    language: str = "zh-CN"  # "zh-CN" | "en-US"
    notification_enabled: bool = True
    voice_enabled: bool = True
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "theme": self.theme,
            "language": self.language,
            "notification_enabled": self.notification_enabled,
            "voice_enabled": self.voice_enabled
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "UserSettings":
        """从字典创建"""
        return cls(
            theme=data.get("theme", "auto"),
            language=data.get("language", "zh-CN"),
            notification_enabled=data.get("notification_enabled", True),
            voice_enabled=data.get("voice_enabled", True)
        )


@dataclass
class User:
    """用户模型"""
    user_id: str  # UUID格式
    username: str  # 3-32字符
    password_hash: str  # bcrypt加密的密码哈希
    public_key: str  # RSA公钥（PEM格式）
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    device_fingerprint: Optional[str] = None
    settings: UserSettings = field(default_factory=UserSettings)
    
    # 登录失败计数
    login_attempts: int = 0
    locked_until: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典（不包含敏感信息）"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
            "settings": self.settings.to_dict()
        }
    
    def to_storage_dict(self) -> dict:
        """转换为存储字典（包含所有字段）"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "password_hash": self.password_hash,
            "public_key": self.public_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
            "device_fingerprint": self.device_fingerprint,
            "settings": self.settings.to_dict(),
            "login_attempts": self.login_attempts,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """从字典创建"""
        settings_data = data.get("settings", {})
        if isinstance(settings_data, dict):
            settings = UserSettings.from_dict(settings_data)
        else:
            settings = UserSettings()
        
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            password_hash=data["password_hash"],
            public_key=data.get("public_key", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            last_login=datetime.fromisoformat(data["last_login"]) if data.get("last_login") else None,
            is_active=data.get("is_active", True),
            device_fingerprint=data.get("device_fingerprint"),
            settings=settings,
            login_attempts=data.get("login_attempts", 0),
            locked_until=datetime.fromisoformat(data["locked_until"]) if data.get("locked_until") else None
        )
    
    def is_locked(self) -> bool:
        """检查账户是否被锁定"""
        if self.locked_until is None:
            return False
        return datetime.now() < self.locked_until
    
    def reset_login_attempts(self):
        """重置登录尝试次数"""
        self.login_attempts = 0
        self.locked_until = None
