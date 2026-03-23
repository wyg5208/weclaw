"""消息模型

定义消息、工具调用和附件的数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AttachmentType(str, Enum):
    """附件类型"""
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"


@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str
    action: str
    arguments: dict = field(default_factory=dict)
    result: str = ""
    status: str = "pending"  # "success" | "failed" | "pending"
    duration_ms: int = 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "action": self.action,
            "arguments": self.arguments,
            "result": self.result,
            "status": self.status,
            "duration_ms": self.duration_ms
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ToolCall":
        """从字典创建"""
        return cls(
            tool_name=data["tool_name"],
            action=data["action"],
            arguments=data.get("arguments", {}),
            result=data.get("result", ""),
            status=data.get("status", "pending"),
            duration_ms=data.get("duration_ms", 0)
        )


@dataclass
class Attachment:
    """附件模型"""
    attachment_id: str  # UUID格式
    type: AttachmentType
    filename: str
    mime_type: str
    size_bytes: int
    storage_path: str
    thumbnail_path: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "attachment_id": self.attachment_id,
            "type": self.type.value,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "storage_path": self.storage_path,
            "thumbnail_path": self.thumbnail_path
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Attachment":
        """从字典创建"""
        type_value = data.get("type", "file")
        attachment_type = AttachmentType(type_value) if isinstance(type_value, str) else type_value
        
        return cls(
            attachment_id=data["attachment_id"],
            type=attachment_type,
            filename=data["filename"],
            mime_type=data["mime_type"],
            size_bytes=data["size_bytes"],
            storage_path=data["storage_path"],
            thumbnail_path=data.get("thumbnail_path")
        )


@dataclass
class Message:
    """消息模型"""
    message_id: str  # UUID格式
    session_id: str  # 所属会话ID
    role: MessageRole
    content: str
    created_at: datetime
    attachments: list[Attachment] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    # metadata 包含:
    # - model: 使用的AI模型
    # - tokens_used: Token消耗
    # - latency_ms: 响应延迟
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "role": self.role.value,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "attachments": [a.to_dict() for a in self.attachments],
            "tool_calls": [t.to_dict() for t in self.tool_calls],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """从字典创建"""
        role_value = data.get("role", "user")
        role = MessageRole(role_value) if isinstance(role_value, str) else role_value
        
        attachments = [
            Attachment.from_dict(a) for a in data.get("attachments", [])
        ]
        
        tool_calls = [
            ToolCall.from_dict(t) for t in data.get("tool_calls", [])
        ]
        
        return cls(
            message_id=data["message_id"],
            session_id=data["session_id"],
            role=role,
            content=data["content"],
            created_at=datetime.fromisoformat(data["created_at"]),
            attachments=attachments,
            tool_calls=tool_calls,
            metadata=data.get("metadata", {})
        )
    
    def add_tool_call(self, tool_call: ToolCall):
        """添加工具调用记录"""
        self.tool_calls.append(tool_call)
    
    def add_attachment(self, attachment: Attachment):
        """添加附件"""
        self.attachments.append(attachment)
