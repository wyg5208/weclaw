"""
感知系统 - AI 的"感官"

负责收集和预处理所有外部输入信号
包括：视觉、听觉、触觉（文件系统）、本体感觉（系统状态）
"""

from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class SensoryInput:
    """感知输入数据结构"""
    user_text: Optional[str]          # 用户文本输入
    voice_transcript: Optional[str]   # 语音转文字
    screen_state: dict                # 屏幕状态
    filesystem_state: dict            # 文件系统状态
    clipboard_content: Optional[str]  # 剪贴板内容
    system_info: dict                 # 系统信息
    timestamp: datetime               # 时间戳


class PerceptionSystem:
    """
    感知系统 - AI 的"感官"
    
    负责：
    - 视觉感知（屏幕截图、OCR）
    - 听觉感知（语音识别）
    - 触觉感知（文件系统状态）
    - 本体感觉（系统状态）
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # 感知缓存
        self._sensory_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 0.1  # 100ms 缓存
        
    async def gather_sensory_input(self) -> SensoryInput:
        """汇聚所有感官输入"""
        
        # 检查缓存
        if self._is_cache_valid():
            return self._sensory_cache
            
        # 并行收集各感官数据
        results = await asyncio.gather(
            self._get_visual_input(),
            self._get_auditory_input(),
            self._get_filesystem_state(),
            self._get_clipboard_content(),
            self._get_system_info(),
            return_exceptions=True
        )
        
        sensory = SensoryInput(
            user_text=None,  # 由调用方设置
            voice_transcript=results[1].get("transcript") if not isinstance(results[1], Exception) else None,
            screen_state=results[0] if not isinstance(results[0], Exception) else {},
            filesystem_state=results[2] if not isinstance(results[2], Exception) else {},
            clipboard_content=results[3].get("content") if not isinstance(results[3], Exception) else None,
            system_info=results[4] if not isinstance(results[4], Exception) else {},
            timestamp=datetime.now()
        )
        
        # 更新缓存
        self._sensory_cache = sensory
        self._cache_timestamp = datetime.now()
        
        return sensory
        
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self._cache_timestamp is None:
            return False
            
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_ttl
        
    async def _get_visual_input(self) -> dict:
        """获取视觉输入"""
        # TODO: 实现屏幕感知
        return {
            "active_window": "Unknown",
            "screenshot_available": False
        }
        
    async def _get_auditory_input(self) -> dict:
        """获取听觉输入"""
        # TODO: 实现语音识别
        return {"transcript": None}
        
    async def _get_filesystem_state(self) -> dict:
        """获取文件系统状态"""
        import os
        import shutil
        
        try:
            # 获取常用目录
            downloads = self._get_user_downloads_path()
            documents = self._get_user_documents_path()
            
            stats = {}
            
            if os.path.exists(downloads):
                stats["downloads"] = self._count_files(downloads)
                
            if os.path.exists(documents):
                stats["documents"] = self._count_files(documents)
                
            # 磁盘空间
            disk = shutil.disk_usage("C:\\")
            stats["disk"] = {
                "total_gb": disk.total / (1024**3),
                "used_gb": disk.used / (1024**3),
                "free_gb": disk.free / (1024**3)
            }
            
            return stats
            
        except Exception as e:
            return {"error": str(e)}
            
    async def _get_clipboard_content(self) -> dict:
        """获取剪贴板内容"""
        # TODO: 实现剪贴板读取
        return {"content": None}
        
    async def _get_system_info(self) -> dict:
        """获取系统信息"""
        try:
            import psutil
            
            now = datetime.now()
            
            return {
                "time": now.strftime("%H:%M:%S"),
                "date": now.strftime("%Y-%m-%d"),
                "day_of_week": now.strftime("%A"),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "battery": self._get_battery_status(),
                "network": self._get_network_status()
            }
        except Exception as e:
            return {"error": str(e)}
            
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
        
    def _get_network_status(self) -> dict:
        """获取网络状态"""
        return {"connected": True, "type": "unknown"}
        
    def _count_files(self, directory: str) -> dict:
        """统计目录文件数"""
        count = 0
        total_size = 0
        
        try:
            for root, dirs, files in os.walk(directory):
                count += len(files)
                total_size += sum(
                    os.path.getsize(os.path.join(root, f))
                    for f in files
                    if os.path.isfile(os.path.join(root, f))
                )
        except:
            pass
            
        return {
            "count": count,
            "size_mb": total_size / (1024 * 1024)
        }
        
    def _get_user_downloads_path(self) -> str:
        """获取下载目录路径"""
        import os
        return os.path.expanduser("~\\Downloads")
        
    def _get_user_documents_path(self) -> str:
        """获取文档目录路径"""
        import os
        return os.path.expanduser("~\\Documents")
