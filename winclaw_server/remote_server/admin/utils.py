"""后台管理模块工具函数"""
import hashlib
from datetime import datetime
from typing import Optional


def hash_password(password: str) -> str:
    """对密码进行 SHA256 哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return hash_password(password) == hashed


def format_bytes(size: int) -> str:
    """格式化字节大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def parse_log_line(line: str) -> Optional[dict]:
    """解析日志行
    
    格式：[LEVEL] timestamp - message
    """
    try:
        # 简单解析，实际可能需要更复杂的逻辑
        if line.startswith('['):
            end_level = line.find(']')
            level = line[1:end_level]
            rest = line[end_level+2:].split(' - ', 1)
            if len(rest) == 2:
                timestamp_str, message = rest
                return {
                    'level': level,
                    'timestamp': timestamp_str,
                    'message': message.strip()
                }
        return None
    except Exception:
        return None
