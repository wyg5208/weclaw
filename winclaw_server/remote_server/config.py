"""远程服务配置模块

从 config/remote_server.toml 加载配置，提供全局配置访问。
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tomli


@dataclass
class DatabaseConfig:
    """数据库配置"""
    type: str = "sqlite"  # "mysql" 或 "sqlite"
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = ""
    database: str = "winclaw"
    pool_size: int = 10
    sqlite_path: str = "data/remote_users.db"


@dataclass
class RedisConfig:
    """Redis 配置"""
    enabled: bool = True
    host: str = "localhost"
    port: int = 6379
    password: str = ""
    db: int = 0


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False


@dataclass
class AuthConfig:
    """认证配置"""
    jwt_algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    secret_key: str = ""  # 运行时从环境变量或密钥文件加载
    private_key_path: str = "keys/private.pem"
    public_key_path: str = "keys/public.pem"


@dataclass
class WebSocketConfig:
    """WebSocket 配置"""
    heartbeat_interval_seconds: int = 30
    connection_timeout_seconds: int = 300
    max_connections_per_user: int = 3


@dataclass
class FilesConfig:
    """文件上传配置"""
    upload_dir: str = "uploads"
    max_file_size_mb: int = 50
    allowed_types: list[str] = field(default_factory=lambda: [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "audio/wav", "audio/mp3", "audio/mpeg", "audio/webm",
        "application/pdf", "text/plain"
    ])
    thumbnail_size: tuple[int, int] = (200, 200)


@dataclass
class BridgeConfig:
    """WinClaw 桥接配置"""
    winclaw_agent_timeout_seconds: int = 120
    stream_chunk_timeout_seconds: int = 60


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    enabled: bool = True
    requests_per_minute: int = 60
    burst: int = 10


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: str = "logs/remote_server.log"


@dataclass
class RemoteServerConfig:
    """远程服务完整配置"""
    server: ServerConfig = field(default_factory=ServerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    files: FilesConfig = field(default_factory=FilesConfig)
    bridge: BridgeConfig = field(default_factory=BridgeConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def from_toml(cls, path: Path) -> "RemoteServerConfig":
        """从 TOML 文件加载配置"""
        if not path.exists():
            return cls()
        
        with open(path, "rb") as f:
            data = tomli.load(f)
        
        config = cls()
        
        # 服务器配置
        if "server" in data:
            config.server = ServerConfig(**data["server"])
        
        # 数据库配置
        if "database" in data:
            config.database = DatabaseConfig(**data["database"])
        
        # Redis 配置
        if "redis" in data:
            config.redis = RedisConfig(**data["redis"])
        
        # 认证配置
        if "auth" in data:
            config.auth = AuthConfig(**data["auth"])
        
        # WebSocket 配置
        if "websocket" in data:
            config.websocket = WebSocketConfig(**data["websocket"])
        
        # 文件配置
        if "files" in data:
            files_data = data["files"].copy()
            if "thumbnail_size" in files_data and isinstance(files_data["thumbnail_size"], list):
                files_data["thumbnail_size"] = tuple(files_data["thumbnail_size"])
            config.files = FilesConfig(**files_data)
        
        # 桥接配置
        if "bridge" in data:
            config.bridge = BridgeConfig(**data["bridge"])
        
        # 速率限制配置
        if "rate_limit" in data:
            config.rate_limit = RateLimitConfig(**data["rate_limit"])
        
        # 日志配置
        if "logging" in data:
            config.logging = LoggingConfig(**data["logging"])
        
        return config


# 全局配置实例
_config: Optional[RemoteServerConfig] = None


def get_config() -> RemoteServerConfig:
    """获取全局配置实例"""
    global _config
    if _config is None:
        config_path = Path(__file__).parent.parent / "config" / "remote_server.toml"
        _config = RemoteServerConfig.from_toml(config_path)
    return _config


def reload_config(config_path: Optional[Path] = None) -> RemoteServerConfig:
    """重新加载配置"""
    global _config
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "remote_server.toml"
    _config = RemoteServerConfig.from_toml(config_path)
    return _config
