"""WinClaw 后台管理模块 - 管理员认证

管理员凭据配置说明：
1. 优先从环境变量读取（推荐）
2. 如果环境变量未配置，使用默认值（仅用于开发环境）

环境变量：
- ADMIN_USERNAMES: 管理员用户名列表，逗号分隔
- ADMIN_PASSWORDS: 管理员密码，格式 "user1:pass1,user2:pass2"
- ADMIN_SECRET_KEY: JWT 密钥
- ADMIN_TOKEN_EXPIRE_MINUTES: Token 过期时间（分钟）
"""
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt as jose_jwt
import logging

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    # 尝试加载 weclaw_server 目录下的 .env
    env_paths = [
        Path(__file__).parent.parent.parent / ".env",  # weclaw_server/.env
        Path(__file__).parent.parent.parent.parent / ".env",  # 项目根目录/.env
    ]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass  # python-dotenv 未安装，使用默认值

logger = logging.getLogger(__name__)

# ========== 从环境变量读取配置 ==========

# JWT 密钥
ADMIN_SECRET_KEY = os.environ.get(
    "ADMIN_SECRET_KEY", 
    "winclaw_admin_secret_key_change_in_production"
)

# 算法和过期时间
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ADMIN_TOKEN_EXPIRE_MINUTES", "1440"))


def _load_admin_passwords() -> Dict[str, str]:
    """从环境变量加载管理员密码
    
    环境变量格式：ADMIN_PASSWORDS=user1:pass1,user2:pass2
    """
    passwords = {}
    env_passwords = os.environ.get("ADMIN_PASSWORDS", "")
    
    if env_passwords:
        # 解析 "user1:pass1,user2:pass2" 格式
        for item in env_passwords.split(","):
            item = item.strip()
            if ":" in item:
                username, password = item.split(":", 1)
                passwords[username.strip()] = password.strip()
    
    # 安全策略：未配置则返回空字典，禁止登录
    if not passwords:
        logger.error("未配置 ADMIN_PASSWORDS 环境变量，管理后台登录已禁用")
    
    return passwords


# 加载密码配置
admin_passwords = _load_admin_passwords()

# 超级管理员用户名列表（从密码字典中提取）
_admin_usernames_env = os.environ.get("ADMIN_USERNAMES", "")
if _admin_usernames_env:
    ADMIN_USERNAMES = [u.strip() for u in _admin_usernames_env.split(",") if u.strip()]
else:
    # 从密码字典中提取用户名
    ADMIN_USERNAMES = list(admin_passwords.keys())

# 记录配置加载状态日志
if admin_passwords:
    logger.info(f"Admin 认证配置已加载，管理员用户: {list(admin_passwords.keys())}")
else:
    logger.warning("Admin 认证未配置，请配置 .env 文件后重启服务")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT Token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jose_jwt.encode(to_encode, ADMIN_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_admin_token(token: str) -> Optional[dict]:
    """验证 JWT Token"""
    try:
        payload = jose_jwt.decode(token, ADMIN_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"Token 验证失败：{e}")
        return None


async def get_current_admin_user(token: str = Depends(oauth2_scheme)) -> str:
    """获取当前管理员用户
    
    Returns:
        管理员用户名
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证身份",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_admin_token(token)
    if payload is None:
        raise credentials_exception
    
    username: str = payload.get("sub")
    if username not in ADMIN_USERNAMES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    return username


def check_admin_credentials(username: str, password: str) -> bool:
    """检查管理员凭据
    
    从环境变量读取配置，如果未配置则使用默认值
    """
    stored_password = admin_passwords.get(username)
    if not stored_password:
        return False
    
    # 直接比较明文密码
    # TODO: 生产环境应该使用 bcrypt 等安全哈希
    return password == stored_password
