"""状态 API

提供 WinClaw 运行状态、工具列表等接口。
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from .. import context
from .auth import get_current_user_with_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", summary="获取 WinClaw 状态")
async def get_status():
    """
    获取 WinClaw 运行状态
    
    无需认证，公开接口。
    """
    bridge = context.get_winclaw_bridge()
    
    if not bridge:
        return {
            "success": True,
            "data": {
                "status": "offline",
                "version": None,
                "uptime_seconds": 0,
                "current_task": None,
                "model": None,
                "statistics": None
            }
        }
    
    status_data = bridge.get_status()
    
    return {
        "success": True,
        "data": status_data
    }


@router.get("/tools", summary="获取可用工具列表")
async def get_tools():
    """
    获取 WinClaw 可用工具列表
    
    无需认证，公开接口。
    """
    bridge = context.get_winclaw_bridge()
    
    if not bridge or not bridge.is_connected():
        return {
            "success": True,
            "data": {
                "tools": [],
                "total": 0,
                "message": "WinClaw 未连接"
            }
        }
    
    tools = bridge.get_tools()
    
    return {
        "success": True,
        "data": {
            "tools": tools,
            "total": len(tools)
        }
    }


@router.get("/tools/{tool_name}", summary="获取工具详情")
async def get_tool_detail(tool_name: str):
    """获取指定工具的详细信息"""
    bridge = context.get_winclaw_bridge()
    
    if not bridge or not bridge.is_connected():
        raise HTTPException(status_code=503, detail="WinClaw 未连接")
    
    tools = bridge.get_tools()
    tool = next((t for t in tools if t.get("name") == tool_name), None)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在")
    
    return {
        "success": True,
        "data": tool
    }


@router.get("/sessions", summary="获取用户会话列表")
async def get_sessions(user_info: dict = Depends(get_current_user_with_db)):
    """获取当前用户的会话列表"""
    user = user_info["user"]
    connection_manager = context.get_connection_manager()
    
    # 获取用户活跃会话
    sessions = []
    if connection_manager:
        sessions = connection_manager.get_user_sessions(user.user_id)
    
    return {
        "success": True,
        "data": {
            "sessions": sessions,
            "total": len(sessions)
        }
    }


@router.get("/health", summary="健康检查")
async def health_check():
    """
    服务健康检查端点
    
    用于负载均衡器或监控服务检测。
    """
    bridge = context.get_winclaw_bridge()
    connection_manager = context.get_connection_manager()
    
    return {
        "status": "healthy",
        "components": {
            "server": "ok",
            "winclaw": "connected" if bridge and bridge.is_connected() else "disconnected",
            "websocket": "ok" if connection_manager else "unavailable"
        },
        "active_connections": connection_manager.get_connection_count() if connection_manager else 0
    }
