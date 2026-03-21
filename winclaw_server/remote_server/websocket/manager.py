"""WebSocket 连接管理器

管理 WebSocket 连接的生命周期、心跳检测、消息推送。
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """连接信息"""
    user_id: str
    websocket: WebSocket
    session_id: str
    connected_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    request_count: int = 0  # 请求计数


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(
        self,
        heartbeat_interval: int = 30,
        connection_timeout: int = 300,
        max_connections_per_user: int = 3
    ):
        """
        初始化连接管理器
        
        Args:
            heartbeat_interval: 心跳间隔（秒）
            connection_timeout: 连接超时（秒）
            max_connections_per_user: 每用户最大连接数
        """
        self.heartbeat_interval = heartbeat_interval
        self.connection_timeout = connection_timeout
        self.max_connections_per_user = max_connections_per_user
        
        # 活跃连接: user_id -> ConnectionInfo
        self._connections: Dict[str, ConnectionInfo] = {}
        
        # 用户连接映射: user_id -> set of connection ids
        self._user_connections: Dict[str, Set[str]] = {}
        
        # 会话映射: session_id -> user_id
        self._session_map: Dict[str, str] = {}
        
        # 心跳任务
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def connect(
        self,
        user_id: str,
        websocket: WebSocket,
        session_id: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        接受 WebSocket 连接
        
        Args:
            user_id: 用户ID
            websocket: WebSocket 连接对象
            session_id: 会话ID
            metadata: 连接元数据
            
        Returns:
            是否连接成功
        """
        # 检查用户连接数限制
        user_conns = self._user_connections.get(user_id, set())
        if len(user_conns) >= self.max_connections_per_user:
            # 关闭最旧的连接
            oldest_conn_id = min(
                user_conns,
                key=lambda cid: self._connections[cid].connected_at
            )
            await self._disconnect_user(oldest_conn_id, reason="超过最大连接数")
        
        # 接受连接
        await websocket.accept()
        
        # 创建连接信息
        conn_id = f"{user_id}_{int(time.time() * 1000)}"
        conn_info = ConnectionInfo(
            user_id=user_id,
            websocket=websocket,
            session_id=session_id,
            metadata=metadata or {}
        )
        
        # 记录连接
        self._connections[conn_id] = conn_info
        
        if user_id not in self._user_connections:
            self._user_connections[user_id] = set()
        self._user_connections[user_id].add(conn_id)
        
        self._session_map[session_id] = user_id
        
        logger.info(f"WebSocket 连接建立: user={user_id}, session={session_id}")
        
        # 发送连接确认
        await self._send_to_connection(conn_id, {
            "type": "connected",
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return True
    
    async def disconnect(self, user_id: str, session_id: str):
        """断开连接"""
        conn_id = self._find_connection_id(user_id, session_id)
        if conn_id:
            await self._disconnect_user(conn_id)
    
    async def _disconnect_user(self, conn_id: str, reason: str = ""):
        """断开指定连接"""
        if conn_id not in self._connections:
            return
        
        conn_info = self._connections[conn_id]
        user_id = conn_info.user_id
        
        try:
            await conn_info.websocket.close(code=1000, reason=reason)
        except Exception:
            pass
        
        # 清理记录
        del self._connections[conn_id]
        
        if user_id in self._user_connections:
            self._user_connections[user_id].discard(conn_id)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
        
        if conn_info.session_id in self._session_map:
            del self._session_map[conn_info.session_id]
        
        logger.info(f"WebSocket 连接断开: user={user_id}, reason={reason}")
    
    async def close_all(self):
        """关闭所有连接"""
        tasks = []
        for conn_id in list(self._connections.keys()):
            tasks.append(self._disconnect_user(conn_id, reason="服务器关闭"))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("所有 WebSocket 连接已关闭")
    
    def _find_connection_id(self, user_id: str, session_id: str) -> Optional[str]:
        """查找连接ID"""
        for conn_id, conn_info in self._connections.items():
            if conn_info.user_id == user_id and conn_info.session_id == session_id:
                return conn_id
        return None
    
    async def send_message(self, user_id: str, message: dict) -> bool:
        """
        向用户发送消息
        
        Args:
            user_id: 用户ID
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        sent = False
        for conn_id in list(self._user_connections.get(user_id, set())):
            if await self._send_to_connection(conn_id, message):
                sent = True
        return sent
    
    async def send_to_session(self, session_id: str, message: dict) -> bool:
        """
        向指定会话发送消息
        
        Args:
            session_id: 会话ID
            message: 消息内容
            
        Returns:
            是否发送成功
        """
        user_id = self._session_map.get(session_id)
        if not user_id:
            return False
        
        conn_id = self._find_connection_id(user_id, session_id)
        if conn_id:
            return await self._send_to_connection(conn_id, message)
        return False
    
    async def _send_to_connection(self, conn_id: str, message: dict) -> bool:
        """向指定连接发送消息"""
        if conn_id not in self._connections:
            # logger.debug(f"发送失败：连接不存在 conn_id={conn_id}")  # 调试用
            return False
        
        conn_info = self._connections[conn_id]
        
        # 检查 WebSocket 连接状态
        try:
            ws_state = conn_info.websocket.client_state
            if ws_state.name != 'CONNECTED':
                logger.warning(f"发送前检测到连接异常: user={conn_info.user_id[:8]}, state={ws_state.name}")
                await self._disconnect_user(conn_id, reason=f"连接状态异常: {ws_state.name}")
                return False
        except Exception as e:
            logger.warning(f"检查连接状态失败: {e}")
        
        try:
            await conn_info.websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"发送消息失败: user={conn_info.user_id[:8]}, error={e}")
            await self._disconnect_user(conn_id, reason=f"发送失败: {e}")
            return False
    
    async def broadcast(self, message: dict, exclude_users: Optional[Set[str]] = None):
        """
        广播消息给所有连接
        
        Args:
            message: 消息内容
            exclude_users: 排除的用户ID集合
        """
        exclude_users = exclude_users or set()
        
        tasks = []
        for user_id in self._user_connections:
            if user_id not in exclude_users:
                tasks.append(self.send_message(user_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def is_connected(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return user_id in self._user_connections and len(self._user_connections[user_id]) > 0
    
    def get_connection_count(self) -> int:
        """获取总连接数"""
        return len(self._connections)
    
    def get_user_count(self) -> int:
        """获取在线用户数"""
        return len(self._user_connections)
    
    def get_user_sessions(self, user_id: str) -> list:
        """获取用户的所有会话"""
        sessions = []
        for conn_id in self._user_connections.get(user_id, set()):
            if conn_id in self._connections:
                conn_info = self._connections[conn_id]
                sessions.append({
                    "session_id": conn_info.session_id,
                    "connected_at": conn_info.connected_at.isoformat(),
                    "metadata": conn_info.metadata
                })
        return sessions
    
    async def update_heartbeat(self, user_id: str, session_id: str):
        """更新心跳时间"""
        conn_id = self._find_connection_id(user_id, session_id)
        if conn_id and conn_id in self._connections:
            self._connections[conn_id].last_heartbeat = time.time()
    
    async def check_timeouts(self):
        """检查超时连接"""
        now = time.time()
        timeout_conns = []
        
        for conn_id, conn_info in self._connections.items():
            if now - conn_info.last_heartbeat > self.connection_timeout:
                timeout_conns.append(conn_id)
        
        for conn_id in timeout_conns:
            await self._disconnect_user(conn_id, reason="连接超时")
    
    async def start_heartbeat_checker(self):
        """启动心跳检查任务"""
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            await self.check_timeouts()
    
    def get_connection_info(self, user_id: str, session_id: str) -> Optional[ConnectionInfo]:
        """获取连接信息"""
        conn_id = self._find_connection_id(user_id, session_id)
        if conn_id:
            return self._connections.get(conn_id)
        return None
    
    def get_all_connections(self) -> list:
        """获取所有连接信息列表
        
        Returns:
            连接信息列表，每个包含 user_id, session_id, connected_at 等
        """
        connections = []
        for conn_id, conn_info in self._connections.items():
            connections.append({
                "user_id": conn_info.user_id,
                "session_id": conn_info.session_id,
                "connected_at": conn_info.connected_at.isoformat(),
                "last_heartbeat": conn_info.last_heartbeat,
                "metadata": conn_info.metadata,
                "username": conn_info.metadata.get("username", ""),
                "request_count": conn_info.request_count
            })
        return connections
    
    def increment_request_count(self, session_id: str) -> int:
        """递增请求计数"""
        for conn_id, conn_info in self._connections.items():
            if conn_info.session_id == session_id:
                conn_info.request_count += 1
                return conn_info.request_count
        return 0
