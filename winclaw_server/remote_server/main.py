"""FastAPI 主入口

WinClaw 远程服务的主应用入口，提供：
- REST API 接口
- WebSocket 实时通信
- 用户认证中间件
- 静态文件服务
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_config
from .auth.jwt_handler import JWTHandler
from .auth.rsa_handler import RSAHandler
from .auth.user_manager import UserManager
from .websocket.manager import ConnectionManager
from .bridge.winclaw_bridge import WinClawBridge
from . import context  # 导入上下文模块
from .logging_config import setup_logging  # 导入日志配置
from .db.database import init_database  # 导入数据库初始化

# 配置日志（使用统一的日志配置模块）
# setup_logging 将在 lifespan 中调用，确保在应用启动前完成配置
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 初始化日志系统
    setup_logging(
        log_dir="logs",
        level="INFO",
        rotation="D",  # D=每天，H=每小时，W=每周
        backup_count=7,
        enable_console=True,
        enable_file=True,
        separate_error=True
    )
    
    logger.info("="*60)
    logger.info("WinClaw 远程服务启动")
    logger.info("="*60)
    
    config = get_config()
    logger.info(f"监听地址：{config.server.host}:{config.server.port}")
    
    # 初始化 RSA 处理器
    rsa_handler = RSAHandler(
        private_key_path=Path(config.auth.private_key_path),
        public_key_path=Path(config.auth.public_key_path)
    )
    context.set_rsa_handler(rsa_handler)
    logger.info("RSA 密钥处理器初始化完成")
    
    # 初始化 JWT 处理器
    jwt_handler = JWTHandler(
        secret_key=config.auth.secret_key or rsa_handler.get_private_key_pem(),
        algorithm=config.auth.jwt_algorithm,
        expires_minutes=config.auth.access_token_expire_minutes
    )
    context.set_jwt_handler(jwt_handler)
    logger.info("JWT 处理器初始化完成")
    
    # 初始化数据库（用于离线消息队列等服务）
    try:
        await init_database({
            "type": "sqlite",
            "path": "data/remote_users.db"
        })
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.warning(f"数据库初始化失败：{e}，部分功能可能不可用")
    
    # 初始化用户管理器
    user_manager = UserManager(
        db_path=Path("data/remote_users.db"),
        max_login_attempts=config.auth.max_login_attempts,
        lockout_duration_minutes=config.auth.lockout_duration_minutes
    )
    context.set_user_manager(user_manager)
    logger.info("用户管理器初始化完成")
    
    # 修复设备绑定表的历史遗留问题（UNIQUE 约束冲突）
    try:
        from .scripts.fix_device_bindings import fix_database
        fix_database()
        logger.info("设备绑定表修复完成")
    except Exception as e:
        logger.warning(f"修复设备绑定表失败：{e}")
    
    # 初始化 WebSocket 连接管理器
    connection_manager = ConnectionManager(
        heartbeat_interval=config.websocket.heartbeat_interval_seconds,
        connection_timeout=config.websocket.connection_timeout_seconds,
        max_connections_per_user=config.websocket.max_connections_per_user
    )
    context.set_connection_manager(connection_manager)
    logger.info("WebSocket 连接管理器初始化完成")
    
    # 初始化 WinClaw 桥接器（延迟初始化，等待 WinClaw 实例）
    # winclaw_bridge 将在 WinClaw 启动后通过 set_winclaw_instance 设置
    logger.info("等待 WinClaw 实例连接...")
    
    # ✅ Phase 3.2: 启动离线消息监控任务
    try:
        from .monitoring.alerts import start_monitoring_task
        
        # 每 5 分钟检查一次队列健康度
        asyncio.create_task(start_monitoring_task(interval_minutes=5))
        logger.info("离线消息监控任务已启动")
        
        # 注册告警回调（示例：邮件告警）
        from .monitoring.alerts import get_monitor, email_alert_callback
        monitor = get_monitor()
        monitor.register_alert_callback(email_alert_callback)
        
    except Exception as e:
        logger.warning(f"启动监控任务失败：{e}，继续运行主服务")
    
    yield
    
    # 清理资源
    logger.info("关闭 WinClaw 远程服务...")
    conn_mgr = context.get_connection_manager()
    if conn_mgr:
        await conn_mgr.close_all()
    usr_mgr = context.get_user_manager()
    if usr_mgr:
        usr_mgr.close()


# 创建 FastAPI 应用
app = FastAPI(
    title="WinClaw Remote Server",
    description="WinClaw 远程访问 API 服务",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载管理后台子应用
from .admin.main import app as admin_app
app.mount("/admin", admin_app)

# 注册 HTTP 请求日志中间件
from .middleware.logging_middleware import setup_request_logging
setup_request_logging(app)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误"
            }
        }
    )


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    # 检查 Bridge 连接管理器中的 WinClaw 连接
    from .websocket.bridge_handler import get_bridge_manager
    
    bridge_mgr = get_bridge_manager()
    has_connection = bridge_mgr is not None and bridge_mgr.has_connections()
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "winclaw_connected": has_connection
    }


# 根路径
@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "name": "WinClaw Remote Server",
        "version": "1.0.0",
        "description": "WinClaw 远程访问 API 服务",
        "endpoints": {
            "auth": "/api/auth",
            "chat": "/api/chat",
            "status": "/api/status",
            "tools": "/api/tools",
            "files": "/api/files",
            "websocket": "/ws/chat"
        }
    }


# 注册路由
from .api import auth, chat, status, files, commands, pwa_logs

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(chat.router, prefix="/api/chat", tags=["聊天"])
app.include_router(status.router, prefix="/api", tags=["状态"])
app.include_router(files.router, prefix="/api/files", tags=["文件"])
app.include_router(commands.router, prefix="/api/commands", tags=["命令"])
app.include_router(pwa_logs.router, prefix="/api", tags=["PWA 日志"])


# WebSocket 路由
from .websocket.handlers import websocket_endpoint
from .websocket.bridge_handler import bridge_websocket_endpoint, get_bridge_manager

app.add_api_websocket_route("/ws/chat", websocket_endpoint, name="websocket_chat")

# Bridge WebSocket 端点 - WinClaw 桌面端连接
@app.websocket("/ws/bridge")
async def bridge_endpoint(websocket: WebSocket):
    """WinClaw 桌面端 Bridge 连接端点
    
    连接参数:
    - session_id: 会话 ID（必填）
    - device_id: 设备 ID（可选）
    - device_name: 设备名称（可选）
    - device_fingerprint: 设备指纹（推荐，用于身份验证）
    """
    # 从查询参数获取参数
    session_id = websocket.query_params.get("session_id")
    device_id = websocket.query_params.get("device_id", "")
    device_name = websocket.query_params.get("device_name", "")
    device_fingerprint = websocket.query_params.get("device_fingerprint", "")
    
    if not session_id:
        await websocket.close(code=4000, reason="Missing session_id")
        return
    
    await bridge_websocket_endpoint(websocket, session_id, device_id, device_name, device_fingerprint)


# 静态文件由 Nginx 直接服务，不在 FastAPI 中挂载
# 避免静态文件处理器拦截 WebSocket 请求
# static_dir = Path(__file__).parent.parent / "pwa" / "dist"
# if static_dir.exists():
#     app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


def set_winclaw_instance(agent, event_bus, session_manager):
    """设置 WinClaw 实例（由 WinClaw 主程序调用）"""
    conn_mgr = context.get_connection_manager()
    
    bridge = WinClawBridge(
        agent=agent,
        event_bus=event_bus,
        session_manager=session_manager,
        connection_manager=conn_mgr
    )
    context.set_winclaw_bridge(bridge)
    logger.info("WinClaw 实例已连接到远程服务")


def get_winclaw_bridge() -> Optional[WinClawBridge]:
    """获取 WinClaw 桥接器实例"""
    return context.get_winclaw_bridge()


def get_connection_manager() -> Optional[ConnectionManager]:
    """获取 WebSocket 连接管理器"""
    return context.get_connection_manager()


def get_bridge_connection_manager():
    """获取 Bridge 连接管理器"""
    return get_bridge_manager()


def get_user_manager() -> Optional[UserManager]:
    """获取用户管理器"""
    return context.get_user_manager()


def get_jwt_handler() -> Optional[JWTHandler]:
    """获取 JWT 处理器"""
    return context.get_jwt_handler()


def get_rsa_handler() -> Optional[RSAHandler]:
    """获取 RSA 处理器"""
    return context.get_rsa_handler()


if __name__ == "__main__":
    import uvicorn
    
    config = get_config()
    uvicorn.run(
        "remote_server.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug
    )
