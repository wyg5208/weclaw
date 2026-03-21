"""日志查看路由"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
import logging
import os

from ..auth import get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["admin-logs"])

# 模板配置
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# 日志文件路径
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
REMOTE_LOG_FILE = LOGS_DIR / "remote_server.log"
ERROR_LOG_FILE = LOGS_DIR / "error.log"


@router.get("", response_class=HTMLResponse)
async def logs_page(request: Request):
    """日志查看页面 - 不需要后端认证，由前端 JavaScript 检查 Token"""
    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "page_title": "日志中心"
        }
    )


@router.get("/list")
async def get_logs(
    log_type: str = Query("remote", pattern="^(remote|error)$"),
    level: str = Query(None, pattern="^(INFO|WARNING|ERROR|CRITICAL)$"),
    lines: int = Query(100, ge=10, le=1000),
    search: str = Query(None),
    current_user: str = Depends(get_current_admin_user)
):
    """获取日志列表"""
    try:
        # 确定日志文件
        if log_type == "error":
            log_file = ERROR_LOG_FILE
        else:
            log_file = REMOTE_LOG_FILE
        
        if not log_file.exists():
            return {"items": [], "message": "日志文件不存在"}
        
        # 读取日志
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # 只取最新 N 行
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # 过滤和解析
        logs = []
        for line in recent_lines:
            line = line.strip()
            if not line:
                continue
            
            # 级别过滤
            if level and level not in line:
                continue
            
            # 关键词搜索
            if search and search.lower() not in line.lower():
                continue
            
            # 简单解析
            log_entry = parse_log_line(line)
            if log_entry:
                logs.append(log_entry)
        
        # 按时间倒序（最新的在前）
        logs.reverse()
        
        return {"items": logs[:lines]}  # 限制返回数量
    
    except Exception as e:
        logger.error(f"读取日志失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


def parse_log_line(line: str) -> dict:
    """解析日志行
    
    预期格式：[LEVEL] YYYY-MM-DD HH:MM:SS - message
    或：YYYY-MM-DD HH:MM:SS,mmm - LEVEL - module: message
    """
    try:
        # 尝试匹配常见日志格式
        if line.startswith('['):
            # 格式 1: [LEVEL] timestamp - message
            end_level = line.find(']')
            if end_level != -1:
                level = line[1:end_level]
                rest = line[end_level+2:].split(' - ', 1)
                if len(rest) == 2:
                    timestamp_str, message = rest
                    return {
                        "level": level,
                        "timestamp": timestamp_str,
                        "message": message.strip(),
                        "raw": line
                    }
        elif ',' in line[:30]:  # 可能是标准 logging 格式
            # 格式 2: timestamp - LEVEL - module: message
            parts = line.split(' - ', 2)
            if len(parts) >= 2:
                timestamp_str = parts[0]
                level = parts[1] if len(parts) > 1 else "INFO"
                message = parts[2] if len(parts) > 2 else parts[1]
                return {
                    "level": level,
                    "timestamp": timestamp_str,
                    "message": message.strip(),
                    "raw": line
                }
        
        # 无法解析，返回原始行
        return {
            "level": "INFO",
            "timestamp": "",
            "message": line,
            "raw": line
        }
    
    except Exception:
        return {
            "level": "INFO",
            "timestamp": "",
            "message": line,
            "raw": line
        }


@router.get("/download")
async def download_logs(
    log_type: str = Query("remote", pattern="^(remote|error)$"),
    current_user: str = Depends(get_current_admin_user)
):
    """下载日志文件"""
    from fastapi.responses import FileResponse
    
    try:
        # 确定日志文件
        if log_type == "error":
            log_file = ERROR_LOG_FILE
        else:
            log_file = REMOTE_LOG_FILE
        
        if not log_file.exists():
            raise HTTPException(status_code=404, detail="日志文件不存在")
        
        # 返回文件下载
        filename = f"{log_type}_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        return FileResponse(
            path=str(log_file),
            filename=filename,
            media_type="text/plain"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载日志失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))
