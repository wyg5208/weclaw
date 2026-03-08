"""聊天 API

提供消息发送、流式响应等接口。
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .. import context
from .auth import get_current_user_with_db

logger = logging.getLogger(__name__)

router = APIRouter()


# ========== Pydantic 模型 ==========

class AttachmentData(BaseModel):
    """附件数据"""
    attachment_id: Optional[str] = Field(default=None, description="附件 ID（上传后返回的 UUID）")
    type: str = Field(..., description="附件类型：image/audio/file")
    data: str = Field(..., description="Base64 编码的数据或 URL")
    filename: str = Field(..., description="文件名")
    mime_type: str = Field(..., description="MIME 类型")


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., min_length=1, max_length=10000, description="消息内容")
    session_id: Optional[str] = Field(default=None, description="会话ID，不传则创建新会话")
    attachments: list[AttachmentData] = Field(default_factory=list, description="附件列表")
    options: dict = Field(default_factory=dict, description="选项")


class ChatResponse(BaseModel):
    """聊天响应"""
    message_id: str
    session_id: str
    status: str


# ========== API 端点 ==========

@router.post("", response_model=ChatResponse, summary="发送消息")
async def send_message(
    request: ChatRequest,
    user_info: dict = Depends(get_current_user_with_db)
):
    """
    发送消息给 WinClaw
    
    - **message**: 消息内容
    - **session_id**: 会话ID（可选，不传则创建新会话）
    - **attachments**: 附件列表（可选）
    - **options**: 其他选项（如指定模型）
    """
    user = user_info["user"]
    
    # 生成消息ID
    message_id = str(uuid.uuid4())
    
    # 确定会话ID
    session_id = request.session_id
    if not session_id:
        session_id = f"remote_{user.user_id}_{int(datetime.now().timestamp())}"
    
    # 处理附件
    attachments = []
    for att in request.attachments:
        # 优先使用 attachment_id（如果提供了）
        attachment_data = {
            "type": att.type,
            "data": att.data,  # URL 或 base64
            "filename": att.filename,
            "mime_type": att.mime_type
        }
        
        # 如果有 attachment_id，也保存下来供 Bridge 层使用
        if hasattr(att, 'attachment_id') and att.attachment_id:
            attachment_data["attachment_id"] = att.attachment_id
        
        attachments.append(attachment_data)
    
    logger.info(f"收到 {len(attachments)} 个附件：{[a.get('filename') for a in attachments]}")
    
    # 存储消息（用于流式响应）
    pending_messages = getattr(router, '_pending_messages', {})
    if not hasattr(router, '_pending_messages'):
        router._pending_messages = pending_messages
    
    pending_messages[message_id] = {
        "user_id": user.user_id,
        "session_id": session_id,
        "message": request.message,
        "attachments": attachments,
        "options": request.options,
        "status": "pending"
    }
    
    # 更新请求计数和活跃用户记录
    from .. import context
    from ..websocket.bridge_handler import get_bridge_manager, send_pwa_status_to_all_winclaws
    
    connection_manager = context.get_connection_manager()
    if connection_manager:
        connection_manager.increment_request_count(session_id)
    
    # 记录 HTTP 活跃用户
    bridge_manager = get_bridge_manager()
    if bridge_manager:
        bridge_manager.record_http_user(user.user_id, user.username)
    
    # 通知 WinClaw 更新 PWA 状态
    await send_pwa_status_to_all_winclaws()
        
    # 转发消息到 WinClaw 桌面端
    bridge_manager = get_bridge_manager()
    if bridge_manager:
        # 使用 message_id 作为 request_id，便于 PWA 端过滤响应
        request_id = message_id
            
        # 注册 PWA 请求，以便响应能正确路由
        bridge_manager.register_pwa_request(request_id, user.user_id, session_id)
            
        # 构建转发消息
        request_msg = {
            "type": "chat",
            "request_id": request_id,
            "payload": {
                "content": request.message,
                "attachments": attachments,
                "options": request.options,
                "user_id": user.user_id,
                "pwa_session_id": session_id  # 用于响应路由
            }
        }
            
        # 发送到用户的 WinClaw 连接
        try:
            sent_to = await bridge_manager.send_to_user_winclaws(user.user_id, request_msg)
            if sent_to:
                logger.info(f"消息已转发到 WinClaw: message_id={message_id[:8]}, request={request_id[:8]}, sessions={len(sent_to)}")
            else:
                logger.warning(f"没有可用的 WinClaw 连接，消息无法转发：user={user.user_id}")
        except Exception as e:
            logger.error(f"转发消息到 WinClaw 失败：{e}")
    else:
        logger.warning("Bridge Manager 未初始化，消息无法转发")
        
    # 更新会话缓存（用于 PWA 历史会话列表）
    _update_session_cache(user.user_id, session_id)
        
    logger.info(f"收到消息：user={user.username}, session={session_id}")
    
    return ChatResponse(
        message_id=message_id,
        session_id=session_id,
        status="processing"
    )


@router.get("/stream", summary="流式接收响应")
async def stream_response(
    session_id: str = Query(..., description="会话ID"),
    message_id: str = Query(..., description="消息ID"),
    user_info: dict = Depends(get_current_user_with_db)
):
    """
    SSE 流式接收 AI 回复
    
    返回 Server-Sent Events 流：
    - event: thinking - 思考状态
    - event: tool_call - 工具调用
    - event: content - 内容片段
    - event: done - 完成
    - event: error - 错误
    """
    user = user_info["user"]
    
    # 获取待处理消息
    pending_messages = getattr(router, '_pending_messages', {})
    message_data = pending_messages.pop(message_id, None)
    
    if not message_data:
        raise HTTPException(status_code=404, detail="消息不存在或已过期")
    
    async def generate() -> AsyncGenerator[str, None]:
        """生成 SSE 事件流"""
        import json
        
        try:
            # 方式1: 本地 WinClaw Bridge（内嵌模式）
            bridge = context.get_winclaw_bridge()
            if bridge and bridge.is_connected():
                # 发送思考状态
                yield f"event: thinking\ndata: {{\"content\": \"正在思考...\"}}\n\n"
                
                # 调用本地 WinClaw 处理消息
                async for chunk in bridge.process_message(
                    user_id=user.user_id,
                    message=message_data["message"],
                    attachments=message_data.get("attachments", [])
                ):
                    chunk_type = chunk.get("type", "content")
                    payload = chunk.get("payload", {})
                    yield f"event: {chunk_type}\ndata: {json.dumps(payload)}\n\n"
            
            # 方式2: 远程 WinClaw Bridge（独立服务器模式）
            else:
                from ..websocket.bridge_handler import get_bridge_manager
                bridge_manager = get_bridge_manager()
                # 使用用户的 user_id 获取其绑定的 WinClaw 连接
                connection = bridge_manager.get_primary_connection(user.user_id)
                
                if not connection:
                    yield f"event: error\ndata: {{\"code\": \"NO_WINCLAW\", \"message\": \"您的 WinClaw PC 未连接或未绑定\"}}\n\n"
                    return
                
                # 发送思考状态
                yield f"event: thinking\ndata: {{\"content\": \"正在发送到 WinClaw...\"}}\n\n"
                
                # 生成 request_id 用于跟踪响应
                request_id = str(uuid.uuid4())
                
                # 注册 PWA 请求，以便响应能正确路由到流式队列
                bridge_manager.register_pwa_request(request_id, user.user_id, message_data["session_id"])
                
                # 注册流式请求队列
                stream_queue = asyncio.Queue()
                bridge_manager.register_stream_request(request_id, stream_queue)
                
                try:
                    # 发送请求到远程 WinClaw
                    request_msg = {
                        "type": "chat",
                        "request_id": request_id,
                        "payload": {
                            "content": message_data["message"],
                            "attachments": message_data.get("attachments", []),
                            "options": message_data.get("options", {}),
                            "user_id": user.user_id,
                            "pwa_session_id": message_data["session_id"]
                        }
                    }
                    
                    await bridge_manager.send_to_winclaw(connection.session_id, request_msg)
                    logger.info(f"消息已转发到 WinClaw: message_id={message_id[:8]}, request={request_id[:8]}")
                    
                    # 流式接收响应
                    while True:
                        try:
                            chunk = await asyncio.wait_for(stream_queue.get(), timeout=120.0)
                            
                            if chunk is None:  # 结束标记
                                break
                            
                            chunk_type = chunk.get("type", "content")
                            payload = chunk.get("payload", {})
                            
                            # 转换为 SSE 格式
                            if chunk_type == "stream":
                                yield f"event: content\ndata: {json.dumps(payload)}\n\n"
                            elif chunk_type in ("done", "error"):
                                yield f"event: {chunk_type}\ndata: {json.dumps(payload)}\n\n"
                                break
                            else:
                                yield f"event: {chunk_type}\ndata: {json.dumps(payload)}\n\n"
                                
                        except asyncio.TimeoutError:
                            yield f"event: error\ndata: {{\"code\": \"TIMEOUT\", \"message\": \"WinClaw 响应超时\"}}\n\n"
                            break
                            
                finally:
                    # 清理请求注册
                    bridge_manager.unregister_stream_request(request_id)
                    bridge_manager.complete_pwa_request(request_id)
            
            # 完成
            yield f"event: done\ndata: {{\"message_id\": \"{message_id}\"}}\n\n"
            
        except asyncio.CancelledError:
            logger.info(f"流式响应被取消: {message_id}")
            yield f"event: error\ndata: {{\"code\": \"CANCELLED\", \"message\": \"请求已取消\"}}\n\n"
            
        except Exception as e:
            logger.error(f"流式响应错误: {e}", exc_info=True)
            import json
            yield f"event: error\ndata: {json.dumps({'code': 'ERROR', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/stop", summary="停止生成")
async def stop_generation(
    session_id: str = Query(..., description="会话ID"),
    user_info: dict = Depends(get_current_user_with_db)
):
    """停止当前生成"""
    user = user_info["user"]
    bridge = context.get_winclaw_bridge()
    
    if bridge:
        stopped = bridge.stop_generation(user.user_id)
        return {
            "success": stopped,
            "message": "已停止生成" if stopped else "没有正在进行的生成"
        }
    
    return {"success": False, "message": "服务不可用"}


@router.get("/history", summary="获取历史消息")
async def get_history(
    session_id: Optional[str] = Query(None, description="会话ID"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    user_info: dict = Depends(get_current_user_with_db)
):
    """获取历史消息"""
    # Bridge 连接是可选的，未连接时返回空历史
    # 未来可从本地数据库或 Bridge 获取历史
    return {
        "session_id": session_id,
        "messages": [],
        "has_more": False
    }


# ========== 会话历史缓存（内存存储）==========
# 用于在远程服务端缓存会话历史，供PWA获取
# 格式: {user_id: {session_id: {"title": str, "created_at": str, "last_active": str, "message_count": int}}}
_session_cache: dict[str, dict[str, dict]] = {}


def _get_user_sessions(user_id: str) -> dict:
    """获取用户的会话缓存"""
    if user_id not in _session_cache:
        _session_cache[user_id] = {}
    return _session_cache[user_id]


def _update_session_cache(user_id: str, session_id: str, title: str = None) -> None:
    """更新会话缓存"""
    user_sessions = _get_user_sessions(user_id)
    now = datetime.now().isoformat()
    
    if session_id in user_sessions:
        user_sessions[session_id]["last_active"] = now
        if title:
            user_sessions[session_id]["title"] = title
        user_sessions[session_id]["message_count"] = user_sessions[session_id].get("message_count", 0) + 1
    else:
        user_sessions[session_id] = {
            "session_id": session_id,
            "title": title or f"对话 {session_id[:8]}",
            "created_at": now,
            "last_active": now,
            "message_count": 1
        }


@router.get("/sessions", summary="获取历史会话列表")
async def get_session_list(
    limit: int = Query(20, ge=1, le=100, description="返回条数"),
    user_info: dict = Depends(get_current_user_with_db)
):
    """
    获取用户的历史会话列表
    
    从远程服务端内存缓存中获取会话列表。
    注意：这是远程服务端的缓存，可能与桌面端本地存储的会话不完全同步。
    """
    user = user_info["user"]
    user_sessions = _get_user_sessions(user.user_id)
    
    # 转换为列表并按最后活跃时间排序
    sessions_list = list(user_sessions.values())
    sessions_list.sort(key=lambda x: x.get("last_active", ""), reverse=True)
    
    # 限制返回数量
    sessions_list = sessions_list[:limit]
    
    return {
        "success": True,
        "data": {
            "sessions": sessions_list,
            "total": len(sessions_list)
        }
    }


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(
    session_id: str,
    user_info: dict = Depends(get_current_user_with_db)
):
    """删除指定会话"""
    user = user_info["user"]
    user_sessions = _get_user_sessions(user.user_id)
    
    if session_id in user_sessions:
        del user_sessions[session_id]
        return {"success": True, "message": "会话已删除"}
    
    return {"success": False, "message": "会话不存在"}
