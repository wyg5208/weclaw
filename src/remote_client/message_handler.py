"""消息处理器

处理来自远程服务器的消息，并转发到本地 Agent 执行。
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolCallResult:
    """工具调用结果"""
    success: bool
    result: Any
    error: Optional[str] = None
    duration_ms: int = 0


class MessageHandler:
    """消息处理器
    
    负责解析和处理远程消息，调用本地 Agent 或工具执行。
    """
    
    def __init__(
        self,
        agent: Any,
        on_response: Optional[Callable] = None,
        on_tool_call: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        """
        初始化消息处理器
        
        Args:
            agent: WinClaw Agent 实例
            on_response: 响应回调
            on_tool_call: 工具调用回调
            on_error: 错误回调
        """
        self.agent = agent
        self.on_response = on_response
        self.on_tool_call = on_tool_call
        self.on_error = on_error
        
        # 工具缓存
        self._tools_cache: Optional[list[dict]] = None
    
    async def process_message(
        self,
        message_type: str,
        payload: dict,
        request_id: str = ""
    ) -> dict:
        """
        处理消息
        
        Args:
            message_type: 消息类型
            payload: 消息负载
            request_id: 请求ID
            
        Returns:
            处理结果
        """
        try:
            if message_type == "chat":
                return await self._handle_chat(payload, request_id)
            elif message_type == "tool_call":
                return await self._handle_tool_call(payload, request_id)
            elif message_type == "command":
                return await self._handle_command(payload, request_id)
            else:
                return {"error": f"未知消息类型: {message_type}"}
                
        except Exception as e:
            logger.error(f"消息处理失败: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _handle_chat(self, payload: dict, request_id: str) -> dict:
        """处理聊天消息"""
        content = payload.get("content", "")
        attachments = payload.get("attachments", [])
        options = payload.get("options", {})
        
        if not content:
            return {"error": "消息内容为空"}
        
        try:
            # 调用 Agent
            if hasattr(self.agent, 'chat_stream'):
                # 流式处理 - 返回生成器
                return {
                    "stream": True,
                    "generator": self.agent.chat_stream(
                        user_input=content,
                        attachments=attachments if attachments else None
                    )
                }
            elif hasattr(self.agent, 'chat'):
                # 同步处理
                response = await self.agent.chat(content)
                return {"content": response, "done": True}
            else:
                return {"error": "Agent 不支持聊天功能"}
                
        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
            return {"error": str(e)}
    
    async def _handle_tool_call(self, payload: dict, request_id: str) -> dict:
        """处理工具调用"""
        tool = payload.get("tool", "")
        action = payload.get("action", "")
        arguments = payload.get("arguments", {})
        
        return await self.execute_tool(tool, action, arguments)
    
    async def _handle_command(self, payload: dict, request_id: str) -> dict:
        """处理命令"""
        command = payload.get("command", "")
        args = payload.get("args", {})
        
        # 支持的命令
        if command == "stop_generation":
            # 停止生成
            return {"success": True, "message": "已停止"}
        
        elif command == "clear_session":
            # 清除会话
            if hasattr(self.agent, 'clear_session'):
                self.agent.clear_session()
            return {"success": True, "message": "会话已清除"}
        
        elif command == "get_status":
            # 获取状态
            status = self._get_agent_status()
            return {"success": True, "status": status}
        
        else:
            return {"error": f"未知命令: {command}"}
    
    async def execute_tool(
        self,
        tool_name: str,
        action: str,
        arguments: dict
    ) -> Any:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            action: 动作名称
            arguments: 参数
            
        Returns:
            执行结果
        """
        start_time = time.time()
        
        try:
            # 获取工具注册表
            if not hasattr(self.agent, 'tool_registry'):
                raise ValueError("Agent 没有工具注册表")
            
            tool_registry = self.agent.tool_registry
            tool_instance = tool_registry.tools.get(tool_name)
            
            if not tool_instance:
                raise ValueError(f"工具 '{tool_name}' 不存在")
            
            # 执行工具
            result = None
            
            # 尝试不同的执行方式
            if hasattr(tool_instance, 'execute'):
                # 标准执行方法
                if asyncio.iscoroutinefunction(tool_instance.execute):
                    result = await tool_instance.execute(action, **arguments)
                else:
                    result = tool_instance.execute(action, **arguments)
            
            elif hasattr(tool_instance, action):
                # 直接调用动作方法
                method = getattr(tool_instance, action)
                if asyncio.iscoroutinefunction(method):
                    result = await method(**arguments)
                else:
                    result = method(**arguments)
            
            else:
                raise ValueError(f"工具 '{tool_name}' 不支持动作 '{action}'")
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"工具执行完成: {tool_name}.{action} ({duration_ms}ms)")
            
            return result
            
        except Exception as e:
            logger.error(f"工具执行失败: {tool_name}.{action}: {e}")
            raise
    
    def get_tools(self) -> list[dict]:
        """获取可用工具列表"""
        if self._tools_cache:
            return self._tools_cache
        
        tools = []
        
        if not hasattr(self.agent, 'tool_registry'):
            return tools
        
        tool_registry = self.agent.tool_registry
        
        for tool_name, tool_instance in tool_registry.tools.items():
            # 获取工具信息
            actions = []
            if hasattr(tool_instance, 'actions'):
                actions = list(tool_instance.actions.keys())
            elif hasattr(tool_instance, 'execute'):
                actions = ['execute']
            
            tool_info = {
                "name": tool_name,
                "description": getattr(tool_instance, 'description', ''),
                "actions": actions,
                "category": getattr(tool_instance, 'category', 'general'),
                "enabled": getattr(tool_instance, 'enabled', True)
            }
            
            tools.append(tool_info)
        
        self._tools_cache = tools
        return tools
    
    def _get_agent_status(self) -> dict:
        """获取 Agent 状态"""
        status = {
            "status": "active",
            "version": getattr(self.agent, 'version', 'unknown'),
            "model": None,
            "statistics": None
        }
        
        # 获取模型信息
        if hasattr(self.agent, 'current_model'):
            status["model"] = {
                "name": self.agent.current_model,
                "provider": getattr(self.agent, 'model_provider', 'unknown')
            }
        
        # 获取统计信息
        if hasattr(self.agent, 'cost_tracker'):
            tracker = self.agent.cost_tracker
            status["statistics"] = {
                "total_messages": getattr(tracker, 'total_messages', 0),
                "total_tokens": getattr(tracker, 'total_tokens', 0),
                "total_cost": getattr(tracker, 'total_cost', 0.0)
            }
        
        return status
    
    def invalidate_tools_cache(self):
        """清除工具缓存"""
        self._tools_cache = None
