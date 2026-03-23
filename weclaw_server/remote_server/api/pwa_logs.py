"""PWA 端日志上报接口

接收 PWA 前端上报的日志信息，记录到服务器日志中。
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])


class PWALogEntry(BaseModel):
    """PWA 日志条目结构"""
    
    level: str = Field(..., description="日志级别 (debug, info, warn, error)")
    message: str = Field(..., description="日志消息")
    timestamp: str = Field(..., description="时间戳 (ISO 格式)")
    context: Optional[dict] = Field(default=None, description="上下文信息")
    url: str = Field(..., description="页面 URL")
    sessionId: str = Field(..., description="会话 ID")
    userId: Optional[str] = Field(default=None, description="用户 ID")


class PWALogsRequest(BaseModel):
    """PWA 日志上报请求体"""
    
    logs: List[PWALogEntry] = Field(..., description="日志条目列表")


@router.post("/pwa")
async def receive_pwa_logs(request: PWALogsRequest) -> dict:
    """接收 PWA 端上报的日志。
    
    Args:
        request: 包含日志列表的请求体
        
    Returns:
        处理结果
        
    Example:
        POST /api/logs/pwa
        {
            "logs": [
                {
                    "level": "error",
                    "message": "API 请求失败",
                    "timestamp": "2026-02-26T14:30:00Z",
                    "context": {"url": "/api/chat", "method": "POST"},
                    "url": "https://pwa.example.com",
                    "sessionId": "sess_123456",
                    "userId": "user_789"
                }
            ]
        }
    """
    try:
        for log_entry in request.logs:
            # 根据日志级别选择对应的 logger 方法
            log_message = (
                f"[PWA] {log_entry.level.upper()}: {log_entry.message} | "
                f"Session={log_entry.sessionId[:8]}... | "
                f"URL={log_entry.url} | "
                f"User={log_entry.userId or 'anonymous'}"
            )
            
            # 添加额外字段便于查询
            extra = {
                "pwa_session_id": log_entry.sessionId,
                "pwa_user_id": log_entry.userId,
                "pwa_url": log_entry.url,
                "pwa_timestamp": log_entry.timestamp,
            }
            
            if log_entry.context:
                extra["context"] = log_entry.context
            
            # 根据级别记录日志
            if log_entry.level.lower() == "error":
                logger.error(log_message, extra=extra)
            elif log_entry.level.lower() == "warn":
                logger.warning(log_message, extra=extra)
            elif log_entry.level.lower() == "info":
                logger.info(log_message, extra=extra)
            elif log_entry.level.lower() == "debug":
                logger.debug(log_message, extra=extra)
            else:
                logger.info(log_message, extra=extra)
        
        return {
            "status": "success",
            "received": len(request.logs),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"处理 PWA 日志失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理日志失败：{str(e)}")
