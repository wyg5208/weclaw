"""仪表盘路由 - 显示系统概览和统计数据"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime, timedelta
import logging

from ..auth import get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["admin-dashboard"])

# 模板配置
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """仪表盘页面 - 不需要后端认证，由前端 JavaScript 检查 Token"""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "page_title": "仪表盘"
        }
    )


@router.get("/stats")
async def dashboard_stats(current_user: str = Depends(get_current_admin_user)):
    """获取仪表盘统计数据"""
    from ..database import get_db_connection, DB_PATH
    
    logger.info(f"正在获取统计数据，数据库路径：{DB_PATH}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 总用户数
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        # 已绑定设备的用户数
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM device_bindings WHERE status='active'")
        bound_users = cursor.fetchone()[0]
        
        # Active 设备总数
        cursor.execute("SELECT COUNT(*) FROM device_bindings WHERE status='active'")
        active_devices = cursor.fetchone()[0]
        
        # 今日新增用户 (假设 created_at 是 ISO 格式)
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE created_at LIKE ?
        """, (f"{today}%",))
        today_new_users = cursor.fetchone()[0]
        
        conn.close()
        
        logger.info(f"统计数据获取成功：总用户={total_users}, 已绑定={bound_users}")
        
        return {
            "total_users": total_users,
            "bound_users": bound_users,
            "unbound_users": total_users - bound_users,
            "active_devices": active_devices,
            "today_new_users": today_new_users,
            "binding_rate": round((bound_users / total_users * 100) if total_users > 0 else 0, 2)
        }
    
    except Exception as e:
        logger.error(f"获取统计数据失败：{e}", exc_info=True)
        if 'conn' in locals():
            conn.close()
        return {
            "total_users": 0,
            "bound_users": 0,
            "unbound_users": 0,
            "active_devices": 0,
            "today_new_users": 0,
            "binding_rate": 0,
            "error": str(e)
        }
