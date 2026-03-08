"""WinClaw 桥接器

连接远程服务与 WinClaw 本地实例，提供消息转发和事件同步。
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Any, AsyncGenerator
from dataclasses import dataclass

from ..config import get_config

logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    actions: list[str]
    category: str


class WinClawBridge:
    """WinClaw 本地实例桥接器
    
    负责将远程客户端的请求转发到本地 WinClaw 实例，
    并将 WinClaw 的事件推送到远程客户端。
    """
    
    def __init__(
        self,
        agent: Any,
        event_bus: Any,
        session_manager: Any,
        connection_manager: Any
    ):
        """
        初始化桥接器
        
        Args:
            agent: WinClaw Agent 实例
            event_bus: WinClaw EventBus 实例
            session_manager: WinClaw SessionManager 实例
            connection_manager: WebSocket 连接管理器
        """
        self.agent = agent
        self.event_bus = event_bus
        self.session_manager = session_manager
        self.connection_manager = connection_manager
        
        # 配置
        self.config = get_config()
        
        # 活跃的流式处理任务
        self._active_streams: dict[str, asyncio.Task] = {}
        
        # 工具缓存
        self._tools_cache: Optional[list[dict]] = None
        
        # 启动时间
        self._start_time = datetime.now()
        
        # 设置事件转发
        self._setup_event_forwarding()
        
        logger.info("WinClaw 桥接器初始化完成")
    
    def _setup_event_forwarding(self):
        """设置事件转发 - 将 WinClaw 事件转发到远程客户端"""
        if not self.event_bus:
            return
        
        # 转发工具调用事件
        self.event_bus.on("tool_call", self._on_tool_call)
        
        # 转发模型响应事件
        self.event_bus.on("model_response", self._on_model_response)
        
        # 转发错误事件
        self.event_bus.on("error", self._on_error)
        
        logger.info("事件转发已设置")
    
    async def _on_tool_call(self, event_data: dict):
        """处理工具调用事件"""
        # 提取用户ID并转发
        user_id = event_data.get("user_id", "")
        if user_id and self.connection_manager:
            await self.connection_manager.send_message(user_id, {
                "type": "tool_call",
                "payload": {
                    "tool": event_data.get("tool", ""),
                    "action": event_data.get("action", ""),
                    "args": event_data.get("args", {}),
                    "status": event_data.get("status", "running")
                }
            })
    
    async def _on_model_response(self, event_data: dict):
        """处理模型响应事件"""
        user_id = event_data.get("user_id", "")
        if user_id and self.connection_manager:
            await self.connection_manager.send_message(user_id, {
                "type": "content",
                "payload": event_data
            })
    
    async def _on_error(self, event_data: dict):
        """处理错误事件"""
        user_id = event_data.get("user_id", "")
        if user_id and self.connection_manager:
            await self.connection_manager.send_message(user_id, {
                "type": "error",
                "payload": event_data
            })
    
    def is_connected(self) -> bool:
        """检查 WinClaw 是否已连接"""
        return self.agent is not None
    
    async def process_message(
        self,
        user_id: str,
        message: str,
        attachments: Optional[list] = None
    ) -> AsyncGenerator[dict, None]:
        """
        处理来自远程客户端的消息
            
        Args:
            user_id: 用户 ID
            message: 消息内容
            attachments: 附件列表
                
        Yields:
            处理过程中的事件
        """
        if not self.agent:
            yield {
                "type": "error",
                "payload": {"code": "NOT_CONNECTED", "message": "WinClaw 未连接"}
            }
            return
            
        try:
            # 构建会话 ID
            session_id = f"remote_{user_id}"
                
            logger.info(f"收到消息：user={user_id}, attachments_count={len(attachments) if attachments else 0}")
            
            # 【关键修复】将附件信息添加到消息中（与 GUI 桌面端保持一致）
            full_message = message
            if attachments:
                # 构建附件上下文
                attachment_lines = ["\n[附件信息]"]
                for att in attachments:
                    att_type = att.get("type", "file")
                    att_filename = att.get("filename", "unknown")
                    att_data = att.get("data", "")  # URL 或 base64
                        
                    type_desc = {
                        "image": "图片",
                        "audio": "音频",
                        "video": "视频",
                        "document": "文档",
                    }.get(att_type, "文件")
                        
                    # 添加附件描述到消息
                    attachment_lines.append(f"- {att_filename} ({type_desc}, URL: {att_data})")
                    
                attachment_lines.append("")
                full_message = "\n".join(attachment_lines) + "\n用户请求：" + message
                        
                logger.info(f"已添加 {len(attachments)} 个附件到消息中")
                logger.info(f"完整消息预览：{full_message[:200]}...")
                
            # 调用 Agent 的流式处理方法（不传 attachments 参数）
            async for chunk in self.agent.chat_stream(
                user_input=full_message,
                session_id=session_id
            ):
                # 【关键增强】如果是工具调用且包含 image_path 参数，需要转换为本地路径
                processed_chunk = await self._process_tool_call(chunk, attachments)
                    
                # 转换 chunk 格式
                yield self._convert_chunk(processed_chunk, user_id)
                    
        except asyncio.CancelledError:
            logger.info(f"消息处理被取消：user={user_id}")
            yield {
                "type": "error",
                "payload": {"code": "CANCELLED", "message": "处理已取消"}
            }
                
        except Exception as e:
            logger.error(f"处理消息失败：{e}", exc_info=True)
            yield {
                "type": "error",
                "payload": {"code": "PROCESSING_ERROR", "message": str(e)}
            }
        
    async def _process_tool_call(self, chunk: dict, attachments: Optional[list]) -> dict:
        """处理工具调用，将图片 URL 转换为本地路径"""
        if chunk.get("type") != "tool_call":
            return chunk
            
        tool_name = chunk.get("tool", "")
        action = chunk.get("action", "")
        args = chunk.get("args", {})
            
        # 检查是否是 OCR 相关操作
        if tool_name == "ocr" and action in ["recognize_file", "recognize_region"]:
            image_path = args.get("image_path", "")
                
            logger.info(f"检测到 OCR 工具调用：action={action}, image_path={image_path}")
                
            # 如果是 URL 格式（如 /api/files/xxx），转换为本地路径
            if image_path.startswith("/api/files/") and attachments:
                logger.info(f"开始转换图片 URL 为本地路径：{image_path}")
                local_path = await self._download_attachment_to_temp(image_path, attachments)
                if local_path:
                    args["image_path"] = local_path
                    chunk["args"] = args
                    logger.info(f"✅ 已将图片 URL 转换为本地路径：{local_path}")
                else:
                    logger.error(f"❌ 图片 URL 转换失败：{image_path}")
            elif not image_path.startswith("/api/files/"):
                logger.info(f"图片路径已是本地路径：{image_path}")
            else:
                logger.warning(f"未找到附件信息，无法转换：{image_path}")
            
        return chunk
        
    async def _download_attachment_to_temp(self, url: str, attachments: list) -> str:
        """下载附件到临时目录，返回本地路径"""
        import tempfile
        import aiohttp
        from pathlib import Path
        
        try:
            # 从 URL 提取 attachment_id
            # /api/files/a348f87d-db56-4a4c-ad70-2c3b6ec9c52f
            attachment_id = url.split("/")[-1]
                
            # 查找对应的附件信息
            att_info = None
            for att in attachments:
                if att.get("attachment_id") == attachment_id or url in att.get("data", ""):
                    att_info = att
                    break
                
            if not att_info:
                logger.warning(f"未找到附件信息：{url}")
                return ""
                
            # 创建临时文件
            filename = att_info.get("filename", "temp_image.jpg")
            temp_dir = Path(tempfile.gettempdir()) / "winclaw_pwa_attachments"
            temp_dir.mkdir(parents=True, exist_ok=True)
                
            # 使用 attachment_id 前 8 位作为文件名（与服务器一致）
            file_ext = Path(filename).suffix
            local_filename = f"{attachment_id[:8]}{file_ext}"
            local_path = temp_dir / local_filename
                
            # 如果文件已存在（缓存），直接返回
            if local_path.exists():
                logger.debug(f"使用缓存的图片：{local_path}")
                return str(local_path)
                
            # 下载文件 - 使用当前服务器的实际地址
            # 注意：url 已经是相对路径如 /api/files/xxx
            # 需要构建完整的下载 URL
            download_url = f"http://127.0.0.1:8188{url}"
                
            logger.info(f"开始下载图片：{download_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(local_path, "wb") as f:
                            f.write(content)
                        
                        logger.info(f"图片已下载到：{local_path} (大小：{len(content)} bytes)")
                        return str(local_path)
                    else:
                        logger.error(f"下载图片失败：{response.status}, URL: {download_url}")
                        return ""
                        
        except Exception as e:
            logger.error(f"下载附件失败：{e}", exc_info=True)
            return ""
    
    def _convert_chunk(self, chunk: dict, user_id: str) -> dict:
        """转换 Agent 输出格式为 WebSocket 消息格式"""
        chunk_type = chunk.get("type", "content")
        
        if chunk_type == "thinking":
            return {
                "type": "thinking",
                "payload": {"content": chunk.get("content", "")}
            }
        
        elif chunk_type == "tool_call":
            return {
                "type": "tool_call",
                "payload": {
                    "tool": chunk.get("tool", ""),
                    "action": chunk.get("action", ""),
                    "args": chunk.get("args", {}),
                    "status": "running"
                }
            }
        
        elif chunk_type == "tool_result":
            return {
                "type": "tool_result",
                "payload": {
                    "tool": chunk.get("tool", ""),
                    "result": chunk.get("result", ""),
                    "status": chunk.get("status", "success")
                }
            }
        
        elif chunk_type == "content":
            return {
                "type": "content",
                "payload": {"delta": chunk.get("delta", chunk.get("content", ""))}
            }
        
        elif chunk_type == "done":
            return {
                "type": "done",
                "payload": {
                    "message_id": chunk.get("message_id", ""),
                    "tokens_used": chunk.get("tokens_used", 0)
                }
            }
        
        elif chunk_type == "error":
            return {
                "type": "error",
                "payload": {
                    "code": chunk.get("code", "ERROR"),
                    "message": chunk.get("message", "")
                }
            }
        
        else:
            return {
                "type": "content",
                "payload": chunk
            }
    
    def stop_generation(self, user_id: str) -> bool:
        """停止生成"""
        task = self._active_streams.get(user_id)
        if task and not task.done():
            task.cancel()
            logger.info(f"已停止生成: user={user_id}")
            return True
        return False
    
    def get_status(self) -> dict:
        """获取 WinClaw 状态"""
        if not self.agent:
            return {
                "status": "offline",
                "version": None,
                "uptime_seconds": 0,
                "current_task": None,
                "model": None,
                "statistics": None
            }
        
        # 计算运行时间
        uptime = (datetime.now() - self._start_time).total_seconds()
        
        # 获取模型信息
        model_info = None
        if hasattr(self.agent, 'current_model'):
            model_info = {
                "name": getattr(self.agent, 'current_model', 'unknown'),
                "provider": getattr(self.agent, 'model_provider', 'unknown')
            }
        
        # 获取统计信息
        statistics = None
        if hasattr(self.agent, 'cost_tracker'):
            cost_tracker = self.agent.cost_tracker
            statistics = {
                "total_messages": getattr(cost_tracker, 'total_messages', 0),
                "total_tokens": getattr(cost_tracker, 'total_tokens', 0),
                "total_cost": getattr(cost_tracker, 'total_cost', 0.0)
            }
        
        return {
            "status": "online",
            "version": getattr(self.agent, 'version', '2.5.2'),
            "uptime_seconds": int(uptime),
            "current_task": None,  # TODO: 从 agent 获取当前任务
            "model": model_info,
            "statistics": statistics
        }
    
    def get_tools(self) -> list[dict]:
        """获取可用工具列表"""
        if self._tools_cache:
            return self._tools_cache
        
        tools = []
        
        if not self.agent:
            return tools
        
        # 从 Agent 获取工具注册表
        if hasattr(self.agent, 'tool_registry'):
            tool_registry = self.agent.tool_registry
            
            for tool_name, tool_info in tool_registry.tools.items():
                actions = []
                if hasattr(tool_info, 'actions'):
                    actions = list(tool_info.actions.keys())
                elif hasattr(tool_info, 'execute'):
                    actions = ['execute']
                
                tools.append({
                    "name": tool_name,
                    "description": getattr(tool_info, 'description', ''),
                    "actions": actions,
                    "category": getattr(tool_info, 'category', 'general')
                })
        
        self._tools_cache = tools
        return tools
    
    async def execute_tool(
        self,
        user_id: str,
        tool: str,
        action: str,
        arguments: dict
    ) -> dict:
        """
        直接执行工具
        
        Args:
            user_id: 用户ID
            tool: 工具名称
            action: 动作名称
            arguments: 参数
            
        Returns:
            执行结果
        """
        if not self.agent:
            return {
                "success": False,
                "result": "WinClaw 未连接",
                "duration_ms": 0
            }
        
        start_time = time.time()
        
        try:
            # 获取工具
            if not hasattr(self.agent, 'tool_registry'):
                return {
                    "success": False,
                    "result": "工具注册表不可用",
                    "duration_ms": 0
                }
            
            tool_registry = self.agent.tool_registry
            tool_instance = tool_registry.tools.get(tool)
            
            if not tool_instance:
                return {
                    "success": False,
                    "result": f"工具 '{tool}' 不存在",
                    "duration_ms": 0
                }
            
            # 执行工具
            if hasattr(tool_instance, 'execute'):
                result = await tool_instance.execute(action, **arguments)
            elif hasattr(tool_instance, action):
                method = getattr(tool_instance, action)
                if asyncio.iscoroutinefunction(method):
                    result = await method(**arguments)
                else:
                    result = method(**arguments)
            else:
                return {
                    "success": False,
                    "result": f"动作 '{action}' 不存在",
                    "duration_ms": 0
                }
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                "success": True,
                "result": str(result),
                "duration_ms": duration_ms
            }
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"执行工具失败: {e}", exc_info=True)
            
            return {
                "success": False,
                "result": str(e),
                "duration_ms": duration_ms
            }
    
    def validate_tool_call(
        self,
        tool: str,
        action: str,
        arguments: dict
    ) -> dict:
        """验证工具调用"""
        errors = []
        warnings = []
        
        tools = self.get_tools()
        tool_info = next((t for t in tools if t.get("name") == tool), None)
        
        if not tool_info:
            errors.append(f"工具 '{tool}' 不存在")
        elif action not in tool_info.get("actions", []):
            errors.append(f"动作 '{action}' 不存在于工具 '{tool}'")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
