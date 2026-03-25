"""全局音乐播放器管理器 - 协调工具和 UI 之间的播放状态。

这个模块提供了一个全局单例的播放器管理器，
让 MusicPlayerTool 可以通知 MiniPlayerPanel 执行实际播放操作。
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class MusicPlayerController:
    """全局音乐播放器控制器。
    
    这是一个单例类，用于在工具层和 UI 层之间传递播放指令。
    - 工具层（MusicPlayerTool）调用 controller 方法发出指令
    - UI 层（MiniPlayerPanel）注册回调接收指令并执行
    """
    
    _instance: Optional[MusicPlayerController] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._callbacks: dict[str, list[Callable]] = {
            "play": [],        # 播放指定歌曲
            "pause": [],       # 暂停
            "resume": [],      # 继续
            "stop": [],        # 停止
            "next": [],        # 下一首
            "prev": [],        # 上一首
            "seek": [],        # 跳转
            "set_volume": [],  # 设置音量
            "set_loop": [],    # 设置循环
            "set_shuffle": [], # 设置随机
        }
        
        # 迷你播放器显示回调（由主窗口注册）
        self._show_mini_player_callback: Optional[Callable] = None
        
        logger.info("MusicPlayerController 已初始化")
    
    def register_callback(self, event: str, callback: Callable) -> None:
        """注册播放事件回调。
        
        Args:
            event: 事件类型 (play/pause/resume/stop/next/prev/seek/set_volume/set_loop/set_shuffle)
            callback: 回调函数，接收相应参数
        """
        if event in self._callbacks:
            if callback not in self._callbacks[event]:
                self._callbacks[event].append(callback)
                logger.debug(f"注册播放事件回调: {event}")
    
    def unregister_callback(self, event: str, callback: Callable) -> None:
        """取消注册播放事件回调。"""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
            logger.debug(f"取消注册播放事件回调：{event}")
        
    def register_show_mini_player_callback(self, callback: Callable) -> None:
        """注册迷你播放器显示回调（由主窗口调用）。"""
        self._show_mini_player_callback = callback
        logger.info("已注册迷你播放器显示回调")
        
    def trigger_show_mini_player(self) -> None:
        """触发迷你播放器显示（在播放歌曲前自动调用）。"""
        if self._show_mini_player_callback is not None:
            try:
                self._show_mini_player_callback()
                logger.info("已触发迷你播放器显示")
            except Exception as e:
                logger.error(f"触发迷你播放器显示失败：{e}")
        else:
            # 回调未注册，说明主窗口可能还没有创建迷你播放器
            # 尝试通过 MainWindow 的实例来创建
            logger.warning("迷你播放器显示回调未注册，尝试延迟触发...")
            # 延迟一下再试一次（给主窗口时间完成初始化）
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, self._try_trigger_show_mini_player)
    
    def _try_trigger_show_mini_player(self) -> None:
        """重试触发显示迷你播放器。"""
        if self._show_mini_player_callback is not None:
            try:
                self._show_mini_player_callback()
                logger.info("延迟触发迷你播放器显示成功")
            except Exception as e:
                logger.error(f"延迟触发迷你播放器显示失败：{e}")
        else:
            logger.warning("重试后仍未注册迷你播放器显示回调")
    
    def play(self, song: dict[str, Any]) -> None:
        """触发播放事件。"""
        for callback in self._callbacks["play"]:
            try:
                callback(song)
            except Exception as e:
                logger.error(f"播放回调执行失败: {e}")
    
    def pause(self) -> None:
        """触发暂停事件。"""
        for callback in self._callbacks["pause"]:
            try:
                callback()
            except Exception as e:
                logger.error(f"暂停回调执行失败: {e}")
    
    def resume(self) -> None:
        """触发继续播放事件。"""
        for callback in self._callbacks["resume"]:
            try:
                callback()
            except Exception as e:
                logger.error(f"继续播放回调执行失败: {e}")
    
    def stop(self) -> None:
        """触发停止事件。"""
        for callback in self._callbacks["stop"]:
            try:
                callback()
            except Exception as e:
                logger.error(f"停止回调执行失败: {e}")
    
    def next(self) -> None:
        """触发下一首事件。"""
        for callback in self._callbacks["next"]:
            try:
                callback()
            except Exception as e:
                logger.error(f"下一首回调执行失败: {e}")
    
    def prev(self) -> None:
        """触发上一首事件。"""
        for callback in self._callbacks["prev"]:
            try:
                callback()
            except Exception as e:
                logger.error(f"上一首回调执行失败: {e}")
    
    def seek(self, position: float, is_percent: bool = False) -> None:
        """触发跳转事件。"""
        for callback in self._callbacks["seek"]:
            try:
                callback(position, is_percent)
            except Exception as e:
                logger.error(f"跳转回调执行失败: {e}")
    
    def set_volume(self, volume: float) -> None:
        """触发设置音量事件。"""
        for callback in self._callbacks["set_volume"]:
            try:
                callback(volume)
            except Exception as e:
                logger.error(f"设置音量回调执行失败: {e}")
    
    def set_loop(self, mode: str) -> None:
        """触发设置循环模式事件。"""
        for callback in self._callbacks["set_loop"]:
            try:
                callback(mode)
            except Exception as e:
                logger.error(f"设置循环回调执行失败: {e}")
    
    def set_shuffle(self, enabled: bool) -> None:
        """触发设置随机播放事件。"""
        for callback in self._callbacks["set_shuffle"]:
            try:
                callback(enabled)
            except Exception as e:
                logger.error(f"设置随机回调执行失败: {e}")


# 全局单例访问函数
def get_player_controller() -> MusicPlayerController:
    """获取全局播放器控制器实例。"""
    return MusicPlayerController()
