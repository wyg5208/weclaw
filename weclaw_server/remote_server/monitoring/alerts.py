"""离线消息监控告警模块

用于监控离线消息队列健康度，及时发现积压、过期等问题。
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict
from enum import Enum

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class OfflineMessageMonitor:
    """离线消息监控器"""
    
    _instance: Optional['OfflineMessageMonitor'] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化监控器"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._alert_callbacks = []
        self._last_check_time: Optional[datetime] = None
        self._metrics_cache: Dict = {}
        self._initialized = True
        
        logger.info("离线消息监控器已初始化")
    
    def register_alert_callback(self, callback):
        """注册告警回调函数
        
        Args:
            callback: async function(alert_level, message, metrics)
        """
        self._alert_callbacks.append(callback)
        logger.debug(f"已注册告警回调：{callback.__name__}")
    
    async def check_queue_health(self) -> Dict:
        """检查队列健康度
        
        Returns:
            包含健康指标的字典
        """
        try:
            from ..services.message_queue import get_message_queue
            
            queue = get_message_queue()
            
            # 获取待处理消息总数
            total_pending = await queue.get_all_pending_count()
            
            # 按用户统计
            user_metrics = await self._get_user_metrics(queue)
            
            # 计算过期消息比例
            expired_ratio = await self._calc_expired_ratio(queue)
            
            # 平均等待时长（分钟）
            avg_wait_time = await self._calc_avg_wait_time(queue)
            
            # 构建指标
            metrics = {
                "total_pending": total_pending,
                "expired_ratio": expired_ratio,
                "avg_wait_time_minutes": avg_wait_time,
                "user_count": len(user_metrics),
                "timestamp": datetime.utcnow().isoformat(),
                "user_metrics": user_metrics
            }
            
            self._metrics_cache = metrics
            self._last_check_time = datetime.utcnow()
            
            # 触发告警检查
            await self._check_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"检查队列健康失败：{e}", exc_info=True)
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_user_metrics(self, queue) -> Dict:
        """获取每个用户的指标"""
        # TODO: 实现按用户维度的统计
        # 目前简化版本，未来可以从数据库查询
        return {}
    
    async def _calc_expired_ratio(self, queue) -> float:
        """计算过期消息比例"""
        try:
            # TODO: 从数据库查询过期消息数量
            # 目前返回 0，后续完善
            return 0.0
        except Exception as e:
            logger.error(f"计算过期比例失败：{e}")
            return 0.0
    
    async def _calc_avg_wait_time(self, queue) -> float:
        """计算平均等待时长（分钟）"""
        try:
            # TODO: 从数据库查询平均等待时间
            # 目前返回 0，后续完善
            return 0.0
        except Exception as e:
            logger.error(f"计算平均等待时间失败：{e}")
            return 0.0
    
    async def _check_alerts(self, metrics: Dict):
        """检查是否需要触发告警"""
        alerts = []
        
        # 告警条件 1: 离线消息积压超过阈值
        if metrics["total_pending"] > 1000:
            alerts.append({
                "level": AlertLevel.WARNING,
                "message": f"离线消息积压超过阈值（当前：{metrics['total_pending']}）",
                "metric": "total_pending",
                "value": metrics["total_pending"],
                "threshold": 1000
            })
        
        if metrics["total_pending"] > 5000:
            alerts.append({
                "level": AlertLevel.CRITICAL,
                "message": f"离线消息严重积压（当前：{metrics['total_pending']}）",
                "metric": "total_pending",
                "value": metrics["total_pending"],
                "threshold": 5000
            })
        
        # 告警条件 2: 大量消息过期
        if metrics["expired_ratio"] > 0.3:
            alerts.append({
                "level": AlertLevel.CRITICAL,
                "message": f"大量消息过期（过期率：{metrics['expired_ratio']*100:.1f}%）",
                "metric": "expired_ratio",
                "value": metrics["expired_ratio"],
                "threshold": 0.3
            })
        
        # 告警条件 3: 平均等待时间过长
        if metrics["avg_wait_time_minutes"] > 60:
            alerts.append({
                "level": AlertLevel.WARNING,
                "message": f"消息平均等待时间过长（{metrics['avg_wait_time_minutes']:.1f}分钟）",
                "metric": "avg_wait_time_minutes",
                "value": metrics["avg_wait_time_minutes"],
                "threshold": 60
            })
        
        # 发送告警
        for alert in alerts:
            await self._send_alert(alert["level"], alert["message"], metrics)
    
    async def _send_alert(self, level: AlertLevel, message: str, metrics: Dict):
        """发送告警"""
        logger.warning(f"[{level.value}] {message}")
        
        # 调用所有注册的回调
        for callback in self._alert_callbacks:
            try:
                await callback(level, message, metrics)
            except Exception as e:
                logger.error(f"告警回调失败：{e}")
    
    def get_metrics(self) -> Dict:
        """获取最新指标缓存"""
        return self._metrics_cache.copy()
    
    def get_last_check_time(self) -> Optional[datetime]:
        """获取最后检查时间"""
        return self._last_check_time


# 全局单例
_monitor_instance: Optional[OfflineMessageMonitor] = None


def get_monitor() -> OfflineMessageMonitor:
    """获取监控器单例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = OfflineMessageMonitor()
    return _monitor_instance


async def start_monitoring_task(interval_minutes: int = 5):
    """启动定期监控任务
    
    Args:
        interval_minutes: 检查间隔（分钟）
    """
    monitor = get_monitor()
    
    logger.info(f"启动离线消息监控任务，间隔：{interval_minutes}分钟")
    
    while True:
        await asyncio.sleep(interval_minutes * 60)
        try:
            await monitor.check_queue_health()
        except Exception as e:
            logger.error(f"定期监控任务失败：{e}")


# 示例告警回调（可以发送邮件、短信等）
async def email_alert_callback(level: AlertLevel, message: str, metrics: Dict):
    """邮件告警回调（示例）"""
    # TODO: 实现邮件发送逻辑
    logger.info(f"[邮件告警] {level.value}: {message}")


async def sms_alert_callback(level: AlertLevel, message: str, metrics: Dict):
    """短信告警回调（仅紧急告警）"""
    if level == AlertLevel.EMERGENCY or level == AlertLevel.CRITICAL:
        # TODO: 实现短信发送逻辑
        logger.info(f"[短信告警] {level.value}: {message}")
