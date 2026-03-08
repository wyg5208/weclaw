"""命令 API

提供远程命令执行接口。
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from .. import context
from .auth import get_current_user_with_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Pydantic 模型 ==========

class ExecuteRequest(BaseModel):
    """执行命令请求"""
    tool: str = Field(..., description="工具名称")
    action: str = Field(..., description="动作名称")
    arguments: dict = Field(default_factory=dict, description="参数")


class ExecuteResponse(BaseModel):
    """执行命令响应"""
    success: bool
    result: str
    duration_ms: int


# ========== API 端点 ==========

@router.post("/execute", response_model=ExecuteResponse, summary="执行工具命令")
async def execute_command(
    request: ExecuteRequest,
    user_info: dict = Depends(get_current_user_with_db)
):
    """
    直接执行工具命令
    
    用于高级用户直接调用 WinClaw 工具。
    需要认证，且某些敏感工具可能需要额外权限。
    """
    user = user_info["user"]
    bridge = context.get_winclaw_bridge()
    
    if not bridge or not bridge.is_connected():
        raise HTTPException(status_code=503, detail="WinClaw 未连接")
    
    # 执行命令
    try:
        result = await bridge.execute_tool(
            user_id=user.user_id,
            tool=request.tool,
            action=request.action,
            arguments=request.arguments
        )
        
        return ExecuteResponse(
            success=result.get("success", False),
            result=result.get("result", ""),
            duration_ms=result.get("duration_ms", 0)
        )
        
    except Exception as e:
        logger.error(f"执行命令失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"执行失败: {str(e)}")


@router.get("/available", summary="获取可用命令")
async def get_available_commands(user_info: dict = Depends(get_current_user_with_db)):
    """获取用户可执行的命令列表"""
    bridge = context.get_winclaw_bridge()
    
    if not bridge or not bridge.is_connected():
        return {
            "success": True,
            "data": {
                "commands": [],
                "total": 0
            }
        }
    
    tools = bridge.get_tools()
    
    # 展开为命令列表
    commands = []
    for tool in tools:
        tool_name = tool.get("name", "")
        actions = tool.get("actions", [])
        
        for action in actions:
            commands.append({
                "tool": tool_name,
                "action": action,
                "description": tool.get("description", ""),
                "category": tool.get("category", "general")
            })
    
    return {
        "success": True,
        "data": {
            "commands": commands,
            "total": len(commands)
        }
    }


@router.post("/validate", summary="验证命令")
async def validate_command(
    request: ExecuteRequest,
    user_info: dict = Depends(get_current_user_with_db)
):
    """
    验证命令是否有效
    
    不执行命令，只检查参数是否正确。
    """
    bridge = context.get_winclaw_bridge()
    
    if not bridge or not bridge.is_connected():
        raise HTTPException(status_code=503, detail="WinClaw 未连接")
    
    # 验证命令
    validation_result = bridge.validate_tool_call(
        tool=request.tool,
        action=request.action,
        arguments=request.arguments
    )
    
    return {
        "success": True,
        "data": {
            "valid": validation_result.get("valid", False),
            "errors": validation_result.get("errors", []),
            "warnings": validation_result.get("warnings", [])
        }
    }
