"""服务模块

提供各类业务逻辑服务。
"""

from .message_queue import get_message_queue, start_cleanup_task

__all__ = [
    "get_message_queue",
    "start_cleanup_task"
]
