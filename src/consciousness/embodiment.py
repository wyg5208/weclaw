"""
身体性接口 - 连接意识系统与 WinClaw 工具系统

将"大脑指令"转换为"肌肉动作"
"""

from typing import Dict, Optional
from datetime import datetime


class WinClawEmbodiment:
    """
    WinClaw 身体性接口
    
    负责：
    - 获取感知输入（相当于感官信号）
    - 执行动作（相当于肌肉收缩）
    """
    
    def __init__(self, tool_registry):
        self.tools = tool_registry
        
        # 感知输入缓存
        self._sensory_cache = {}
        self._cache_timestamp = None
        
    async def get_sensory_input(self) -> dict:
        """获取感知输入 - 相当于感官信号"""
        
        # 检查缓存（100ms内复用）
        if self._cache_timestamp and \
           (datetime.now() - self._cache_timestamp).total_seconds() < 0.1:
            return self._sensory_cache
            
        # 收集各感官输入
        sensory = {
            # 视觉
            "visual": await self._get_visual_input(),
            
            # 文件系统状态
            "filesystem": await self._get_filesystem_state(),
            
            # 系统状态
            "system": await self._get_system_state(),
            
            # 剪贴板
            "clipboard": await self._get_clipboard(),
            
            # 时间上下文
            "temporal": self._get_temporal_context()
        }
        
        self._sensory_cache = sensory
        self._cache_timestamp = datetime.now()
        
        return sensory
        
    async def execute_action(self, action: dict) -> 'ActionResult':
        """
        执行动作 - 相当于肌肉收缩
        
        Args:
            action: {
                "type": "tool_name",
                "params": {...},
                "confirmation_required": False
            }
            
        Returns:
            ActionResult: 执行结果
        """
        tool_name = action.get("type")
        params = action.get("params", {})
        
        # 获取对应工具
        tool = self.tools.get(tool_name)
        if not tool:
            return ActionResult(
                success=False,
                error=f"Unknown tool: {tool_name}"
            )
            
        # 权限检查
        if action.get("confirmation_required"):
            confirmed = await self._request_confirmation(action)
            if not confirmed:
                return ActionResult(
                    success=False,
                    error="User denied the action"
                )
                
        # 执行工具
        try:
            result = await tool.execute(**params)
            return ActionResult(
                success=True,
                result=result
            )
        except Exception as e:
            return ActionResult(
                success=False,
                error=str(e)
            )
            
    async def _get_visual_input(self) -> dict:
        """获取视觉输入"""
        screen_tool = self.tools.get("screen")
        if screen_tool:
            screenshot = await screen_tool.capture()
            return {
                "screenshot_available": True,
                "active_window": self._get_active_window_title()
            }
        return {"screenshot_available": False}
        
    async def _get_filesystem_state(self) -> dict:
        """获取文件系统状态"""
        file_tool = self.tools.get("file")
        if file_tool:
            # 获取常用目录状态
            return {
                "downloads_count": await self._count_files_in_downloads(),
                "recent_files": await self._get_recent_files(5)
            }
        return {}
        
    async def _get_system_state(self) -> dict:
        """获取系统状态"""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "battery": self._get_battery_status()
            }
        except:
            return {}
            
    async def _get_clipboard(self) -> dict:
        """获取剪贴板内容"""
        clipboard_tool = self.tools.get("clipboard")
        if clipboard_tool:
            content = await clipboard_tool.get()
            return {
                "has_content": bool(content),
                "type": "text" if isinstance(content, str) else "image",
                "preview": content[:100] if isinstance(content, str) else None
            }
        return {"has_content": False}
        
    def _get_temporal_context(self) -> dict:
        """获取时间上下文"""
        now = datetime.now()
        hour = now.hour
        
        # 判断时段
        if 6 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 14:
            period = "noon"
        elif 14 <= hour < 18:
            period = "afternoon"
        elif 18 <= hour < 22:
            period = "evening"
        else:
            period = "night"
            
        return {
            "time": now.strftime("%H:%M"),
            "date": now.strftime("%Y-%m-%d"),
            "weekday": now.strftime("%A"),
            "period": period,
            "is_weekend": now.weekday() >= 5
        }
        
    def _get_active_window_title(self) -> str:
        """获取活动窗口标题"""
        # TODO: 实现窗口检测
        return "Unknown"
        
    async def _count_files_in_downloads(self) -> int:
        """统计下载目录文件数"""
        import os
        downloads_path = os.path.expanduser("~\\Downloads")
        
        if not os.path.exists(downloads_path):
            return 0
            
        count = 0
        try:
            for item in os.listdir(downloads_path):
                if os.path.isfile(os.path.join(downloads_path, item)):
                    count += 1
        except:
            pass
        return count
        
    async def _get_recent_files(self, limit: int = 5) -> list:
        """获取最近的文件"""
        # TODO: 实现最近文件检索
        return []
        
    def _get_battery_status(self) -> dict:
        """获取电池状态"""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                return {
                    "percent": battery.percent,
                    "plugged": battery.power_plugged
                }
        except:
            pass
        return {"percent": None, "plugged": True}
        
    async def _request_confirmation(self, action: dict) -> bool:
        """请求用户确认"""
        # TODO: 实现用户确认界面
        return True


class ActionResult:
    """动作执行结果"""
    
    def __init__(self, success: bool, result=None, error: str = ""):
        self.success = success
        self.result = result
        self.error = error
        
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error
        }
