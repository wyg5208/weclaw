"""WeClaw 后台管理主应用"""
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

from .auth import create_access_token, check_admin_credentials, get_current_admin_user
from .routes import dashboard, users, devices, logs, statistics

logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="WeClaw Admin API",
    description="WeClaw 后台管理系统 API",
    version="1.0.0"
)

# CORS 配置（允许跨域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录（CDN 资源）
cdn_resources_path = Path(__file__).parent / "cdn_resources"
app.mount("/cdn_resources", StaticFiles(directory=str(cdn_resources_path)), name="cdn_resources")

# 注册路由
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(devices.router)
app.include_router(logs.router)
app.include_router(statistics.router)


# 登录页面
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """管理员登录页面"""
    from fastapi.templating import Jinja2Templates
    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "page_title": "管理员登录"}
    )


# 登出
@app.get("/logout")
async def logout():
    """管理员登出"""
    # 重定向到 Admin 登录页（而不是 PWA 登录页）
    return RedirectResponse(url="/admin/login")


# API: 管理员登录
@app.post("/api/admin/login")
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    """管理员登录接口"""
    if not check_admin_credentials(form_data.username, form_data.password):
        return JSONResponse(
            status_code=401,
            content={"detail": "用户名或密码错误"}
        )
    
    # 创建 access token
    access_token = create_access_token(data={"sub": form_data.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "weclaw-admin"}


# 首页重定向
@app.get("/")
async def index():
    """首页重定向到仪表盘"""
    return RedirectResponse(url="/admin/dashboard")
