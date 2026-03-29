"""远程桥接客户端

运行在 WinClaw 本机端，负责：
1. 连接远程服务器
2. 接收远程指令并转发到本地 Agent
3. 流式返回执行结果
4. 上报本地状态
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional
import uuid

try:
    import websockets
    from websockets.client import WebSocketClientProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketClientProtocol = Any

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class BridgeConfig:
    """桥接配置"""
    server_url: str = "wss://localhost:8000/ws/bridge"
    token: str = ""
    device_id: str = ""  # 设备 ID（绑定后获得）
    device_name: str = ""  # 设备名称
    auto_fingerprint: bool = True  # 自动生成设备指纹
    reconnect_interval: float = 5.0
    max_reconnect_attempts: int = 999  # 增加上限，几乎无限重连
    heartbeat_interval: float = 20.0  # 缩短心跳间隔
    connection_timeout: float = 60.0  # 增加连接超时
    message_timeout: float = 300.0
    auto_connect: bool = True
    enabled: bool = False


@dataclass
class PWAConnection:
    """PWA 连接信息"""
    user_id: str
    username: str = ""
    session_id: str = ""
    connected_at: Optional[datetime] = None
    last_request_at: Optional[datetime] = None
    request_count: int = 0


@dataclass
class BridgeStats:
    """桥接统计"""
    connected_at: Optional[datetime] = None
    messages_received: int = 0
    messages_sent: int = 0
    tool_calls_executed: int = 0
    errors: int = 0
    last_heartbeat: Optional[datetime] = None
    reconnect_count: int = 0
    # PWA 连接信息
    pwa_connections: list[PWAConnection] = field(default_factory=list)
    active_pwa_count: int = 0


class RemoteBridgeClient:
    """远程桥接客户端
    
    负责将远程服务器的请求转发到本地 WinClaw Agent，
    并将执行结果流式返回给服务器。
    
    使用方式:
        client = RemoteBridgeClient(agent, config)
        await client.start()
        
        # 停止
        await client.stop()
    """
    
    def __init__(
        self,
        agent: Any,
        event_bus: Any = None,
        session_manager: Any = None,
        config: Optional[BridgeConfig] = None,
        on_state_change: Optional[Callable[[ConnectionState], None]] = None
    ):
        """
        初始化桥接客户端
        
        Args:
            agent: WinClaw Agent 实例
            event_bus: WinClaw 事件总线（可选）
            session_manager: WinClaw 会话管理器（可选）
            config: 桥接配置
            on_state_change: 状态变化回调
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets 库未安装，请运行: pip install websockets")
        
        self.agent = agent
        self.event_bus = event_bus
        self.session_manager = session_manager
        self.config = config or BridgeConfig()
        self.on_state_change = on_state_change
        
        # 连接状态
        self._state = ConnectionState.DISCONNECTED
        self._ws: Optional[WebSocketClientProtocol] = None
        self._session_id: str = ""
        
        # 任务管理
        self._tasks: dict[str, asyncio.Task] = {}
        self._active_streams: dict[str, asyncio.Task] = {}
        
        # 统计
        self._stats = BridgeStats()
        
        # 运行标志
        self._running = False
        self._reconnect_attempts = 0
        
        # 设备指纹缓存（WebSocket 和 HTTP 共用）
        self._device_fingerprint: str = ""
        
        # 消息处理器
        from .message_handler import MessageHandler
        from .status_reporter import StatusReporter
        
        self._message_handler = MessageHandler(
            agent=agent,
            on_response=self._send_response,
            on_tool_call=self._send_tool_call,
            on_error=self._send_error
        )
        
        self._status_reporter = StatusReporter(
            agent=agent,
            get_status_callback=self._send_status
        )
    
    @property
    def state(self) -> ConnectionState:
        """当前连接状态"""
        return self._state
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._state == ConnectionState.CONNECTED and self._ws is not None
    
    @property
    def stats(self) -> BridgeStats:
        """获取统计信息"""
        return self._stats
    
    def update_pwa_connections(self, connections: list[dict]) -> None:
        """更新 PWA 连接信息"""
        self._stats.pwa_connections = []
        for conn in connections:
            self._stats.pwa_connections.append(PWAConnection(
                user_id=conn.get("user_id", ""),
                username=conn.get("username", ""),
                session_id=conn.get("session_id", ""),
                connected_at=datetime.fromisoformat(conn["connected_at"]) if conn.get("connected_at") else None,
                last_request_at=datetime.fromisoformat(conn["last_request_at"]) if conn.get("last_request_at") else None,
                request_count=conn.get("request_count", 0)
            ))
        self._stats.active_pwa_count = len(self._stats.pwa_connections)
    
    def add_pwa_request(self, user_id: str) -> None:
        """记录 PWA 请求"""
        for conn in self._stats.pwa_connections:
            if conn.user_id == user_id:
                conn.last_request_at = datetime.now()
                conn.request_count += 1
                break
    
    def _set_state(self, state: ConnectionState):
        """设置连接状态"""
        if self._state != state:
            self._state = state
            logger.info(f"桥接状态变更: {state.value}")
            if self.on_state_change:
                try:
                    self.on_state_change(state)
                except Exception as e:
                    logger.error(f"状态回调执行失败: {e}")
    
    async def start(self):
        """启动桥接客户端"""
        if not self.config.enabled:
            logger.info("远程桥接已禁用")
            return
        
        if self._running:
            logger.warning("桥接客户端已在运行")
            return
        
        self._running = True
        self._session_id = str(uuid.uuid4())
        
        logger.info(f"启动远程桥接客户端，服务器: {self.config.server_url}")
        
        # 启动连接任务
        self._tasks["connector"] = asyncio.create_task(self._connection_loop())
    
    async def stop(self):
        """停止桥接客户端"""
        logger.info("停止远程桥接客户端")
        self._running = False
        
        # 取消所有任务
        for name, task in self._tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._tasks.clear()
        
        # 关闭连接
        await self._disconnect()
        
        self._set_state(ConnectionState.DISCONNECTED)
    
    async def _connection_loop(self):
        """连接循环 - 自动重连（带指数退避）"""
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"连接失败：{e}")
                self._stats.errors += 1
                
            if not self._running:
                break
                
            # 重连延迟（指数退避 + 随机抖动）
            self._set_state(ConnectionState.RECONNECTING)
            self._reconnect_attempts += 1
            self._stats.reconnect_count += 1
                
            # 计算退避时间：base * 2^(attempt-1)，最大 60 秒
            backoff_seconds = min(
                self.config.reconnect_interval * (2 ** (self._reconnect_attempts - 1)),
                60.0
            )
            # 添加随机抖动（±20%）避免雪崩
            import random
            jitter = backoff_seconds * 0.2 * (random.random() - 0.5)
            actual_delay = max(1.0, backoff_seconds + jitter)
                
            logger.info(f"{actual_delay:.1f}秒后尝试重连 (第{self._reconnect_attempts}次)")
            await asyncio.sleep(actual_delay)
    
    async def _connect(self):
        """建立 WebSocket 连接"""
        self._set_state(ConnectionState.CONNECTING)
        
        # 自动生成设备指纹（缓存到实例属性，HTTP 上传时复用）
        if not self._device_fingerprint and self.config.auto_fingerprint:
            try:
                from .device_fingerprint import get_device_fingerprint
                self._device_fingerprint = get_device_fingerprint()
                logger.info(f"自动生成设备指纹: {self._device_fingerprint[:16]}...")
            except Exception as e:
                logger.warning(f"生成设备指纹失败: {e}")
        device_fingerprint = self._device_fingerprint
        
        # 构建连接 URL
        url = f"{self.config.server_url}?session_id={self._session_id}"
        
        # 添加设备信息
        if self.config.device_id:
            url += f"&device_id={self.config.device_id}"
        if self.config.device_name:
            import urllib.parse
            url += f"&device_name={urllib.parse.quote(self.config.device_name)}"
        if device_fingerprint:
            url += f"&device_fingerprint={device_fingerprint}"
        
        # 连接头
        headers = {}
        if self.config.token:
            headers["Authorization"] = f"Bearer {self.config.token}"
        
        logger.info(f"连接远程服务器: {url}")
        
        try:
            # 兼容不同版本的 websockets 库
            import websockets
            ws_version = tuple(int(x) for x in websockets.__version__.split('.')[:2])
            
            # websockets >= 11.0 使用 additional_headers，< 11.0 使用 extra_headers 或不传
            if ws_version >= (11, 0):
                connect_kwargs = {"additional_headers": headers}
            elif ws_version >= (10, 0):
                connect_kwargs = {"extra_headers": headers}
            else:
                # 旧版本不支持自定义头，在 URL 中传递 token
                if self.config.token:
                    url += f"&token={self.config.token}"
                connect_kwargs = {}
            
            async with websockets.connect(
                url,
                ping_interval=self.config.heartbeat_interval,
                ping_timeout=10,
                close_timeout=5,
                max_size=10 * 1024 * 1024,  # 10MB
                **connect_kwargs
            ) as ws:
                self._ws = ws
                self._set_state(ConnectionState.CONNECTED)
                self._stats.connected_at = datetime.now()
                self._reconnect_attempts = 0
                
                logger.info("远程桥接连接成功")
                
                # ✅ Phase 2.4: 重连后通知服务器恢复离线消息
                await self._on_reconnected()
                
                # 启动状态上报
                self._tasks["status_reporter"] = asyncio.create_task(
                    self._status_reporter.start(self.config.heartbeat_interval)
                )
                
                # 消息循环
                await self._message_loop()
                
        except websockets.exceptions.InvalidURI as e:
            logger.error(f"无效的服务器URL: {e}")
            raise
        except websockets.exceptions.InvalidHandshake as e:
            logger.error(f"WebSocket 握手失败: {e}")
            raise
        except Exception as e:
            logger.error(f"连接异常: {e}")
            raise
        finally:
            self._ws = None
    
    async def _disconnect(self):
        """断开连接"""
        if self._ws:
            try:
                await self._ws.close(code=1000, reason="Client shutdown")
            except Exception as e:
                logger.error(f"关闭连接失败: {e}")
            self._ws = None
        
        # 停止状态上报
        await self._status_reporter.stop()
    
    async def _message_loop(self):
        """消息接收循环"""
        if not self._ws:
            return
        
        try:
            async for raw_message in self._ws:
                if not self._running:
                    break
                
                self._stats.messages_received += 1
                
                try:
                    message = json.loads(raw_message)
                    await self._handle_message(message)
                except json.JSONDecodeError as e:
                    logger.error(f"消息解析失败: {e}")
                    await self._send_error("PARSE_ERROR", "消息格式错误")
                except Exception as e:
                    logger.error(f"消息处理失败: {e}", exc_info=True)
                    await self._send_error("HANDLER_ERROR", str(e))
                    
        except websockets.exceptions.ConnectionClosed as e:
            logger.warning(f"连接关闭: {e}")
        except Exception as e:
            logger.error(f"消息循环异常: {e}", exc_info=True)
    
    async def _handle_message(self, message: dict):
        """处理收到的消息"""
        msg_type = message.get("type", "")
        payload = message.get("payload", {})
        request_id = message.get("request_id", "")
        
        logger.debug(f"收到消息: type={msg_type}, request_id={request_id}")
        
        if msg_type == "ping":
            await self._send_pong()
        
        elif msg_type == "connected":
            # 服务器确认连接成功
            user_bound = message.get("user_bound", False)
            device_id = message.get("device_id", "")
            
            if user_bound:
                logger.info(f"服务器确认连接成功，设备已绑定")
            else:
                logger.warning(f"服务器确认连接成功，但设备未绑定用户，请在 PWA 端完成绑定")
            
            # 通知 GUI 更新状态
            if self.event_bus:
                try:
                    await self.event_bus.emit("bridge_connected", {
                        "user_bound": user_bound,
                        "device_id": device_id
                    })
                except Exception as e:
                    logger.warning(f"发送 bridge_connected 事件失败: {e}")
        
        elif msg_type == "chat":
            # 处理聊天消息
            await self._handle_chat(request_id, payload)
        
        elif msg_type == "tool_call":
            # 处理工具调用
            await self._handle_tool_call(request_id, payload)
        
        elif msg_type == "stop":
            # 停止当前处理
            await self._handle_stop(request_id, payload)
        
        elif msg_type == "get_status":
            # 获取状态
            await self._send_status()
        
        elif msg_type == "get_tools":
            # 获取工具列表
            await self._send_tools_list()
        
        elif msg_type == "pwa_status":
            # PWA 连接状态更新
            await self._handle_pwa_status(payload)
        
        elif msg_type == "file_request":
            # PWA 请求桌面端提供文件
            await self._handle_file_request(request_id, payload)
        
        else:
            logger.warning(f"未知消息类型: {msg_type}")
    
    async def _handle_chat(self, request_id: str, payload: dict):
        """处理聊天请求。
        
        若 Agent 正在处理其他请求（本地或其他 PWA），
        先向发起方发送"排队等待"通知，待 Agent 空闲后再处理。
        """
        content = payload.get("content", "")
        attachments = payload.get("attachments", [])
        options = payload.get("options", {})
        user_id = payload.get("user_id", "")
        session_id = payload.get("session_id", "")  # 获取会话 ID
        
        if not content:
            await self._send_error("EMPTY_MESSAGE", "消息内容为空", request_id)
            return
        
        # 如果 Agent 已持有锁（正在处理其他请求），先通知 PWA 排队等待
        agent = self.agent
        if hasattr(agent, '_chat_lock') and agent._chat_lock is not None and agent._chat_lock.locked():
            logger.info(f"Agent 正忙，请求排队: request={request_id[:8]}, user={user_id[:8]}")
            try:
                await self._send_response(request_id, {
                    "type": "queued",
                    "payload": {
                        "message": "当前 AI 正在处理其他请求，您的请求已排队，请稍等...",
                        "request_id": request_id,
                    }
                })
            except Exception as e:
                logger.debug(f"发送排队通知失败: {e}")
        
        # 创建流式处理任务
        stream_task = asyncio.create_task(
            self._stream_chat_response(
                request_id=request_id,
                user_id=user_id,
                content=content,
                attachments=attachments,
                session_id=session_id,
            )
        )
        self._active_streams[request_id] = stream_task
        
        try:
            await stream_task
        except asyncio.CancelledError:
            await self._send_response(request_id, {
                "type": "cancelled",
                "payload": {"message": "处理已取消"}
            })
        finally:
            self._active_streams.pop(request_id, None)
    
    async def _handle_pwa_status(self, payload: dict):
        """处理 PWA 连接状态更新"""
        connections = payload.get("connections", [])
        count = payload.get("count", 0)
            
        # 更新统计信息
        self._stats.active_pwa_count = count
            
        # 更新连接列表
        self.update_pwa_connections(connections)
            
        logger.info(f"PWA 连接状态更新：{count} 个在线用户")
            
        # 通知 GUI 更新（通过 event_bus）
        if self.event_bus:
            try:
                self.event_bus.emit("pwa_status_update", connections)
            except Exception as e:
                logger.warning(f"发送 PWA 状态事件失败：{e}")
    
    async def _handle_file_request(self, request_id: str, payload: dict):
        """处理来自 PWA 的文件请求 (file_request)
        
        当 PWA 端请求桌面端发送特定文件时，桌面端收到此消息后：
        1. 通过 event_bus 通知 GUI 弹出文件选择对话框
        2. 用户选择文件后，GUI 调用 respond_file_request() 发送文件
        
        注意：PWA 请求路由映射（register_pwa_request）由服务器端维护，
        桌面端只需通过 event_bus 通知 GUI 并最终回传 file_response 即可。
        
        Args:
            request_id: 请求追踪ID（用于响应路由）
            payload: 消息负载
                - user_id: 请求的用户ID
                - session_id: 关联的会话ID
                - reason: 请求原因描述
                - filters: 文件类型过滤（可选）
        """
        user_id = payload.get("user_id", "")
        session_id = payload.get("session_id", "")
        reason = payload.get("reason", "")
        filters = payload.get("filters", {})
        
        logger.info(
            f"收到远程文件请求: request={request_id[:8]}, "
            f"user={user_id[:8] if user_id else 'unknown'}, reason={reason}"
        )
        
        # 若没有事件总线，当前版本无法交互式选择文件，返回错误
        if not self.event_bus:
            logger.warning("event_bus 不可用，无法处理交互式文件请求")
            await self._send_error(
                "FILE_REQUEST_UNSUPPORTED",
                "当前桌面端不支持远程文件请求处理",
                request_id=request_id,
            )
            return
        
        try:
            # 通知 GUI 弹出「远程文件请求」对话框
            # GUI 应在用户选择完后调用 respond_file_request()
            await self.event_bus.emit("remote_file_request", {
                "request_id": request_id,
                "user_id": user_id,
                "session_id": session_id,
                "reason": reason,
                "filters": filters,
            })
            logger.info(f"已发送 remote_file_request 事件到 GUI")
        except Exception as e:
            logger.error(f"发送 remote_file_request 事件失败: {e}", exc_info=True)
            await self._send_error(
                "FILE_REQUEST_EVENT_FAILED",
                "无法处理远程文件请求",
                request_id=request_id,
            )
    
    # ✅ Phase 2.4: 重连后的恢复逻辑
    async def _on_reconnected(self):
        """重连成功后的处理 - 通知服务器恢复离线消息"""
        try:
            logger.info("发送重连通知到服务器")
                
            # 发送重连消息到服务器
            await self._send_raw({
                "type": "reconnected",
                "payload": {
                    "device_id": self.config.device_id,
                    "device_name": self.config.device_name,
                    "reconnected_at": datetime.utcnow().isoformat()
                }
            })
                
            # 服务器会自动推送积压的离线消息
            logger.info("已通知服务器恢复离线消息队列")
                
        except Exception as e:
            logger.error(f"重连通知失败：{e}")
    
    def _get_username_for_user(self, user_id: str) -> str:
        """根据 user_id 查找用户名。"""
        for conn in self._stats.pwa_connections:
            if conn.user_id == user_id and conn.username:
                return conn.username
        return user_id[:8] if user_id else "远程用户"

    async def _stream_chat_response(
        self,
        request_id: str,
        user_id: str,
        content: str,
        attachments: list,
        session_id: str = "",
    ):
        """流式处理聊天响应
        
        处理远程 PWA 发来的消息，包含附件信息时：
        1. 构建附件上下文描述（包含远程 URL）
        2. 拼接到用户消息前面
        3. 调用 Agent 处理
        """
        try:
            # 构建完整消息（包含附件上下文）
            full_message = self._build_remote_attachment_context(
                attachments=attachments,
                user_message=content,
                user_id=user_id,
                session_id=session_id,
            )
            
            logger.info(f"处理远程消息: user={user_id}, attachments={len(attachments)}, request={request_id[:8]}")
            if attachments:
                logger.info(f"附件列表: {[a.get('filename', 'unknown') for a in attachments]}")
            
            # 通知 GUI：远程请求开始
            if self.event_bus:
                username = self._get_username_for_user(user_id)
                try:
                    await self.event_bus.emit("remote_request_started", {
                        "user_id": user_id,
                        "username": username,
                        "request_id": request_id,
                    })
                except Exception as _e:
                    logger.debug(f"发射 remote_request_started 事件失败: {_e}")
            
            # 调用 Agent 的流式处理
            full_response = ""
            chunk_count = 0
            if hasattr(self.agent, 'chat_stream'):
                # Agent.chat_stream 返回字符串片段
                async for chunk in self.agent.chat_stream(user_input=full_message):
                    # chunk 是字符串，直接收集
                    if isinstance(chunk, str):
                        full_response += chunk
                        chunk_count += 1
                        # 发送流式内容
                        await self._send_stream_chunk(request_id, {"delta": chunk})
                    elif isinstance(chunk, dict):
                        # 兼容字典格式
                        if chunk.get("type") == "content":
                            delta = chunk.get("delta", "")
                            full_response += delta
                            chunk_count += 1
                            await self._send_stream_chunk(request_id, {"delta": delta})
                
                logger.info(f"流式响应完成: request={request_id[:8]}, length={len(full_response)}")
                
                # 发送完成消息（PWA 期望 stream_end 类型）
                await self._send_response(request_id, {
                    "type": "stream_end",
                    "payload": {"content": full_response, "message_id": request_id}
                })
            else:
                # 降级：同步处理
                response = await self.agent.chat(full_message)
                await self._send_response(request_id, {
                    "type": "stream_end",
                    "payload": {"content": response, "message_id": request_id}
                })
                
        except Exception as e:
            logger.error(f"聊天处理失败: {e}", exc_info=True)
            await self._send_error("CHAT_ERROR", str(e), request_id)
        finally:
            # 通知 GUI：远程请求结束
            if self.event_bus:
                try:
                    await self.event_bus.emit("remote_request_ended", {
                        "request_id": request_id,
                        "user_id": user_id,
                    })
                except Exception as _e:
                    logger.debug(f"发射 remote_request_ended 事件失败: {_e}")
    
    def _get_server_base_url(self) -> str:
        """从 WebSocket server_url 推导 HTTP 基础地址
        
        用于构建文件上传/下载的 HTTP API 地址。
        复用逻辑，避免各处重复 ws→http 转换。
        
        Returns:
            HTTP/HTTPS 基础 URL
        """
        server_url = getattr(self.config, "server_url", "")
        if not server_url:
            return "https://weclaw.cc:8188"
        
        base = server_url.replace("/ws/bridge", "")
        if base.startswith("wss://"):
            base = "https://" + base[len("wss://"):]
        elif base.startswith("ws://"):
            base = "http://" + base[len("ws://"):]
        return base

    def _get_valid_access_token(self) -> str:
        """获取有效的 access_token，支持 keystore 加载和自动刷新。
        
        优先级：
        1. 检查 self.config.token 是否有效（未过期）
        2. 从 keystore 加载 WECLAW_ACCESS_TOKEN
        3. 使用 WECLAW_REFRESH_TOKEN 刷新获取新 token
        4. 刷新成功后同步更新 self.config.token 和 keystore
        
        Returns:
            有效的 access_token，获取失败返回空字符串
        """
        import time
        
        def _is_token_valid(token: str) -> bool:
            """简单检查 JWT token 是否未过期（解码 payload 但不验证签名）。"""
            if not token:
                return False
            try:
                import base64
                import json
                # JWT = header.payload.signature
                parts = token.split(".")
                if len(parts) != 3:
                    return False
                # Base64url 解码 payload
                payload_b64 = parts[1]
                # 补齐 padding
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding
                payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                exp = payload.get("exp", 0)
                # 提前 60 秒视为过期，留出安全余量
                return exp > time.time() + 60
            except Exception:
                return False
        
        # 1. 检查当前 config.token
        if _is_token_valid(self.config.token):
            return self.config.token
        
        # 2. 从 keystore 加载
        try:
            from ..ui.keystore import load_key, save_key
            stored_token = load_key("WECLAW_ACCESS_TOKEN")
            if _is_token_valid(stored_token):
                self.config.token = stored_token
                logger.info("从 keystore 加载有效 access_token")
                return stored_token
        except Exception as e:
            logger.debug(f"从 keystore 加载 token 失败: {e}")
        
        # 3. 使用 refresh_token 刷新
        try:
            from ..ui.keystore import load_key, save_key
            refresh_token = load_key("WECLAW_REFRESH_TOKEN")
            if not refresh_token:
                logger.warning("无 refresh_token，无法刷新 access_token")
                return self.config.token or ""
            
            import requests as http_requests
            base_url = self._get_server_base_url()
            refresh_url = f"{base_url}/api/auth/refresh"
            
            resp = http_requests.post(
                refresh_url,
                headers={"Authorization": f"Bearer {refresh_token}"},
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
            
            new_token = ""
            if isinstance(result, dict):
                # 兼容 {"success": true, "data": {"access_token": "..."}} 格式
                data = result.get("data", result)
                new_token = data.get("access_token", "")
            
            if new_token and _is_token_valid(new_token):
                self.config.token = new_token
                save_key("WECLAW_ACCESS_TOKEN", new_token)
                logger.info("access_token 自动刷新成功")
                return new_token
            else:
                logger.warning(f"刷新返回的 token 无效")
        except Exception as e:
            logger.warning(f"刷新 access_token 失败: {e}")
        
        return self.config.token or ""
    
    def _build_remote_attachment_context(
        self, 
        attachments: list, 
        user_message: str,
        user_id: str = "",
        session_id: str = "",
    ) -> str:
        """构建远程附件上下文
        
        将远程 PWA 传来的附件信息转换为 Agent 可理解的文本描述。
        对于图片附件，会下载到本地持久化目录，返回本地路径供 OCR 工具使用。
        
        注意：这里的附件都是【当前对话】中用户刚刚上传的，
        与【历史对话】中的附件区分开（历史附件需要通过 attachment_search 工具搜索）。
        
        Args:
            attachments: 远程附件列表，每个元素是 dict：
                - attachment_id: 附件 ID
                - type: 类型 (image/audio/file)
                - data: URL 或 base64
                - filename: 文件名
                - mime_type: MIME 类型
            user_message: 用户消息
            user_id: 用户 ID（用于附件存储）
            session_id: 会话 ID（用于附件存储，区分不同对话）
            
        Returns:
            构建好的完整消息（附件上下文 + 用户请求）
        """
        if not attachments:
            return user_message
        
        # 获取服务器基础 URL（用于构建完整的图片地址）
        server_base_url = self._get_server_base_url()
        
        # 【重要】明确标注这是当前对话的附件
        lines = [
            "[当前对话附件]",
            f"（会话ID: {session_id[:16]}... 以下是用户在本次对话中刚刚上传的文件）"
        ]
        
        # 收集不同类型的附件，用于生成工具使用建议
        image_files = []
        audio_files = []
        document_files = []
        code_files = []
        other_files = []
        
        for att in attachments:
            filename = att.get("filename", "未知文件")
            att_type = att.get("type", "file")
            mime_type = att.get("mime_type", "")
            data = att.get("data", "")
            attachment_id = att.get("attachment_id", "")
            
            # 智能判断文件类型（基于 MIME 类型和扩展名）
            file_category = self._categorize_file(filename, mime_type, att_type)
            
            # 类型描述
            type_desc = {
                "image": "图片",
                "audio": "音频",
                "video": "视频",
                "document": "文档",
                "code": "代码",
                "file": "文件",
            }.get(file_category, "文件")
            
            # 构建完整的 URL
            if data.startswith("/api/files/"):
                full_url = f"{server_base_url}{data}"
            elif data.startswith("http"):
                full_url = data
            else:
                full_url = None
            
            # 下载文件到本地（支持所有类型）
            local_path = None
            if full_url:
                local_path = self._download_remote_file(
                    url=full_url,
                    filename=filename,
                    attachment_id=attachment_id,
                    user_id=user_id,
                    session_id=session_id,
                    mime_type=mime_type,
                    file_type=file_category,
                    user_message=user_message,
                )
            
            # 构建附件描述
            if local_path:
                lines.append(f"- {filename} ({type_desc}, 路径: {local_path})")
                logger.info(f"远程文件已下载到本地: {filename} -> {local_path}")
            elif full_url:
                lines.append(f"- {filename} ({type_desc}，URL: {full_url})")
            else:
                lines.append(f"- {filename} ({type_desc}，ID: {attachment_id})")
            
            # 收集到对应类别
            file_info = {"filename": filename, "path": local_path, "url": full_url}
            if file_category == "image":
                image_files.append(file_info)
            elif file_category == "audio":
                audio_files.append(file_info)
            elif file_category in ("document", "code"):
                if file_category == "code":
                    code_files.append(file_info)
                else:
                    document_files.append(file_info)
            else:
                other_files.append(file_info)
        
        # 添加工具使用建议
        lines.append("")
        lines.append("[工具使用建议]")
        if image_files:
            lines.append(f"- 图片文件: 请使用 ocr_recognize_file 工具识别图片中的文字")
        if audio_files:
            lines.append(f"- 音频文件: 请使用 voice_input_transcribe_file 工具转录音频内容")
        if document_files:
            pdf_files = [f for f in document_files if f['filename'].lower().endswith('.pdf')]
            doc_files = [f for f in document_files if f['filename'].lower().endswith(('.doc', '.docx'))]
            if pdf_files:
                lines.append(f"- PDF文档: 请使用 knowledge_rag_add_document 添加到知识库，或 file_read 直接读取")
            if doc_files:
                lines.append(f"- Word文档: 请使用 file_read 工具读取内容")
        if code_files:
            lines.append(f"- 代码文件: 请使用 file_read 工具读取代码内容")
        if other_files:
            lines.append(f"- 其他文件: 请使用 file_read 工具读取文件内容")
        
        lines.append("")
        lines.append(f"用户请求: {user_message}")
        
        full_context = "\n".join(lines)
        logger.debug(f"构建的附件上下文:\n{full_context}")
        
        return full_context
    
    def _categorize_file(
        self, 
        filename: str, 
        mime_type: str, 
        att_type: str
    ) -> str:
        """智能分类文件类型
        
        基于 MIME 类型、文件扩展名和传入的类型进行综合判断。
        
        Returns:
            文件类别: 'image' | 'audio' | 'video' | 'document' | 'code' | 'file'
        """
        # 优先使用 MIME 类型判断
        if mime_type:
            if mime_type.startswith('image/'):
                return 'image'
            if mime_type.startswith('audio/'):
                return 'audio'
            if mime_type.startswith('video/'):
                return 'video'
        
        # 使用扩展名判断
        ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
        
        # 图片扩展名
        if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'ico'):
            return 'image'
        
        # 音频扩展名
        if ext in ('mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a', 'wma'):
            return 'audio'
        
        # 视频扩展名
        if ext in ('mp4', 'webm', 'avi', 'mov', 'mkv', 'flv'):
            return 'video'
        
        # 代码文件扩展名
        if ext in ('py', 'js', 'ts', 'java', 'c', 'cpp', 'h', 'go', 'rs', 'rb', 
                   'php', 'swift', 'kt', 'scala', 'sh', 'bash', 'ps1', 'bat',
                   'html', 'htm', 'css', 'scss', 'less', 'json', 'xml', 'yaml', 'yml',
                   'sql', 'vue', 'jsx', 'tsx'):
            return 'code'
        
        # 文档扩展名
        if ext in ('pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 
                   'txt', 'md', 'rtf', 'csv', 'odt', 'ods', 'odp'):
            return 'document'
        
        # 使用传入的类型
        if att_type in ('image', 'audio', 'video', 'document', 'code'):
            return att_type
        
        return 'file'
    
    def _download_remote_file(
        self, 
        url: str, 
        filename: str, 
        attachment_id: str,
        user_id: str = "",
        session_id: str = "",
        mime_type: str = "",
        file_type: str = "file",
        user_message: str = "",
    ) -> str | None:
        """下载远程文件到本地持久化目录，并保存元数据
        
        支持所有类型的文件（图片、音频、文档、代码等）。
        
        Args:
            url: 文件的完整 URL
            filename: 原始文件名
            attachment_id: 附件 ID
            user_id: 用户 ID
            session_id: 会话 ID
            mime_type: MIME 类型
            file_type: 文件类型 ('image'/'audio'/'document'/'code'/'file')
            user_message: 用户消息（用于提取描述）
            
        Returns:
            本地文件路径，失败返回 None
        """
        from pathlib import Path
        
        try:
            import requests
        except ImportError:
            logger.warning("requests 库未安装，无法下载远程文件")
            return None
        
        try:
            # 使用持久化存储系统
            from .attachment_storage import get_attachment_storage, StoredAttachment
            storage = get_attachment_storage()
            
            # 先检查是否已有缓存
            existing = storage.get_attachment(attachment_id)
            if existing and Path(existing.local_path).exists():
                # 更新访问记录
                storage.update_access(attachment_id)
                logger.info(f"使用已缓存的文件: {existing.local_path}")
                return existing.local_path
            
            # 创建存储目录
            cache_dir = storage.attachments_dir
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成本地文件名（使用 attachment_id 避免冲突）
            safe_filename = f"{attachment_id[:8]}_{filename}"
            local_path = cache_dir / safe_filename
            
            # 下载文件
            logger.info(f"正在下载远程文件: {url}")
            response = requests.get(url, timeout=60, stream=True)  # 文件可能较大，增加超时
            response.raise_for_status()
            
            # 保存到本地
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = local_path.stat().st_size
            logger.info(f"远程文件下载成功: {local_path} ({file_size} bytes)")
            
            # 提取描述信息（从用户消息中）
            description = self._extract_attachment_description(user_message, filename)
            
            # 保存附件元数据
            attachment = StoredAttachment(
                id=attachment_id,
                session_id=session_id or self._session_id,
                user_id=user_id,
                filename=filename,
                file_type=file_type,
                mime_type=mime_type or "application/octet-stream",
                local_path=str(local_path),
                remote_url=url,
                file_size=file_size,
                description=description,
            )
            storage.save_attachment(attachment)
            
            return str(local_path)
            
        except Exception as e:
            logger.error(f"下载远程文件失败: {e}", exc_info=True)
            return None
    
    def _download_remote_image(
        self, 
        url: str, 
        filename: str, 
        attachment_id: str,
        user_id: str = "",
        session_id: str = "",
        mime_type: str = "",
        user_message: str = "",
    ) -> str | None:
        """下载远程图片到本地持久化目录，并保存元数据
        
        Args:
            url: 图片的完整 URL
            filename: 原始文件名
            attachment_id: 附件 ID
            user_id: 用户 ID
            session_id: 会话 ID
            mime_type: MIME 类型
            user_message: 用户消息（用于提取描述）
            
        Returns:
            本地文件路径，失败返回 None
        """
        from pathlib import Path
        
        try:
            import requests
        except ImportError:
            logger.warning("requests 库未安装，无法下载远程图片")
            return None
        
        try:
            # 使用持久化存储系统
            from .attachment_storage import get_attachment_storage, StoredAttachment
            storage = get_attachment_storage()
            
            # 先检查是否已有缓存
            existing = storage.get_attachment(attachment_id)
            if existing and Path(existing.local_path).exists():
                # 更新访问记录
                storage.update_access(attachment_id)
                logger.info(f"使用已缓存的图片: {existing.local_path}")
                return existing.local_path
            
            # 创建存储目录
            cache_dir = storage.attachments_dir
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成本地文件名（使用 attachment_id 避免冲突）
            safe_filename = f"{attachment_id[:8]}_{filename}"
            local_path = cache_dir / safe_filename
            
            # 下载图片
            logger.info(f"正在下载远程图片: {url}")
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # 保存到本地
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = local_path.stat().st_size
            logger.info(f"远程图片下载成功: {local_path} ({file_size} bytes)")
            
            # 提取描述信息（从用户消息中）
            description = self._extract_attachment_description(user_message, filename)
            
            # 保存附件元数据
            attachment = StoredAttachment(
                id=attachment_id,
                session_id=session_id or self._session_id,
                user_id=user_id,
                filename=filename,
                file_type="image",
                mime_type=mime_type or "image/jpeg",
                local_path=str(local_path),
                remote_url=url,
                file_size=file_size,
                description=description,
            )
            storage.save_attachment(attachment)
            
            return str(local_path)
            
        except requests.RequestException as e:
            logger.error(f"下载远程图片失败: {url}, 错误: {e}")
            return None
        except Exception as e:
            logger.error(f"保存远程图片失败: {e}")
            return None
    
    def _extract_attachment_description(self, user_message: str, filename: str) -> str:
        """从用户消息中提取附件的描述信息
        
        Args:
            user_message: 用户的消息内容
            filename: 文件名
            
        Returns:
            提取的描述信息
        """
        # 简单策略：使用用户消息的前100个字符作为描述
        # 后续可以用 NLP 提取更精准的描述
        if not user_message:
            return filename
        
        # 去掉常见的指令词，保留描述性内容
        desc = user_message.strip()
        
        # 如果消息太长，截取前100个字符
        if len(desc) > 100:
            desc = desc[:100] + "..."
        
        return desc
    
    def _upload_file_to_remote(
        self,
        file_path: str,
        user_id: str,
        session_id: str = "",
        description: str = "",
    ) -> dict | None:
        """上传本地文件到远程文件服务
        
        将本地文件通过 HTTP POST 上传到服务器 /api/files/upload 接口，
        并将上传成功的元数据写入 AttachmentStorage 以便历史检索。
        
        Args:
            file_path: 本地文件的绝对路径或相对路径
            user_id: 关联的用户ID（用于存储隔离）
            session_id: 关联的会话ID（可选）
            description: 文件描述（可选，用于搜索）
            
        Returns:
            上传成功的响应数据，包含 attachment_id, filename, size_bytes, url
            失败返回 None
        """
        import mimetypes
        
        try:
            import requests
        except ImportError:
            logger.warning("requests 库未安装，无法上传文件到远程服务器")
            return None
        
        path = Path(file_path)
        if not path.is_file():
            logger.warning(f"待上传文件不存在: {file_path}")
            return None
        
        # 检查文件大小（防止上传超大文件）
        file_size = path.stat().st_size
        max_size = 50 * 1024 * 1024  # 50MB，与服务器配置一致
        if file_size > max_size:
            logger.warning(f"文件大小超过限制: {file_size} bytes > {max_size} bytes")
            return None
        
        base_url = self._get_server_base_url()
        upload_url = f"{base_url}/api/files/upload"
        
        # 推测 MIME 类型
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "application/octet-stream"
        
        # 构建认证头：
        # 主认证: X-Device-Fingerprint（复用 Bridge 已验证的设备指纹）
        # 后备: JWT Bearer Token（从 keystore 加载 + 自动刷新）
        headers = {}
        if self._device_fingerprint:
            headers["X-Device-Fingerprint"] = self._device_fingerprint
        access_token = self._get_valid_access_token()
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        
        if not self._device_fingerprint and not access_token:
            logger.warning("无设备指纹也无 access_token，上传可能因 401 认证失败")
        
        logger.info(f"开始上传本地文件: {file_path} -> {upload_url}")
        
        try:
            with open(path, "rb") as f:
                files = {"file": (path.name, f, mime_type)}
                data = {"session_id": session_id} if session_id else {}
                
                resp = requests.post(
                    upload_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=120  # 大文件需要较长超时
                )
            
            if resp.status_code == 401:
                # 两种认证都失败，尝试强制刷新 JWT 后重试
                logger.warning("上传认证失败(401)，尝试刷新 token 后重试")
                self.config.token = ""  # 清除旧 token 强制刷新
                new_token = self._get_valid_access_token()
                if new_token:
                    headers["Authorization"] = f"Bearer {new_token}"
                    with open(path, "rb") as f:
                        files = {"file": (path.name, f, mime_type)}
                        resp = requests.post(
                            upload_url, headers=headers,
                            files=files, data=data, timeout=120,
                        )
                else:
                    logger.error("刷新 token 失败，无法重试上传")
            
            resp.raise_for_status()
            result = resp.json()
        except requests.RequestException as e:
            status = getattr(getattr(e, 'response', None), 'status_code', '?')
            detail = ""
            try:
                detail = e.response.json().get('detail', '') if e.response else ''
            except Exception:
                pass
            logger.error(f"上传文件失败: HTTP {status} {detail or e}")
            return None
        except Exception as e:
            logger.error(f"上传文件异常: {e}")
            return None
        
        # 验证响应完整性
        attachment_id = result.get("attachment_id")
        filename = result.get("filename", path.name)
        size_bytes = result.get("size_bytes", file_size)
        url = result.get("url")
        
        if not attachment_id or not url:
            logger.error(f"上传返回结果不完整: {result}")
            return None
        
        logger.info(
            f"本地文件上传成功: id={attachment_id[:8]}, "
            f"name={filename}, size={size_bytes}"
        )
        
        # 写入附件持久化存储（便于历史检索）
        try:
            from .attachment_storage import get_attachment_storage, StoredAttachment
            storage = get_attachment_storage()
            
            attachment = StoredAttachment(
                id=attachment_id,
                session_id=session_id or self._session_id,
                user_id=user_id,
                filename=filename,
                file_type=self._categorize_file(filename, mime_type, "file"),
                mime_type=mime_type,
                local_path=str(path),
                remote_url=f"{base_url}{url}",
                file_size=size_bytes,
                description=description or path.name,
            )
            storage.save_attachment(attachment)
        except Exception as e:
            logger.warning(f"保存上传文件元数据失败: {e}")
        
        return {
            "attachment_id": attachment_id,
            "filename": filename,
            "size_bytes": size_bytes,
            "url": url,
        }
    
    async def _handle_tool_call(self, request_id: str, payload: dict):
        """处理工具调用请求"""
        tool = payload.get("tool", "")
        action = payload.get("action", "")
        arguments = payload.get("arguments", {})
        
        if not tool:
            await self._send_error("MISSING_TOOL", "未指定工具名称", request_id)
            return
        
        self._stats.tool_calls_executed += 1
        start_time = time.time()
        
        try:
            # 发送开始状态
            await self._send_tool_call(request_id, {
                "tool": tool,
                "action": action,
                "status": "running"
            })
            
            # 执行工具
            result = await self._message_handler.execute_tool(tool, action, arguments)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 发送结果
            await self._send_tool_call(request_id, {
                "tool": tool,
                "action": action,
                "status": "success",
                "result": result,
                "duration_ms": duration_ms
            })
            
        except Exception as e:
            logger.error(f"工具执行失败: {e}", exc_info=True)
            await self._send_tool_call(request_id, {
                "tool": tool,
                "action": action,
                "status": "failed",
                "error": str(e)
            })
    
    async def _handle_stop(self, request_id: str, payload: dict):
        """处理停止请求"""
        target_id = payload.get("request_id", request_id)
        
        if target_id in self._active_streams:
            task = self._active_streams[target_id]
            if not task.done():
                task.cancel()
            await self._send_response(request_id, {
                "type": "stopped",
                "payload": {"target": target_id}
            })
        else:
            await self._send_response(request_id, {
                "type": "error",
                "payload": {"message": "未找到目标请求"}
            })
    
    # ========== 文件传输公开 API ==========
    
    async def send_file_to_pwa(
        self,
        user_id: str,
        file_path: str,
        description: str = "",
        session_id: str = "",
    ) -> bool:
        """将本地文件主动分享给指定 PWA 用户
        
        用法示例：
            - 桌面端生成报告后，一键发送到 PWA 查看
            - 截图后直接分享到手机
        
        Args:
            user_id: 目标用户的 ID
            file_path: 本地文件路径
            description: 文件描述（可选）
            session_id: 会话 ID（可选）
            
        Returns:
            是否发送成功
        """
        if not self.is_connected:
            logger.warning("发送文件失败：Bridge 未连接")
            return False
        
        # 1. 上传文件到服务器
        upload_result = self._upload_file_to_remote(
            file_path=file_path,
            user_id=user_id,
            session_id=session_id,
            description=description,
        )
        if not upload_result:
            logger.error(f"上传文件失败: {file_path}")
            return False
        
        # 2. 构建并发送 file_share 消息
        base_url = self._get_server_base_url()
        full_url = f"{base_url}{upload_result['url']}"
        
        # 推断文件类型
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        file_type = self._categorize_file(
            upload_result['filename'], 
            mime_type or "", 
            "file"
        )
        
        message = {
            "type": "file_share",
            "payload": {
                "user_id": user_id,
                "session_id": session_id,
                "files": [{  # 统一使用 files 数组格式，与服务器端一致
                    "file_id": upload_result["attachment_id"],
                    "filename": upload_result["filename"],
                    "file_type": file_type,
                    "mime_type": mime_type or "application/octet-stream",
                    "size_bytes": upload_result["size_bytes"],
                    "url": full_url,
                    "description": description,
                }],
            },
        }
        
        await self._send_raw(message)
        logger.info(
            f"已发送 file_share: user={user_id[:8]}, "
            f"file={upload_result['filename']}"
        )
        return True
    
    async def send_files_to_pwa(
        self,
        user_id: str,
        file_paths: list[str],
        message: str = "",
        session_id: str = "",
    ) -> bool:
        """将多个本地文件分享给指定 PWA 用户
        
        Args:
            user_id: 目标用户的 ID
            file_paths: 本地文件路径列表
            message: 附带的文字消息
            session_id: 会话 ID（可选）
            
        Returns:
            是否全部发送成功
        """
        if not self.is_connected:
            return False
        
        import mimetypes
        
        success_count = 0
        files = []
        
        for file_path in file_paths:
            result = self._upload_file_to_remote(
                file_path=file_path,
                user_id=user_id,
                session_id=session_id,
            )
            if result:
                success_count += 1
                mime_type, _ = mimetypes.guess_type(str(file_path))
                files.append({
                    "file_id": result["attachment_id"],
                    "filename": result["filename"],
                    "file_type": self._categorize_file(result['filename'], mime_type or "", "file"),
                    "mime_type": mime_type or "application/octet-stream",
                    "size_bytes": result["size_bytes"],
                    "url": f"{self._get_server_base_url()}{result['url']}",
                })
        
        if not files:
            return False
        
        await self._send_raw({
            "type": "file_share",
            "payload": {
                "user_id": user_id,
                "session_id": session_id,
                "files": files,
                "message": message,
            },
        })
        
        logger.info(f"已发送 {success_count}/{len(file_paths)} 个文件到 PWA")
        return success_count == len(file_paths)
    
    async def respond_file_request(
        self,
        request_id: str,
        user_id: str,
        file_path: str,
        description: str = "",
        session_id: str = "",
    ) -> bool:
        """响应来自 PWA 的文件请求
        
        当用户通过 GUI 选择文件后，调用此方法将文件发送给请求方 PWA。
        
        注意：请求映射清理（complete_pwa_request）由服务器端在转发 file_response 后自动执行，
        桌面端无需也无法调用服务器端的 BridgeConnectionManager。
        
        Args:
            request_id: 原始 file_request 的 request_id
            user_id: 请求的用户 ID
            file_path: 要发送的本地文件路径
            description: 文件描述（可选）
            session_id: 会话 ID（可选）
            
        Returns:
            是否发送成功
        """
        if not self.is_connected:
            logger.warning("发送文件响应失败：Bridge 未连接")
            return False
        
        # 1. 上传文件到服务器
        upload_result = self._upload_file_to_remote(
            file_path=file_path,
            user_id=user_id,
            session_id=session_id,
            description=description,
        )
        if not upload_result:
            # 通知 PWA 上传失败
            await self._send_error(
                "FILE_UPLOAD_FAILED",
                "桌面端上传文件到服务器失败",
                request_id=request_id,
            )
            return False
        
        # 2. 构建并发送 file_response 消息
        base_url = self._get_server_base_url()
        
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        response_message = {
            "type": "file_response",
            "request_id": request_id,  # 关键：沿用原始 request_id 用于路由
            "payload": {
                "user_id": user_id,
                "session_id": session_id,
                "files": [{
                    "file_id": upload_result["attachment_id"],
                    "filename": upload_result["filename"],
                    "file_type": self._categorize_file(
                        upload_result['filename'], mime_type or "", "file"
                    ),
                    "mime_type": mime_type or "application/octet-stream",
                    "size_bytes": upload_result["size_bytes"],
                    "url": f"{base_url}{upload_result['url']}",
                    "description": description,
                }],
                "message": description or "",
            },
        }
        
        await self._send_raw(response_message)
        
        logger.info(
            f"已发送 file_response: request={request_id[:8]}, "
            f"user={user_id[:8]}, file={upload_result['filename']}"
        )
        return True
    
    # ========== 消息发送方法 ==========
    
    async def _send_raw(self, message: dict):
        """发送原始消息"""
        if self._ws and self._state == ConnectionState.CONNECTED:
            try:
                await self._ws.send(json.dumps(message, ensure_ascii=False))
                self._stats.messages_sent += 1
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
    
    async def _send_pong(self):
        """发送心跳响应"""
        await self._send_raw({"type": "pong", "timestamp": datetime.now().isoformat()})
        self._stats.last_heartbeat = datetime.now()
    
    async def _send_response(self, request_id: str, response: dict):
        """发送响应消息"""
        response["request_id"] = request_id
        await self._send_raw(response)
    
    async def _send_stream_chunk(self, request_id: str, chunk: dict):
        """发送流式响应块
        
        转换为 PWA 端期望的格式：
        - type: "stream"
        - payload.content: 文本内容
        """
        # 获取文本内容（兼容 delta 或 content 字段）
        content = chunk.get("delta", "") or chunk.get("content", "")
        
        # 转换为 PWA 期望的格式
        message = {
            "type": "stream",
            "request_id": request_id,
            "payload": {"content": content}  # PWA 期望 content 字段
        }
        
        await self._send_raw(message)
    
    async def _send_tool_call(self, request_id: str, data: dict):
        """发送工具调用状态"""
        await self._send_raw({
            "type": "tool_call",
            "request_id": request_id,
            "payload": data
        })
    
    async def _send_error(self, code: str, message: str, request_id: str = ""):
        """发送错误消息"""
        await self._send_raw({
            "type": "error",
            "request_id": request_id,
            "payload": {"code": code, "message": message}
        })
    
    async def _send_status(self):
        """发送状态更新"""
        status = self._status_reporter.get_current_status()
        status["session_id"] = self._session_id
        await self._send_raw({
            "type": "status_update",
            "payload": status
        })
    
    async def _send_tools_list(self):
        """发送工具列表"""
        tools = self._message_handler.get_tools()
        await self._send_raw({
            "type": "tools_list",
            "payload": {"tools": tools}
        })
