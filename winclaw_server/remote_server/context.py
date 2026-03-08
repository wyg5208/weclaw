"""全局上下文模块

存放全局实例和获取函数，避免循环导入问题。
"""

from typing import Optional, Any

# 全局实例
_jwt_handler: Any = None
_rsa_handler: Any = None
_user_manager: Any = None
_connection_manager: Any = None
_winclaw_bridge: Any = None
_bridge_manager: Any = None


def set_jwt_handler(handler: Any):
    """设置 JWT 处理器"""
    global _jwt_handler
    _jwt_handler = handler


def get_jwt_handler() -> Optional[Any]:
    """获取 JWT 处理器"""
    return _jwt_handler


def set_rsa_handler(handler: Any):
    """设置 RSA 处理器"""
    global _rsa_handler
    _rsa_handler = handler


def get_rsa_handler() -> Optional[Any]:
    """获取 RSA 处理器"""
    return _rsa_handler


def set_user_manager(manager: Any):
    """设置用户管理器"""
    global _user_manager
    _user_manager = manager


def get_user_manager() -> Optional[Any]:
    """获取用户管理器"""
    return _user_manager


def set_connection_manager(manager: Any):
    """设置 WebSocket 连接管理器"""
    global _connection_manager
    _connection_manager = manager


def get_connection_manager() -> Optional[Any]:
    """获取 WebSocket 连接管理器"""
    return _connection_manager


def set_winclaw_bridge(bridge: Any):
    """设置 WinClaw 桥接器"""
    global _winclaw_bridge
    _winclaw_bridge = bridge


def get_winclaw_bridge() -> Optional[Any]:
    """获取 WinClaw 桥接器"""
    return _winclaw_bridge


def set_bridge_manager(manager: Any):
    """设置 Bridge 连接管理器"""
    global _bridge_manager
    _bridge_manager = manager


def get_bridge_manager() -> Optional[Any]:
    """获取 Bridge 连接管理器"""
    return _bridge_manager


def reset_all():
    """重置所有全局实例（用于测试）"""
    global _jwt_handler, _rsa_handler, _user_manager
    global _connection_manager, _winclaw_bridge, _bridge_manager
    
    _jwt_handler = None
    _rsa_handler = None
    _user_manager = None
    _connection_manager = None
    _winclaw_bridge = None
    _bridge_manager = None
