"""远程桥接客户端模块

连接远程服务器，实现 WinClaw 桌面端与移动端的交互。
支持远程附件持久化存储和历史检索。
"""

from .client import RemoteBridgeClient
from .message_handler import MessageHandler
from .status_reporter import StatusReporter
from .device_fingerprint import get_device_fingerprint, get_device_id, DeviceFingerprint
from .attachment_storage import (
    AttachmentStorage,
    StoredAttachment,
    get_attachment_storage,
    search_user_attachments,
)

__all__ = [
    "RemoteBridgeClient", 
    "MessageHandler", 
    "StatusReporter",
    "get_device_fingerprint",
    "get_device_id",
    "DeviceFingerprint",
    # 附件存储
    "AttachmentStorage",
    "StoredAttachment",
    "get_attachment_storage",
    "search_user_attachments",
]
