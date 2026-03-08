"""远程附件持久化存储

支持：
- 附件元数据持久化（SQLite）
- 本地缓存管理
- 基于描述/文件名的模糊搜索
- 历史附件检索和再次调用
- 区分当前对话和历史对话的附件

设计原则：
- 每个附件关联 user_id（用户隔离）和 session_id（对话隔离）
- 当前对话的附件：直接使用，不需要搜索
- 历史对话的附件：需要通过搜索工具查找

使用场景：
- 用户说"我昨天上传的关于拙政园的图片"
- 系统可以检索到历史附件并再次分析
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

# 默认存储路径
DEFAULT_ATTACHMENTS_DIR = Path.home() / ".winclaw" / "remote_attachments"
DEFAULT_DB_PATH = Path.home() / ".winclaw" / "attachments.db"


@dataclass
class StoredAttachment:
    """存储的附件元数据"""
    id: str                     # 附件ID（attachment_id）
    session_id: str             # 关联的远程会话ID
    user_id: str                # 用户ID
    filename: str               # 原始文件名
    file_type: str              # 类型：image/audio/file
    mime_type: str              # MIME类型
    local_path: str             # 本地缓存路径
    remote_url: str             # 远程URL
    file_size: int              # 文件大小（字节）
    description: str = ""       # 描述（从用户消息中提取，用于搜索）
    ocr_text: str = ""          # OCR识别的文字（便于搜索图片内容）
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 1       # 访问次数
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "local_path": self.local_path,
            "remote_url": self.remote_url,
            "file_size": self.file_size,
            "description": self.description,
            "ocr_text": self.ocr_text,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
        }


class AttachmentStorage:
    """附件持久化存储"""
    
    def __init__(
        self,
        db_path: Path | str | None = None,
        attachments_dir: Path | str | None = None,
        max_cache_size_mb: int = 500,  # 最大缓存大小 500MB
        max_cache_days: int = 30,      # 最大缓存天数 30天
    ):
        """
        初始化附件存储
        
        Args:
            db_path: 数据库文件路径
            attachments_dir: 附件缓存目录
            max_cache_size_mb: 最大缓存大小（MB）
            max_cache_days: 最大缓存天数
        """
        self._db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._attachments_dir = Path(attachments_dir) if attachments_dir else DEFAULT_ATTACHMENTS_DIR
        self._max_cache_size_mb = max_cache_size_mb
        self._max_cache_days = max_cache_days
        
        # 确保目录存在
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._attachments_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._ensure_tables()
        
        logger.info(f"附件存储初始化完成: db={self._db_path}, cache={self._attachments_dir}")
    
    def _ensure_tables(self) -> None:
        """确保数据库表已创建"""
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS attachments (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    remote_url TEXT NOT NULL,
                    file_size INTEGER DEFAULT 0,
                    description TEXT DEFAULT '',
                    ocr_text TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 1
                )
            """)
            # 创建索引以加速搜索
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_user ON attachments(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_session ON attachments(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_created ON attachments(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_attachments_filename ON attachments(filename)")
            conn.commit()
        finally:
            conn.close()
    
    @property
    def attachments_dir(self) -> Path:
        """获取附件缓存目录"""
        return self._attachments_dir
    
    def save_attachment(self, attachment: StoredAttachment) -> bool:
        """保存附件元数据
        
        Args:
            attachment: 附件元数据
            
        Returns:
            是否保存成功
        """
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO attachments 
                (id, session_id, user_id, filename, file_type, mime_type, 
                 local_path, remote_url, file_size, description, ocr_text,
                 created_at, last_accessed, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attachment.id,
                attachment.session_id,
                attachment.user_id,
                attachment.filename,
                attachment.file_type,
                attachment.mime_type,
                attachment.local_path,
                attachment.remote_url,
                attachment.file_size,
                attachment.description,
                attachment.ocr_text,
                attachment.created_at.isoformat(),
                attachment.last_accessed.isoformat(),
                attachment.access_count,
            ))
            conn.commit()
            logger.info(f"保存附件元数据: {attachment.filename} (id={attachment.id[:8]})")
            return True
        except Exception as e:
            logger.error(f"保存附件元数据失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_attachment(self, attachment_id: str) -> Optional[StoredAttachment]:
        """根据ID获取附件
        
        Args:
            attachment_id: 附件ID
            
        Returns:
            附件元数据，不存在返回None
        """
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("""
                SELECT id, session_id, user_id, filename, file_type, mime_type,
                       local_path, remote_url, file_size, description, ocr_text,
                       created_at, last_accessed, access_count
                FROM attachments WHERE id = ?
            """, (attachment_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_attachment(row)
            return None
        finally:
            conn.close()
    
    def search_attachments(
        self,
        user_id: str,
        query: str = "",
        file_type: str = "",
        days: int = 30,
        limit: int = 10,
    ) -> list[StoredAttachment]:
        """搜索附件
        
        支持模糊搜索：文件名、描述、OCR文字
        
        Args:
            user_id: 用户ID
            query: 搜索关键词（搜索文件名、描述、OCR文字）
            file_type: 文件类型过滤（image/audio/file）
            days: 搜索最近N天的附件
            limit: 返回数量限制
            
        Returns:
            匹配的附件列表
        """
        conn = sqlite3.connect(self._db_path)
        try:
            # 构建查询条件
            conditions = ["user_id = ?"]
            params: list[Any] = [user_id]
            
            if query:
                # 模糊搜索：文件名、描述、OCR文字
                conditions.append("""
                    (filename LIKE ? OR description LIKE ? OR ocr_text LIKE ?)
                """)
                like_query = f"%{query}%"
                params.extend([like_query, like_query, like_query])
            
            if file_type:
                conditions.append("file_type = ?")
                params.append(file_type)
            
            if days > 0:
                from datetime import timedelta
                cutoff = (datetime.now() - timedelta(days=days)).isoformat()
                conditions.append("created_at > ?")
                params.append(cutoff)
            
            params.append(limit)
            
            sql = f"""
                SELECT id, session_id, user_id, filename, file_type, mime_type,
                       local_path, remote_url, file_size, description, ocr_text,
                       created_at, last_accessed, access_count
                FROM attachments
                WHERE {' AND '.join(conditions)}
                ORDER BY last_accessed DESC
                LIMIT ?
            """
            
            cursor = conn.execute(sql, params)
            return [self._row_to_attachment(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def update_access(self, attachment_id: str) -> None:
        """更新附件访问记录
        
        Args:
            attachment_id: 附件ID
        """
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                UPDATE attachments 
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
            """, (datetime.now().isoformat(), attachment_id))
            conn.commit()
        finally:
            conn.close()
    
    def update_ocr_text(self, attachment_id: str, ocr_text: str) -> None:
        """更新附件的OCR识别文字
        
        Args:
            attachment_id: 附件ID
            ocr_text: OCR识别的文字
        """
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                UPDATE attachments SET ocr_text = ? WHERE id = ?
            """, (ocr_text, attachment_id))
            conn.commit()
            logger.info(f"更新附件OCR文字: {attachment_id[:8]}, 长度={len(ocr_text)}")
        finally:
            conn.close()
    
    def update_description(self, attachment_id: str, description: str) -> None:
        """更新附件描述
        
        Args:
            attachment_id: 附件ID
            description: 描述文字
        """
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("""
                UPDATE attachments SET description = ? WHERE id = ?
            """, (description, attachment_id))
            conn.commit()
        finally:
            conn.close()
    
    def get_recent_attachments(
        self,
        user_id: str,
        limit: int = 10,
        file_type: str = "",
    ) -> list[StoredAttachment]:
        """获取最近的附件
        
        Args:
            user_id: 用户ID
            limit: 返回数量
            file_type: 类型过滤
            
        Returns:
            最近的附件列表
        """
        return self.search_attachments(
            user_id=user_id,
            file_type=file_type,
            days=0,  # 不限制天数
            limit=limit,
        )
    
    def get_session_attachments(
        self,
        user_id: str,
        session_id: str,
    ) -> list[StoredAttachment]:
        """获取指定会话的所有附件（当前对话的附件）
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            该会话的所有附件列表
        """
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("""
                SELECT id, session_id, user_id, filename, file_type, mime_type,
                       local_path, remote_url, file_size, description, ocr_text,
                       created_at, last_accessed, access_count
                FROM attachments
                WHERE user_id = ? AND session_id = ?
                ORDER BY created_at DESC
            """, (user_id, session_id))
            return [self._row_to_attachment(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_other_session_attachments(
        self,
        user_id: str,
        current_session_id: str,
        query: str = "",
        limit: int = 10,
    ) -> list[StoredAttachment]:
        """获取其他会话的附件（历史对话的附件，排除当前会话）
        
        Args:
            user_id: 用户ID
            current_session_id: 当前会话ID（要排除）
            query: 搜索关键词
            limit: 返回数量
            
        Returns:
            其他会话的附件列表
        """
        conn = sqlite3.connect(self._db_path)
        try:
            conditions = ["user_id = ?", "session_id != ?"]
            params: list[Any] = [user_id, current_session_id]
            
            if query:
                conditions.append("""
                    (filename LIKE ? OR description LIKE ? OR ocr_text LIKE ?)
                """)
                like_query = f"%{query}%"
                params.extend([like_query, like_query, like_query])
            
            params.append(limit)
            
            sql = f"""
                SELECT id, session_id, user_id, filename, file_type, mime_type,
                       local_path, remote_url, file_size, description, ocr_text,
                       created_at, last_accessed, access_count
                FROM attachments
                WHERE {' AND '.join(conditions)}
                ORDER BY last_accessed DESC
                LIMIT ?
            """
            
            cursor = conn.execute(sql, params)
            return [self._row_to_attachment(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def cleanup_old_cache(self) -> int:
        """清理过期的缓存文件
        
        Returns:
            清理的文件数量
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=self._max_cache_days)
        removed_count = 0
        
        conn = sqlite3.connect(self._db_path)
        try:
            # 查找过期的附件
            cursor = conn.execute("""
                SELECT id, local_path FROM attachments
                WHERE last_accessed < ?
                ORDER BY last_accessed ASC
            """, (cutoff.isoformat(),))
            
            for row in cursor.fetchall():
                attachment_id, local_path = row
                path = Path(local_path)
                if path.exists():
                    try:
                        path.unlink()
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"删除缓存文件失败: {path}, 错误: {e}")
                
                # 删除数据库记录
                conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
            
            conn.commit()
            
            if removed_count > 0:
                logger.info(f"清理了 {removed_count} 个过期缓存文件")
            
            return removed_count
        finally:
            conn.close()
    
    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute("""
                SELECT COUNT(*), SUM(file_size), MIN(created_at), MAX(last_accessed)
                FROM attachments
            """)
            row = cursor.fetchone()
            
            total_count = row[0] or 0
            total_size = row[1] or 0
            oldest = row[2] or ""
            newest = row[3] or ""
            
            # 按类型统计
            cursor = conn.execute("""
                SELECT file_type, COUNT(*) FROM attachments GROUP BY file_type
            """)
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                "total_count": total_count,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_created": oldest,
                "newest_accessed": newest,
                "by_type": type_counts,
                "cache_dir": str(self._attachments_dir),
            }
        finally:
            conn.close()
    
    def _row_to_attachment(self, row: tuple) -> StoredAttachment:
        """将数据库行转换为 StoredAttachment 对象"""
        return StoredAttachment(
            id=row[0],
            session_id=row[1],
            user_id=row[2],
            filename=row[3],
            file_type=row[4],
            mime_type=row[5],
            local_path=row[6],
            remote_url=row[7],
            file_size=row[8],
            description=row[9],
            ocr_text=row[10],
            created_at=datetime.fromisoformat(row[11]),
            last_accessed=datetime.fromisoformat(row[12]),
            access_count=row[13],
        )


# 全局实例（懒加载）
_attachment_storage: Optional[AttachmentStorage] = None


def get_attachment_storage() -> AttachmentStorage:
    """获取附件存储单例"""
    global _attachment_storage
    if _attachment_storage is None:
        _attachment_storage = AttachmentStorage()
    return _attachment_storage


def search_user_attachments(
    user_id: str,
    query: str,
    file_type: str = "image",
    limit: int = 5,
) -> list[dict]:
    """便捷函数：搜索用户的附件
    
    Args:
        user_id: 用户ID
        query: 搜索关键词
        file_type: 文件类型
        limit: 返回数量
        
    Returns:
        附件信息列表
    """
    storage = get_attachment_storage()
    attachments = storage.search_attachments(
        user_id=user_id,
        query=query,
        file_type=file_type,
        limit=limit,
    )
    return [att.to_dict() for att in attachments]
