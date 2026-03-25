"""家庭大事记工具 — 家庭重大事件、纪念日、议程管理。

支持动作：
- create_milestone: 创建大事记
- query_milestones: 查询大事记（多条件筛选）
- update_milestone: 更新大事记
- delete_milestone: 删除大事记
- get_timeline: 获取时间线展示（6种模板风格）
- get_upcoming: 获取即将到来的事件
- get_statistics: 统计概览
- export_timeline: 导出时间线

存储位置：~/.weclaw/weclaw_tools.db 的 family_milestones 表
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generator

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# 默认数据库路径
_DEFAULT_DB = Path.home() / ".weclaw" / "weclaw_tools.db"

# 事件类型映射
MILESTONE_TYPES = {
    "anniversary": "纪念日",
    "celebration": "庆典活动",
    "milestone": "人生里程碑",
    "agenda": "重要议程",
    "achievement": "成就荣誉",
    "memory": "珍贵回忆",
    "other": "其他事件",
}

# 事件类型图标
MILESTONE_ICONS = {
    "anniversary": "💕",
    "celebration": "🎉",
    "milestone": "🎯",
    "agenda": "📋",
    "achievement": "🏆",
    "memory": "📸",
    "other": "📌",
}

# 重要级别图标
IMPORTANCE_ICONS = {
    1: "⭐",
    2: "⭐⭐",
    3: "⭐⭐⭐",
    4: "⭐⭐⭐⭐",
    5: "⭐⭐⭐⭐⭐",
}

# 展示模板风格
TEMPLATE_STYLES = ["timeline", "card", "calendar", "album", "list", "annual"]


class FamilyMilestoneTool(BaseTool):
    """家庭大事记管理工具。

    提供家庭重大事件、纪念日、议程的完整管理功能。
    支持6种展示模板风格。
    """

    name = "family_milestone"
    emoji = "🎊"
    title = "家庭大事记"
    description = "记录家庭重大事件、纪念日、议程，支持多种展示模板"

    def __init__(self, db_path: str = ""):
        super().__init__()
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self._db_path))
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS family_milestones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    event_date TEXT NOT NULL,
                    end_date TEXT,
                    event_type TEXT NOT NULL,
                    importance_level INTEGER DEFAULT 3,
                    related_members TEXT DEFAULT '[]',
                    location TEXT,
                    cover_image TEXT,
                    photos TEXT DEFAULT '[]',
                    tags TEXT DEFAULT '[]',
                    is_annual INTEGER DEFAULT 0,
                    reminder_days TEXT DEFAULT '[]',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_milestones_date
                ON family_milestones(event_date DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_milestones_type
                ON family_milestones(event_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_milestones_annual
                ON family_milestones(is_annual)
            """)
            conn.commit()

    # ------------------------------------------------------------------
    # Action 定义
    # ------------------------------------------------------------------

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="create_milestone",
                description="创建新的家庭大事记",
                parameters={
                    "title": {
                        "type": "string",
                        "description": "事件标题",
                    },
                    "event_date": {
                        "type": "string",
                        "description": "事件日期 YYYY-MM-DD（开始日期）",
                    },
                    "event_type": {
                        "type": "string",
                        "description": "事件类型：anniversary(纪念日)/celebration(庆典)/milestone(里程碑)/agenda(议程)/achievement(成就)/memory(回忆)/other(其他)",
                        "enum": list(MILESTONE_TYPES.keys()),
                    },
                    "description": {
                        "type": "string",
                        "description": "详细描述（可选）",
                    },
                    "importance_level": {
                        "type": "integer",
                        "description": "重要级别 1-5（可选，默认 3）",
                    },
                    "related_members": {
                        "type": "string",
                        "description": "关联成员名称，多个用逗号分隔（可选）",
                    },
                    "location": {
                        "type": "string",
                        "description": "地点（可选）",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期 YYYY-MM-DD（可选，支持跨日事件如旅行）",
                    },
                    "is_annual": {
                        "type": "boolean",
                        "description": "是否年度重复（纪念日类型默认为 true）",
                    },
                    "reminder_days": {
                        "type": "string",
                        "description": "提前提醒天数，多个用逗号分隔，如 '7,3,1'（可选）",
                    },
                    "tags": {
                        "type": "string",
                        "description": "自定义标签，多个用逗号分隔（可选）",
                    },
                    "cover_image": {
                        "type": "string",
                        "description": "封面图片路径（可选）",
                    },
                    "notes": {
                        "type": "string",
                        "description": "备注信息（可选）",
                    },
                },
                required_params=["title", "event_date", "event_type"],
            ),
            ActionDef(
                name="query_milestones",
                description="查询家庭大事记，支持多条件筛选",
                parameters={
                    "milestone_id": {
                        "type": "integer",
                        "description": "事件 ID（指定则返回详情）",
                    },
                    "date_range": {
                        "type": "string",
                        "description": "时间范围：today/week/month/year/all（可选，默认 all）",
                    },
                    "event_type": {
                        "type": "string",
                        "description": "按事件类型筛选（可选）",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词（可选）",
                    },
                    "related_member": {
                        "type": "string",
                        "description": "按关联成员筛选（可选）",
                    },
                    "year": {
                        "type": "integer",
                        "description": "按年份筛选（可选）",
                    },
                    "month": {
                        "type": "integer",
                        "description": "按月份筛选 1-12（可选）",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量，默认 20（可选）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="update_milestone",
                description="更新家庭大事记",
                parameters={
                    "milestone_id": {
                        "type": "integer",
                        "description": "事件 ID",
                    },
                    "title": {
                        "type": "string",
                        "description": "新标题（可选）",
                    },
                    "description": {
                        "type": "string",
                        "description": "新描述（可选）",
                    },
                    "event_date": {
                        "type": "string",
                        "description": "新日期（可选）",
                    },
                    "event_type": {
                        "type": "string",
                        "description": "新类型（可选）",
                    },
                    "importance_level": {
                        "type": "integer",
                        "description": "新重要级别（可选）",
                    },
                    "related_members": {
                        "type": "string",
                        "description": "新关联成员（可选）",
                    },
                    "location": {
                        "type": "string",
                        "description": "新地点（可选）",
                    },
                    "is_annual": {
                        "type": "boolean",
                        "description": "是否年度重复（可选）",
                    },
                    "tags": {
                        "type": "string",
                        "description": "新标签（可选）",
                    },
                    "notes": {
                        "type": "string",
                        "description": "新备注（可选）",
                    },
                },
                required_params=["milestone_id"],
            ),
            ActionDef(
                name="delete_milestone",
                description="删除家庭大事记",
                parameters={
                    "milestone_id": {
                        "type": "integer",
                        "description": "事件 ID",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "确认删除（必须为 true）",
                    },
                },
                required_params=["milestone_id", "confirm"],
            ),
            ActionDef(
                name="get_timeline",
                description="获取时间线展示，支持6种模板风格",
                parameters={
                    "start_date": {
                        "type": "string",
                        "description": "开始日期（可选）",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期（可选）",
                    },
                    "style": {
                        "type": "string",
                        "description": "展示风格：timeline(时间线)/card(卡片)/calendar(日历)/album(相册)/list(列表)/annual(年度报告)",
                        "enum": TEMPLATE_STYLES,
                    },
                    "event_type": {
                        "type": "string",
                        "description": "按类型筛选（可选）",
                    },
                    "year": {
                        "type": "integer",
                        "description": "指定年份（可选）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="get_upcoming",
                description="获取即将到来的事件（纪念日、议程等）",
                parameters={
                    "days": {
                        "type": "integer",
                        "description": "未来多少天，默认 30",
                    },
                    "include_annual": {
                        "type": "boolean",
                        "description": "是否包含年度纪念日，默认 true",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="get_statistics",
                description="获取大事记统计概览",
                parameters={
                    "year": {
                        "type": "integer",
                        "description": "统计年份，默认当年",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="export_timeline",
                description="导出时间线为文件",
                parameters={
                    "format": {
                        "type": "string",
                        "description": "导出格式：md/html/json",
                    },
                    "style": {
                        "type": "string",
                        "description": "展示风格（可选）",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "开始日期（可选）",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "结束日期（可选）",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "输出文件路径（可选，默认 generated 目录）",
                    },
                },
                required_params=["format"],
            ),
        ]

    # ------------------------------------------------------------------
    # Action 实现
    # ------------------------------------------------------------------

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        action_map = {
            "create_milestone": self._create_milestone,
            "query_milestones": self._query_milestones,
            "update_milestone": self._update_milestone,
            "delete_milestone": self._delete_milestone,
            "get_timeline": self._get_timeline,
            "get_upcoming": self._get_upcoming,
            "get_statistics": self._get_statistics,
            "export_timeline": self._export_timeline,
        }

        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未知操作：{action}",
            )

        try:
            return handler(params)
        except Exception as e:
            logger.error("大事记操作失败: %s", e)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"执行失败：{str(e)}",
            )

    def _create_milestone(self, params: dict[str, Any]) -> ToolResult:
        title = params.get("title", "").strip()
        event_date = params.get("event_date", "").strip()
        event_type = params.get("event_type", "").strip()

        # 参数验证
        if not title:
            return ToolResult(status=ToolResultStatus.ERROR, error="标题不能为空")
        if not event_date:
            return ToolResult(status=ToolResultStatus.ERROR, error="日期不能为空")
        if not event_type:
            return ToolResult(status=ToolResultStatus.ERROR, error="事件类型不能为空")

        # 验证日期格式
        try:
            datetime.strptime(event_date, "%Y-%m-%d")
        except ValueError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="日期格式错误，请使用 YYYY-MM-DD",
            )

        # 验证事件类型
        if event_type not in MILESTONE_TYPES:
            valid_types = ", ".join(MILESTONE_TYPES.keys())
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无效的事件类型。有效值：{valid_types}",
            )

        # 验证结束日期
        end_date = params.get("end_date", "").strip() or None
        if end_date:
            try:
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="结束日期格式错误，请使用 YYYY-MM-DD",
                )

        # 处理重要级别
        importance_level = params.get("importance_level", 3)
        if not isinstance(importance_level, int) or not 1 <= importance_level <= 5:
            importance_level = 3

        # 处理关联成员
        related_members_str = params.get("related_members", "")
        related_members = []
        if related_members_str:
            related_members = [m.strip() for m in related_members_str.split(",") if m.strip()]

        # 处理标签
        tags_str = params.get("tags", "")
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []

        # 处理提醒天数
        reminder_str = params.get("reminder_days", "")
        reminder_days = []
        if reminder_str:
            try:
                reminder_days = [int(d.strip()) for d in reminder_str.split(",") if d.strip().isdigit()]
            except ValueError:
                reminder_days = []

        # 纪念日类型默认年度重复
        is_annual = params.get("is_annual")
        if is_annual is None:
            is_annual = 1 if event_type == "anniversary" else 0
        else:
            is_annual = 1 if is_annual else 0

        now = datetime.now()
        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO family_milestones (
                    title, description, event_date, end_date, event_type,
                    importance_level, related_members, location, cover_image,
                    photos, tags, is_annual, reminder_days, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                params.get("description", "").strip() or None,
                event_date,
                end_date,
                event_type,
                importance_level,
                json.dumps(related_members, ensure_ascii=False),
                params.get("location", "").strip() or None,
                params.get("cover_image", "").strip() or None,
                json.dumps([], ensure_ascii=False),
                json.dumps(tags, ensure_ascii=False),
                is_annual,
                json.dumps(reminder_days, ensure_ascii=False),
                params.get("notes", "").strip() or None,
                now.isoformat(),
                now.isoformat(),
            ))
            conn.commit()
            milestone_id = cursor.lastrowid

        # 格式化输出
        type_display = MILESTONE_TYPES.get(event_type, event_type)
        type_icon = MILESTONE_ICONS.get(event_type, "📌")
        importance_stars = IMPORTANCE_ICONS.get(importance_level, "⭐⭐⭐")

        output_lines = [
            f"✅ 大事记创建成功！(ID: {milestone_id})",
            f"{type_icon} {type_display}",
            f"📝 {title}",
            f"📅 {event_date}",
            f"{' - ' + end_date if end_date else ''}",
            f"{importance_stars} 重要级别：{importance_level}",
        ]
        if related_members:
            output_lines.append(f"👥 关联成员：{', '.join(related_members)}")
        if params.get("location"):
            output_lines.append(f"📍 地点：{params['location']}")
        if is_annual:
            output_lines.append("🔄 年度重复")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(output_lines),
            data={
                "milestone_id": milestone_id,
                "title": title,
                "event_date": event_date,
                "event_type": event_type,
                "importance_level": importance_level,
                "is_annual": bool(is_annual),
            },
        )

    def _query_milestones(self, params: dict[str, Any]) -> ToolResult:
        milestone_id = params.get("milestone_id")

        # 单条详情查询
        if milestone_id:
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT * FROM family_milestones WHERE id = ?",
                    (milestone_id,),
                ).fetchone()
            if not row:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"大事记不存在: ID {milestone_id}",
                )
            data = self._row_to_dict(row)
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=self._format_detail(data),
                data=data,
            )

        # 多条件查询
        clauses: list[str] = []
        values: list[Any] = []

        date_range = params.get("date_range", "all")
        today = datetime.now()

        if date_range == "today":
            clauses.append("event_date = ?")
            values.append(today.strftime("%Y-%m-%d"))
        elif date_range == "week":
            clauses.append("event_date >= ?")
            values.append((today - timedelta(days=7)).strftime("%Y-%m-%d"))
        elif date_range == "month":
            clauses.append("event_date >= ?")
            values.append((today - timedelta(days=30)).strftime("%Y-%m-%d"))
        elif date_range == "year":
            clauses.append("event_date >= ?")
            values.append((today - timedelta(days=365)).strftime("%Y-%m-%d"))

        if params.get("event_type"):
            clauses.append("event_type = ?")
            values.append(params["event_type"])

        if params.get("keyword"):
            clauses.append("(title LIKE ? OR description LIKE ? OR location LIKE ?)")
            keyword = f"%{params['keyword']}%"
            values.extend([keyword, keyword, keyword])

        if params.get("related_member"):
            clauses.append("related_members LIKE ?")
            values.append(f'%"{params["related_member"]}"%')

        if params.get("year"):
            clauses.append("strftime('%Y', event_date) = ?")
            values.append(str(params["year"]))

        if params.get("month"):
            clauses.append("CAST(strftime('%m', event_date) AS INTEGER) = ?")
            values.append(params["month"])

        where = " AND ".join(clauses) if clauses else "1=1"
        limit = min(params.get("limit", 20), 100)

        sql = f"""
            SELECT * FROM family_milestones
            WHERE {where}
            ORDER BY event_date DESC
            LIMIT ?
        """
        values.append(limit)

        with self._conn() as conn:
            rows = conn.execute(sql, values).fetchall()

        if not rows:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="未找到符合条件的大事记。",
                data={"milestones": [], "count": 0},
            )

        data_list = [self._row_to_dict(row) for row in rows]
        output = self._format_list(data_list)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"milestones": data_list, "count": len(data_list)},
        )

    def _update_milestone(self, params: dict[str, Any]) -> ToolResult:
        milestone_id = params.get("milestone_id")
        if not milestone_id:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少 milestone_id")

        # 检查是否存在
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id FROM family_milestones WHERE id = ?",
                (milestone_id,),
            ).fetchone()
            if not row:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"大事记不存在: ID {milestone_id}",
                )

        updates: dict[str, Any] = {}
        update_fields = [
            "title", "description", "event_date", "end_date", "event_type",
            "importance_level", "location", "cover_image", "notes",
        ]

        for key in update_fields:
            if key in params and params[key]:
                updates[key] = params[key]

        # 特殊字段处理
        if "related_members" in params:
            members = [m.strip() for m in params["related_members"].split(",") if m.strip()]
            updates["related_members"] = json.dumps(members, ensure_ascii=False)

        if "tags" in params:
            tags = [t.strip() for t in params["tags"].split(",") if t.strip()]
            updates["tags"] = json.dumps(tags, ensure_ascii=False)

        if "is_annual" in params:
            updates["is_annual"] = 1 if params["is_annual"] else 0

        if "reminder_days" in params:
            days = [int(d.strip()) for d in params["reminder_days"].split(",") if d.strip().isdigit()]
            updates["reminder_days"] = json.dumps(days, ensure_ascii=False)

        if not updates:
            return ToolResult(status=ToolResultStatus.ERROR, error="没有可更新的字段")

        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [milestone_id]

        with self._conn() as conn:
            conn.execute(
                f"UPDATE family_milestones SET {set_clause} WHERE id = ?",
                values,
            )
            conn.commit()

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已更新大事记 ID:{milestone_id}",
            data={"milestone_id": milestone_id, "updated_fields": list(updates.keys())},
        )

    def _delete_milestone(self, params: dict[str, Any]) -> ToolResult:
        milestone_id = params.get("milestone_id")
        confirm = params.get("confirm", False)

        if not milestone_id:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少 milestone_id")
        if not confirm:
            return ToolResult(status=ToolResultStatus.ERROR, error="需要确认才能删除")

        with self._conn() as conn:
            row = conn.execute(
                "SELECT title, event_date FROM family_milestones WHERE id = ?",
                (milestone_id,),
            ).fetchone()
            if not row:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"大事记不存在: ID {milestone_id}",
                )
            title, event_date = row
            conn.execute("DELETE FROM family_milestones WHERE id = ?", (milestone_id,))
            conn.commit()

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已删除大事记: {title} ({event_date})",
            data={"milestone_id": milestone_id, "deleted": True},
        )

    def _get_timeline(self, params: dict[str, Any]) -> ToolResult:
        style = params.get("style", "timeline")
        year = params.get("year")
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        event_type = params.get("event_type")

        # 构建查询条件
        clauses: list[str] = []
        values: list[Any] = []

        if year:
            clauses.append("strftime('%Y', event_date) = ?")
            values.append(str(year))
        else:
            if start_date:
                clauses.append("event_date >= ?")
                values.append(start_date)
            if end_date:
                clauses.append("event_date <= ?")
                values.append(end_date)

        if event_type:
            clauses.append("event_type = ?")
            values.append(event_type)

        where = " AND ".join(clauses) if clauses else "1=1"

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM family_milestones WHERE {where} ORDER BY event_date DESC",
                values,
            ).fetchall()

        if not rows:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="暂无大事记记录。",
                data={"milestones": [], "count": 0},
            )

        data_list = [self._row_to_dict(row) for row in rows]

        # 根据风格格式化输出
        if style == "timeline":
            output = self._format_timeline(data_list, year)
        elif style == "card":
            output = self._format_card_grid(data_list)
        elif style == "calendar":
            output = self._format_calendar(data_list, year)
        elif style == "album":
            output = self._format_album(data_list)
        elif style == "list":
            output = self._format_simple_list(data_list)
        elif style == "annual":
            output = self._format_annual_report(data_list, year or datetime.now().year)
        else:
            output = self._format_timeline(data_list, year)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"milestones": data_list, "count": len(data_list), "style": style},
        )

    def _get_upcoming(self, params: dict[str, Any]) -> ToolResult:
        days = params.get("days", 30)
        include_annual = params.get("include_annual", True)
        today = datetime.now().date()
        end_date = today + timedelta(days=days)

        results = []

        with self._conn() as conn:
            # 查询未来的单次事件
            rows = conn.execute("""
                SELECT * FROM family_milestones
                WHERE is_annual = 0 AND event_date >= ?
                ORDER BY event_date ASC
            """, (today.strftime("%Y-%m-%d"),)).fetchall()

            for row in rows:
                data = self._row_to_dict(row)
                event_dt = datetime.strptime(data["event_date"], "%Y-%m-%d").date()
                if event_dt <= end_date:
                    data["days_until"] = (event_dt - today).days
                    results.append(data)

            # 查询年度纪念日
            if include_annual:
                rows = conn.execute("""
                    SELECT * FROM family_milestones
                    WHERE is_annual = 1
                    ORDER BY event_date ASC
                """).fetchall()

                for row in rows:
                    data = self._row_to_dict(row)
                    next_date = self._get_next_anniversary_date(data["event_date"])
                    if next_date and today <= next_date <= end_date:
                        data["next_date"] = next_date.strftime("%Y-%m-%d")
                        data["days_until"] = (next_date - today).days
                        results.append(data)

        # 按剩余天数排序
        results.sort(key=lambda x: x.get("days_until", 999))

        if not results:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"未来 {days} 天内没有即将到来的事件。",
                data={"upcoming": [], "count": 0},
            )

        # 格式化输出
        lines = [f"📅 未来 {days} 天内即将到来的事件：", "━" * 50]
        for item in results:
            days_until = item.get("days_until", 0)
            type_icon = MILESTONE_ICONS.get(item.get("event_type", "other"), "📌")
            if days_until == 0:
                lines.append(f"🔴 今天！{type_icon} {item['title']}")
            elif days_until == 1:
                lines.append(f"🟠 明天 {type_icon} {item['title']}")
            else:
                lines.append(f"🟢 {days_until}天后 {type_icon} {item['title']}")
            lines.append(f"    📆 {item.get('next_date') or item['event_date']}")
            if item.get("location"):
                lines.append(f"    📍 {item['location']}")

        lines.append(f"\n📊 共 {len(results)} 个即将到来")
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"upcoming": results, "count": len(results)},
        )

    def _get_statistics(self, params: dict[str, Any]) -> ToolResult:
        year = params.get("year", datetime.now().year)

        with self._conn() as conn:
            # 总数统计
            total = conn.execute(
                "SELECT COUNT(*) FROM family_milestones WHERE strftime('%Y', event_date) = ?",
                (str(year),),
            ).fetchone()[0]

            # 按类型统计
            type_stats = conn.execute("""
                SELECT event_type, COUNT(*) as cnt
                FROM family_milestones
                WHERE strftime('%Y', event_date) = ?
                GROUP BY event_type
                ORDER BY cnt DESC
            """, (str(year),)).fetchall()

            # 按月份统计
            month_stats = conn.execute("""
                SELECT CAST(strftime('%m', event_date) AS INTEGER) as month, COUNT(*) as cnt
                FROM family_milestones
                WHERE strftime('%Y', event_date) = ?
                GROUP BY month
                ORDER BY month
            """, (str(year),)).fetchall()

            # 重要级别分布
            importance_stats = conn.execute("""
                SELECT importance_level, COUNT(*) as cnt
                FROM family_milestones
                WHERE strftime('%Y', event_date) = ?
                GROUP BY importance_level
                ORDER BY importance_level DESC
            """, (str(year),)).fetchall()

        # 格式化输出
        lines = [
            f"📊 {year} 年家庭大事记统计",
            "━" * 50,
            f"\n📈 总计：{total} 条大事记",
        ]

        if type_stats:
            lines.append("\n📋 按类型分布：")
            for event_type, cnt in type_stats:
                icon = MILESTONE_ICONS.get(event_type, "📌")
                display = MILESTONE_TYPES.get(event_type, event_type)
                bar = "█" * min(cnt, 20)
                lines.append(f"  {icon} {display}: {cnt} {bar}")

        if month_stats:
            lines.append("\n📅 按月份分布：")
            month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月",
                          "七月", "八月", "九月", "十月", "十一月", "十二月"]
            for month, cnt in month_stats:
                lines.append(f"  {month_names[month]}: {cnt} 条")

        if importance_stats:
            lines.append("\n⭐ 重要级别分布：")
            for level, cnt in importance_stats:
                stars = IMPORTANCE_ICONS.get(level, "⭐")
                lines.append(f"  {stars}: {cnt} 条")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={
                "year": year,
                "total": total,
                "by_type": {t: c for t, c in type_stats},
                "by_month": {m: c for m, c in month_stats},
                "by_importance": {i: c for i, c in importance_stats},
            },
        )

    def _export_timeline(self, params: dict[str, Any]) -> ToolResult:
        export_format = params.get("format", "md")
        style = params.get("style", "timeline")
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        output_path = params.get("output_path")

        # 获取数据
        timeline_result = self._get_timeline({
            "start_date": start_date,
            "end_date": end_date,
            "style": style,
        })
        milestones = timeline_result.data.get("milestones", [])

        if not milestones:
            return timeline_result

        # 根据格式导出
        if export_format == "json":
            content = json.dumps(milestones, ensure_ascii=False, indent=2)
        elif export_format == "html":
            content = self._export_html(milestones, style)
        else:  # md
            content = timeline_result.output

        # 确定输出路径
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = {"md": "md", "html": "html", "json": "json"}[export_format]
            output_path = str(Path("generated") / f"family_milestone_{timestamp}.{ext}")

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding="utf-8")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"已导出到: {output_file}",
            data={"path": str(output_file), "format": export_format, "count": len(milestones)},
        )

    # ------------------------------------------------------------------
    # 格式化方法
    # ------------------------------------------------------------------

    def _format_timeline(self, milestones: list[dict], year: int = None) -> str:
        lines = ["🎊 家庭大事记时间线", "━" * 50]

        # 按年份分组
        by_year: dict[int, list] = {}
        for m in milestones:
            y = int(m["event_date"][:4])
            if y not in by_year:
                by_year[y] = []
            by_year[y].append(m)

        for y in sorted(by_year.keys(), reverse=True):
            lines.append(f"\n📅 {y} 年")
            lines.append("━" * 50)

            for m in sorted(by_year[y], key=lambda x: x["event_date"]):
                type_icon = MILESTONE_ICONS.get(m["event_type"], "📌")
                date_str = m["event_date"][5:]  # MM-DD
                stars = IMPORTANCE_ICONS.get(m["importance_level"], "⭐⭐⭐")

                lines.append(f"\n📆 {date_str}  {type_icon} {m['title']}")
                lines.append(f"         {stars} |", end="")
                if m.get("location"):
                    lines[-1] += f" 📍 {m['location']}"
                else:
                    lines[-1] = lines[-1][:-1]

                if m.get("related_members"):
                    members = m["related_members"]
                    if members:
                        lines.append(f"         👥 关联成员：{', '.join(members)}")

                if m.get("description"):
                    desc = m["description"]
                    if len(desc) > 60:
                        desc = desc[:60] + "..."
                    lines.append(f"         📝 {desc}")

                # 计算已过天数或倒计时
                event_date = datetime.strptime(m["event_date"], "%Y-%m-%d").date()
                today = datetime.now().date()
                days_diff = (today - event_date).days

                if m.get("is_annual"):
                    next_anniv = self._get_next_anniversary_date(m["event_date"])
                    if next_anniv:
                        days_until = (next_anniv - today).days
                        years = (today.year - event_date.year)
                        lines.append(f"         [第 {years} 周年，还有 {days_until} 天]")
                elif days_diff >= 0:
                    lines.append(f"         [已过 {days_diff} 天]")
                else:
                    lines.append(f"         [还有 {abs(days_diff)} 天]")

        # 统计
        lines.append(f"\n{'━' * 50}")
        lines.append(f"📊 共 {len(milestones)} 条大事记")

        # 类型分布
        type_counts: dict[str, int] = {}
        for m in milestones:
            t = m["event_type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        type_strs = []
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
            display = MILESTONE_TYPES.get(t, t)
            type_strs.append(f"{display} {c}")
        lines.append(f"类型分布：{' | '.join(type_strs)}")

        return "\n".join(lines)

    def _format_card_grid(self, milestones: list[dict]) -> str:
        lines = ["🎴 大事记卡片视图", "━" * 50]

        for m in milestones:
            type_icon = MILESTONE_ICONS.get(m["event_type"], "📌")
            stars = IMPORTANCE_ICONS.get(m["importance_level"], "⭐⭐⭐")

            lines.append(f"\n┌{'─' * 22}┐")
            lines.append(f"│ {type_icon} {m['title'][:18]:<18}│")
            lines.append(f"│ 📅 {m['event_date']:<18}│")
            lines.append(f"│ {stars:<20}│")
            if m.get("location"):
                lines.append(f"│ 📍 {m['location'][:18]:<18}│")
            lines.append(f"└{'─' * 22}┘")

        lines.append(f"\n📊 共 {len(milestones)} 张卡片")
        return "\n".join(lines)

    def _format_calendar(self, milestones: list[dict], year: int = None) -> str:
        year = year or datetime.now().year
        lines = [f"📆 {year} 年大事记日历", "━" * 50]

        # 按月份分组
        by_month: dict[int, list] = {}
        for m in milestones:
            y, mth = int(m["event_date"][:4]), int(m["event_date"][5:7])
            if y == year:
                if mth not in by_month:
                    by_month[mth] = []
                by_month[mth].append(m)

        month_names = ["", "一月", "二月", "三月", "四月", "五月", "六月",
                      "七月", "八月", "九月", "十月", "十一月", "十二月"]

        for month in range(1, 13):
            if month in by_month:
                lines.append(f"\n📅 {month_names[month]}")
                lines.append("-" * 30)
                for m in sorted(by_month[month], key=lambda x: x["event_date"]):
                    day = m["event_date"][8:]
                    type_icon = MILESTONE_ICONS.get(m["event_type"], "📌")
                    lines.append(f"  {day}日 {type_icon} {m['title']}")

        lines.append(f"\n📊 {year} 年共 {len(milestones)} 条大事记")
        return "\n".join(lines)

    def _format_album(self, milestones: list[dict]) -> str:
        lines = ["📸 家庭大事记相册", "━" * 50]

        for m in milestones:
            type_icon = MILESTONE_ICONS.get(m["event_type"], "📌")
            lines.append(f"\n{type_icon} {m['title']}")
            lines.append(f"📅 {m['event_date']}")
            if m.get("description"):
                lines.append(f"💭 {m['description'][:100]}")
            lines.append("-" * 30)

        lines.append(f"\n📊 共 {len(milestones)} 个回忆")
        return "\n".join(lines)

    def _format_simple_list(self, milestones: list[dict]) -> str:
        lines = ["📋 大事记列表", "━" * 50]

        for m in milestones:
            type_icon = MILESTONE_ICONS.get(m["event_type"], "📌")
            lines.append(f"{m['event_date']} {type_icon} {m['title']}")

        lines.append(f"\n📊 共 {len(milestones)} 条")
        return "\n".join(lines)

    def _format_annual_report(self, milestones: list[dict], year: int) -> str:
        lines = [
            f"🎊 {year} 年度家庭大事记报告",
            "═" * 50,
            "",
        ]

        # 年度关键词
        all_titles = " ".join([m["title"] for m in milestones])
        lines.append(f"📝 年度记录：{len(milestones)} 条大事记")

        # 最重要的5件事
        important = sorted(milestones, key=lambda x: -x.get("importance_level", 3))[:5]
        lines.append("\n🏆 年度重要事件：")
        for i, m in enumerate(important, 1):
            type_icon = MILESTONE_ICONS.get(m["event_type"], "📌")
            lines.append(f"  {i}. {type_icon} {m['title']} ({m['event_date']})")

        # 各类型精选
        lines.append("\n📋 分类回顾：")
        for event_type, display in MILESTONE_TYPES.items():
            type_items = [m for m in milestones if m["event_type"] == event_type]
            if type_items:
                icon = MILESTONE_ICONS.get(event_type, "📌")
                lines.append(f"  {icon} {display}：{len(type_items)} 条")

        lines.append(f"\n{'═' * 50}")
        lines.append(f"感谢 {year} 年的每一个重要时刻!")

        return "\n".join(lines)

    def _format_detail(self, data: dict) -> str:
        type_icon = MILESTONE_ICONS.get(data.get("event_type", "other"), "📌")
        type_display = MILESTONE_TYPES.get(data.get("event_type", "other"), "其他")
        stars = IMPORTANCE_ICONS.get(data.get("importance_level", 3), "⭐⭐⭐")

        lines = [
            f"🎊 大事记详情 (ID: {data['id']})",
            "━" * 50,
            f"{type_icon} {type_display}",
            f"📝 {data['title']}",
            f"📅 {data['event_date']}",
            f"{stars} 重要级别：{data.get('importance_level', 3)}",
        ]

        if data.get("end_date"):
            lines.append(f"🔚 结束日期：{data['end_date']}")
        if data.get("location"):
            lines.append(f"📍 地点：{data['location']}")
        if data.get("related_members"):
            lines.append(f"👥 关联成员：{', '.join(data['related_members'])}")
        if data.get("description"):
            lines.append(f"📝 描述：{data['description']}")
        if data.get("tags"):
            lines.append(f"🏷️ 标签：{', '.join(data['tags'])}")
        if data.get("is_annual"):
            lines.append("🔄 年度重复")
        if data.get("reminder_days"):
            lines.append(f"⏰ 提醒：提前 {', '.join(map(str, data['reminder_days']))} 天")
        if data.get("notes"):
            lines.append(f"📌 备注：{data['notes']}")

        lines.append(f"\n创建时间：{data.get('created_at', '')}")
        lines.append(f"更新时间：{data.get('updated_at', '')}")

        return "\n".join(lines)

    def _format_list(self, milestones: list[dict]) -> str:
        lines = [f"找到 {len(milestones)} 条大事记：", "━" * 50]

        for i, m in enumerate(milestones, 1):
            type_icon = MILESTONE_ICONS.get(m["event_type"], "📌")
            stars = IMPORTANCE_ICONS.get(m["importance_level"], "⭐⭐⭐")
            lines.append(f"\n{i}. {type_icon} {m['title']} (ID:{m['id']})")
            lines.append(f"   📅 {m['event_date']} | {stars}")
            if m.get("location"):
                lines.append(f"   📍 {m['location']}")

        return "\n".join(lines)

    def _export_html(self, milestones: list[dict], style: str) -> str:
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>家庭大事记</title>
    <style>
        body { font-family: 'Microsoft YaHei', sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        h1 { color: #333; text-align: center; }
        .milestone { background: white; margin: 15px 0; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .title { font-size: 18px; font-weight: bold; color: #333; }
        .date { color: #666; margin: 5px 0; }
        .type { display: inline-block; padding: 2px 8px; border-radius: 4px; background: #e3f2fd; color: #1976d2; font-size: 12px; }
        .importance { color: #ffc107; }
        .location { color: #666; font-size: 14px; }
        .description { margin-top: 10px; color: #444; line-height: 1.6; }
    </style>
</head>
<body>
    <h1>🎊 家庭大事记</h1>
"""
        for m in milestones:
            type_display = MILESTONE_TYPES.get(m["event_type"], "其他")
            stars = "⭐" * m.get("importance_level", 3)
            html += f"""
    <div class="milestone">
        <div class="title">{m['title']}</div>
        <div class="date">📅 {m['event_date']}</div>
        <span class="type">{type_display}</span>
        <span class="importance">{stars}</span>
        {f'<div class="location">📍 {m["location"]}</div>' if m.get('location') else ''}
        {f'<div class="description">{m["description"]}</div>' if m.get('description') else ''}
    </div>
"""
        html += """
    <p style="text-align: center; color: #999; margin-top: 30px;">
        共 """ + str(len(milestones)) + """ 条大事记
    </p>
</body>
</html>"""
        return html

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _row_to_dict(self, row: tuple) -> dict:
        columns = [
            "id", "title", "description", "event_date", "end_date",
            "event_type", "importance_level", "related_members", "location",
            "cover_image", "photos", "tags", "is_annual", "reminder_days",
            "notes", "created_at", "updated_at",
        ]
        data = dict(zip(columns, row))

        # JSON 字段解析
        for key in ["related_members", "photos", "tags", "reminder_days"]:
            if data.get(key):
                try:
                    data[key] = json.loads(data[key])
                except (json.JSONDecodeError, TypeError):
                    data[key] = []
            else:
                data[key] = []

        # 布尔值转换
        data["is_annual"] = bool(data.get("is_annual", 0))

        return data

    def _calculate_days_since(self, event_date: str) -> int:
        """计算已过天数"""
        try:
            event_dt = datetime.strptime(event_date, "%Y-%m-%d").date()
            today = datetime.now().date()
            return (today - event_dt).days
        except ValueError:
            return 0

    def _calculate_days_until(self, event_date: str, is_annual: bool = False) -> int:
        """计算倒计时天数"""
        try:
            if is_annual:
                next_date = self._get_next_anniversary_date(event_date)
                if next_date:
                    today = datetime.now().date()
                    return (next_date - today).days
            else:
                event_dt = datetime.strptime(event_date, "%Y-%m-%d").date()
                today = datetime.now().date()
                return (event_dt - today).days
        except ValueError:
            pass
        return 0

    def _get_next_anniversary_date(self, original_date: str) -> datetime.date | None:
        """计算下次纪念日日期"""
        try:
            original = datetime.strptime(original_date, "%Y-%m-%d").date()
            today = datetime.now().date()

            # 今年的纪念日
            this_year = original.replace(year=today.year)

            # 如果今年已过，则为明年
            if this_year < today:
                next_date = original.replace(year=today.year + 1)
            else:
                next_date = this_year

            return next_date
        except ValueError:
            return None
