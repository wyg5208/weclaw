"""统计分析路由"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime, timedelta
import logging

from ..auth import get_current_admin_user
from ..database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/statistics", tags=["admin-statistics"])

# 模板配置
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("", response_class=HTMLResponse)
async def statistics_page(request: Request):
    """统计分析页面 - 不需要后端认证，由前端 JavaScript 检查 Token"""
    return templates.TemplateResponse(
        "statistics.html",
        {
            "request": request,
            "page_title": "统计分析"
        }
    )


@router.get("/overview")
async def get_statistics_overview(current_user: str = Depends(get_current_admin_user)):
    """获取统计概览数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 用户增长趋势（最近 7 天）
        user_growth = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).date()
            date_str = date.isoformat()
            
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE created_at LIKE ?
            """, (f"{date_str}%",))
            
            count = cursor.fetchone()[0]
            user_growth.append({
                "date": date_str,
                "count": count
            })
        
        # 绑定率统计
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM device_bindings WHERE status='active'")
        bound_users = cursor.fetchone()[0]
        
        binding_rate = round((bound_users / total_users * 100) if total_users > 0 else 0, 2)
        
        # 设备绑定趋势（最近 7 天）
        device_growth = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).date()
            date_str = date.isoformat()
            
            cursor.execute("""
                SELECT COUNT(*) FROM device_bindings 
                WHERE status = 'active' AND bound_at LIKE ?
            """, (f"{date_str}%",))
            
            count = cursor.fetchone()[0]
            device_growth.append({
                "date": date_str,
                "count": count
            })
        
        # 用户状态分布
        unbound_users = total_users - bound_users
        
        conn.close()
        
        return {
            "user_growth": user_growth,
            "device_growth": device_growth,
            "total_users": total_users,
            "bound_users": bound_users,
            "unbound_users": unbound_users,
            "binding_rate": binding_rate
        }
    
    except Exception as e:
        logger.error(f"获取统计数据失败：{e}")
        conn.close()
        return {
            "user_growth": [],
            "device_growth": [],
            "total_users": 0,
            "bound_users": 0,
            "unbound_users": 0,
            "binding_rate": 0.0
        }
