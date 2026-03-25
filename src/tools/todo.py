"""待办事项工具 — 管理短期、中期、远期所有任务事项。

支持动作：
1. create_todo — 创建待办事项
2. update_todo — 更新待办事项
3. delete_todo — 删除待办事项
4. get_todo — 获取单个待办事项详情
5. list_todos — 列出待办事项（支持筛选）
6. complete_todo — 完成待办事项
7. cancel_todo — 取消待办事项
8. decompose_todo — 分解任务为子任务
9. get_overdue_todos — 获取过期未完成任务
10. get_upcoming_todos — 获取即将到期任务

数据存储：~/.winclaw/winclaw_tools.db
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus
from src.tools.todo_storage import (
    DailyTask,
    RecurrenceType,
    TaskCategory,
    TimeFrame,
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

_TIME_FRAME_DISPLAY = {
    "today": "今日",
    "week": "本周",
    "month": "本月",
    "quarter": "本季度",
    "year": "今年",
    "future": "未来",
}

_STATUS_DISPLAY = {
    "pending": "待办",
    "in_progress": "进行中",
    "completed": "已完成",
    "cancelled": "已取消",
    "paused": "已中止",
}

_PRIORITY_ICONS = {
    1: "🔴",  # 最高优先级
    2: "🟠",  # 高优先级
    3: "🟡",  # 中优先级
    4: "🟢",  # 低优先级
    5: "⚪",  # 最低优先级
}


class TodoTool(BaseTool):
    """待办事项管理工具。

    管理用户的所有待办事项，支持：
    - 六级时间周期分类（今日/本周/本月/季度/年/未来）
    - 八种任务类型（工作/学习/健康/家庭/社交/财务/爱好/其他）
    - 五种任务状态（待办/进行中/已完成/已取消/已中止）
    - 任务分解与关联家庭成员
    - 过期提醒与即将到期提醒
    """

    name = "todo"
    emoji = "📋"
    title = "待办事项"
    description = "管理短期、中期、远期所有任务事项，支持任务分解、优先级管理、关联家庭成员"

    def __init__(self, db_path: str = ""):
        """初始化待办事项工具。

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
                name="create_todo",
                description="创建新的待办事项",
                parameters={
                    "title": {
                        "type": "string",
                        "description": "任务标题（必填）",
                    },
                    "description": {
                        "type": "string",
                        "description": "任务描述（可选）",
                    },
                    "category": {
                        "type": "string",
                        "description": "任务类型：work/study/health/family/social/finance/hobby/other（可选，默认general）",
                    },
                    "time_frame": {
                        "type": "string",
                        "description": "时间周期：today/week/month/quarter/year/future（可选，默认future）",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "优先级 1-5（1最高，可选，默认3）",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "开始日期 YYYY-MM-DD（可选）",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "开始时间 HH:MM（可选）",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期 YYYY-MM-DD（可选）",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "结束时间 HH:MM（可选）",
                    },
                    "deadline": {
                        "type": "string",
                        "description": "截止日期时间（可选）",
                    },
                    "related_members": {
                        "type": "string",
                        "description": "任务关系人ID列表，JSON数组格式如 [1,2,3]（可选）",
                    },
                    "assignee": {
                        "type": "string",
                        "description": "任务执行人（可选）",
                    },
                    "recurrence": {
                        "type": "string",
                        "description": "重复规则：none/daily/weekly/monthly/yearly（可选，默认none）",
                    },
                    "tags": {
                        "type": "string",
                        "description": "标签列表，JSON数组格式如 [\"重要\",\"紧急\"]（可选）",
                    },
                    "notes": {
                        "type": "string",
                        "description": "备注（可选）",
                    },
                },
                required_params=["title"],
            ),
            ActionDef(
                name="update_todo",
                description="更新待办事项信息",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "待办事项ID（必填）",
                    },
                    "title": {
                        "type": "string",
                        "description": "新标题（可选）",
                    },
                    "description": {
                        "type": "string",
                        "description": "新描述（可选）",
                    },
                    "category": {
                        "type": "string",
                        "description": "新类型（可选）",
                    },
                    "time_frame": {
                        "type": "string",
                        "description": "新时间周期（可选）",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "新优先级 1-5（可选）",
                    },
                    "status": {
                        "type": "string",
                        "description": "新状态：pending/in_progress/completed/cancelled/paused（可选）",
                    },
                    "progress": {
                        "type": "integer",
                        "description": "进度 0-100（可选）",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "新开始日期（可选）",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "新开始时间（可选）",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "新结束日期（可选）",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "新结束时间（可选）",
                    },
                    "deadline": {
                        "type": "string",
                        "description": "新截止日期（可选）",
                    },
                    "related_members": {
                        "type": "string",
                        "description": "新关系人ID列表（可选）",
                    },
                    "assignee": {
                        "type": "string",
                        "description": "新执行人（可选）",
                    },
                    "recurrence": {
                        "type": "string",
                        "description": "新重复规则（可选）",
                    },
                    "tags": {
                        "type": "string",
                        "description": "新标签列表（可选）",
                    },
                    "notes": {
                        "type": "string",
                        "description": "新备注（可选）",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="delete_todo",
                description="删除待办事项",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "待办事项ID",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="get_todo",
                description="获取单个待办事项详情",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "待办事项ID",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="list_todos",
                description="列出待办事项（支持多条件筛选）",
                parameters={
                    "time_frame": {
                        "type": "string",
                        "description": "按时间周期筛选：today/week/month/quarter/year/future（可选）",
                    },
                    "category": {
                        "type": "string",
                        "description": "按类型筛选（可选）",
                    },
                    "status": {
                        "type": "string",
                        "description": "按状态筛选（可选）",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "按优先级筛选（可选）",
                    },
                    "assignee": {
                        "type": "string",
                        "description": "按执行人筛选（可选）",
                    },
                    "search": {
                        "type": "string",
                        "description": "搜索关键词（可选）",
                    },
                    "include_completed": {
                        "type": "boolean",
                        "description": "是否包含已完成的任务（可选，默认false）",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制（可选，默认100）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="complete_todo",
                description="完成待办事项",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "待办事项ID",
                    },
                    "completion_note": {
                        "type": "string",
                        "description": "完成备注（可选）",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="cancel_todo",
                description="取消待办事项",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "待办事项ID",
                    },
                    "reason": {
                        "type": "string",
                        "description": "取消原因（可选）",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="decompose_todo",
                description="将任务分解为子任务",
                parameters={
                    "id": {
                        "type": "integer",
                        "description": "父任务ID",
                    },
                    "subtasks": {
                        "type": "string",
                        "description": "子任务列表，JSON数组格式如 [{\"title\":\"子任务1\"},{\"title\":\"子任务2\"}]",
                    },
                },
                required_params=["id", "subtasks"],
            ),
            ActionDef(
                name="get_overdue_todos",
                description="获取过期未完成的任务列表",
                parameters={},
                required_params=[],
            ),
            ActionDef(
                name="get_upcoming_todos",
                description="获取即将到期的任务列表",
                parameters={
                    "days": {
                        "type": "integer",
                        "description": "查询未来多少天内到期的任务（可选，默认7天）",
                    },
                },
                required_params=[],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定动作。"""
        storage = self._get_storage()

        try:
            if action == "create_todo":
                return self._create_todo(storage, params)
            elif action == "update_todo":
                return self._update_todo(storage, params)
            elif action == "delete_todo":
                return self._delete_todo(storage, params)
            elif action == "get_todo":
                return self._get_todo(storage, params)
            elif action == "list_todos":
                return self._list_todos(storage, params)
            elif action == "complete_todo":
                return self._complete_todo(storage, params)
            elif action == "cancel_todo":
                return self._cancel_todo(storage, params)
            elif action == "decompose_todo":
                return self._decompose_todo(storage, params)
            elif action == "get_overdue_todos":
                return self._get_overdue_todos(storage)
            elif action == "get_upcoming_todos":
                return self._get_upcoming_todos(storage, params)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"未知动作: {action}"
                )
        except Exception as e:
            logger.error("TodoTool 执行失败: %s - %s", action, e)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=str(e)
            )

    def _create_todo(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """创建待办事项。"""
        import json

        title = params.get("title", "").strip()
        if not title:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="任务标题不能为空"
            )

        # 解析参数
        category = TaskCategory(params.get("category", "general"))
        time_frame = TimeFrame(params.get("time_frame", "future"))
        priority = params.get("priority", 3)
        if not isinstance(priority, int) or priority < 1 or priority > 5:
            priority = 3

        # 解析JSON字段
        related_members = []
        if params.get("related_members"):
            try:
                related_members = json.loads(params["related_members"])
            except json.JSONDecodeError:
                pass

        tags = []
        if params.get("tags"):
            try:
                tags = json.loads(params["tags"])
            except json.JSONDecodeError:
                pass

        recurrence = RecurrenceType(params.get("recurrence", "none"))

        # 创建Todo对象
        todo = Todo(
            title=title,
            description=params.get("description", ""),
            category=category,
            time_frame=time_frame,
            priority=priority,
            start_date=params.get("start_date"),
            start_time=params.get("start_time"),
            end_date=params.get("end_date"),
            end_time=params.get("end_time"),
            deadline=params.get("deadline"),
            related_members=related_members,
            assignee=params.get("assignee", ""),
            recurrence=recurrence,
            tags=tags,
            notes=params.get("notes", ""),
        )

        todo_id = storage.create_todo(todo)

        # 构建输出
        priority_icon = _PRIORITY_ICONS.get(priority, "🟡")
        category_display = _CATEGORY_DISPLAY.get(category.value, "通用")
        time_frame_display = _TIME_FRAME_DISPLAY.get(time_frame.value, "未来")

        output = f"✅ 待办事项已创建 (ID: {todo_id})\n"
        output += f"{priority_icon} {title}\n"
        output += f"类型: {category_display} | 周期: {time_frame_display} | 优先级: {priority}"

        if todo.deadline:
            output += f"\n⏰ 截止: {todo.deadline}"
        if todo.start_date:
            output += f"\n📅 开始: {todo.start_date}"
        if related_members:
            output += f"\n👥 关系人: {len(related_members)} 人"
        if recurrence != RecurrenceType.NONE:
            output += f"\n🔄 重复: {recurrence.value}"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"id": todo_id, "todo": todo.to_dict()}
        )

    def _update_todo(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """更新待办事项。"""
        import json

        todo_id = params.get("id")
        if todo_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少待办事项ID"
            )

        # 检查任务是否存在
        todo = storage.get_todo(todo_id)
        if not todo:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"待办事项不存在: ID {todo_id}"
            )

        # 构建更新字段
        updates: dict[str, Any] = {}

        simple_fields = [
            "title", "description", "priority", "start_date", "start_time",
            "end_date", "end_time", "deadline", "assignee", "notes"
        ]
        for field in simple_fields:
            if field in params and params[field] is not None:
                updates[field] = params[field]

        if "category" in params:
            updates["category"] = TaskCategory(params["category"])
        if "time_frame" in params:
            updates["time_frame"] = TimeFrame(params["time_frame"])
        if "status" in params:
            updates["status"] = TodoStatus(params["status"])
        if "recurrence" in params:
            updates["recurrence"] = RecurrenceType(params["recurrence"])
        if "progress" in params:
            updates["progress"] = min(100, max(0, int(params["progress"])))

        if "related_members" in params:
            try:
                updates["related_members"] = json.loads(params["related_members"])
            except json.JSONDecodeError:
                pass
        if "tags" in params:
            try:
                updates["tags"] = json.loads(params["tags"])
            except json.JSONDecodeError:
                pass

        if not updates:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="无更新内容",
                data={"id": todo_id}
            )

        storage.update_todo(todo_id, updates)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 待办事项已更新 (ID: {todo_id})\n更新字段: {', '.join(updates.keys())}",
            data={"id": todo_id, "updates": list(updates.keys())}
        )

    def _delete_todo(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """删除待办事项。"""
        todo_id = params.get("id")
        if todo_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少待办事项ID"
            )

        # 检查任务是否存在
        todo = storage.get_todo(todo_id)
        if not todo:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"待办事项不存在: ID {todo_id}"
            )

        storage.delete_todo(todo_id)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 待办事项已删除 (ID: {todo_id})\n{todo.title}",
            data={"id": todo_id}
        )

    def _get_todo(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """获取单个待办事项。"""
        todo_id = params.get("id")
        if todo_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少待办事项ID"
            )

        todo = storage.get_todo(todo_id)
        if not todo:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"待办事项不存在: ID {todo_id}"
            )

        # 构建详细输出
        output = self._format_todo_detail(todo)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data=todo.to_dict()
        )

    def _list_todos(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """列出待办事项。"""
        todos = storage.list_todos(
            time_frame=params.get("time_frame"),
            category=params.get("category"),
            status=params.get("status"),
            priority=params.get("priority"),
            assignee=params.get("assignee"),
            search=params.get("search"),
            include_completed=params.get("include_completed", False),
            limit=params.get("limit", 100),
        )

        if not todos:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="📭 暂无待办事项",
                data={"todos": [], "count": 0}
            )

        # 构建输出
        lines = [f"📋 待办事项列表 ({len(todos)} 条)"]

        # 按时间周期分组
        grouped: dict[str, list[Todo]] = {}
        for todo in todos:
            tf = todo.time_frame.value
            if tf not in grouped:
                grouped[tf] = []
            grouped[tf].append(todo)

        for tf in ["today", "week", "month", "quarter", "year", "future"]:
            if tf in grouped:
                tf_display = _TIME_FRAME_DISPLAY.get(tf, tf)
                lines.append(f"\n【{tf_display}】")
                for todo in grouped[tf]:
                    icon = _PRIORITY_ICONS.get(todo.priority, "🟡")
                    status_icon = "✅" if todo.status == TodoStatus.COMPLETED else "⏳" if todo.status == TodoStatus.IN_PROGRESS else "○"
                    lines.append(f"  {icon} {status_icon} {todo.title}")
                    if todo.deadline:
                        lines.append(f"      截止: {todo.deadline}")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"todos": [t.to_dict() for t in todos], "count": len(todos)}
        )

    def _complete_todo(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """完成待办事项。"""
        todo_id = params.get("id")
        if todo_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少待办事项ID"
            )

        todo = storage.get_todo(todo_id)
        if not todo:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"待办事项不存在: ID {todo_id}"
            )

        completion_note = params.get("completion_note", "")
        storage.complete_todo(todo_id, completion_note)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"🎉 待办事项已完成！\n{todo.title}",
            data={"id": todo_id, "completed_at": datetime.now().isoformat()}
        )

    def _cancel_todo(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """取消待办事项。"""
        todo_id = params.get("id")
        if todo_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少待办事项ID"
            )

        todo = storage.get_todo(todo_id)
        if not todo:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"待办事项不存在: ID {todo_id}"
            )

        reason = params.get("reason", "")
        storage.cancel_todo(todo_id, reason)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"❌ 待办事项已取消\n{todo.title}",
            data={"id": todo_id}
        )

    def _decompose_todo(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """分解任务为子任务。"""
        import json

        todo_id = params.get("id")
        if todo_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少父任务ID"
            )

        parent = storage.get_todo(todo_id)
        if not parent:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"父任务不存在: ID {todo_id}"
            )

        subtasks_json = params.get("subtasks", "[]")
        try:
            subtasks_data = json.loads(subtasks_json)
        except json.JSONDecodeError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="子任务列表格式错误，应为JSON数组"
            )

        if not isinstance(subtasks_data, list):
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="子任务列表应为数组格式"
            )

        # 创建子任务
        created_ids = []
        for i, st in enumerate(subtasks_data):
            if isinstance(st, dict) and st.get("title"):
                sub_todo = Todo(
                    title=st["title"],
                    description=st.get("description", ""),
                    category=parent.category,
                    time_frame=parent.time_frame,
                    priority=parent.priority,
                    parent_id=todo_id,
                    assignee=parent.assignee,
                )
                sub_id = storage.create_todo(sub_todo)
                created_ids.append(sub_id)

        output = f"✅ 任务已分解\n"
        output += f"父任务: {parent.title}\n"
        output += f"创建子任务: {len(created_ids)} 个"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={
                "parent_id": todo_id,
                "subtask_ids": created_ids,
                "count": len(created_ids)
            }
        )

    def _get_overdue_todos(self, storage: TodoStorage) -> ToolResult:
        """获取过期未完成任务。"""
        todos = storage.get_overdue_todos()

        if not todos:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="✅ 没有过期未完成的任务",
                data={"todos": [], "count": 0}
            )

        lines = [f"⚠️ 过期未完成任务 ({len(todos)} 条)"]
        for todo in todos:
            icon = _PRIORITY_ICONS.get(todo.priority, "🟡")
            lines.append(f"  {icon} {todo.title}")
            lines.append(f"      截止: {todo.deadline}")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"todos": [t.to_dict() for t in todos], "count": len(todos)}
        )

    def _get_upcoming_todos(self, storage: TodoStorage, params: dict[str, Any]) -> ToolResult:
        """获取即将到期任务。"""
        days = params.get("days", 7)
        if not isinstance(days, int) or days < 1:
            days = 7

        todos = storage.get_upcoming_todos(days)

        if not todos:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"📭 未来 {days} 天内没有即将到期的任务",
                data={"todos": [], "count": 0}
            )

        lines = [f"📅 未来 {days} 天内即将到期 ({len(todos)} 条)"]
        for todo in todos:
            icon = _PRIORITY_ICONS.get(todo.priority, "🟡")
            lines.append(f"  {icon} {todo.title}")
            lines.append(f"      截止: {todo.deadline}")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"todos": [t.to_dict() for t in todos], "count": len(todos)}
        )

    def _format_todo_detail(self, todo: Todo) -> str:
        """格式化待办事项详情。"""
        icon = _PRIORITY_ICONS.get(todo.priority, "🟡")
        category_display = _CATEGORY_DISPLAY.get(todo.category.value, "通用")
        time_frame_display = _TIME_FRAME_DISPLAY.get(todo.time_frame.value, "未来")
        status_display = _STATUS_DISPLAY.get(todo.status.value, "待办")

        lines = [
            f"{icon} {todo.title}",
            f"─" * 30,
            f"ID: {todo.id}",
            f"状态: {status_display}",
            f"类型: {category_display}",
            f"时间周期: {time_frame_display}",
            f"优先级: {todo.priority}",
        ]

        if todo.description:
            lines.append(f"描述: {todo.description}")
        if todo.start_date:
            time_str = f"{todo.start_date} {todo.start_time}" if todo.start_time else todo.start_date
            lines.append(f"开始: {time_str}")
        if todo.end_date:
            time_str = f"{todo.end_date} {todo.end_time}" if todo.end_time else todo.end_date
            lines.append(f"结束: {time_str}")
        if todo.deadline:
            lines.append(f"截止: {todo.deadline}")
        if todo.progress > 0:
            lines.append(f"进度: {todo.progress}%")
        if todo.related_members:
            lines.append(f"关系人: {len(todo.related_members)} 人")
        if todo.assignee:
            lines.append(f"执行人: {todo.assignee}")
        if todo.recurrence != RecurrenceType.NONE:
            lines.append(f"重复: {todo.recurrence.value}")
        if todo.tags:
            lines.append(f"标签: {', '.join(todo.tags)}")
        if todo.notes:
            lines.append(f"备注: {todo.notes}")

        lines.append(f"创建: {todo.created_at.strftime('%Y-%m-%d %H:%M')}")
        if todo.completed_at:
            lines.append(f"完成: {todo.completed_at.strftime('%Y-%m-%d %H:%M')}")

        return "\n".join(lines)
