"""会话模型

定义远程会话数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class SessionStatus(str, Enum):
    """会话状态"""
    ACTIVE = "active"
    IDLE = "idle"
    CLOSED = "closed"


@dataclass
class RemoteSession:
    """远程会话模型"""
    session_id: str  # 格式: "remote_{user_id}_{timestamp}"
    user_id: str  # 所属用户ID
    created_at: datetime
    last_active: datetime
    status: SessionStatus = SessionStatus.ACTIVE
    message_count: int = 0
    metadata: dict = field(default_factory=dict)
    # metadata 包含:
    # - device_type: "mobile" | "tablet" | "desktop"
    # - os: "iOS" | "Android" | "Windows" | "macOS"
    # - app_version: PWA版本号
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "status": self.status.value,
            "message_count": self.message_count,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RemoteSession":
        """从字典创建"""
        status_value = data.get("status", "active")
        status = SessionStatus(status_value) if isinstance(status_value, str) else status_value
        
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_active=datetime.fromisoformat(data["last_active"]),
            status=status,
            message_count=data.get("message_count", 0),
            metadata=data.get("metadata", {})
        )
    
    def update_activity(self):
        """更新活跃时间"""
        self.last_active = datetime.now()
    
    def increment_message_count(self):
        """增加消息计数"""
        self.message_count += 1
    
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """检查会话是否过期"""
        if self.status == SessionStatus.CLOSED:
            return True
        elapsed = (datetime.now() - self.last_active).total_seconds()
        return elapsed > timeout_seconds
    
    def close(self):
        """关闭会话"""
        self.status = SessionStatus.CLOSED
