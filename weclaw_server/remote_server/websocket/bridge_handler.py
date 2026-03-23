"""服务器端 Bridge WebSocket 处理器

处理来自 WeClaw 桌面端的 WebSocket 连接，实现：
1. WeClaw 实例注册和管理
2. 消息路由（将 PWA 用户请求转发到对应 WeClaw）
3. 状态广播
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import uuid

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class WeClawConnection:
    """WeClaw 连接信息"""
    session_id: str
    websocket: WebSocket
    user_id: str  # 绑定的用户ID（通过 device_fingerprint 关联）
    device_id: str = ""  # 设备唯一标识
    device_name: str = ""
    device_fingerprint: str = ""  # 设备指纹
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    status: dict = field(default_factory=dict)
    tools: list = field(default_factory=list)
    pending_requests: dict = field(default_factory=dict)  # request_id -> future
    
    @property
    def connection_id(self) -> str:
        return f"wc_{self.session_id[:8]}"


class BridgeConnectionManager:
    """Bridge 连接管理器
    
    管理所有 WeClaw 桌面端的连接。
    支持用户-设备绑定路由。
    """
    
    def __init__(self):
        # session_id -> WeClawConnection
        self._connections: dict[str, WeClawConnection] = {}
        # device_id -> session_id 映射
        self._device_connections: dict[str, str] = {}
        # user_id -> device_id 映射（通过绑定关系）
        self._user_device_map: dict[str, str] = {}
        # user_id -> session_id 直接映射（用于快速查找）
        self._user_session_map: dict[str, str] = {}
        # request_id -> (user_id, pwa_session_id) 映射，用于响应路由
        self._pwa_requests: dict[str, tuple[str, str]] = {}
        # request_id -> asyncio.Queue 映射，用于流式响应
        self._stream_queues: dict[str, asyncio.Queue] = {}
        # HTTP 活跃用户跟踪: user_id -> {username, last_request_at, request_count}
        self._http_active_users: dict[str, dict] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        device_id: str = "",
        device_name: str = "",
        device_fingerprint: str = ""
    ) -> WeClawConnection:
        """注册新的 WeClaw 连接
        
        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
            device_id: 设备 ID
            device_name: 设备名称
            device_fingerprint: 设备指纹（用于身份验证）
        """
        await websocket.accept()
        
        # 优先使用设备指纹验证身份
        user_id = ""
        if device_fingerprint:
            from .. import context
            user_manager = context.get_user_manager()
            if user_manager:
                user_id = user_manager.verify_device_fingerprint(device_fingerprint) or ""
                if user_id:
                    if device_id:
                        user_manager.update_device_last_connected(device_id)
                        self._user_device_map[user_id] = device_id
        
        # 如果指纹验证失败，尝试使用 device_id（向后兼容）
        if not user_id and device_id:
            from .. import context
            user_manager = context.get_user_manager()
            if user_manager:
                user_id = user_manager.get_device_user(device_id) or ""
                if user_id:
                    user_manager.update_device_last_connected(device_id)
                    self._user_device_map[user_id] = device_id
        
        connection = WeClawConnection(
            session_id=session_id,
            websocket=websocket,
            user_id=user_id,
            device_id=device_id,
            device_name=device_name,
            device_fingerprint=device_fingerprint
        )
        
        self._connections[session_id] = connection
        
        # 更新设备映射
        if device_id:
            self._device_connections[device_id] = session_id
        
        # 更新用户->会话映射（关键：确保能通过 user_id 找到连接）
        if user_id:
            self._user_session_map[user_id] = session_id
        
        logger.info(f"WeClaw 已连接：session={session_id[:8]}, device={device_id[:8] if device_id else 'unknown'}, user={user_id[:8] if user_id else 'unbound'}, fingerprint_valid={bool(user_id)}")
            
        # ✅ Phase 2.3: 如果有用户绑定，自动发送离线消息
        if user_id:
            asyncio.create_task(
                self._flush_offline_messages(user_id, session_id)
            )
            
            # ✅ 新增：通知 PWA 端设备已上线
            asyncio.create_task(
                broadcast_weclaw_status_change(user_id, "online")
            )
            
        return connection
        
    async def _flush_offline_messages(self, user_id: str, session_id: str):
        """发送离线消息到刚上线的 WeClaw"""
        try:
            from ..services.message_queue import get_message_queue
                
            queue = get_message_queue()
            sent_count = await queue.flush_to_weclaw(user_id, session_id, self)
                
            if sent_count > 0:
                logger.info(f"已发送 {sent_count} 条离线消息到 WeClaw: user={user_id[:8]}")
        except Exception as e:
            logger.error(f"发送离线消息失败：{e}")
    
    def disconnect(self, session_id: str):
        """断开 WeClaw 连接"""
        connection = self._connections.pop(session_id, None)
            
        if connection:
            # 清理设备映射
            if connection.device_id and connection.device_id in self._device_connections:
                del self._device_connections[connection.device_id]
                
            # 清理用户映射
            if connection.user_id and connection.user_id in self._user_device_map:
                if self._user_device_map[connection.user_id] == connection.device_id:
                    del self._user_device_map[connection.user_id]
                
            # 清理用户->会话映射
            if connection.user_id and connection.user_id in self._user_session_map:
                if self._user_session_map[connection.user_id] == session_id:
                    del self._user_session_map[connection.user_id]
                
            logger.info(f"WeClaw 已断开：session={session_id[:8]}")
                
            # ✅ 新增：广播状态变化到 PWA（带超时保护）
            if connection.user_id:
                asyncio.create_task(
                    broadcast_weclaw_status_change(connection.user_id, "offline")
                )
    
    def get_connection(self, session_id: str) -> Optional[WeClawConnection]:
        """获取连接"""
        return self._connections.get(session_id)
    
    def get_connection_by_device(self, device_id: str) -> Optional[WeClawConnection]:
        """根据设备 ID 获取连接"""
        session_id = self._device_connections.get(device_id)
        if session_id:
            return self._connections.get(session_id)
        return None
    
    def get_user_connection(self, user_id: str) -> Optional[WeClawConnection]:
        """获取用户绑定的 WeClaw 连接
        
        策略：
        1. 优先使用 user_id -> session_id 直接映射
        2. 通过 device_id 查找
        3. ✅ 新增：检查所有连接的设备指纹是否对应该用户（降级兼容）
        """
        # 优先使用 user_id -> session_id 直接映射
        session_id = self._user_session_map.get(user_id)
        if session_id:
            conn = self._connections.get(session_id)
            if conn:
                # logger.debug(f"找到用户 {user_id[:8]} 的直接连接：session={session_id[:8]}")  # 调试用
                return conn
        
        # 降级：通过 device_id查找
        device_id = self._user_device_map.get(user_id)
        if device_id:
            conn = self.get_connection_by_device(device_id)
            if conn:
                # logger.debug(f"通过设备 ID 找到用户 {user_id[:8]} 的连接：device={device_id[:8]}")  # 调试用
                return conn
        
        # ✅ Phase 3.1: 检查所有活跃连接，查找设备指纹匹配该用户的连接
        # 这用于处理 PWA 用户与桌面端绑定用户不一致的情况
        from .. import context
        user_manager = context.get_user_manager()
        
        if user_manager:
            for session_id, conn in self._connections.items():
                # 如果连接已经有 user_id，跳过（已经在前面的逻辑中处理过）
                if conn.user_id and conn.user_id != user_id:
                    continue
                
                # 检查这个设备的指纹是否属于目标用户
                if conn.device_fingerprint:
                    fingerprint_owner = user_manager.verify_device_fingerprint(conn.device_fingerprint)
                    if fingerprint_owner == user_id:
                        logger.info(f"通过设备指纹匹配找到用户 {user_id[:8]} 的连接：session={session_id[:8]}, fingerprint={conn.device_fingerprint[:16]}...")
                        # 更新映射，便于下次快速查找
                        self._user_session_map[user_id] = session_id
                        if conn.device_id:
                            self._user_device_map[user_id] = conn.device_id
                        return conn
        
        logger.warning(f"未找到用户 {user_id[:8]} 的 WeClaw 连接")
        return None
    
    def get_user_connections(self, user_id: str) -> list[WeClawConnection]:
        """获取用户绑定的所有 WeClaw 连接
        
        设计定义：系统采用严格 1：1 绑定模型（一个用户只能绑定一个桌面端）。
        此方法返回列表以兼容展展功能，实际正常情况应不超过 1 个连接。
        对话类消息请使用 get_primary_connection()。
        
        包含降级策略：如果直接映射没有结果，会检查设备指纹匹配。
        """
        connections = []
        
        # 查找所有该用户的连接（通过直接映射）
        for session_id, conn in self._connections.items():
            if conn.user_id == user_id:
                connections.append(conn)
        
        # [建议E] 降级内容：如果没有找到直接连接，尝试通过设备指纹匹配
        if not connections:
            from .. import context
            user_manager = context.get_user_manager()
            
            if user_manager:
                for session_id, conn in self._connections.items():
                    # 跳过已经有 user_id 的连接
                    if conn.user_id and conn.user_id != user_id:
                        continue
                    
                    # 检查设备指纹是否属于该用户
                    if conn.device_fingerprint:
                        fingerprint_owner = user_manager.verify_device_fingerprint(conn.device_fingerprint)
                        if fingerprint_owner == user_id:
                            logger.info(f"通过设备指纹匹配找到用户 {user_id[:8]} 的额外连接：session={session_id[:8]}")
                            connections.append(conn)
        
        return connections
    
    def has_connections(self) -> bool:
        """检查是否有活跃的 WeClaw 连接"""
        return len(self._connections) > 0
    
    def get_primary_connection(self, user_id: str) -> Optional[WeClawConnection]:
        """获取用户绑定的主 WeClaw 连接（第一个连接的）"""
        connections = self.get_user_connections(user_id)
        return connections[0] if connections else None
    
    def record_http_user(self, user_id: str, username: str = ""):
        """记录 HTTP API 活跃用户"""
        from datetime import datetime
        
        if user_id in self._http_active_users:
            self._http_active_users[user_id]["last_request_at"] = datetime.now().isoformat()
            self._http_active_users[user_id]["request_count"] += 1
        else:
            self._http_active_users[user_id] = {
                "user_id": user_id,
                "username": username,
                "connected_at": datetime.now().isoformat(),
                "last_request_at": datetime.now().isoformat(),
                "request_count": 1
            }
    
    def get_http_active_users(self, max_age_seconds: int = 300) -> list:
        """获取最近活跃的 HTTP 用户（默认 5 分钟内）"""
        from datetime import datetime
        
        now = datetime.now()
        active_users = []
        expired_users = []
        
        for user_id, info in self._http_active_users.items():
            try:
                last_request = datetime.fromisoformat(info["last_request_at"])
                age = (now - last_request).total_seconds()
                if age <= max_age_seconds:
                    active_users.append(info)
                else:
                    expired_users.append(user_id)
            except:
                expired_users.append(user_id)
        
        # 清理过期用户
        for user_id in expired_users:
            self._http_active_users.pop(user_id, None)
        
        return active_users
    
    def register_pwa_request(self, request_id: str, user_id: str, pwa_session_id: str):
        """注册 PWA 请求，用于响应路由"""
        self._pwa_requests[request_id] = (user_id, pwa_session_id)
        # logger.debug(f"PWA 请求已注册：request={request_id[:8]}, user={user_id[:8]}, session={pwa_session_id[:16]}")  # 调试用
    
    def get_pwa_session(self, request_id: str) -> Optional[tuple[str, str]]:
        """获取请求对应的 PWA session
        
        Returns:
            (user_id, pwa_session_id) 或 None
        """
        return self._pwa_requests.get(request_id)
    
    def complete_pwa_request(self, request_id: str):
        """完成 PWA 请求，清理映射"""
        self._pwa_requests.pop(request_id, None)
    
    def register_stream_request(self, request_id: str, queue: asyncio.Queue):
        """注册流式请求队列"""
        self._stream_queues[request_id] = queue
        # logger.debug(f"流式请求已注册：request={request_id[:8]}")  # 调试用
    
    def unregister_stream_request(self, request_id: str):
        """注销流式请求队列"""
        self._stream_queues.pop(request_id, None)
        # logger.debug(f"流式请求已注销：request={request_id[:8]}")  # 调试用
    
    def get_stream_queue(self, request_id: str) -> Optional[asyncio.Queue]:
        """获取流式请求队列"""
        return self._stream_queues.get(request_id)
    
    async def push_to_stream(self, request_id: str, message: dict) -> bool:
        """将消息推送到流式队列"""
        queue = self._stream_queues.get(request_id)
        if queue:
            await queue.put(message)
            return True
        return False
    
    async def end_stream(self, request_id: str):
        """结束流式响应"""
        queue = self._stream_queues.get(request_id)
        if queue:
            await queue.put(None)  # 结束标记
    
    def update_status(self, session_id: str, status: dict):
        """更新连接状态"""
        connection = self._connections.get(session_id)
        if connection:
            connection.status = status
            connection.last_heartbeat = datetime.now()
    
    def update_tools(self, session_id: str, tools: list):
        """更新工具列表"""
        connection = self._connections.get(session_id)
        if connection:
            connection.tools = tools
    
    async def send_to_weclaw(
        self,
        session_id: str,
        message: dict
    ) -> bool:
        """发送消息到 WeClaw"""
        connection = self._connections.get(session_id)
        if not connection:
            return False
        
        try:
            await connection.websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"发送到 WeClaw 失败: {e}")
            return False
    
    async def send_to_user_weclaws(
        self,
        user_id: str,
        message: dict
    ) -> list[str]:
        """发送消息到用户的所有 WeClaw 实例"""
        sent_to = []
        
        for conn in self.get_user_connections(user_id):
            if await self.send_to_weclaw(conn.session_id, message):
                sent_to.append(conn.session_id)
        
        return sent_to
    
    async def request_to_weclaw(
        self,
        session_id: str,
        message: dict,
        timeout: float = 300.0
    ) -> dict:
        """发送请求到 WeClaw 并等待响应"""
        connection = self._connections.get(session_id)
        if not connection:
            return {"error": "WeClaw 未连接"}
        
        request_id = message.get("request_id", str(uuid.uuid4()))
        message["request_id"] = request_id
        
        # 创建 Future 用于等待响应
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        connection.pending_requests[request_id] = future
        
        try:
            # 发送请求
            await connection.websocket.send_json(message)
            
            # 等待响应
            return await asyncio.wait_for(future, timeout=timeout)
            
        except asyncio.TimeoutError:
            return {"error": "请求超时"}
        finally:
            connection.pending_requests.pop(request_id, None)
    
    def complete_request(self, session_id: str, request_id: str, response: dict):
        """完成请求（由响应处理调用）"""
        connection = self._connections.get(session_id)
        if connection and request_id in connection.pending_requests:
            future = connection.pending_requests[request_id]
            if not future.done():
                future.set_result(response)
    
    @property
    def connection_count(self) -> int:
        """当前连接数"""
        return len(self._connections)
    
    def get_all_status(self) -> dict:
        """获取所有连接状态"""
        return {
            "total_connections": self.connection_count,
            "connections": [
                {
                    "session_id": conn.session_id[:8],
                    "user_id": conn.user_id,
                    "connected_at": conn.connected_at.isoformat(),
                    "status": conn.status.get("status", "unknown"),
                    "tools_count": len(conn.tools)
                }
                for conn in self._connections.values()
            ]
        }


# 全局 Bridge 连接管理器
_bridge_manager: Optional[BridgeConnectionManager] = None


def get_bridge_manager() -> BridgeConnectionManager:
    """获取全局 Bridge 管理器"""
    global _bridge_manager
    if _bridge_manager is None:
        _bridge_manager = BridgeConnectionManager()
    return _bridge_manager


async def bridge_websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    device_id: str = "",
    device_name: str = "",
    device_fingerprint: str = ""
):
    """
    Bridge WebSocket 端点处理
    
    Args:
        websocket: WebSocket 连接
        session_id: WeClaw 会话ID
        device_id: 设备 ID
        device_name: 设备名称
        device_fingerprint: 设备指纹（用于身份验证）
    """
    manager = get_bridge_manager()
    
    # 注册连接
    connection = await manager.connect(websocket, session_id, device_id, device_name, device_fingerprint)
    
    try:
        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "device_id": device_id,
            "user_bound": bool(connection.user_id),
            "fingerprint_valid": bool(device_fingerprint and connection.user_id),
            "message": "WeClaw 桥接连接成功" if connection.user_id else "WeClaw 已连接，设备未绑定或指纹验证失败"
        })
        
        # 发送当前 PWA 连接状态
        await send_pwa_status_to_weclaw(websocket)
        
        # 消息循环
        while True:
            # 接收消息
            raw_message = await websocket.receive_text()
            
            try:
                message = json.loads(raw_message)
                await handle_bridge_message(connection, message)
            except json.JSONDecodeError as e:
                logger.error(f"消息解析失败: {e}")
                await websocket.send_json({
                    "type": "error",
                    "payload": {"code": "PARSE_ERROR", "message": "消息格式错误"}
                })
            
    except WebSocketDisconnect:
        logger.info(f"WeClaw 断开连接: session={session_id[:8]}")
    except Exception as e:
        logger.error(f"Bridge WebSocket 异常: {e}", exc_info=True)
    finally:
        manager.disconnect(session_id)


async def handle_bridge_message(connection: WeClawConnection, message: dict):
    """处理来自 WeClaw 的消息"""
    msg_type = message.get("type", "")
    payload = message.get("payload", {})
    request_id = message.get("request_id", "")
    
    manager = get_bridge_manager()
    
    if msg_type == "pong":
        # 心跳响应
        connection.last_heartbeat = datetime.now()
    
    elif msg_type == "status_update":
        # 状态更新
        manager.update_status(connection.session_id, payload)
    
    elif msg_type == "tools_list":
        # 工具列表
        manager.update_tools(connection.session_id, payload.get("tools", []))
    
    elif msg_type in ("stream", "content"):
        # 流式响应 - 优先推送到流式队列，否则转发到 PWA WebSocket
        if request_id and await manager.push_to_stream(request_id, message):
            pass  # 已推送到队列
        else:
            await forward_to_pwa_by_request(manager, request_id, message)
    
    elif msg_type in ("done", "error", "stream_end"):
        # 最终响应 - 推送到队列并结束流
        if request_id:
            pushed = await manager.push_to_stream(request_id, message)
            if pushed:
                await manager.end_stream(request_id)
            else:
                await forward_to_pwa_by_request(manager, request_id, message)
            
            manager.complete_request(connection.session_id, request_id, message)
            manager.complete_pwa_request(request_id)
            # logger.info(f"响应完成：request={request_id[:8]}, type={msg_type}")  # 调试用
    
    elif msg_type in ("tool_call", "tool_result", "thinking", "thinking_start"):
        # 工具调用消息 - 优先推送到队列
        if request_id and await manager.push_to_stream(request_id, message):
            pass  # 已推送到队列
        else:
            await forward_to_pwa_by_request(manager, request_id, message)
    
    elif msg_type == "log":
        # 日志消息
        logger.info(f"[WeClaw] {payload}")
    
    elif msg_type == "reconnected":
        # WeClaw 重连通知
        device_id = payload.get("device_id", "unknown")
        logger.info(f"WeClaw 重连成功: session={connection.session_id[:8]}, device={device_id}")
    
    else:
        logger.warning(f"未知的 Bridge 消息类型: {msg_type}")


async def forward_to_pwa_by_request(manager: BridgeConnectionManager, request_id: str, message: dict):
    """通过请求 ID 转发消息到对应的 PWA 用户
    
    [建议B] 修复回路逻辑：
    1. 优先使用 pwa_session_id 定点路由到具体浏览器标签页（WebSocket 路径）
    2. 对于 WebSocket 路径，pwa_session_id 就是该浏览器的 WS session_id，可直接路由
    3. 对于 HTTP/SSE 路径，响应通过 stream_queue 传递，不依赖此函数
    4. 降级内容：如果 session 路由失败，才广播给该用户所有 WS 连接
    
    注：PWA 的 HTTP session_id 和 WebSocket session_id 格式不同，
    所以 HTTP 消息返回主要靠 SSE stream_queue，此处仅处理 WS 路由。
    """
    from .. import context
    
    msg_type = message.get("type", "unknown")
    
    pwa_manager = context.get_connection_manager()
    if not pwa_manager:
        logger.warning(f"转发响应失败: PWA 管理器不存在, request={request_id[:8] if request_id else 'none'}, type={msg_type}")
        return
    
    user_id = None
    pwa_session_id = None
    
    # 尝试通过 request_id 获取 user_id 和 pwa_session_id
    if request_id:
        pwa_info = manager.get_pwa_session(request_id)
        if pwa_info:
            user_id, pwa_session_id = pwa_info
            # logger.info(f"响应路由查找：request={request_id[:8]}, user={user_id[:8]}, session={pwa_session_id[:16] if pwa_session_id else 'none'}")  # 调试用
        else:
            logger.warning(f"响应路由查找失败：request={request_id[:8]} 未找到对应的 PWA session")
    
    # 如果没有从 request_id 获取到 user_id，尝试从 payload 中获取
    if not user_id:
        payload = message.get("payload", {})
        user_id = payload.get("user_id", "")
        if user_id:
            logger.info(f"从 payload 获取 user_id: {user_id[:8]}")
    
    if not user_id:
        logger.warning(f"无法转发到 PWA：缺少 user_id, request={request_id[:8] if request_id else 'none'}")
        return
    
    # 检查 PWA连接状态
    ws_connected = pwa_manager.is_connected(user_id)
    ws_count = len(pwa_manager._user_connections.get(user_id, set()))
    # logger.info(f"PWA连接状态：user={user_id[:8]}, ws_connected={ws_connected}, ws_count={ws_count}")  # 调试用
    
    # [建议 B] 优先路由到具体的 WebSocket session（防止广播到同一用户的其他浏览器标签页）
    if pwa_session_id:
        sent = await pwa_manager.send_to_session(pwa_session_id, message)
        if sent:
            # logger.info(f"响应已定点路由：request={request_id[:8]}, session={pwa_session_id[:16]}, type={msg_type}")  # 调试用
            return
        # send_to_session 返回 False 说明该 session 不是 WS 连接（HTTP/SSE 路径）
        logger.info(f"定点路由失败: session={pwa_session_id[:16] if len(pwa_session_id)>16 else pwa_session_id} 不在 WS 中，尝试广播")
    
    # 降级：广播到用户所有 WebSocket 连接（主要用于状态通知类消息）
    sent = await pwa_manager.send_message(user_id, message)
    logger.info(f"广播响应到用户: user={user_id[:8]}, type={msg_type}, sent={sent}")


async def forward_to_pwa(user_id: str, message: dict):
    """转发消息到用户的 PWA 连接"""
    # 使用 context 获取 PWA 连接管理器
    from .. import context
    
    pwa_manager = context.get_connection_manager()
    if pwa_manager:
        await pwa_manager.send_message(user_id, message)


async def send_pwa_status_to_weclaw(websocket: WebSocket):
    """发送 PWA 连接状态到 WeClaw"""
    from .. import context
    
    pwa_manager = context.get_connection_manager()
    bridge_manager = get_bridge_manager()
    
    # 收集 WebSocket 连接的用户
    ws_connections = []
    if pwa_manager:
        ws_connections = pwa_manager.get_all_connections()
    
    # 收集 HTTP 活跃用户
    http_users = []
    if bridge_manager:
        http_users = bridge_manager.get_http_active_users()
    
    # 合并去重（优先使用 WebSocket 连接的信息）
    seen_users = set()
    all_connections = []
    
    for conn in ws_connections:
        user_id = conn.get("user_id", "")
        if user_id and user_id not in seen_users:
            seen_users.add(user_id)
            all_connections.append(conn)
    
    for user in http_users:
        user_id = user.get("user_id", "")
        if user_id and user_id not in seen_users:
            seen_users.add(user_id)
            all_connections.append(user)
    
    await websocket.send_json({
        "type": "pwa_status",
        "payload": {
            "count": len(all_connections),
            "connections": all_connections
        }
    })


async def send_pwa_status_to_all_weclaws():
    """发送 PWA 连接状态到所有 WeClaw 连接"""
    from .. import context
    
    pwa_manager = context.get_connection_manager()
    bridge_manager = get_bridge_manager()
    
    if not bridge_manager:
        return
    
    # 收集 WebSocket 连接的用户
    ws_connections = []
    if pwa_manager:
        ws_connections = pwa_manager.get_all_connections()
    
    # 收集 HTTP 活跃用户
    http_users = bridge_manager.get_http_active_users()
    
    # 合并去重
    seen_users = set()
    all_connections = []
    
    for conn in ws_connections:
        user_id = conn.get("user_id", "")
        if user_id and user_id not in seen_users:
            seen_users.add(user_id)
            all_connections.append(conn)
    
    for user in http_users:
        user_id = user.get("user_id", "")
        if user_id and user_id not in seen_users:
            seen_users.add(user_id)
            all_connections.append(user)
    
    message = {
        "type": "pwa_status",
        "payload": {
            "count": len(all_connections),
            "connections": all_connections
        }
    }
    
    # 发送给所有 WeClaw 连接
    for session_id, conn in list(bridge_manager._connections.items()):
        try:
            await conn.websocket.send_json(message)
        except Exception as e:
            logger.warning(f"发送 PWA 状态到 WeClaw 失败：{e}")


async def broadcast_weclaw_status_change(user_id: str, status: str):
    """广播 WeClaw 状态变化到 PWA（带超时保护）"""
    from .. import context
    
    pwa_manager = context.get_connection_manager()
    if not pwa_manager:
        return
    
    try:
        # ✅ 添加超时控制，避免阻塞
        await asyncio.wait_for(
            pwa_manager.send_message(user_id, {
                "type": "weclaw_status",
                "payload": {
                    "status": status,  # online/offline/reconnecting
                    "timestamp": datetime.now().isoformat()
                }
            }),
            timeout=5.0  # 5 秒超时
        )
    except asyncio.TimeoutError:
        logger.warning(f"广播状态变化超时：user={user_id[:8]}")
    except Exception as e:
        logger.error(f"广播状态变化失败：{e}")
