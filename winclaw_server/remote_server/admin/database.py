"""数据库连接辅助模块"""
import sqlite3
from pathlib import Path
from typing import Generator


# 数据库路径 - 与主服务保持一致
# 主服务使用 data/remote_users.db（相对于工作目录）
# Admin 模块需要找到正确的数据库文件

# 尝试多个可能的数据库路径
POSSIBLE_PATHS = [
    Path(__file__).parent.parent.parent / "data" / "remote_users.db",  # weclaw_server/data/remote_users.db
    Path(__file__).parent.parent / "data" / "remote_users.db",  # remote_server/data/remote_users.db
    Path("data/remote_users.db"),  # 相对路径
]

DB_PATH = None
for path in POSSIBLE_PATHS:
    if path.exists():
        DB_PATH = path
        break

if DB_PATH is None:
    # 默认使用第一个路径
    DB_PATH = POSSIBLE_PATHS[0]


def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接
    
    Returns:
        sqlite3.Connection 对象，已设置 row_factory
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def db_context() -> Generator[sqlite3.Connection, None, None]:
    """数据库上下文管理器
    
    Yields:
        sqlite3.Connection 对象
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()
