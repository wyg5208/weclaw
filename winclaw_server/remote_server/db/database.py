"""数据库抽象层

支持 MySQL 和 SQLite 双数据库，通过配置切换。
"""

import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any
import json

logger = logging.getLogger(__name__)


class DatabaseBackend(ABC):
    """数据库后端抽象基类"""
    
    @abstractmethod
    async def initialize(self):
        """初始化数据库"""
        pass
    
    @abstractmethod
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        pass
    
    @abstractmethod
    async def execute(self, query: str, params: tuple = ()) -> Any:
        """执行SQL"""
        pass
    
    @abstractmethod
    async def fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        """查询单条"""
        pass
    
    @abstractmethod
    async def fetchall(self, query: str, params: tuple = ()) -> List[dict]:
        """查询多条"""
        pass
    
    @abstractmethod
    async def close(self):
        """关闭连接"""
        pass


class SQLiteBackend(DatabaseBackend):
    """SQLite 数据库后端"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._pool = None
        
    async def initialize(self):
        """初始化 SQLite 数据库"""
        import sqlite3
        
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建表
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(self._get_create_tables_sql())
            conn.commit()
        
        logger.info(f"SQLite 数据库初始化完成: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    async def execute(self, query: str, params: tuple = ()) -> Any:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
    
    async def fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    async def fetchall(self, query: str, params: tuple = ()) -> List[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    async def close(self):
        pass  # SQLite 每次操作后自动关闭
    
    def _get_create_tables_sql(self) -> str:
        """获取建表SQL"""
        return """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            public_key TEXT,
            created_at TEXT NOT NULL,
            last_login TEXT,
            is_active INTEGER DEFAULT 1,
            device_fingerprint TEXT,
            settings TEXT,
            login_attempts INTEGER DEFAULT 0,
            locked_until TEXT
        );
        
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_active TEXT NOT NULL,
            status TEXT NOT NULL,
            message_count INTEGER DEFAULT 0,
            metadata TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );
        
        CREATE TABLE IF NOT EXISTS attachments (
            attachment_id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            type TEXT NOT NULL,
            filename TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            storage_path TEXT NOT NULL,
            thumbnail_path TEXT,
            FOREIGN KEY (message_id) REFERENCES messages(message_id)
        );
        
        CREATE TABLE IF NOT EXISTS tool_calls (
            call_id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            action TEXT NOT NULL,
            arguments TEXT,
            result TEXT,
            status TEXT NOT NULL,
            duration_ms INTEGER,
            FOREIGN KEY (message_id) REFERENCES messages(message_id)
        );
        
        -- ✅ 新增：离线消息表（Phase 2.1）
        CREATE TABLE IF NOT EXISTS offline_messages (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            attachments TEXT,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            priority TEXT DEFAULT 'normal',
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3
        );
        
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
        CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments(message_id);
        -- ✅ 新增：离线消息索引（Phase 2.1）
        CREATE INDEX IF NOT EXISTS idx_offline_messages_user ON offline_messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_offline_messages_status ON offline_messages(status);
        CREATE INDEX IF NOT EXISTS idx_offline_messages_expires ON offline_messages(expires_at);
        """


class MySQLBackend(DatabaseBackend):
    """MySQL 数据库后端"""
    
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        pool_size: int = 5
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.pool_size = pool_size
        self._pool = None
    
    async def initialize(self):
        """初始化 MySQL 数据库"""
        import aiomysql
        
        # 创建连接池
        self._pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            minsize=1,
            maxsize=self.pool_size,
            autocommit=True,
            charset='utf8mb4'
        )
        
        # 创建表
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(self._get_create_tables_sql())
        
        logger.info(f"MySQL 数据库初始化完成: {self.host}:{self.port}/{self.database}")
    
    @contextmanager
    def get_connection(self):
        """MySQL 使用 async with，不使用此方法"""
        raise NotImplementedError("MySQL 请使用 async 方法")
    
    async def execute(self, query: str, params: tuple = ()) -> Any:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params)
                return cursor
    
    async def fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchone()
    
    async def fetchall(self, query: str, params: tuple = ()) -> List[dict]:
        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, params)
                return await cursor.fetchall()
    
    async def close(self):
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
    
    def _get_create_tables_sql(self) -> str:
        """获取建表SQL（MySQL语法）"""
        return """
        CREATE TABLE IF NOT EXISTS users (
            user_id VARCHAR(36) PRIMARY KEY,
            username VARCHAR(32) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            public_key TEXT,
            created_at DATETIME NOT NULL,
            last_login DATETIME,
            is_active TINYINT DEFAULT 1,
            device_fingerprint VARCHAR(255),
            settings JSON,
            login_attempts INT DEFAULT 0,
            locked_until DATETIME
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        
        CREATE TABLE IF NOT EXISTS sessions (
            session_id VARCHAR(64) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            created_at DATETIME NOT NULL,
            last_active DATETIME NOT NULL,
            status VARCHAR(20) NOT NULL,
            message_count INT DEFAULT 0,
            metadata JSON,
            INDEX idx_sessions_user (user_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        
        CREATE TABLE IF NOT EXISTS messages (
            message_id VARCHAR(36) PRIMARY KEY,
            session_id VARCHAR(64) NOT NULL,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            metadata JSON,
            INDEX idx_messages_session (session_id),
            INDEX idx_messages_created (created_at),
            FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        
        CREATE TABLE IF NOT EXISTS attachments (
            attachment_id VARCHAR(36) PRIMARY KEY,
            message_id VARCHAR(36) NOT NULL,
            type VARCHAR(20) NOT NULL,
            filename VARCHAR(255) NOT NULL,
            mime_type VARCHAR(100) NOT NULL,
            size_bytes INT NOT NULL,
            storage_path VARCHAR(500) NOT NULL,
            thumbnail_path VARCHAR(500),
            INDEX idx_attachments_message (message_id),
            FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        
        CREATE TABLE IF NOT EXISTS tool_calls (
            call_id VARCHAR(36) PRIMARY KEY,
            message_id VARCHAR(36) NOT NULL,
            tool_name VARCHAR(50) NOT NULL,
            action VARCHAR(50) NOT NULL,
            arguments JSON,
            result TEXT,
            status VARCHAR(20) NOT NULL,
            duration_ms INT,
            FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        
        -- ✅ 新增：离线消息表（Phase 2.1）
        CREATE TABLE IF NOT EXISTS offline_messages (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            content TEXT NOT NULL,
            attachments JSON,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL,
            priority VARCHAR(20) DEFAULT 'normal',
            status VARCHAR(20) DEFAULT 'pending',
            retry_count INT DEFAULT 0,
            max_retries INT DEFAULT 3,
            INDEX idx_offline_messages_user (user_id),
            INDEX idx_offline_messages_status (status),
            INDEX idx_offline_messages_expires (expires_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """


class Database:
    """数据库管理器"""
    
    def __init__(self, backend: DatabaseBackend):
        self.backend = backend
    
    async def initialize(self):
        await self.backend.initialize()
    
    async def execute(self, query: str, params: tuple = ()):
        return await self.backend.execute(query, params)
    
    async def fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        return await self.backend.fetchone(query, params)
    
    async def fetchall(self, query: str, params: tuple = ()) -> List[dict]:
        return await self.backend.fetchall(query, params)
    
    async def close(self):
        await self.backend.close()


# 全局数据库实例
_db: Optional[Database] = None


def get_database() -> Optional[Database]:
    """获取数据库实例"""
    return _db


async def init_database(config: dict) -> Database:
    """初始化数据库"""
    global _db
    
    db_type = config.get("type", "sqlite")
    
    if db_type == "mysql":
        backend = MySQLBackend(
            host=config.get("host", "localhost"),
            port=config.get("port", 3306),
            user=config.get("user", "root"),
            password=config.get("password", ""),
            database=config.get("database", "winclaw"),
            pool_size=config.get("pool_size", 5)
        )
    else:
        backend = SQLiteBackend(
            db_path=Path(config.get("path", "data/remote_users.db"))
        )
    
    _db = Database(backend)
    await _db.initialize()
    
    return _db
