"""WebSocket 消息处理器

处理 WebSocket 消息的接收和转发。
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect, Query

from .. import context

logger = logging.getLogger(__name__)


async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT Token")
):
    """
    WebSocket 端点
    
    通过 JWT Token 认证，建立 WebSocket 连接后可进行实时双向通信。
    
    消息格式:
    - 发送消息: {"type": "message", "payload": {"content": "..."}}
    - 停止生成: {"type": "stop_generation"}
    - 心跳: {"type": "ping", "timestamp": 1234567890}
    
    接收消息:
    - 思考开始: {"type": "thinking_start", "payload": {}}
    - 思考过程: {"type": "thinking", "payload": {"content": "..."}}
    - 工具调用: {"type": "tool_call", "payload": {...}}
    - 内容片段: {"type": "content", "payload": {"delta": "..."}}
    - 完成: {"type": "done", "payload": {...}}
    - 错误: {"type": "error", "payload": {...}}
    """
    # 验证 Token
    jwt_handler = context.get_jwt_handler()
    connection_manager = context.get_connection_manager()
    winclaw_bridge = context.get_winclaw_bridge()
    user_manager = context.get_user_manager()
    
    if not jwt_handler or not connection_manager:
        await websocket.close(code=1011, reason="服务未初始化")
        return
    
    payload = jwt_handler.verify_token(token)
    if not payload:
        await websocket.close(code=1008, reason="无效或过期的令牌")
        return
    
    user_id = payload.get("sub")
    device_fingerprint = payload.get("device")
    
    # 获取用户名
    username = ""
    if user_manager:
        try:
            user = user_manager.get_user_by_id(user_id)
            if user:
                username = user.username
        except Exception:
            pass
    
    # 生成会话ID
    session_id = f"remote_{user_id}_{int(time.time() * 1000)}"
    
    # 建立连接
    connected = await connection_manager.connect(
        user_id=user_id,
        websocket=websocket,
        session_id=session_id,
        metadata={
            "device": device_fingerprint,
            "connected_at": datetime.now().isoformat(),
            "username": username
        }
    )
    
    if not connected:
        return
    
    # 通知 WinClaw 有新的 PWA 连接
    from .bridge_handler import send_pwa_status_to_all_winclaws
    await send_pwa_status_to_all_winclaws()
    
    try:
        # 主消息循环
        while True:
            # 接收消息
            data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=connection_manager.connection_timeout
            )
            
            # 处理消息
            await handle_message(
                user_id=user_id,
                session_id=session_id,
                data=data,
                connection_manager=connection_manager,
                winclaw_bridge=winclaw_bridge
            )
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: user={user_id}")
        
    except asyncio.TimeoutError:
        logger.info(f"WebSocket 超时: user={user_id}")
        await connection_manager.send_to_session(session_id, {
            "type": "error",
            "payload": {"code": "TIMEOUT", "message": "连接超时"}
        })
        
    except json.JSONDecodeError as e:
        logger.warning(f"无效的 JSON 消息: {e}")
        
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}", exc_info=True)
        
    finally:
        await connection_manager.disconnect(user_id, session_id)
        # 通知 WinClaw PWA 连接断开
        from .bridge_handler import send_pwa_status_to_all_winclaws
        await send_pwa_status_to_all_winclaws()


async def handle_message(
    user_id: str,
    session_id: str,
    data: dict,
    connection_manager,
    winclaw_bridge
):
    """处理 WebSocket 消息"""
    message_type = data.get("type", "")
    payload = data.get("payload", {})
    
    if message_type == "message":
        await handle_chat_message(
            user_id=user_id,
            session_id=session_id,
            content=payload.get("content", ""),
            attachments=payload.get("attachments", []),
            request_id=payload.get("request_id"),  # ✅ 接收客户端传来的 request_id
            connection_manager=connection_manager,
            winclaw_bridge=winclaw_bridge
        )
    
    elif message_type == "stop_generation":
        await handle_stop_generation(
            user_id=user_id,
            winclaw_bridge=winclaw_bridge,
            connection_manager=connection_manager,
            session_id=session_id
        )
    
    elif message_type == "ping":
        await handle_ping(
            user_id=user_id,
            session_id=session_id,
            timestamp=payload.get("timestamp", time.time()),
            connection_manager=connection_manager
        )
    
    else:
        logger.warning(f"未知的消息类型: {message_type}")


async def handle_chat_message(
    user_id: str,
    session_id: str,
    content: str,
    attachments: list,
    connection_manager,
    winclaw_bridge,  # 已废弃，使用 bridge_handler 代替
    request_id: str = None  # ✅ 新增：客户端传来的 request_id
):
    """处理聊天消息 - 转发到用户绑定的 WinClaw PC 端"""
    from .bridge_handler import get_bridge_manager
    from .. import context
    import uuid
    
    bridge_manager = get_bridge_manager()
    
    # 查找用户绑定的 WinClaw 连接（包含设备指纹匹配）
    winclaw_conn = bridge_manager.get_user_connection(user_id)
    
    if not winclaw_conn:
        # ✅ 差异化错误检测：区分"未绑定"和"离线"
        user_manager = context.get_user_manager()
        has_bound_device = False
        device_info = None
        
        if user_manager:
            # 获取用户绑定的设备信息
            device_info = user_manager.get_user_device(user_id)
            has_bound_device = device_info is not None
        
        if has_bound_device:
            # ✅ Phase 2.3 + Phase 3.1: 设备已绑定但离线 - 存入离线消息队列（带国际化）
            from ..services.message_queue import get_message_queue
            from ..models.offline_message import MessagePriority
            from ..i18n import t, get_user_language
            
            queue = get_message_queue()
            
            # 根据用户等级设置优先级（简化版，默认普通）
            priority = MessagePriority.NORMAL
            ttl_minutes = 30  # 默认 30 分钟
            
            try:
                await queue.enqueue(
                    user_id=user_id,
                    content=content,
                    attachments=attachments,
                    priority=priority,
                    ttl_minutes=ttl_minutes
                )
                logger.info(f"消息已存入离线队列：user={user_id[:8]}")
            except Exception as e:
                logger.error(f"存入离线队列失败：{e}")
            
            error_code = "DEVICE_OFFLINE"
            # ✅ 使用国际化翻译函数
            lang = get_user_language(user_id)
            message = t("device_offline_msg", lang, default="💻 您的 WinClaw PC 端当前离线，消息将在其上线后自动发送")
            
            # ✅ 新增：同时通过 WebSocket 推送状态通知
            from .bridge_handler import broadcast_winclaw_status_change
            asyncio.create_task(
                broadcast_winclaw_status_change(user_id, "offline")
            )
        else:
            # 未绑定设备
            error_code = "NO_DEVICE_BOUND"
            lang = get_user_language(user_id)
            message = t("no_device_bound_msg", lang, default="📱 您还没有绑定 WinClaw PC 端，请在设置中完成设备绑定")
        
        await connection_manager.send_to_session(session_id, {
            "type": "error",
            "payload": {
                "code": error_code,
                "message": message
            }
        })
        return
    
    try:
        # 发送思考开始
        await connection_manager.send_to_session(session_id, {
            "type": "thinking_start",
            "payload": {}
        })
        
        # 生成或使用客户端的请求 ID
        # ✅ 关键修复：优先使用客户端传来的 request_id，确保响应能正确路由回 PWA
        if not request_id:
            request_id = str(uuid.uuid4())
            # logger.debug(f"生成新的 request_id: {request_id[:8]}")  # 调试用
        else:
            pass  # logger.debug(f"使用客户端 request_id: {request_id[:8]}")  # 调试用
        
        # 记录这个请求对应的 PWA session，以便响应能够路由回来
        bridge_manager.register_pwa_request(request_id, user_id, session_id)
        
        # 发送消息到 WinClaw PC 端
        await bridge_manager.send_to_winclaw(winclaw_conn.session_id, {
            "type": "chat",
            "request_id": request_id,
            "payload": {
                "user_id": user_id,
                "content": content,
                "attachments": attachments,
                "pwa_session_id": session_id  # 用于响应路由
            }
        })
        
        # logger.info(f"消息已转发到 WinClaw: user={user_id[:8]}, request={request_id[:8]}")  # 调试用
        
        # 响应会通过 bridge_handler 异步转发回 PWA
        # 不需要在这里等待
        
    except Exception as e:
        logger.error(f"转发消息失败: {e}", exc_info=True)
        await connection_manager.send_to_session(session_id, {
            "type": "error",
            "payload": {"code": "FORWARD_ERROR", "message": str(e)}
        })


async def handle_stop_generation(
    user_id: str,
    winclaw_bridge,
    connection_manager,
    session_id: str
):
    """处理停止生成请求"""
    if winclaw_bridge:
        stopped = winclaw_bridge.stop_generation(user_id)
        
        await connection_manager.send_to_session(session_id, {
            "type": "generation_stopped",
            "payload": {"success": stopped}
        })


async def handle_ping(
    user_id: str,
    session_id: str,
    timestamp: float,
    connection_manager
):
    """处理心跳"""
    # 更新心跳时间
    await connection_manager.update_heartbeat(user_id, session_id)
    
    # 发送 pong 响应
    await connection_manager.send_to_session(session_id, {
        "type": "pong",
        "timestamp": timestamp,
        "server_time": time.time()
    })
