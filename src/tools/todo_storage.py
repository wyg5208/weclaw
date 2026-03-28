"""待办事项与每日任务持久化存储 — 基于 SQLite 的任务存储。

功能:
1. 待办事项（todos）CRUD 操作
2. 每日任务（daily_tasks）CRUD 操作
3. 每日推荐（daily_recommendations）管理
4. 多条件筛选与排序

数据模型：
- Todo: 待办事项（短期/中期/远期）
- DailyTask: 每日任务（从待办事项提取或临时创建）
- DailyRecommendation: 每日任务推荐记录
"""

from __future__ import annotations

import calendar
import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date as _date
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)

# 默认数据库路径
_DEFAULT_DB = Path.home() / ".winclaw" / "winclaw_tools.db"


# ----------------------------------------------------------------------
# 工具函数
# ----------------------------------------------------------------------

def compute_time_frame(start_date: str | None) -> str | None:
    """根据起始日期动态计算 time_frame（相对于今天）。

    Args:
        start_date: ISO日期字符串，如 "2026-03-28" 或 "2026-03-28 10:00"

    Returns:
        time_frame 字符串 (today/week/month/quarter/year/future)；
        如果 start_date 为空或无法解析则返回 None。
    """
    if not start_date:
        return None
    try:
        d = _date.fromisoformat(str(start_date)[:10])
    except (ValueError, TypeError):
        return None

    today = _date.today()

    # 今天或过去（已过期/今日待办）
    if d <= today:
        return "today"

    # 本周结束（周日）
    days_to_week_end = 6 - today.weekday()
    week_end = today + timedelta(days=days_to_week_end)
    if d <= week_end:
        return "week"

    # 本月最后一天
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]
    month_end = today.replace(day=last_day_of_month)
    if d <= month_end:
        return "month"

    # 本季度最后一天
    quarter_end_month = ((today.month - 1) // 3 + 1) * 3
    last_day_of_quarter = calendar.monthrange(today.year, quarter_end_month)[1]
    quarter_end = _date(today.year, quarter_end_month, last_day_of_quarter)
    if d <= quarter_end:
        return "quarter"

    # 今年最后一天
    if d.year == today.year:
        return "year"

    return "future"


# ----------------------------------------------------------------------
# 枚举定义
# ----------------------------------------------------------------------

class TodoStatus(str, Enum):
    """待办事项状态。"""
    PENDING = "pending"           # 待办
    IN_PROGRESS = "in_progress"   # 进行中
    COMPLETED = "completed"       # 已完成
    CANCELLED = "cancelled"       # 已取消
    PAUSED = "paused"             # 已中止


class TimeFrame(str, Enum):
    """时间周期分类。"""
    TODAY = "today"       # 今日
    WEEK = "week"         # 本周
    MONTH = "month"       # 本月
    QUARTER = "quarter"   # 本季度
    YEAR = "year"         # 今年
    FUTURE = "future"     # 未来


class TaskCategory(str, Enum):
    """任务类型。"""
    WORK = "work"           # 工作
    STUDY = "study"         # 学习
    HEALTH = "health"       # 健康
    FAMILY = "family"       # 家庭
    SOCIAL = "social"       # 社交
    FINANCE = "finance"     # 财务
    HOBBY = "hobby"         # 爱好
    GENERAL = "general"     # 通用
    OTHER = "other"         # 其他


class RecurrenceType(str, Enum):
    """重复规则。"""
    NONE = "none"           # 不重复
    DAILY = "daily"         # 每天
    WEEKLY = "weekly"       # 每周
    MONTHLY = "monthly"     # 每月
    YEARLY = "yearly"       # 每年
    CUSTOM = "custom"       # 自定义


class RecommendationStatus(str, Enum):
    """推荐状态。"""
    PENDING = "pending"     # 待推送
    PUSHED = "pushed"       # 已推送
    ACCEPTED = "accepted"   # 已接受
    MODIFIED = "modified"   # 已修改


# ----------------------------------------------------------------------
# 数据类定义
# ----------------------------------------------------------------------

@dataclass
class Todo:
    """待办事项数据模型。"""
    id: int | None = None
    title: str = ""
    description: str = ""
    category: TaskCategory = TaskCategory.GENERAL
    time_frame: TimeFrame = TimeFrame.FUTURE
    priority: int = 3  # 1-5, 1最高

    # 时间信息
    start_date: str | None = None       # YYYY-MM-DD
    start_time: str | None = None       # HH:MM
    end_date: str | None = None         # YYYY-MM-DD
    end_time: str | None = None         # HH:MM
    deadline: str | None = None         # ISO格式或YYYY-MM-DD HH:MM

    # 状态与进度
    status: TodoStatus = TodoStatus.PENDING
    progress: int = 0  # 0-100

    # 关联信息
    related_members: list[int] = field(default_factory=list)  # 家庭成员ID列表
    assignee: str = ""                  # 执行人
    parent_id: int | None = None        # 父任务ID

    # 智能推荐相关
    ai_suggested: bool = False
    ai_reason: str = ""
    recurrence: RecurrenceType = RecurrenceType.NONE

    # 元数据
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "time_frame": self.time_frame.value,
            "priority": self.priority,
            "start_date": self.start_date,
            "start_time": self.start_time,
            "end_date": self.end_date,
            "end_time": self.end_time,
            "deadline": self.deadline,
            "status": self.status.value,
            "progress": self.progress,
            "related_members": self.related_members,
            "assignee": self.assignee,
            "parent_id": self.parent_id,
            "ai_suggested": self.ai_suggested,
            "ai_reason": self.ai_reason,
            "recurrence": self.recurrence.value,
            "tags": self.tags,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    @classmethod
    def from_row(cls, row: tuple) -> Todo:
        """从数据库行创建对象。"""
        return cls(
            id=row[0],
            title=row[1] or "",
            description=row[2] or "",
            category=TaskCategory(row[3]) if row[3] else TaskCategory.GENERAL,
            time_frame=TimeFrame(row[4]) if row[4] else TimeFrame.FUTURE,
            priority=row[5] or 3,
            start_date=row[6],
            start_time=row[7],
            end_date=row[8],
            end_time=row[9],
            deadline=row[10],
            status=TodoStatus(row[11]) if row[11] else TodoStatus.PENDING,
            progress=row[12] or 0,
            related_members=json.loads(row[13]) if row[13] else [],
            assignee=row[14] or "",
            parent_id=row[15],
            ai_suggested=bool(row[16]),
            ai_reason=row[17] or "",
            recurrence=RecurrenceType(row[18]) if row[18] else RecurrenceType.NONE,
            tags=json.loads(row[19]) if row[19] else [],
            notes=row[20] or "",
            created_at=datetime.fromisoformat(row[21]) if row[21] else datetime.now(),
            updated_at=datetime.fromisoformat(row[22]) if row[22] else datetime.now(),
            completed_at=datetime.fromisoformat(row[23]) if row[23] else None,
        )

    def get_effective_time_frame(self) -> str:
        """动态计算有效时间周期。

        优先使用 start_date 推算；若无 start_date 则沿用存储的 time_frame。
        这确保随着时间推移，任务分类始终准确反映其与今天的时间关系。
        """
        computed = compute_time_frame(self.start_date)
        if computed is not None:
            return computed
        return self.time_frame.value


@dataclass
class DailyTask:
    """每日任务数据模型。"""
    id: int | None = None
    todo_id: int | None = None          # 关联的待办事项ID
    task_date: str = ""                 # YYYY-MM-DD

    # 任务信息
    title: str = ""
    description: str = ""
    category: TaskCategory = TaskCategory.GENERAL
    priority: int = 3

    # 时间安排
    scheduled_start: str | None = None  # HH:MM
    scheduled_end: str | None = None    # HH:MM
    actual_start: str | None = None     # HH:MM
    actual_end: str | None = None       # HH:MM

    # 状态
    status: TodoStatus = TodoStatus.PENDING
    completion_note: str = ""

    # 推荐来源
    source: str = "manual"              # manual/ai_suggested/from_todo
    ai_confidence: float = 0.0          # 0-1
    ai_reason: str = ""

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "todo_id": self.todo_id,
            "task_date": self.task_date,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority,
            "scheduled_start": self.scheduled_start,
            "scheduled_end": self.scheduled_end,
            "actual_start": self.actual_start,
            "actual_end": self.actual_end,
            "status": self.status.value,
            "completion_note": self.completion_note,
            "source": self.source,
            "ai_confidence": self.ai_confidence,
            "ai_reason": self.ai_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_row(cls, row: tuple) -> DailyTask:
        """从数据库行创建对象。"""
        return cls(
            id=row[0],
            todo_id=row[1],
            task_date=row[2] or "",
            title=row[3] or "",
            description=row[4] or "",
            category=TaskCategory(row[5]) if row[5] else TaskCategory.GENERAL,
            priority=row[6] or 3,
            scheduled_start=row[7],
            scheduled_end=row[8],
            actual_start=row[9],
            actual_end=row[10],
            status=TodoStatus(row[11]) if row[11] else TodoStatus.PENDING,
            completion_note=row[12] or "",
            source=row[13] or "manual",
            ai_confidence=row[14] or 0.0,
            ai_reason=row[15] or "",
            created_at=datetime.fromisoformat(row[16]) if row[16] else datetime.now(),
            updated_at=datetime.fromisoformat(row[17]) if row[17] else datetime.now(),
        )


@dataclass
class DailyRecommendation:
    """每日任务推荐记录。"""
    id: int | None = None
    task_date: str = ""                 # YYYY-MM-DD
    generated_at: datetime = field(default_factory=datetime.now)
    pushed_at: datetime | None = None
    status: RecommendationStatus = RecommendationStatus.PENDING

    # 推荐内容
    recommendations: list[dict] = field(default_factory=list)  # 推荐任务列表
    analysis_summary: str = ""

    # 用户反馈
    user_feedback: str = ""
    accepted_count: int = 0
    modified_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "id": self.id,
            "task_date": self.task_date,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "pushed_at": self.pushed_at.isoformat() if self.pushed_at else None,
            "status": self.status.value,
            "recommendations": self.recommendations,
            "analysis_summary": self.analysis_summary,
            "user_feedback": self.user_feedback,
            "accepted_count": self.accepted_count,
            "modified_count": self.modified_count,
        }

    @classmethod
    def from_row(cls, row: tuple) -> DailyRecommendation:
        """从数据库行创建对象。"""
        return cls(
            id=row[0],
            task_date=row[1] or "",
            generated_at=datetime.fromisoformat(row[2]) if row[2] else datetime.now(),
            pushed_at=datetime.fromisoformat(row[3]) if row[3] else None,
            status=RecommendationStatus(row[4]) if row[4] else RecommendationStatus.PENDING,
            recommendations=json.loads(row[5]) if row[5] else [],
            analysis_summary=row[6] or "",
            user_feedback=row[7] or "",
            accepted_count=row[8] or 0,
            modified_count=row[9] or 0,
        )


# ----------------------------------------------------------------------
# 存储类
# ----------------------------------------------------------------------

class TodoStorage:
    """待办事项与每日任务持久化存储。"""

    def __init__(self, db_path: Path | str | None = None):
        """初始化存储。

        Args:
            db_path: 数据库文件路径，为空时使用默认路径 ~/.winclaw/winclaw_tools.db
        """
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        """获取数据库连接。"""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self) -> None:
        """初始化数据库表。"""
        with self._conn() as conn:
            # 待办事项表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL DEFAULT 'general',
                    time_frame TEXT NOT NULL DEFAULT 'future',
                    priority INTEGER DEFAULT 3,

                    start_date TEXT,
                    start_time TEXT,
                    end_date TEXT,
                    end_time TEXT,
                    deadline TEXT,

                    status TEXT DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,

                    related_members TEXT,
                    assignee TEXT,
                    parent_id INTEGER,

                    ai_suggested INTEGER DEFAULT 0,
                    ai_reason TEXT,
                    recurrence TEXT DEFAULT 'none',

                    tags TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,

                    FOREIGN KEY (parent_id) REFERENCES todos(id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_todos_status ON todos(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_todos_time_frame ON todos(time_frame)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_todos_category ON todos(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_todos_deadline ON todos(deadline)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_todos_parent_id ON todos(parent_id)")

            # 每日任务表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    todo_id INTEGER,
                    task_date TEXT NOT NULL,

                    title TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    priority INTEGER,

                    scheduled_start TEXT,
                    scheduled_end TEXT,
                    actual_start TEXT,
                    actual_end TEXT,

                    status TEXT DEFAULT 'pending',
                    completion_note TEXT,

                    source TEXT DEFAULT 'manual',
                    ai_confidence REAL,
                    ai_reason TEXT,

                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,

                    FOREIGN KEY (todo_id) REFERENCES todos(id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_tasks_date ON daily_tasks(task_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_tasks_status ON daily_tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_tasks_todo_id ON daily_tasks(todo_id)")

            # 每日任务推荐记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_date TEXT NOT NULL UNIQUE,
                    generated_at TEXT NOT NULL,
                    pushed_at TEXT,
                    status TEXT DEFAULT 'pending',

                    recommendations TEXT NOT NULL,
                    analysis_summary TEXT,

                    user_feedback TEXT,
                    accepted_count INTEGER DEFAULT 0,
                    modified_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_rec_date ON daily_recommendations(task_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_rec_status ON daily_recommendations(status)")

            conn.commit()

    # ------------------------------------------------------------------
    # 待办事项 CRUD
    # ------------------------------------------------------------------

    def create_todo(self, todo: Todo) -> int:
        """创建待办事项。

        Args:
            todo: 待办事项对象

        Returns:
            新创建的记录ID
        """
        now = datetime.now().isoformat()
        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO todos (
                    title, description, category, time_frame, priority,
                    start_date, start_time, end_date, end_time, deadline,
                    status, progress, related_members, assignee, parent_id,
                    ai_suggested, ai_reason, recurrence, tags, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                todo.title, todo.description, todo.category.value, todo.time_frame.value, todo.priority,
                todo.start_date, todo.start_time, todo.end_date, todo.end_time, todo.deadline,
                todo.status.value, todo.progress,
                json.dumps(todo.related_members), todo.assignee, todo.parent_id,
                int(todo.ai_suggested), todo.ai_reason, todo.recurrence.value,
                json.dumps(todo.tags), todo.notes,
                now, now
            ))
            conn.commit()
            return cursor.lastrowid

    def get_todo(self, todo_id: int) -> Todo | None:
        """获取单个待办事项。"""
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
            if row:
                return Todo.from_row(tuple(row))
            return None

    def list_todos(
        self,
        time_frame: str | None = None,
        category: str | None = None,
        status: str | None = None,
        priority: int | None = None,
        assignee: str | None = None,
        parent_id: int | None = None,
        search: str | None = None,
        include_completed: bool = False,
        limit: int = 100,
    ) -> list[Todo]:
        """列出待办事项（支持多条件筛选）。

        time_frame 筛选使用动态计算（基于 start_date），确保分类随时间自动更新。
        """
        query = "SELECT * FROM todos WHERE 1=1"
        params: list[Any] = []

        # time_frame 改为 Python 侧动态筛选，不写入 SQL，避免静态值失效
        if category:
            query += " AND category = ?"
            params.append(category)
        if status:
            query += " AND status = ?"
            params.append(status)
        elif not include_completed:
            query += " AND status != 'completed'"
        if priority is not None:
            query += " AND priority = ?"
            params.append(priority)
        if assignee:
            query += " AND assignee = ?"
            params.append(assignee)
        if parent_id is not None:
            query += " AND parent_id = ?"
            params.append(parent_id)
        if search:
            query += " AND (title LIKE ? OR description LIKE ? OR notes LIKE ?)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        query += " ORDER BY priority ASC, start_date ASC, created_at DESC"

        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            todos = [Todo.from_row(tuple(row)) for row in rows]

        # 动态 time_frame 筛选：基于 get_effective_time_frame()
        if time_frame:
            todos = [t for t in todos if t.get_effective_time_frame() == time_frame]

        return todos[:limit]

    def update_todo(self, todo_id: int, updates: dict[str, Any]) -> bool:
        """更新待办事项。"""
        if not updates:
            return False

        # 构建更新语句
        set_clauses = []
        params = []

        field_mapping = {
            "title": "title",
            "description": "description",
            "category": "category",
            "time_frame": "time_frame",
            "priority": "priority",
            "start_date": "start_date",
            "start_time": "start_time",
            "end_date": "end_date",
            "end_time": "end_time",
            "deadline": "deadline",
            "status": "status",
            "progress": "progress",
            "related_members": "related_members",
            "assignee": "assignee",
            "parent_id": "parent_id",
            "ai_suggested": "ai_suggested",
            "ai_reason": "ai_reason",
            "recurrence": "recurrence",
            "tags": "tags",
            "notes": "notes",
            "completed_at": "completed_at",
        }

        for key, value in updates.items():
            if key in field_mapping:
                set_clauses.append(f"{field_mapping[key]} = ?")
                # 处理特殊字段
                if key in ("related_members", "tags"):
                    params.append(json.dumps(value) if isinstance(value, list) else value)
                elif key in ("category", "time_frame", "status", "recurrence"):
                    params.append(value.value if hasattr(value, "value") else value)
                elif key == "ai_suggested":
                    params.append(int(value))
                else:
                    params.append(value)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(todo_id)

        with self._conn() as conn:
            conn.execute(f"UPDATE todos SET {', '.join(set_clauses)} WHERE id = ?", params)
            conn.commit()
            return True

    def delete_todo(self, todo_id: int) -> bool:
        """删除待办事项。"""
        with self._conn() as conn:
            # 同时删除关联的每日任务
            conn.execute("DELETE FROM daily_tasks WHERE todo_id = ?", (todo_id,))
            conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            conn.commit()
            return True

    def complete_todo(self, todo_id: int, completion_note: str = "") -> bool:
        """完成待办事项。"""
        now = datetime.now()
        return self.update_todo(todo_id, {
            "status": TodoStatus.COMPLETED,
            "progress": 100,
            "completed_at": now.isoformat(),
            "notes": completion_note,
        })

    def cancel_todo(self, todo_id: int, reason: str = "") -> bool:
        """取消待办事项。"""
        return self.update_todo(todo_id, {
            "status": TodoStatus.CANCELLED,
            "notes": reason,
        })

    def get_overdue_todos(self) -> list[Todo]:
        """获取过期未完成任务。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM todos
                WHERE status IN ('pending', 'in_progress')
                AND deadline IS NOT NULL
                AND deadline < ?
                ORDER BY deadline ASC
            """, (now,)).fetchall()
            return [Todo.from_row(tuple(row)) for row in rows]

    def get_upcoming_todos(self, days: int = 7) -> list[Todo]:
        """获取即将到期任务。"""
        now = datetime.now()
        end_date = (now + timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        now_str = now.strftime("%Y-%m-%d %H:%M")

        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM todos
                WHERE status IN ('pending', 'in_progress')
                AND deadline IS NOT NULL
                AND deadline >= ? AND deadline <= ?
                ORDER BY deadline ASC
            """, (now_str, end_date)).fetchall()
            return [Todo.from_row(tuple(row)) for row in rows]

    def get_sub_todos(self, parent_id: int) -> list[Todo]:
        """获取子任务列表。"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM todos WHERE parent_id = ? ORDER BY priority ASC, created_at ASC",
                (parent_id,)
            ).fetchall()
            return [Todo.from_row(tuple(row)) for row in rows]

    # ------------------------------------------------------------------
    # 每日任务 CRUD
    # ------------------------------------------------------------------

    def create_daily_task(self, task: DailyTask) -> int:
        """创建每日任务。"""
        now = datetime.now().isoformat()
        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO daily_tasks (
                    todo_id, task_date, title, description, category, priority,
                    scheduled_start, scheduled_end, actual_start, actual_end,
                    status, completion_note, source, ai_confidence, ai_reason,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.todo_id, task.task_date, task.title, task.description,
                task.category.value if task.category else None, task.priority,
                task.scheduled_start, task.scheduled_end, task.actual_start, task.actual_end,
                task.status.value, task.completion_note,
                task.source, task.ai_confidence, task.ai_reason,
                now, now
            ))
            conn.commit()
            return cursor.lastrowid

    def get_daily_task(self, task_id: int) -> DailyTask | None:
        """获取单个每日任务。"""
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM daily_tasks WHERE id = ?", (task_id,)).fetchone()
            if row:
                return DailyTask.from_row(tuple(row))
            return None

    def get_daily_tasks(self, date: str) -> list[DailyTask]:
        """获取某日的所有任务。"""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM daily_tasks WHERE task_date = ? ORDER BY scheduled_start ASC, priority ASC",
                (date,)
            ).fetchall()
            return [DailyTask.from_row(tuple(row)) for row in rows]

    def update_daily_task(self, task_id: int, updates: dict[str, Any]) -> bool:
        """更新每日任务。"""
        if not updates:
            return False

        set_clauses = []
        params = []

        field_mapping = {
            "title": "title",
            "description": "description",
            "category": "category",
            "priority": "priority",
            "scheduled_start": "scheduled_start",
            "scheduled_end": "scheduled_end",
            "actual_start": "actual_start",
            "actual_end": "actual_end",
            "status": "status",
            "completion_note": "completion_note",
            "source": "source",
            "ai_confidence": "ai_confidence",
            "ai_reason": "ai_reason",
        }

        for key, value in updates.items():
            if key in field_mapping:
                set_clauses.append(f"{field_mapping[key]} = ?")
                if key in ("category", "status"):
                    params.append(value.value if hasattr(value, "value") else value)
                else:
                    params.append(value)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(task_id)

        with self._conn() as conn:
            conn.execute(f"UPDATE daily_tasks SET {', '.join(set_clauses)} WHERE id = ?", params)
            conn.commit()
            return True

    def delete_daily_task(self, task_id: int) -> bool:
        """删除每日任务。"""
        with self._conn() as conn:
            conn.execute("DELETE FROM daily_tasks WHERE id = ?", (task_id,))
            conn.commit()
            return True

    def get_today_summary(self) -> dict[str, Any]:
        """获取今日任务摘要。"""
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = self.get_daily_tasks(today)

        pending = sum(1 for t in tasks if t.status == TodoStatus.PENDING)
        in_progress = sum(1 for t in tasks if t.status == TodoStatus.IN_PROGRESS)
        completed = sum(1 for t in tasks if t.status == TodoStatus.COMPLETED)
        cancelled = sum(1 for t in tasks if t.status == TodoStatus.CANCELLED)

        return {
            "date": today,
            "total": len(tasks),
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "cancelled": cancelled,
            "completion_rate": round(completed / len(tasks) * 100, 1) if tasks else 0,
        }

    # ------------------------------------------------------------------
    # 每日推荐管理
    # ------------------------------------------------------------------

    def create_recommendation(self, rec: DailyRecommendation) -> int:
        """创建每日推荐记录。"""
        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO daily_recommendations (
                    task_date, generated_at, pushed_at, status,
                    recommendations, analysis_summary,
                    user_feedback, accepted_count, modified_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.task_date, rec.generated_at.isoformat(),
                rec.pushed_at.isoformat() if rec.pushed_at else None,
                rec.status.value,
                json.dumps(rec.recommendations), rec.analysis_summary,
                rec.user_feedback, rec.accepted_count, rec.modified_count
            ))
            conn.commit()
            return cursor.lastrowid

    def get_recommendation(self, date: str) -> DailyRecommendation | None:
        """获取某日的推荐记录。"""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM daily_recommendations WHERE task_date = ?", (date,)
            ).fetchone()
            if row:
                return DailyRecommendation.from_row(tuple(row))
            return None

    def update_recommendation_status(self, date: str, status: RecommendationStatus) -> bool:
        """更新推荐状态。"""
        now = datetime.now().isoformat()
        with self._conn() as conn:
            if status == RecommendationStatus.PUSHED:
                conn.execute(
                    "UPDATE daily_recommendations SET status = ?, pushed_at = ? WHERE task_date = ?",
                    (status.value, now, date)
                )
            else:
                conn.execute(
                    "UPDATE daily_recommendations SET status = ? WHERE task_date = ?",
                    (status.value, date)
                )
            conn.commit()
            return True

    # ------------------------------------------------------------------
    # 统计信息
    # ------------------------------------------------------------------

    def get_statistics(self) -> dict[str, Any]:
        """获取任务统计信息。"""
        with self._conn() as conn:
            total_todos = conn.execute("SELECT COUNT(*) FROM todos").fetchone()[0]
            pending_todos = conn.execute(
                "SELECT COUNT(*) FROM todos WHERE status = 'pending'"
            ).fetchone()[0]
            completed_todos = conn.execute(
                "SELECT COUNT(*) FROM todos WHERE status = 'completed'"
            ).fetchone()[0]
            overdue_todos = len(self.get_overdue_todos())

            return {
                "total_todos": total_todos,
                "pending_todos": pending_todos,
                "completed_todos": completed_todos,
                "overdue_todos": overdue_todos,
            }
