"""每日任务调度器 — 凌晨自动分析、早上主动推送每日任务清单。

调度流程：
1. 凌晨 02:00 — 智能分析引擎运行，生成每日任务推荐
2. 上午 07:00 — 检查今日推荐，推送到对话栏
3. 应用启动时 — 检查今日是否已推送，如未则推送

使用示例：
    scheduler = DailyTaskScheduler(event_bus)
    await scheduler.start()

    # 应用启动时检查
    await scheduler.check_and_push_on_startup()
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 延迟导入标记
_APS_AVAILABLE: bool | None = None
_AsyncIOScheduler = None


def _check_apscheduler() -> bool:
    """检查 APScheduler 是否可用。"""
    global _APS_AVAILABLE, _AsyncIOScheduler
    if _APS_AVAILABLE is not None:
        return _APS_AVAILABLE

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        _AsyncIOScheduler = AsyncIOScheduler
        _APS_AVAILABLE = True
        logger.debug("APScheduler 加载成功")
    except ImportError:
        _APS_AVAILABLE = False
        logger.debug("APScheduler 不可用，使用简化调度")

    return _APS_AVAILABLE


class DailyTaskScheduler:
    """每日任务调度器。

    负责定时执行每日任务的分析和推送：
    - 凌晨2点：运行智能分析引擎，生成今日任务推荐
    - 早上7点：通过 CompanionEngine 推送任务清单到对话栏
    - 启动检查：用户首次打开程序时推送任务
    """

    def __init__(
        self,
        event_bus: Any = None,
        companion_engine: Any = None,
        db_path: Path | str | None = None,
    ):
        """初始化调度器。

        Args:
            event_bus: 事件总线（用于发布事件）
            companion_engine: 陪伴引擎（用于推送消息）
            db_path: 数据库路径
        """
        self._event_bus = event_bus
        self._companion_engine = companion_engine
        self._db_path = Path(db_path) if db_path else None

        self._scheduler = None
        self._running = False

        # 推送状态跟踪
        self._last_push_date: str | None = None
        self._last_analysis_date: str | None = None

    def set_companion_engine(self, engine: Any) -> None:
        """设置陪伴引擎。"""
        self._companion_engine = engine
        logger.info("DailyTaskScheduler 已设置 CompanionEngine")

    async def start(self) -> None:
        """启动调度器。"""
        if self._running:
            logger.warning("DailyTaskScheduler 已经在运行")
            return

        self._running = True

        if _check_apscheduler():
            await self._start_apscheduler()
        else:
            # 使用简化的定时检查
            asyncio.create_task(self._simple_scheduler_loop())

        logger.info("DailyTaskScheduler 已启动")

    async def stop(self) -> None:
        """停止调度器。"""
        self._running = False

        if self._scheduler:
            self._scheduler.shutdown()
            self._scheduler = None

        logger.info("DailyTaskScheduler 已停止")

    async def _start_apscheduler(self) -> None:
        """使用 APScheduler 启动调度。"""
        if _AsyncIOScheduler is None:
            return

        self._scheduler = _AsyncIOScheduler()

        # 凌晨2点分析任务
        self._scheduler.add_job(
            self._run_analysis,
            'cron',
            hour=2,
            minute=0,
            id='daily_task_analysis',
        )

        # 早上7点推送任务
        self._scheduler.add_job(
            self._push_recommendations,
            'cron',
            hour=7,
            minute=0,
            id='daily_task_push',
        )

        self._scheduler.start()
        logger.info("APScheduler 调度已启动: 分析=02:00, 推送=07:00")

    async def _simple_scheduler_loop(self) -> None:
        """简化的定时检查循环（无APScheduler时使用）。"""
        while self._running:
            try:
                now = datetime.now()
                hour = now.hour
                minute = now.minute
                today = now.strftime("%Y-%m-%d")

                # 凌晨2点分析
                if hour == 2 and minute == 0:
                    if self._last_analysis_date != today:
                        await self._run_analysis()
                        self._last_analysis_date = today

                # 早上7点推送
                if hour == 7 and minute == 0:
                    if self._last_push_date != today:
                        await self._push_recommendations()
                        self._last_push_date = today

                # 每分钟检查一次
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("简化调度循环错误: %s", e)
                await asyncio.sleep(60)

    # ------------------------------------------------------------------
    # 核心方法
    # ------------------------------------------------------------------

    async def _run_analysis(self) -> None:
        """凌晨运行智能分析。"""
        today = datetime.now().strftime("%Y-%m-%d")
        logger.info("开始每日任务分析: %s", today)

        try:
            from src.core.task_analyzer import TaskAnalyzer

            analyzer = TaskAnalyzer(self._db_path)
            result = await analyzer.analyze_and_recommend(today)

            logger.info(
                "每日任务分析完成: %d 条推荐",
                len(result.get("recommendations", []))
            )

        except Exception as e:
            logger.error("每日任务分析失败: %s", e)

    async def _push_recommendations(self) -> None:
        """早上7点推送任务。"""
        today = datetime.now().strftime("%Y-%m-%d")
        logger.info("开始推送每日任务: %s", today)

        try:
            from src.tools.todo_storage import (
                DailyRecommendation,
                RecommendationStatus,
                TodoStorage,
            )

            storage = TodoStorage(self._db_path)

            # 检查今日推荐
            rec = storage.get_recommendation(today)

            if not rec:
                # 如果没有推荐，先分析生成
                logger.info("未找到今日推荐，先生成推荐")
                await self._run_analysis()
                rec = storage.get_recommendation(today)

            if not rec or rec.status == RecommendationStatus.PUSHED:
                logger.info("今日任务已推送或无推荐")
                return

            # 格式化推送消息
            message = self._format_recommendation_message(rec)

            # 通过 CompanionEngine 推送
            if self._companion_engine:
                await self._companion_engine.send_daily_task_message(message)
            elif self._event_bus:
                # 通过事件总线发布
                from src.core.events import EventType
                await self._event_bus.emit(
                    EventType.COMPANION_CARE_TRIGGERED,
                    {
                        "message": message,
                        "source": "daily_task_scheduler",
                    }
                )
            else:
                logger.warning("无法推送每日任务：未设置 CompanionEngine 或 EventBus")

            # 更新推送状态
            storage.update_recommendation_status(today, RecommendationStatus.PUSHED)
            self._last_push_date = today

            logger.info("每日任务推送完成")

        except Exception as e:
            logger.error("推送每日任务失败: %s", e)

    async def check_and_push_on_startup(self) -> bool:
        """应用启动时检查是否需要推送。

        Returns:
            是否执行了推送
        """
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        hour = now.hour

        # 只在早上6点到10点之间检查（用户可能刚起床）
        if hour < 6 or hour > 10:
            logger.debug("不在推送时间窗口，跳过启动检查")
            return False

        # 检查今天是否已推送
        if self._last_push_date == today:
            logger.debug("今日已推送，跳过")
            return False

        try:
            from src.tools.todo_storage import RecommendationStatus, TodoStorage

            storage = TodoStorage(self._db_path)
            rec = storage.get_recommendation(today)

            # 如果已有推送记录，跳过
            if rec and rec.status == RecommendationStatus.PUSHED:
                self._last_push_date = today
                return False

            # 执行推送
            await self._push_recommendations()
            return True

        except Exception as e:
            logger.error("启动检查失败: %s", e)
            return False

    def _format_recommendation_message(self, rec: Any) -> str:
        """格式化推荐消息。"""
        now = datetime.now()
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekdays[now.weekday()]

        lines = [
            f"📋 今日任务清单（{now.strftime('%m月%d日')} {weekday}）",
            "",
        ]

        recommendations = rec.recommendations if hasattr(rec, 'recommendations') else []

        if not recommendations:
            lines.append("📭 今日暂无推荐任务")
        else:
            # 按来源分组
            overdue_tasks = [r for r in recommendations if r.get("source") == "todo_overdue"]
            today_tasks = [r for r in recommendations if r.get("source") == "todo_today"]
            family_tasks = [r for r in recommendations if r.get("family") in r.get("source", "")]
            other_tasks = [r for r in recommendations if r not in overdue_tasks + today_tasks + family_tasks]

            if overdue_tasks:
                lines.append("⚠️ 过期任务：")
                for task in overdue_tasks[:3]:
                    priority_icon = self._get_priority_icon(task.get("priority", 3))
                    lines.append(f"  {priority_icon} {task.get('title', '')}")

            if today_tasks:
                lines.append("\n📅 今日到期：")
                for task in today_tasks[:3]:
                    priority_icon = self._get_priority_icon(task.get("priority", 3))
                    lines.append(f"  {priority_icon} {task.get('title', '')}")

            if family_tasks:
                lines.append("\n👨‍👩‍👧 家庭相关：")
                for task in family_tasks[:3]:
                    priority_icon = self._get_priority_icon(task.get("priority", 3))
                    lines.append(f"  {priority_icon} {task.get('title', '')}")

            if other_tasks:
                lines.append("\n📋 推荐任务：")
                for task in other_tasks[:5]:
                    priority_icon = self._get_priority_icon(task.get("priority", 3))
                    time_str = ""
                    if task.get("scheduled_start"):
                        time_str = f" {task['scheduled_start']}"
                    lines.append(f"  {priority_icon} {task.get('title', '')}{time_str}")

        # 添加分析摘要
        if hasattr(rec, 'analysis_summary') and rec.analysis_summary:
            lines.append(f"\n💡 {rec.analysis_summary}")

        lines.append("\n💬 回复「确认任务」开始今日计划，或「调整任务」修改安排。")

        return "\n".join(lines)

    def _get_priority_icon(self, priority: int) -> str:
        """获取优先级图标。"""
        icons = {
            1: "🔴",
            2: "🟠",
            3: "🟡",
            4: "🟢",
            5: "⚪",
        }
        return icons.get(priority, "🟡")

    # ------------------------------------------------------------------
    # 手动触发方法
    # ------------------------------------------------------------------

    async def trigger_analysis_now(self) -> dict[str, Any]:
        """手动触发分析。"""
        await self._run_analysis()

        today = datetime.now().strftime("%Y-%m-%d")
        from src.tools.todo_storage import TodoStorage

        storage = TodoStorage(self._db_path)
        rec = storage.get_recommendation(today)

        if rec:
            return {
                "success": True,
                "date": today,
                "recommendations": rec.recommendations,
                "analysis_summary": rec.analysis_summary,
            }
        return {"success": False, "error": "分析结果未找到"}

    async def trigger_push_now(self) -> dict[str, Any]:
        """手动触发推送。"""
        await self._push_recommendations()

        today = datetime.now().strftime("%Y-%m-%d")
        return {
            "success": True,
            "date": today,
            "pushed": self._last_push_date == today,
        }
