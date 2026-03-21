"""认证 API

提供用户注册、登录、令牌刷新等接口。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator

from .. import context

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


# ========== Pydantic 模型 ==========

class RegisterRequest(BaseModel):
    """注册请求"""
    username: str = Field(..., min_length=3, max_length=32, description="用户名")
    password: str = Field(..., min_length=8, max_length=64, description="密码")
    public_key: str = Field(default="", description="RSA 公钥（PEM 格式）")
    device_fingerprint: Optional[str] = Field(default=None, description="设备指纹")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v and '-' not in v:
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    device_fingerprint: Optional[str] = Field(default=None, description="设备指纹")


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    """刷新请求"""
    # 使用 Authorization 头传递 refresh_token


class UserResponse(BaseModel):
    """用户响应"""
    user_id: str
    username: str
    created_at: str
    last_login: Optional[str]
    is_active: bool
    settings: dict


# ========== 依赖项 ==========

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """获取当前用户（从 JWT Token）"""
    jwt_handler = context.get_jwt_handler()
    if not jwt_handler:
        raise HTTPException(status_code=500, detail="认证服务未初始化")
    
    token = credentials.credentials
    payload = jwt_handler.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="无效或过期的令牌",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return payload


async def get_current_user_with_db(
    payload: dict = Depends(get_current_user)
) -> dict:
    """获取当前用户并验证数据库中的用户状态"""
    user_manager = context.get_user_manager()
    if not user_manager:
        raise HTTPException(status_code=500, detail="用户服务未初始化")
    
    user_id = payload.get("sub")
    user = user_manager.find_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已禁用")
    
    # [建议D] 检查 Token 是否已被吊销
    token_iat = payload.get("iat", 0)
    if user_manager.is_token_revoked(user_id, token_iat):
        raise HTTPException(
            status_code=401,
            detail="Token 已被吊销，请重新登录",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return {"payload": payload, "user": user}


# ========== API 端点 ==========

@router.post("/register", summary="用户注册")
async def register(request: RegisterRequest):
    """
    注册新用户
    
    - **username**: 用户名，3-32字符
    - **password**: 密码，8-64字符
    - **public_key**: RSA公钥（PEM格式），用于加密返回的JWT
    - **device_fingerprint**: 设备指纹（可选）
    """
    user_manager = context.get_user_manager()
    jwt_handler = context.get_jwt_handler()
    rsa_handler = context.get_rsa_handler()
    
    if not user_manager or not jwt_handler:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    try:
        # 创建用户
        user = user_manager.create_user(
            username=request.username,
            password=request.password,
            public_key=request.public_key,
            device_fingerprint=request.device_fingerprint
        )
        
        logger.info(f"用户注册成功: {request.username}")
        
        return {
            "success": True,
            "data": {
                "user_id": user.user_id,
                "username": user.username,
                "created_at": user.created_at.isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"注册失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="注册失败")


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(request: LoginRequest):
    """
    用户登录
    
    返回加密的 JWT Token 对。
    如果用户设置了公钥，access_token 会使用该公钥加密。
    """
    user_manager = context.get_user_manager()
    jwt_handler = context.get_jwt_handler()
    rsa_handler = context.get_rsa_handler()
    
    if not user_manager or not jwt_handler:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 验证用户
    user = user_manager.authenticate(
        username=request.username,
        password=request.password,
        device_fingerprint=request.device_fingerprint
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    # 创建令牌对
    token_pair = jwt_handler.create_token_pair(
        user_id=user.user_id,
        device_fingerprint=request.device_fingerprint
    )
    
    # 如果用户有公钥，加密 access_token
    access_token = token_pair["access_token"]
    if user.public_key and rsa_handler:
        try:
            access_token = rsa_handler.encrypt_for_user(access_token, user.public_key)
        except Exception as e:
            logger.warning(f"加密令牌失败，返回明文：{e}")
    
    # [调试] 记录详细的登录信息
    logger.info(f"用户登录成功：{request.username} (user_id={user.user_id[:8]}, has_device_fp={bool(request.device_fingerprint)})")
    logger.debug(f"[DEBUG] 生成 Token: user_id={user.user_id[:8]}, fp={request.device_fingerprint[:16] if request.device_fingerprint else 'None'}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=token_pair["refresh_token"],
        token_type=token_pair["token_type"],
        expires_in=token_pair["expires_in"],
        user=user.to_dict()
    )


@router.post("/refresh", summary="刷新令牌")
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    刷新访问令牌
    
    使用 refresh_token 获取新的 access_token。
    """
    jwt_handler = context.get_jwt_handler()
    rsa_handler = context.get_rsa_handler()
    user_manager = context.get_user_manager()
    
    if not jwt_handler:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    refresh_token = credentials.credentials
    
    # 验证 refresh_token
    payload = jwt_handler.verify_token(refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="无效或过期的刷新令牌")
    
    user_id = payload.get("sub")
    device_fingerprint = payload.get("device")
    
    # 检查用户状态
    if user_manager:
        user = user_manager.find_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    
    # 创建新的 access_token
    access_token = jwt_handler.create_access_token(
        user_id=user_id,
        device_fingerprint=device_fingerprint
    )
    
    # 如果用户有公钥，加密令牌
    if user and user.public_key and rsa_handler:
        try:
            access_token = rsa_handler.encrypt_for_user(access_token, user.public_key)
        except Exception as e:
            logger.warning(f"加密令牌失败: {e}")
    
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "expires_in": jwt_handler.expires_minutes * 60
        }
    }


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(user_info: dict = Depends(get_current_user_with_db)):
    """获取当前登录用户的详细信息"""
    user = user_info["user"]
    
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
        is_active=user.is_active,
        settings=user.settings.to_dict()
    )


@router.post("/logout", summary="退出登录")
async def logout(user_info: dict = Depends(get_current_user_with_db),
                 credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    退出登录
    
    [建议D] 服务端主动吊销该用户所有 Token，
    确保即使客户端未删除本地 Token 也无法再使用。
    """
    user = user_info["user"]
    user_manager = context.get_user_manager()
    
    # [建议D] 吊销该用户的所有 Token
    if user_manager:
        user_manager.revoke_tokens(user.user_id)
    
    logger.info(f"用户退出登录并吊销 token: {user.username}")
    
    return {
        "success": True,
        "message": "已退出登录"
    }


# ========== 设备绑定 API ==========

class BindingTokenResponse(BaseModel):
    """绑定 Token 响应"""
    binding_token: str
    expires_in: int = 600  # 10分钟有效期
    message: str = "请在 WinClaw PC 端输入此 Token 完成绑定"


class BindDeviceRequest(BaseModel):
    """设备绑定请求"""
    binding_token: str = Field(..., description="绑定 Token")
    device_name: str = Field(default="", description="设备名称")
    device_fingerprint: str = Field(default="", description="设备指纹（自动生成）")


class DeviceInfoResponse(BaseModel):
    """设备信息响应"""
    device_id: str
    device_name: str
    bound_at: str
    last_connected: Optional[str]
    status: str


@router.post("/binding-token", response_model=BindingTokenResponse, summary="生成设备绑定 Token")
async def generate_binding_token(user_info: dict = Depends(get_current_user_with_db)):
    """
    生成设备绑定 Token
    
    用户在 PWA 端生成 Token，然后在 WinClaw PC 端输入 Token 完成绑定。
    每个用户只能绑定一个 WinClaw PC。
    """
    user = user_info["user"]
    user_manager = context.get_user_manager()
    
    if not user_manager:
        raise HTTPException(status_code=500, detail="用户管理器未初始化")
    
    token = user_manager.generate_binding_token(user.user_id)
    
    if not token:
        raise HTTPException(status_code=400, detail="您已绑定设备，请先解绑后再绑定新设备")
    
    logger.info(f"用户 {user.username} 生成绑定 Token")
    
    return BindingTokenResponse(binding_token=token)


@router.post("/bind-device", summary="绑定设备（PC 端调用）")
async def bind_device(request: BindDeviceRequest):
    """
    绑定设备
    
    WinClaw PC 端调用此接口，使用用户提供的绑定 Token 完成绑定。
    设备指纹必须由 PC 端自动生成，不可手动输入。
    
    注意：此 API 不需要认证，通过 binding_token 验证用户身份。
    """
    user_manager = context.get_user_manager()
    jwt_handler = context.get_jwt_handler()
    
    if not user_manager or not jwt_handler:
        raise HTTPException(status_code=500, detail="用户管理器或 JWT 处理器未初始化")
    
    # 验证设备指纹
    if not request.device_fingerprint:
        raise HTTPException(status_code=400, detail="设备指纹不能为空，请确保客户端正常工作")
    
    if len(request.device_fingerprint) < 32:
        raise HTTPException(status_code=400, detail="设备指纹格式无效")
    
    # 通过 binding_token 获取用户 ID
    user_id = user_manager.get_user_id_by_binding_token(request.binding_token)
    if not user_id:
        raise HTTPException(status_code=400, detail="绑定 Token 无效或已过期")
    
    # 生成设备 ID（基于指纹）
    import hashlib
    device_id = hashlib.sha256(
        f"{request.device_fingerprint}:{user_id}".encode()
    ).hexdigest()[:32]
    
    success = user_manager.bind_device(
        binding_token=request.binding_token,
        device_id=device_id,
        device_name=request.device_name or f"WinClaw-{device_id[:8]}",
        device_fingerprint=request.device_fingerprint
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="绑定失败，请检查 Token 是否正确或设备是否已被绑定")
    
    logger.info(f"设备绑定成功：user={user_id[:8]}, device={device_id[:8]}")
    
    # ✅ 新增：生成 JWT Token 对，用于后续认证
    token_pair = jwt_handler.create_token_pair(
        user_id=user_id,
        device_fingerprint=request.device_fingerprint
    )
    
    return {
        "success": True,
        "device_id": device_id,
        "device_name": request.device_name or f"WinClaw-{device_id[:8]}",
        "device_fingerprint": request.device_fingerprint[:16] + "...",
        "message": "设备绑定成功",
        "access_token": token_pair["access_token"],
        "refresh_token": token_pair["refresh_token"],
        "token_type": token_pair.get("token_type", "Bearer")
    }


@router.get("/device", response_model=DeviceInfoResponse, summary="获取绑定的设备信息")
async def get_device_info(user_info: dict = Depends(get_current_user_with_db)):
    """获取当前用户绑定的设备信息（包含在线状态）"""
    user = user_info["user"]
    payload = user_info.get("payload", {})
    
    user_manager = context.get_user_manager()
    
    if not user_manager:
        raise HTTPException(status_code=500, detail="用户管理器未初始化")
    
    # [调试] 记录 Token 中的用户 ID 和实际用户名
    token_user_id = payload.get("sub", "unknown")[:8]
    logger.debug(f"[DEBUG] Token 中的 user_id: {token_user_id}, 解析出的用户名：{user.username}")
    
    device_info = user_manager.get_user_device(user.user_id)
    
    if not device_info:
        logger.warning(f"用户 {user.username} (user_id={user.user_id[:8]}) 未找到设备绑定信息")
        raise HTTPException(status_code=404, detail="未绑定设备")
    
    # ✅ 新增：检查设备在线状态
    from ..websocket.bridge_handler import get_bridge_manager
    bridge_manager = get_bridge_manager()
    
    is_online = False
    connection_details = None
    
    if bridge_manager:
        # 检查用户是否有活跃的连接
        user_connections = bridge_manager.get_user_connections(user.user_id)
        is_online = len(user_connections) > 0
        
        # 收集连接详情
        if is_online:
            connection_details = {
                "session_count": len(user_connections),
                "sessions": [
                    {
                        "session_id": conn.session_id[:16],
                        "device_name": conn.device_name,
                        "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
                        "last_heartbeat": conn.last_heartbeat.isoformat() if conn.last_heartbeat else None
                    }
                    for conn in user_connections
                ]
            }
    
    # 合并在线状态到设备信息
    # 注意：保留数据库中的 status 值（'active'），用 is_online 表示在线状态
    # 前端通过 hasDevice = status === 'active' 判断是否绑定
    device_info["is_online"] = is_online
    # 不覆盖 status 字段，保持数据库中的值（'active' 或其他）
    if connection_details:
        device_info["connection_details"] = connection_details
    
    logger.info(f"用户 {user.username} (user_id={user.user_id[:8]}, token_sub={token_user_id}) 查询设备状态：{'在线' if is_online else '离线'}，device_info={device_info}")
    
    return DeviceInfoResponse(**device_info)


@router.delete("/device", summary="解绑设备")
async def unbind_device(user_info: dict = Depends(get_current_user_with_db)):
    """解绑当前用户的设备，并吊销相关 Token"""
    user = user_info["user"]
    user_manager = context.get_user_manager()
    
    if not user_manager:
        raise HTTPException(status_code=500, detail="用户管理器未初始化")
    
    success = user_manager.unbind_device(user.user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="未找到绑定的设备")
    
    # [建议D] 解绑同时吊销该用户的所有 Token，防止老 token 被继续用于连接
    user_manager.revoke_tokens(user.user_id)
    
    logger.info(f"用户 {user.username} 解绑设备并吊销 token")
    
    return {
        "success": True,
        "message": "设备已解绑"
    }
