"""状态上报器

定期向远程服务器上报 WinClaw 本地状态。
"""

import asyncio
import logging
import platform
import psutil
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class StatusReporter:
    """状态上报器
    
    定期收集并上报 WinClaw 运行状态到远程服务器。
    """
    
    def __init__(
        self,
        agent: Any,
        get_status_callback: Optional[Callable] = None
    ):
        """
        初始化状态上报器
        
        Args:
            agent: WinClaw Agent 实例
            get_status_callback: 获取状态的回调函数
        """
        self.agent = agent
        self.get_status_callback = get_status_callback
        
        # 上报任务
        self._task: Optional[asyncio.Task] = None
        self._running = False
        
        # 上次状态
        self._last_status: dict = {}
        self._start_time = datetime.now()
    
    async def start(self, interval: float = 30.0):
        """
        启动状态上报
        
        Args:
            interval: 上报间隔（秒）
        """
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._report_loop(interval))
        logger.info(f"状态上报器已启动，间隔: {interval}秒")
    
    async def stop(self):
        """停止状态上报"""
        self._running = False
        
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("状态上报器已停止")
    
    async def _report_loop(self, interval: float):
        """上报循环"""
        while self._running:
            try:
                await self._do_report()
            except Exception as e:
                logger.error(f"状态上报失败: {e}")
            
            await asyncio.sleep(interval)
    
    async def _do_report(self):
        """执行状态上报"""
        status = self.get_current_status()
        
        # 只在状态变化时上报
        if status != self._last_status:
            if self.get_status_callback:
                await self.get_status_callback()
            self._last_status = status.copy()
    
    def get_current_status(self) -> dict:
        """
        获取当前状态
        
        Returns:
            状态字典
        """
        now = datetime.now()
        uptime = (now - self._start_time).total_seconds()
        
        status = {
            "timestamp": now.isoformat(),
            "uptime_seconds": int(uptime),
            "status": self._get_agent_status(),
            "system": self._get_system_status(),
            "model": self._get_model_info(),
            "tools": self._get_tools_summary(),
            "statistics": self._get_statistics()
        }
        
        return status
    
    def _get_agent_status(self) -> str:
        """获取 Agent 运行状态"""
        if not self.agent:
            return "offline"
        
        # 检查是否正在处理
        if hasattr(self.agent, 'is_processing') and self.agent.is_processing:
            return "busy"
        
        return "idle"
    
    def _get_system_status(self) -> dict:
        """获取系统状态"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存使用
            memory = psutil.virtual_memory()
            
            # 磁盘使用
            disk = psutil.disk_usage('/')
            
            return {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": platform.python_version(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024**3), 2)
            }
        except Exception as e:
            logger.warning(f"获取系统状态失败: {e}")
            return {
                "platform": platform.system(),
                "error": str(e)
            }
    
    def _get_model_info(self) -> Optional[dict]:
        """获取模型信息"""
        if not self.agent:
            return None
        
        model_info = {}
        
        # 当前模型
        if hasattr(self.agent, 'current_model'):
            model_info["name"] = self.agent.current_model
        
        # 模型提供商
        if hasattr(self.agent, 'model_provider'):
            model_info["provider"] = self.agent.model_provider
        
        # 模型配置
        if hasattr(self.agent, 'model_config'):
            config = self.agent.model_config
            model_info["config"] = {
                "temperature": getattr(config, 'temperature', None),
                "max_tokens": getattr(config, 'max_tokens', None)
            }
        
        return model_info if model_info else None
    
    def _get_tools_summary(self) -> dict:
        """获取工具摘要"""
        if not hasattr(self.agent, 'tool_registry'):
            return {"total": 0, "enabled": 0}
        
        tool_registry = self.agent.tool_registry
        
        # 使用 get_all_tools() 方法获取工具列表
        tools_list = tool_registry.get_all_tools() if hasattr(tool_registry, 'get_all_tools') else []
        
        total = len(tools_list)
        enabled = sum(
            1 for t in tools_list
            if getattr(t, 'enabled', True)
        )
        
        # 按类别统计
        categories = {}
        for tool in tools_list:
            cat = getattr(tool, 'category', 'general')
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total": total,
            "enabled": enabled,
            "categories": categories
        }
    
    def _get_statistics(self) -> Optional[dict]:
        """获取统计信息"""
        if not self.agent:
            return None
        
        stats = {}
        
        # 成本追踪
        if hasattr(self.agent, 'cost_tracker'):
            tracker = self.agent.cost_tracker
            stats["cost"] = {
                "total_messages": getattr(tracker, 'total_messages', 0),
                "total_tokens": getattr(tracker, 'total_tokens', 0),
                "total_cost": getattr(tracker, 'total_cost', 0.0),
                "input_tokens": getattr(tracker, 'total_input_tokens', 0),
                "output_tokens": getattr(tracker, 'total_output_tokens', 0)
            }
        
        # 会话统计
        if hasattr(self.agent, 'session_manager'):
            sm = self.agent.session_manager
            stats["sessions"] = {
                "total": getattr(sm, 'total_sessions', 0),
                "active": getattr(sm, 'active_sessions', 1)
            }
        
        return stats if stats else None
    
    def get_quick_status(self) -> dict:
        """获取快速状态（用于心跳）"""
        return {
            "status": self._get_agent_status(),
            "uptime_seconds": int((datetime.now() - self._start_time).total_seconds()),
            "timestamp": datetime.now().isoformat()
        }
