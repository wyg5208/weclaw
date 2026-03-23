"""设备管理路由"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging

from ..auth import get_current_admin_user
from ..database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/devices", tags=["admin-devices"])

# 模板配置
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("", response_class=HTMLResponse)
async def devices_page(request: Request):
    """设备管理页面 - 不需要后端认证，由前端 JavaScript 检查 Token"""
    return templates.TemplateResponse(
        "devices.html",
        {
            "request": request,
            "page_title": "设备管理"
        }
    )


@router.get("/list")
async def get_devices_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: str = Depends(get_current_admin_user)
):
    """获取设备列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询总数
        cursor.execute("""
            SELECT COUNT(*) FROM device_bindings WHERE status = 'active'
        """)
        total = cursor.fetchone()[0]
        
        # 查询数据
        offset = (page - 1) * page_size
        cursor.execute("""
            SELECT 
                db.binding_id,
                db.user_id,
                u.username,
                db.device_id,
                db.device_name,
                db.device_fingerprint,
                db.bound_at,
                db.last_connected
            FROM device_bindings db
            LEFT JOIN users u ON db.user_id = u.user_id
            WHERE db.status = 'active'
            ORDER BY db.bound_at DESC
            LIMIT ? OFFSET ?
        """, (page_size, offset))
        rows = cursor.fetchall()
        
        devices = []
        for row in rows:
            devices.append({
                "binding_id": row["binding_id"],
                "user_id": row["user_id"],
                "username": row["username"],
                "device_id": row["device_id"],
                "device_name": row["device_name"] or "N/A",
                "device_fingerprint": row["device_fingerprint"],
                "bound_at": row["bound_at"],
                "last_connected": row["last_connected"]
            })
        
        conn.close()
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "items": devices
        }
    
    except Exception as e:
        logger.error(f"获取设备列表失败：{e}")
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{binding_id}/unbind")
async def unbind_device(binding_id: str, current_user: str = Depends(get_current_admin_user)):
    """解绑设备"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查绑定是否存在
        cursor.execute("""
            SELECT binding_id, user_id FROM device_bindings 
            WHERE binding_id = ? AND status = 'active'
        """, (binding_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="绑定不存在")
        
        user_id = row["user_id"]
        
        # 更新绑定状态为 inactive
        cursor.execute("""
            UPDATE device_bindings 
            SET status = 'inactive'
            WHERE binding_id = ?
        """, (binding_id,))
        
        conn.commit()
        
        # 吊销用户 Token
        from ...auth.user_manager import UserManager
        from ..database import DB_PATH as ADMIN_DB_PATH
        
        um = UserManager(ADMIN_DB_PATH)
        um.revoke_tokens(user_id)
        
        conn.close()
        
        logger.info(f"管理员 {current_user} 解绑了设备 {binding_id}，用户 {user_id}")
        
        return {"message": "设备已解绑", "success": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解绑设备失败：{e}")
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
