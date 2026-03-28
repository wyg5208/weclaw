"""统一文件缓存管理器

Phase 2: OCR 统一缓存层核心实现

功能：
- 基于文件 SHA256 指纹的缓存
- TTL 自动过期清理
- 兼容 document_scanner 的现有 scanner.db
- 支持多种缓存类型（ocr, vision, pdf 等）

使用方式：
    from src.core.cache import FileCacheManager
    
    cache = FileCacheManager()
    
    # 检查缓存
    cached = await cache.get("abc123", "ocr")
    if cached:
        return cached
    
    # 设置缓存
    await cache.set("abc123", "ocr", {"text": "...", "boxes": [...]})
"""

import aiosqlite
import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)


class FileCacheManager:
    """统一文件缓存管理器
    
    基于文件指纹的缓存，支持 TTL 过期自动清理。
    """
    
    DEFAULT_TTL_DAYS = 7
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        legacy_db_path: Optional[str] = None
    ):
        """初始化缓存管理器
        
        Args:
            db_path: 新缓存库路径，默认 ~/.weclaw/file_cache.db
            legacy_db_path: 兼容旧库路径，默认 ~/.weclaw/scanner.db
        """
        # 新缓存库
        self.db_path = Path(db_path) if db_path else Path.home() / ".weclaw" / "file_cache.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 兼容旧库（document_scanner 使用的 scanner.db）
        self.legacy_db_path = Path(legacy_db_path) if legacy_db_path else Path.home() / ".weclaw" / "scanner.db"
        
        self._initialized = False
    
    async def _ensure_db(self):
        """确保数据库已初始化"""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # 创建缓存表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    file_hash TEXT NOT NULL,
                    cache_type TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    PRIMARY KEY (file_hash, cache_type)
                )
            """)
            
            # 创建索引
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_hash 
                ON file_cache(file_hash)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires 
                ON file_cache(expires_at)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_type 
                ON file_cache(cache_type)
            """)
            
            await db.commit()
        
        self._initialized = True
        logger.info(f"文件缓存管理器初始化完成: {self.db_path}")
    
    @staticmethod
    def compute_hash(file_path: str) -> str:
        """计算文件 SHA256 哈希
        
        Args:
            file_path: 文件路径
            
        Returns:
            32位十六进制哈希字符串
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:32]
    
    async def get(
        self,
        file_hash: str,
        cache_type: str = "ocr"
    ) -> Optional[dict]:
        """获取缓存结果
        
        Args:
            file_hash: 文件哈希
            cache_type: 缓存类型 (ocr, vision, pdf 等)
            
        Returns:
            缓存结果字典，如果不存在或已过期返回 None
        """
        await self._ensure_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT result_json, expires_at FROM file_cache 
                WHERE file_hash = ? AND cache_type = ?
            """, (file_hash, cache_type))
            
            row = await cursor.fetchone()
            
            if not row:
                # 尝试从旧库获取
                return await self._get_from_legacy(file_hash, cache_type)
            
            result_json, expires_at_str = row
            expires_at = datetime.fromisoformat(expires_at_str)
            
            # 检查是否过期
            if datetime.now() > expires_at:
                # 删除过期缓存
                await db.execute("""
                    DELETE FROM file_cache 
                    WHERE file_hash = ? AND cache_type = ?
                """, (file_hash, cache_type))
                await db.commit()
                return None
            
            # 更新命中计数
            await db.execute("""
                UPDATE file_cache SET hit_count = hit_count + 1
                WHERE file_hash = ? AND cache_type = ?
            """, (file_hash, cache_type))
            await db.commit()
            
            logger.debug(f"缓存命中: {file_hash[:8]}... ({cache_type})")
            return json.loads(result_json)
    
    async def _get_from_legacy(
        self,
        file_hash: str,
        cache_type: str
    ) -> Optional[dict]:
        """从旧库获取缓存（兼容 document_scanner）
        
        Args:
            file_hash: 文件哈希
            cache_type: 缓存类型
            
        Returns:
            缓存结果字典
        """
        if not self.legacy_db_path.exists():
            return None
        
        try:
            async with aiosqlite.connect(str(self.legacy_db_path)) as db:
                # 尝试从 scan_records 表获取（document_scanner 使用的表）
                cursor = await db.execute("""
                    SELECT md_file_path, json_file_path, problem_count, status
                    FROM scan_records 
                    WHERE file_hash = ? AND status = 'success'
                """, (file_hash,))
                
                row = await cursor.fetchone()
                
                if row:
                    md_path, json_path, problem_count, status = row
                    result = {
                        "cached": True,
                        "md_file_path": md_path,
                        "json_file_path": json_path,
                        "problem_count": problem_count,
                        "legacy": True  # 标记为旧库缓存
                    }
                    logger.info(f"从旧库恢复缓存: {file_hash[:8]}...")
                    return result
                    
        except Exception as e:
            logger.warning(f"读取旧库缓存失败: {e}")
        
        return None
    
    async def set(
        self,
        file_hash: str,
        cache_type: str,
        result: dict,
        ttl_days: Optional[int] = None
    ) -> None:
        """设置缓存
        
        Args:
            file_hash: 文件哈希
            cache_type: 缓存类型
            result: 缓存结果数据
            ttl_days: 过期天数，默认 7 天
        """
        await self._ensure_db()
        
        ttl_days = ttl_days or self.DEFAULT_TTL_DAYS
        expires_at = datetime.now() + timedelta(days=ttl_days)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO file_cache 
                (file_hash, cache_type, result_json, expires_at, hit_count)
                VALUES (?, ?, ?, ?, COALESCE(
                    (SELECT hit_count FROM file_cache WHERE file_hash = ? AND cache_type = ?),
                    0
                ))
            """, (
                file_hash,
                cache_type,
                json.dumps(result, ensure_ascii=False),
                expires_at.isoformat(),
                file_hash,
                cache_type
            ))
            await db.commit()
        
        logger.debug(f"缓存已保存: {file_hash[:8]}... ({cache_type})")
    
    async def delete(
        self,
        file_hash: str,
        cache_type: Optional[str] = None
    ) -> int:
        """删除缓存
        
        Args:
            file_hash: 文件哈希
            cache_type: 缓存类型，如果为 None 则删除所有该哈希的缓存
            
        Returns:
            删除的缓存数量
        """
        await self._ensure_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            if cache_type:
                cursor = await db.execute("""
                    DELETE FROM file_cache 
                    WHERE file_hash = ? AND cache_type = ?
                """, (file_hash, cache_type))
            else:
                cursor = await db.execute("""
                    DELETE FROM file_cache WHERE file_hash = ?
                """, (file_hash,))
            
            await db.commit()
            deleted = cursor.rowcount
        
        logger.info(f"缓存已删除: {file_hash[:8]}... ({cache_type or 'all'})")
        return deleted
    
    async def cleanup_expired(self) -> int:
        """清理过期缓存
        
        Returns:
            清理的缓存数量
        """
        await self._ensure_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM file_cache 
                WHERE expires_at < ?
            """, (datetime.now().isoformat(),))
            
            await db.commit()
            deleted = cursor.rowcount
        
        if deleted > 0:
            logger.info(f"清理了 {deleted} 条过期缓存")
        
        return deleted
    
    async def get_stats(self) -> dict:
        """获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        await self._ensure_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            # 总数
            cursor = await db.execute("SELECT COUNT(*) FROM file_cache")
            total = (await cursor.fetchone())[0]
            
            # 过期数
            cursor = await db.execute(
                "SELECT COUNT(*) FROM file_cache WHERE expires_at < ?",
                (datetime.now().isoformat(),)
            )
            expired = (await cursor.fetchone())[0]
            
            # 有效数
            valid = total - expired
            
            # 按类型统计
            cursor = await db.execute("""
                SELECT cache_type, COUNT(*), SUM(hit_count)
                FROM file_cache
                GROUP BY cache_type
            """)
            type_stats = {}
            for row in await cursor.fetchall():
                cache_type, count, hits = row
                type_stats[cache_type] = {"count": count, "hits": hits or 0}
            
            # 缓存文件大小
            cache_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        
        return {
            "total": total,
            "valid": valid,
            "expired": expired,
            "by_type": type_stats,
            "size_bytes": cache_size,
            "size_mb": round(cache_size / (1024 * 1024), 2)
        }
    
    async def clear_all(self) -> int:
        """清空所有缓存
        
        Returns:
            删除的缓存数量
        """
        await self._ensure_db()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM file_cache")
            total = (await cursor.fetchone())[0]
            
            await db.execute("DELETE FROM file_cache")
            await db.commit()
        
        logger.warning(f"已清空所有缓存: {total} 条")
        return total


# 全局单例
_global_cache: Optional[FileCacheManager] = None


def get_cache() -> FileCacheManager:
    """获取全局缓存管理器单例
    
    Returns:
        FileCacheManager 实例
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = FileCacheManager()
    return _global_cache

