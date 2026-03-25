"""每日任务工具 — 管理每日任务清单与智能推荐。

支持动作：
1. add_daily_task — 添加每日任务
2. update_daily_task — 更新每日任务
3. remove_daily_task — 移除每日任务
4. get_daily_tasks — 获取某日任务列表
5. start_task — 开始任务
6. complete_task — 完成任务
7. cancel_task — 取消任务
8. get_today_summary — 获取今日任务摘要
9. generate_recommendations — 生成每日任务推荐
10. accept_recommendations — 接受推荐任务

数据存储：~/.winclaw/winclaw_tools.db
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus
from src.tools.todo_storage import (
    DailyRecommendation,
    DailyTask,
    RecommendationStatus,
    TaskCategory,
    Todo,
    TodoStatus,
    TodoStorage,
)

logger = logging.getLogger(__name__)

# 默认数据库路径
_DEFAULT_DB = Path.home() / ".winclaw" / "winclaw_tools.db"

# 类型显示名称映射
_CATEGORY_DISPLAY = {
    "work": "工作",
    "study": "学习",
    "health": "健康",
    "family": "家庭",
    "social": "社交",
    "finance": "财务",
    "hobby": "爱好",
    "general": "通用",
    "other": "其他",
}

_STATUS_DISPLAY = {
    "pending": "待办",
    "in_progress": "进行中",
    "completed": "已完成",
    "cancelled": "已取消",
    "paused": "已中止",
}

_PRIORITY_ICONS = {
    1: "🔴",
    2: "🟠",
    3: "🟡",
    4: "🟢",
    5: "⚪",
}


class DailyTaskTool(BaseTool):
    """每日任务管理工具。

    管理用户的每日任务清单，支持：
    - 从待办事项提取每日任务
    - 临时添加每日任务
    - 任务状态跟踪（待办/进行中/已完成/已取消）
    - 时间安排与实际执行记录
    - AI 智能推荐任务
    """

    name = "daily_task"
    emoji = "📅"
    title = "每日任务"
    description = "管理每日任务清单，支持从待办事项提取、智能推荐、状态跟踪"

    def __init__(self, db_path: str = ""):
        """初始化每日任务工具。

        Args:
            db_path: 数据库路径，为空时使用默认路径
        """
        super().__init__()
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._storage: TodoStorage | None = None

    def _get_storage(self) -> TodoStorage:
        """延迟获取存储实例。"""
        if self._storage is None:
            self._storage = TodoStorage(self._db_path)
        return self._storage

    def get_actions(self) -> list[ActionDef]:
        """返回所有支持的动作定义。"""
        return [
            ActionDef(
                name="add_daily_task",
                description="添加每日任务（可从待办事项提取或临时创建）",
                parameters={
                    "todo_id": {
                        "type": "integer",
                        "description": "关联的待办事项ID（可选，为空表示临时任务）",
                    },
                    "task_date": {
                        "type": "string",
                        "description": "任务日期 YYYY-MM-DD（可选，默认今天）",
                    },
                    "title": {
                        "type": "string",
                        "description": "任务标题（必填，如果todo_id为空）",
                    },
                    "description": {
                        "type": "string",
                        "description": "任务描述（可选）",
                    },
                    "category": {
                        "type": "string",
                        "description": "任务类型（可选）",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "优先级 1-5（可选，默认3）",
                    },
                    "scheduled_start": {
                        "type": "string",
                        "description": "计划开始时间 HH:MM（可选）",
                    },
                    "scheduled_end": {
                        "type": "string",
                        "description": "计划结束时间 HH:MM（可选）",
                    },
                    "ai_reason": {
                        "type": "string",
                        "description": "AI推荐理由（可选）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="update_daily_task",
                description="更新每日任务信息",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "任务ID（必填）",
                    },
                    "title": {
                        "type": "string",
                        "description": "新标题（可选）",
                    },
                    "description": {
                        "type": "string",
                        "description": "新描述（可选）",
                    },
                    "scheduled_start": {
                        "type": "string",
                        "description": "新计划开始时间（可选）",
                    },
                    "scheduled_end": {
                        "type": "string",
                        "description": "新计划结束时间（可选）",
                    },
                    "status": {
                        "type": "string",
                        "description": "新状态（可选）",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="remove_daily_task",
                description="移除每日任务",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "任务ID",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="get_daily_tasks",
                description="获取某日的任务列表",
                parameters={
                    "date": {
                        "type": "string",
                        "description": "日期 YYYY-MM-DD（可选，默认今天）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="start_task",
                description="开始执行任务",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "任务ID",
                    },
                    "actual_start": {
                        "type": "string",
                        "description": "实际开始时间 HH:MM（可选，默认当前时间）",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="complete_task",
                description="完成任务",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "任务ID",
                    },
                    "completion_note": {
                        "type": "string",
                        "description": "完成备注（可选）",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="cancel_task",
                description="取消任务",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "任务ID",
                    },
                    "reason": {
                        "type": "string",
                        "description": "取消原因（可选）",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="get_today_summary",
                description="获取今日任务摘要统计",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="generate_recommendations",
                description="生成每日任务推荐（从待办事项智能分析）",
                parameters={
                    "date": {
                        "type": "string",
                        "description": "目标日期 YYYY-MM-DD（可选，默认今天）",
                    },
                    "max_count": {
                        "type": "integer",
                        "description": "最大推荐数量（可选，默认10）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="accept_recommendations",
                description="接受推荐的每日任务",
                parameters={
                    "date": {
                        "type": "string",
                        "description": "日期 YYYY-MM-DD（可选，默认今天）",
                    },
                    "task_ids": {
                        "type": "string",
                        "description": "接受的任务ID列表，JSON数组格式如 [1,2,3]（可选，默认接受全部）",
                    },
                },
                required_params=[],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定动作。"""
        storage = self._get_storage()

        try:
            if action == "add_daily_task":
                return self._add_daily_task(storage, params)
            elif action == "update_daily_task":
                return self._update_daily_task(storage, params)
            elif action == "remove_daily_task":
                return self._remove_daily_task(storage, params)
            elif action == "get_daily_tasks":
                return self._get_daily_tasks(storage, params)
            elif action == "start_task":
                return self._start_task(storage, params)
            elif action == "complete_task":
                return self._complete_task(storage, params)
            elif action == "cancel_task":
                return self._cancel_task(storage, params)
            elif action == "get_today_summary":
                return self._get_today_summary(storage)
            elif action == "generate_recommendations":
                return self._generate_recommendations(storage, params)
            elif action == "accept_recommendations":
                return self._accept_recommendations(storage, params)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"未知动作: {action}"
                )
        except Exception as e:
            logger.error("DailyTaskTool 执行失败: %s - %s", action, e)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=str(e)
            )

    def _add_daily_task(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """添加每日任务。"""
        # 确定任务日期
        task_date = params.get("task_date") or datetime.now().strftime("%Y-%m-%d")

        # 如果有 todo_id，从待办事项提取信息
        todo_id = params.get("todo_id")
        todo: Todo | None = None
        if todo_id:
            todo = storage.get_todo(todo_id)
            if not todo:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"待办事项不存在: ID {todo_id}"
                )

        # 确定标题
        title = params.get("title", "")
        if not title and todo:
            title = todo.title
        if not title:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="任务标题不能为空"
            )

        # 创建每日任务
        task = DailyTask(
            todo_id=todo_id,
            task_date=task_date,
            title=title,
            description=params.get("description") or (todo.description if todo else ""),
            category=TaskCategory(params.get("category")) if params.get("category") else (todo.category if todo else TaskCategory.GENERAL),
            priority=params.get("priority") or (todo.priority if todo else 3),
            scheduled_start=params.get("scheduled_start"),
            scheduled_end=params.get("scheduled_end"),
            source="from_todo" if todo_id else "manual",
            ai_reason=params.get("ai_reason", ""),
        )

        task_id = storage.create_daily_task(task)

        # 构建输出
        priority_icon = _PRIORITY_ICONS.get(task.priority, "🟡")
        category_display = _CATEGORY_DISPLAY.get(task.category.value, "通用") if task.category else "通用"

        output = f"✅ 每日任务已添加 (ID: {task_id})\n"
        output += f"{priority_icon} {title}\n"
        output += f"日期: {task_date} | 类型: {category_display}"

        if task.scheduled_start:
            time_str = f"{task.scheduled_start}"
            if task.scheduled_end:
                time_str += f" - {task.scheduled_end}"
            output += f"\n⏰ {time_str}"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"id": task_id, "task": task.to_dict()}
        )

    def _update_daily_task(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """更新每日任务。"""
        task_id = params.get("id")
        if task_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少任务ID"
            )

        task = storage.get_daily_task(task_id)
        if not task:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"任务不存在: ID {task_id}"
            )

        updates: dict[str, Any] = {}
        for field in ["title", "description", "scheduled_start", "scheduled_end", "actual_start", "actual_end", "completion_note"]:
            if field in params and params[field] is not None:
                updates[field] = params[field]

        if "category" in params:
            updates["category"] = TaskCategory(params["category"])
        if "status" in params:
            updates["status"] = TodoStatus(params["status"])
        if "priority" in params:
            updates["priority"] = params["priority"]

        if not updates:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="无更新内容",
                data={"id": task_id}
            )

        storage.update_daily_task(task_id, updates)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 任务已更新 (ID: {task_id})",
            data={"id": task_id, "updates": list(updates.keys())}
        )

    def _remove_daily_task(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """移除每日任务。"""
        task_id = params.get("id")
        if task_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少任务ID"
            )

        task = storage.get_daily_task(task_id)
        if not task:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"任务不存在: ID {task_id}"
            )

        storage.delete_daily_task(task_id)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 任务已移除\n{task.title}",
            data={"id": task_id}
        )

    def _get_daily_tasks(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """获取某日任务列表。"""
        date = params.get("date") or datetime.now().strftime("%Y-%m-%d")
        tasks = storage.get_daily_tasks(date)

        if not tasks:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"📭 {date} 暂无任务",
                data={"date": date, "tasks": [], "count": 0}
            )

        # 按状态分组
        pending = [t for t in tasks if t.status == TodoStatus.PENDING]
        in_progress = [t for t in tasks if t.status == TodoStatus.IN_PROGRESS]
        completed = [t for t in tasks if t.status == TodoStatus.COMPLETED]

        # 格式化日期显示
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            date_display = f"{date} {weekdays[dt.weekday()]}"
        except ValueError:
            date_display = date

        lines = [f"📅 {date_display} 任务清单 ({len(tasks)} 条)"]

        if in_progress:
            lines.append(f"\n⏳ 进行中 ({len(in_progress)})")
            for task in in_progress:
                icon = _PRIORITY_ICONS.get(task.priority, "🟡")
                time_str = f" {task.scheduled_start}" if task.scheduled_start else ""
                lines.append(f"  {icon} {task.title}{time_str}")

        if pending:
            lines.append(f"\n○ 待办 ({len(pending)})")
            for task in pending:
                icon = _PRIORITY_ICONS.get(task.priority, "🟡")
                time_str = f" {task.scheduled_start}" if task.scheduled_start else ""
                lines.append(f"  {icon} {task.title}{time_str}")

        if completed:
            lines.append(f"\n✅ 已完成 ({len(completed)})")
            for task in completed:
                lines.append(f"  ✓ {task.title}")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"date": date, "tasks": [t.to_dict() for t in tasks], "count": len(tasks)}
        )

    def _start_task(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """开始执行任务。"""
        task_id = params.get("id")
        if task_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少任务ID"
            )

        task = storage.get_daily_task(task_id)
        if not task:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"任务不存在: ID {task_id}"
            )

        actual_start = params.get("actual_start") or datetime.now().strftime("%H:%M")

        storage.update_daily_task(task_id, {
            "status": TodoStatus.IN_PROGRESS,
            "actual_start": actual_start,
        })

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"🚀 开始执行任务\n{task.title}\n开始时间: {actual_start}",
            data={"id": task_id, "actual_start": actual_start}
        )

    def _complete_task(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """完成任务。"""
        task_id = params.get("id")
        if task_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少任务ID"
            )

        task = storage.get_daily_task(task_id)
        if not task:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"任务不存在: ID {task_id}"
            )

        actual_end = datetime.now().strftime("%H:%M")
        completion_note = params.get("completion_note", "")

        storage.update_daily_task(task_id, {
            "status": TodoStatus.COMPLETED,
            "actual_end": actual_end,
            "completion_note": completion_note,
        })

        # 如果关联了待办事项，也更新待办事项进度
        if task.todo_id:
            todo = storage.get_todo(task.todo_id)
            if todo and todo.status != TodoStatus.COMPLETED:
                # 检查是否所有子任务都完成了
                sub_tasks = storage.get_sub_todos(task.todo_id)
                if not sub_tasks:  # 没有子任务，直接完成
                    storage.complete_todo(task.todo_id, completion_note)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"🎉 任务完成！\n{task.title}",
            data={"id": task_id, "actual_end": actual_end}
        )

    def _cancel_task(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """取消任务。"""
        task_id = params.get("id")
        if task_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少任务ID"
            )

        task = storage.get_daily_task(task_id)
        if not task:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"任务不存在: ID {task_id}"
            )

        reason = params.get("reason", "")

        storage.update_daily_task(task_id, {
            "status": TodoStatus.CANCELLED,
            "completion_note": reason,
        })

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"❌ 任务已取消\n{task.title}",
            data={"id": task_id}
        )

    def _get_today_summary(self, storage: TodoStorage) -> ToolResult:
        """获取今日任务摘要。"""
        summary = storage.get_today_summary()

        today = datetime.now().strftime("%Y-%m-%d")
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekdays[datetime.now().weekday()]

        lines = [
            f"📊 今日任务摘要 ({today} {weekday})",
            f"─" * 30,
            f"总任务: {summary['total']} 个",
            f"  ○ 待办: {summary['pending']} 个",
            f"  ⏳ 进行中: {summary['in_progress']} 个",
            f"  ✅ 已完成: {summary['completed']} 个",
            f"  ❌ 已取消: {summary['cancelled']} 个",
            f"",
            f"完成率: {summary['completion_rate']}%",
        ]

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data=summary
        )

    def _generate_recommendations(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """生成每日任务推荐。"""
        date = params.get("date") or datetime.now().strftime("%Y-%m-%d")
        max_count = params.get("max_count", 10)

        # 检查是否已有今日推荐
        existing = storage.get_recommendation(date)
        if existing and existing.status == RecommendationStatus.PUSHED:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"今日推荐已存在，请查看或接受",
                data=existing.to_dict()
            )

        # 获取待办事项
        todos = storage.list_todos(include_completed=False, limit=50)

        # 获取过期任务
        overdue = storage.get_overdue_todos()

        # 获取即将到期任务
        upcoming = storage.get_upcoming_todos(days=7)

        # 构建推荐列表
        recommendations = []

        # 1. 过期任务优先
        for todo in overdue[:3]:
            recommendations.append({
                "todo_id": todo.id,
                "title": todo.title,
                "category": todo.category.value,
                "priority": todo.priority,
                "deadline": todo.deadline,
                "source": "overdue",
                "ai_confidence": 0.95,
                "ai_reason": "任务已过期，建议优先处理",
            })

        # 2. 即将到期任务
        for todo in upcoming[:5]:
            if todo.id not in [r["todo_id"] for r in recommendations]:
                recommendations.append({
                    "todo_id": todo.id,
                    "title": todo.title,
                    "category": todo.category.value,
                    "priority": todo.priority,
                    "deadline": todo.deadline,
                    "source": "upcoming",
                    "ai_confidence": 0.85,
                    "ai_reason": "任务即将到期",
                })

        # 3. 高优先级待办
        high_priority = [t for t in todos if t.priority <= 2]
        for todo in high_priority[:5]:
            if todo.id not in [r["todo_id"] for r in recommendations]:
                recommendations.append({
                    "todo_id": todo.id,
                    "title": todo.title,
                    "category": todo.category.value,
                    "priority": todo.priority,
                    "deadline": todo.deadline,
                    "source": "high_priority",
                    "ai_confidence": 0.75,
                    "ai_reason": "高优先级任务",
                })

        # 按评分排序并限制数量
        recommendations = sorted(
            recommendations,
            key=lambda x: (x["priority"], -x["ai_confidence"])
        )[:max_count]

        # 生成分析摘要
        analysis_summary = self._build_analysis_summary(overdue, upcoming, recommendations)

        # 存储推荐记录
        rec = DailyRecommendation(
            task_date=date,
            recommendations=recommendations,
            analysis_summary=analysis_summary,
        )
        rec_id = storage.create_recommendation(rec)

        # 构建输出
        lines = [f"📋 每日任务推荐已生成 ({date})"]
        lines.append(f"推荐任务: {len(recommendations)} 个")

        if overdue:
            lines.append(f"⚠️ 过期任务: {len(overdue)} 个")
        if upcoming:
            lines.append(f"📅 即将到期: {len(upcoming)} 个")

        lines.append("\n推荐列表:")
        for i, r in enumerate(recommendations, 1):
            icon = _PRIORITY_ICONS.get(r["priority"], "🟡")
            lines.append(f"  {i}. {icon} {r['title']}")
            if r.get("deadline"):
                lines.append(f"      截止: {r['deadline']}")
            lines.append(f"      原因: {r['ai_reason']}")

        lines.append("\n使用 accept_recommendations 接受推荐任务")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={
                "id": rec_id,
                "date": date,
                "recommendations": recommendations,
                "analysis_summary": analysis_summary,
            }
        )

    def _accept_recommendations(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """接受推荐的每日任务。"""
        date = params.get("date") or datetime.now().strftime("%Y-%m-%d")

        # 获取推荐记录
        rec = storage.get_recommendation(date)
        if not rec:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到 {date} 的推荐记录，请先生成推荐"
            )

        # 解析要接受的任务ID
        task_ids = None
        if params.get("task_ids"):
            try:
                task_ids = json.loads(params["task_ids"])
            except json.JSONDecodeError:
                pass

        # 筛选要接受的任务
        to_accept = rec.recommendations
        if task_ids:
            to_accept = [r for r in rec.recommendations if r.get("todo_id") in task_ids]

        # 创建每日任务
        created_ids = []
        for r in to_accept:
            task = DailyTask(
                todo_id=r.get("todo_id"),
                task_date=date,
                title=r["title"],
                category=TaskCategory(r.get("category", "general")),
                priority=r.get("priority", 3),
                source="ai_suggested",
                ai_confidence=r.get("ai_confidence", 0.5),
                ai_reason=r.get("ai_reason", ""),
            )
            task_id = storage.create_daily_task(task)
            created_ids.append(task_id)

        # 更新推荐状态
        storage.update_recommendation_status(date, RecommendationStatus.ACCEPTED)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 已接受 {len(created_ids)} 个推荐任务\n日期: {date}",
            data={
                "date": date,
                "accepted_count": len(created_ids),
                "task_ids": created_ids,
            }
        )

    def _build_analysis_summary(
        self,
        overdue: list[Todo],
        upcoming: list[Todo],
        recommendations: list[dict]
    ) -> str:
        """构建分析摘要。"""
        parts = []

        if overdue:
            parts.append(f"发现 {len(overdue)} 个过期未完成任务")
        if upcoming:
            parts.append(f"{len(upcoming)} 个任务即将在7天内到期")

        high_priority_count = sum(1 for r in recommendations if r["priority"] <= 2)
        if high_priority_count:
            parts.append(f"{high_priority_count} 个高优先级任务")

        if parts:
            return "；".join(parts) + "。建议优先处理。"
        return "暂无特别需要关注的任务。"
