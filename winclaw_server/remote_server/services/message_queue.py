"""离线消息队列服务

用于管理 WinClaw 离线时 PWA 用户发送的消息，支持服务器重启后数据不丢失。
"""

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass

from ..models.offline_message import OfflineMessage, MessagePriority, MessageStatus
from ..db.database import get_database

logger = logging.getLogger(__name__)


@dataclass
class PendingMessage:
    """内存中的消息对象（用于临时处理）"""
    message_id: str
    user_id: str
    content: str
    attachments: list
    created_at: datetime
    expires_at: datetime
    priority: MessagePriority = MessagePriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return datetime.utcnow() > self.expires_at


class OfflineMessageQueue:
    """离线消息队列服务（内存 + 数据库双写）"""
    
    _instance: Optional['OfflineMessageQueue'] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化队列服务"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        # 延迟获取数据库实例，避免在服务器启动前访问
        self.db = None
        try:
            self.db = get_database()
            if self.db is None:
                logger.warning("数据库未初始化，离线消息队列将使用内存模式")
        except Exception as e:
            logger.warning(f"获取数据库失败：{e}，离线消息队列将使用内存模式")
        
        # 内存缓存：用于快速访问
        self._memory_queues: Dict[str, deque[PendingMessage]] = {}
        self._initialized = True
        
        logger.info("离线消息队列服务已初始化")
    
    async def enqueue(
        self,
        user_id: str,
        content: str,
        attachments: Optional[list] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl_minutes: int = 30
    ) -> str:
        """入队消息（同时写入数据库和内存）
        
        Args:
            user_id: 用户 ID
            content: 消息内容
            attachments: 附件列表
            priority: 优先级
            ttl_minutes: TTL（分钟）
            
        Returns:
            消息 ID
        """
        message_id = f"om_{datetime.utcnow().timestamp()}_{user_id[:8]}"
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=ttl_minutes)
        
        # 1. 写入数据库（如果有）
        if self.db:
            try:
                db_message = OfflineMessage(
                    message_id=message_id,
                    user_id=user_id,
                    content=content,
                    attachments=json.dumps(attachments) if attachments else "",
                    created_at=now,
                    expires_at=expires_at,
                    priority=priority,
                    status=MessageStatus.PENDING,
                    retry_count=0,
                    max_retries=3
                )
                
                await self.db.execute("""
                    INSERT INTO offline_messages 
                    (id, user_id, content, attachments, created_at, expires_at, priority, status, retry_count, max_retries)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    db_message.message_id,
                    db_message.user_id,
                    db_message.content,
                    db_message.attachments,
                    db_message.created_at.isoformat(),
                    db_message.expires_at.isoformat(),
                    db_message.priority.value,
                    db_message.status.value,
                    db_message.retry_count,
                    db_message.max_retries
                ))
            except Exception as e:
                logger.error(f"保存离线消息到数据库失败：{e}")
        
        # 2. 写入内存缓存（总是执行）
        if user_id not in self._memory_queues:
            self._memory_queues[user_id] = deque(maxlen=50)  # 最多 50 条
        
        pending_msg = PendingMessage(
            message_id=message_id,
            user_id=user_id,
            content=content,
            attachments=attachments or [],
            created_at=now,
            expires_at=expires_at,
            priority=priority
        )
        self._memory_queues[user_id].append(pending_msg)
        
        logger.info(f"离线消息已保存：user={user_id[:8]}, msg={message_id[:8]}")
        return message_id
    
    async def flush_to_winclaw(self, user_id: str, winclaw_session_id: str, bridge_manager) -> int:
        """WinClaw 上线后发送所有待处理消息
        
        Args:
            user_id: 用户 ID
            winclaw_session_id: WinClaw 会话 ID
            bridge_manager: Bridge 管理器
            
        Returns:
            发送的消息数量
        """
        if not self.db:
            # 数据库未初始化，只发送内存中的消息
            logger.warning("数据库未初始化，跳过离线消息同步")
            return 0
        
        try:
            # 从数据库查询未过期的消息
            rows = await self.db.fetchall("""
                SELECT * FROM offline_messages
                WHERE user_id = ? AND status = 'pending'
                AND expires_at > ?
                ORDER BY created_at ASC
            """, (user_id, datetime.utcnow().isoformat()))
            
            sent_count = 0
            for row in rows:
                try:
                    # 构建消息
                    msg = PendingMessage(
                        message_id=row["id"],
                        user_id=row["user_id"],
                        content=row["content"],
                        attachments=json.loads(row["attachments"]) if row["attachments"] else [],
                        created_at=datetime.fromisoformat(row["created_at"]),
                        expires_at=datetime.fromisoformat(row["expires_at"]),
                        priority=MessagePriority(row["priority"]),
                        retry_count=row["retry_count"]
                    )
                    
                    # 发送到 WinClaw
                    await bridge_manager.send_to_winclaw(winclaw_session_id, {
                        "type": "chat",
                        "request_id": msg.message_id,
                        "payload": {
                            "content": msg.content,
                            "attachments": msg.attachments,
                            "user_id": user_id
                        }
                    })
                    
                    # 更新状态为已发送
                    await self.db.execute("""
                        UPDATE offline_messages
                        SET status = 'sent', retry_count = retry_count + 1
                        WHERE id = ?
                    """, (msg.message_id,))
                    
                    sent_count += 1
                    logger.info(f"离线消息已发送：msg={msg.message_id[:8]}")
                    
                except Exception as e:
                    logger.error(f"发送离线消息失败：{e}")
                    # 增加重试次数
                    await self.db.execute("""
                        UPDATE offline_messages
                        SET retry_count = retry_count + 1,
                            status = CASE WHEN retry_count + 1 >= max_retries THEN 'failed' ELSE 'pending' END
                        WHERE id = ?
                    """, (row["id"],))
            
            return sent_count
            
        except Exception as e:
            logger.error(f"批量发送离线消息失败：{e}", exc_info=True)
            return 0
    
    async def cleanup_expired(self) -> int:
        """定期清理过期消息（定时任务）
        
        Returns:
            清理的消息数量
        """
        try:
            result = await self.db.execute("""
                DELETE FROM offline_messages
                WHERE expires_at < ?
            """, (datetime.utcnow().isoformat(),))
            
            cleaned_count = result.rowcount if hasattr(result, 'rowcount') else 0
            logger.info(f"已清理过期离线消息：{cleaned_count} 条")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期消息失败：{e}", exc_info=True)
            return 0
    
    async def get_pending_count(self, user_id: str) -> int:
        """获取用户待处理消息数量"""
        try:
            row = await self.db.fetchone("""
                SELECT COUNT(*) as count FROM offline_messages
                WHERE user_id = ? AND status = 'pending'
                AND expires_at > ?
            """, (user_id, datetime.utcnow().isoformat()))
            
            return row["count"] if row else 0
            
        except Exception as e:
            logger.error(f"获取待处理消息数量失败：{e}", exc_info=True)
            return 0
    
    async def get_all_pending_count(self) -> int:
        """获取所有待处理消息总数"""
        if not self.db:
            # 数据库未初始化，返回内存中的数量
            total = sum(len(q) for q in self._memory_queues.values())
            return total
        
        try:
            row = await self.db.fetchone("""
                SELECT COUNT(*) as count FROM offline_messages
                WHERE status = 'pending' AND expires_at > ?
            """, (datetime.utcnow().isoformat(),))
            
            return row["count"] if row else 0
            
        except Exception as e:
            logger.error(f"获取所有待处理消息数量失败：{e}", exc_info=True)
            return 0


# 全局单例
_queue_instance: Optional[OfflineMessageQueue] = None


def get_message_queue() -> OfflineMessageQueue:
    """获取消息队列单例"""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = OfflineMessageQueue()
    return _queue_instance


async def start_cleanup_task(interval_minutes: int = 60):
    """启动定期清理任务"""
    queue = get_message_queue()
    
    while True:
        await asyncio.sleep(interval_minutes * 60)
        try:
            await queue.cleanup_expired()
        except Exception as e:
            logger.error(f"定期清理任务失败：{e}")
