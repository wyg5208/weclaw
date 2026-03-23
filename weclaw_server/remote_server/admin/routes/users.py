"""用户管理路由"""
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
import logging
import uuid

from ..auth import get_current_admin_user
from ..database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["admin-users"])

# 模板配置
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("", response_class=HTMLResponse)
async def users_page(request: Request):
    """用户管理页面 - 不需要后端认证，由前端 JavaScript 检查 Token"""
    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "page_title": "用户管理"
        }
    )


@router.get("/list")
async def get_users_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    bound: bool = Query(None),
    current_user: str = Depends(get_current_admin_user)
):
    """获取用户列表（支持分页、搜索、筛选）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 构建查询条件
        conditions = []
        params = []
        
        if search:
            conditions.append("username LIKE ?")
            params.append(f"%{search}%")
        
        if bound is not None:
            if bound:
                conditions.append("db.status = 'active'")
            else:
                conditions.append("(db.status IS NULL OR db.status != 'active')")
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 查询总数
        count_sql = f"""
            SELECT COUNT(DISTINCT u.user_id) 
            FROM users u
            LEFT JOIN device_bindings db ON u.user_id = db.user_id AND db.status = 'active'
            {where_clause}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]
        
        # 查询数据
        offset = (page - 1) * page_size
        sql = f"""
            SELECT 
                u.user_id,
                u.username,
                u.created_at,
                u.last_login,
                u.tokens_revoked_at,
                CASE WHEN db.status = 'active' THEN 1 ELSE 0 END as is_bound,
                db.device_name,
                db.device_fingerprint
            FROM users u
            LEFT JOIN device_bindings db ON u.user_id = db.user_id AND db.status = 'active'
            {where_clause}
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        users = []
        for row in rows:
            users.append({
                "user_id": row["user_id"],
                "username": row["username"],
                "created_at": row["created_at"],
                "last_login": row["last_login"],
                "tokens_revoked_at": row["tokens_revoked_at"],
                "is_bound": bool(row["is_bound"]),
                "device_name": row["device_name"],
                "device_fingerprint": row["device_fingerprint"][:16] + "..." if row["device_fingerprint"] else None
            })
        
        conn.close()
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "items": users
        }
    
    except Exception as e:
        logger.error(f"获取用户列表失败：{e}")
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
async def get_user_detail(user_id: str, current_user: str = Depends(get_current_admin_user)):
    """获取用户详情"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 用户基本信息
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        if not user_row:
            conn.close()
            raise HTTPException(status_code=404, detail="用户不存在")
        
        user = {
            "user_id": user_row["user_id"],
            "username": user_row["username"],
            "created_at": user_row["created_at"],
            "last_login": user_row["last_login"],
            "tokens_revoked_at": user_row["tokens_revoked_at"],
            "is_active": bool(user_row["is_active"])
        }
        
        # 绑定设备信息
        cursor.execute("""
            SELECT * FROM device_bindings 
            WHERE user_id = ? AND status = 'active'
        """, (user_id,))
        device_row = cursor.fetchone()
        
        if device_row:
            user["device"] = {
                "device_id": device_row["device_id"],
                "device_name": device_row["device_name"],
                "device_fingerprint": device_row["device_fingerprint"],
                "bound_at": device_row["bound_at"],
                "last_connected": device_row["last_connected"]
            }
        else:
            user["device"] = None
        
        conn.close()
        
        return user
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户详情失败：{e}")
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: str = Depends(get_current_admin_user)):
    """删除用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查用户是否存在
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 检查是否有绑定设备
        cursor.execute("""
            SELECT binding_id FROM device_bindings 
            WHERE user_id = ? AND status = 'active'
        """, (user_id,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=400, 
                detail="用户已绑定设备，请先解绑设备再删除用户"
            )
        
        # 删除用户
        cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        logger.info(f"管理员 {current_user} 删除了用户 {user_id}")
        
        return {"message": "用户已删除", "success": True}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败：{e}")
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/revoke")
async def revoke_user_token(user_id: str, current_user: str = Depends(get_current_admin_user)):
    """吊销用户 Token"""
    from ...auth.user_manager import UserManager
    from ..database import DB_PATH
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查用户是否存在
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 吊销 Token
        um = UserManager(DB_PATH)
        success = um.revoke_tokens(user_id)
        
        conn.close()
        
        if success:
            logger.info(f"管理员 {current_user} 吊销了用户 {user_id} 的 Token")
            return {"message": "Token 已吊销", "success": True}
        else:
            raise HTTPException(status_code=500, detail="吊销失败")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"吊销 Token 失败：{e}")
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
