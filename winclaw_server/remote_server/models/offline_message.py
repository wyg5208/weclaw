"""离线消息模型

用于存储 WinClaw 离线时 PWA 用户发送的消息，支持服务器重启后数据不丢失。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum


class MessagePriority(str, Enum):
    """消息优先级"""
    HIGH = "high"      # 高优先级（VIP 用户）
    NORMAL = "normal"  # 普通优先级
    LOW = "low"        # 低优先级


class MessageStatus(str, Enum):
    """消息状态"""
    PENDING = "pending"   # 待发送
    SENT = "sent"         # 已发送
    EXPIRED = "expired"   # 已过期
    FAILED = "failed"     # 发送失败


@dataclass
class OfflineMessage:
    """离线消息
    
    Attributes:
        message_id: 消息唯一 ID
        user_id: 用户 ID
        content: 消息内容
        attachments: 附件列表（JSON 字符串）
        created_at: 创建时间
        expires_at: 过期时间
        priority: 优先级
        status: 状态
        retry_count: 重试次数
        max_retries: 最大重试次数
    """
    message_id: str
    user_id: str
    content: str
    attachments: str = ""  # JSON 字符串
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    priority: MessagePriority = MessagePriority.NORMAL
    status: MessageStatus = MessageStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        """初始化后处理"""
        if self.expires_at is None:
            # 根据优先级设置默认 TTL
            ttl_map = {
                MessagePriority.HIGH: 60,     # 高优先级 60 分钟
                MessagePriority.NORMAL: 30,   # 普通 30 分钟
                MessagePriority.LOW: 10       # 低优先级 10 分钟
            }
            ttl_minutes = ttl_map.get(self.priority, 30)
            self.expires_at = self.created_at + timedelta(minutes=ttl_minutes)
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def can_retry(self) -> bool:
        """检查是否可以重试"""
        return self.retry_count < self.max_retries
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "user_id": self.user_id,
            "content": self.content,
            "attachments": self.attachments,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "priority": self.priority.value,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "OfflineMessage":
        """从字典创建"""
        return cls(
            message_id=data["message_id"],
            user_id=data["user_id"],
            content=data["content"],
            attachments=data.get("attachments", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            priority=MessagePriority(data.get("priority", "normal")),
            status=MessageStatus(data.get("status", "pending")),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )
