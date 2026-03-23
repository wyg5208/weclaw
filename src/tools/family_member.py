"""家庭成员管理工具 - 专业的家庭成员档案管理系统。

提供完整的家庭成员信息管理功能：
- 创建家庭成员档案
- 查询家庭成员列表和详情
- 编辑家庭成员信息
- 删除家庭成员记录
- 家庭关系图谱
- 重要日期提醒（生日等）

数据存储到 ~/.weclaw/weclaw_tools.db 的 family_members 表。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

# 默认数据库路径
_DEFAULT_DB = Path.home() / ".weclaw" / "weclaw_tools.db"

# 关系类型映射（中英文）
_RELATIONSHIP_MAP = {
    "spouse": "配偶",
    "child": "子女",
    "parent": "父母",
    "sibling": "兄弟姐妹",
    "grandparent": "祖父母/外祖父母",
    "grandchild": "孙子女/外孙子女",
    "uncle": "叔叔/舅舅",
    "aunt": "阿姨/姑姑",
    "nephew": "侄子/外甥",
    "niece": "侄女/外甥女",
    "cousin": "表/堂兄弟姐妹",
    "other": "其他",
}

# 性别映射
_GENDER_MAP = {
    "male": "男",
    "female": "女",
}

# 重要级别图标
_IMPORTANCE_ICONS = {
    1: "⭐",
    2: "⭐⭐",
    3: "⭐⭐⭐",
    4: "⭐⭐⭐⭐",
    5: "⭐⭐⭐⭐⭐",
}


class FamilyMemberTool(BaseTool):
    """家庭成员管理工具。

    提供专业的家庭成员档案管理功能。
    """

    name = "family_member"
    emoji = "👨‍👩‍👧‍👦"
    title = "家庭成员管理"
    description = "创建、查询、编辑和删除家庭成员档案，管理家庭关系和重要日期"

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
            # 家庭成员表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS family_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    relationship TEXT NOT NULL,
                    birthday TEXT,
                    gender TEXT,
                    phone TEXT,
                    wechat TEXT,
                    email TEXT,
                    address TEXT,
                    occupation TEXT,
                    company TEXT,
                    importance_level INTEGER DEFAULT 3,
                    preferences TEXT DEFAULT '{}',
                    notes TEXT,
                    avatar_url TEXT,
                    is_minor INTEGER DEFAULT 0,
                    guardian_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (guardian_id) REFERENCES family_members(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_family_members_name
                ON family_members(name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_family_members_relationship
                ON family_members(relationship)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_family_members_birthday
                ON family_members(birthday)
            """)
            conn.commit()

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="create_member",
                description="创建新的家庭成员档案",
                parameters={
                    "name": {
                        "type": "string",
                        "description": "成员姓名",
                    },
                    "relationship": {
                        "type": "string",
                        "description": "关系：spouse/child/parent/sibling/grandparent/grandchild/uncle/aunt/nephew/niece/cousin/other",
                    },
                    "birthday": {
                        "type": "string",
                        "description": "生日 YYYY-MM-DD（可选）",
                    },
                    "gender": {
                        "type": "string",
                        "description": "性别：male/female（可选）",
                    },
                    "phone": {
                        "type": "string",
                        "description": "电话号码（可选）",
                    },
                    "wechat": {
                        "type": "string",
                        "description": "微信号（可选）",
                    },
                    "email": {
                        "type": "string",
                        "description": "邮箱（可选）",
                    },
                    "address": {
                        "type": "string",
                        "description": "地址（可选）",
                    },
                    "occupation": {
                        "type": "string",
                        "description": "职业（可选）",
                    },
                    "company": {
                        "type": "string",
                        "description": "公司/学校（可选）",
                    },
                    "importance_level": {
                        "type": "integer",
                        "description": "重要级别 1-5（可选，默认 3）",
                    },
                    "preferences": {
                        "type": "string",
                        "description": "偏好设置，JSON 格式如 {\"favorite_food\":\"苹果\",\"hobby\":\"阅读\"}（可选）",
                    },
                    "notes": {
                        "type": "string",
                        "description": "备注（可选）",
                    },
                    "is_minor": {
                        "type": "boolean",
                        "description": "是否未成年（可选，默认 false）",
                    },
                    "guardian_id": {
                        "type": "integer",
                        "description": "监护人 ID（可选，当 is_minor 为 true 时指定）",
                    },
                },
                required_params=["name", "relationship"],
            ),
            ActionDef(
                name="query_members",
                description="查询家庭成员列表或详情",
                parameters={
                    "member_id": {
                        "type": "integer",
                        "description": "成员 ID（指定则返回详情）",
                    },
                    "name": {
                        "type": "string",
                        "description": "按姓名模糊搜索（可选）",
                    },
                    "relationship": {
                        "type": "string",
                        "description": "按关系筛选（可选）",
                    },
                    "upcoming_birthday_days": {
                        "type": "integer",
                        "description": "查询未来 N 天内过生日的成员（可选）",
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "是否包含详细信息（可选，默认 true）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="update_member",
                description="更新家庭成员信息",
                parameters={
                    "member_id": {
                        "type": "integer",
                        "description": "成员 ID",
                    },
                    "name": {
                        "type": "string",
                        "description": "新姓名（可选）",
                    },
                    "relationship": {
                        "type": "string",
                        "description": "新关系（可选）",
                    },
                    "birthday": {
                        "type": "string",
                        "description": "新生日（可选）",
                    },
                    "gender": {
                        "type": "string",
                        "description": "新性别（可选）",
                    },
                    "phone": {
                        "type": "string",
                        "description": "新电话（可选）",
                    },
                    "wechat": {
                        "type": "string",
                        "description": "新微信（可选）",
                    },
                    "email": {
                        "type": "string",
                        "description": "新邮箱（可选）",
                    },
                    "address": {
                        "type": "string",
                        "description": "新地址（可选）",
                    },
                    "occupation": {
                        "type": "string",
                        "description": "新职业（可选）",
                    },
                    "company": {
                        "type": "string",
                        "description": "新公司/学校（可选）",
                    },
                    "importance_level": {
                        "type": "integer",
                        "description": "新重要级别（可选）",
                    },
                    "preferences": {
                        "type": "string",
                        "description": "新偏好设置，JSON 格式（可选）",
                    },
                    "notes": {
                        "type": "string",
                        "description": "新备注（可选）",
                    },
                    "is_minor": {
                        "type": "boolean",
                        "description": "是否未成年（可选）",
                    },
                    "guardian_id": {
                        "type": "integer",
                        "description": "新监护人 ID（可选）",
                    },
                },
                required_params=["member_id"],
            ),
            ActionDef(
                name="delete_member",
                description="删除家庭成员记录",
                parameters={
                    "member_id": {
                        "type": "integer",
                        "description": "要删除的成员 ID",
                    },
                    "confirm": {
                        "type": "boolean",
                        "description": "确认删除（必须为 true）",
                    },
                },
                required_params=["member_id", "confirm"],
            ),
            ActionDef(
                name="get_family_tree",
                description="获取家庭关系图谱",
                parameters={
                    "root_member_id": {
                        "type": "integer",
                        "description": "根成员 ID（可选，默认查询所有关系）",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "最大深度（可选，默认 3）",
                    },
                },
                required_params=[],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        action_map = {
            "create_member": self._create_member,
            "query_members": self._query_members,
            "update_member": self._update_member,
            "delete_member": self._delete_member,
            "get_family_tree": self._get_family_tree,
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
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"执行失败：{str(e)}",
            )

    def _create_member(self, params: dict[str, Any]) -> ToolResult:
        name = params.get("name", "").strip()
        relationship = params.get("relationship", "").strip()

        if not name:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="姓名不能为空",
            )
        if not relationship:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="关系不能为空",
            )

        # 验证关系类型
        if relationship not in _RELATIONSHIP_MAP:
            valid_rels = ", ".join(_RELATIONSHIP_MAP.keys())
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无效的关系类型。有效值：{valid_rels}",
            )

        # 验证生日格式
        birthday = params.get("birthday", "").strip() or None
        if birthday:
            try:
                datetime.strptime(birthday, "%Y-%m-%d")
            except ValueError:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="生日格式错误，请使用 YYYY-MM-DD",
                )

        # 验证性别
        gender = params.get("gender", "").strip() or None
        if gender and gender not in _GENDER_MAP:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="性别格式错误，请使用 male 或 female",
            )

        # 验证重要级别
        importance_level = params.get("importance_level", 3)
        if not isinstance(importance_level, int) or not 1 <= importance_level <= 5:
            importance_level = 3

        # 处理偏好设置
        preferences = params.get("preferences", "{}")
        if isinstance(preferences, str):
            try:
                import json

                json.loads(preferences)
            except Exception:
                preferences = "{}"

        now = datetime.now().isoformat()

        with self._conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO family_members (
                    name, relationship, birthday, gender, phone, wechat, email,
                    address, occupation, company, importance_level, preferences,
                    notes, avatar_url, is_minor, guardian_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    relationship,
                    birthday,
                    gender,
                    params.get("phone", "").strip() or None,
                    params.get("wechat", "").strip() or None,
                    params.get("email", "").strip() or None,
                    params.get("address", "").strip() or None,
                    params.get("occupation", "").strip() or None,
                    params.get("company", "").strip() or None,
                    importance_level,
                    preferences,
                    params.get("notes", "").strip() or None,
                    params.get("avatar_url", "").strip() or None,
                    1 if params.get("is_minor") else 0,
                    params.get("guardian_id"),
                    now,
                    now,
                ),
            )
            conn.commit()
            member_id = cursor.lastrowid

        rel_display = self._get_relationship_display(relationship)
        gender_icon = "👦" if gender == "male" else "👧" if gender == "female" else "👤"
        importance_stars = _IMPORTANCE_ICONS.get(importance_level, "⭐⭐⭐")

        output = f"✅ 家庭成员已创建 (ID: {member_id})\n{gender_icon} **{name}** | 关系：{rel_display}"
        if birthday:
            output += f"\n🎂 生日：{birthday}"
        if phone := params.get("phone", "").strip():
            output += f"\n📱 电话：{phone}"
        if wechat := params.get("wechat", "").strip():
            output += f"\n💬 微信：{wechat}"
        output += f"\n重要级别：{importance_stars}"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"member_id": member_id, "name": name, "relationship": relationship},
        )

    def _query_members(self, params: dict[str, Any]) -> ToolResult:
        member_id = params.get("member_id")
        name_filter = params.get("name", "").strip()
        relationship_filter = params.get("relationship", "").strip()
        upcoming_days = params.get("upcoming_birthday_days")
        include_details = params.get("include_details", True)

        with self._conn() as conn:
            query = "SELECT * FROM family_members WHERE 1=1"
            args: list[Any] = []

            if member_id:
                query += " AND id = ?"
                args.append(member_id)
            if name_filter:
                query += " AND name LIKE ?"
                args.append(f"%{name_filter}%")
            if relationship_filter:
                query += " AND relationship = ?"
                args.append(relationship_filter)

            query += " ORDER BY importance_level DESC, name ASC"

            rows = conn.execute(query, args).fetchall()

        if not rows:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="📋 未找到符合条件的家庭成员",
                data={"members": [], "count": 0},
            )

        # 处理即将到来的生日
        if upcoming_days:
            from datetime import timedelta

            today = datetime.now().date()
            end_date = today + timedelta(days=upcoming_days)
            birthday_members = []

            for row in rows:
                birthday = row[3]  # birthday 字段索引
                if birthday:
                    days_until = self._calculate_days_until_birthday(birthday)
                    if days_until is not None and days_until <= upcoming_days:
                        member_data = self._row_to_dict(row, include_details)
                        member_data["days_until_birthday"] = days_until
                        birthday_members.append(member_data)

            birthday_members.sort(key=lambda x: x["days_until_birthday"])

            lines = [f"🎂 未来 {upcoming_days} 天内的生日 ({len(birthday_members)} 人)"]
            for member in birthday_members:
                days_str = "今天🎉" if member["days_until_birthday"] == 0 else f"还有 {member['days_until_birthday']} 天"
                bday_md = member["birthday"][5:] if member["birthday"] else ""
                lines.append(
                    f"  • **{member['name']}** ({member['relationship_display']}) - {bday_md} ({days_str})"
                )

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="\n".join(lines),
                data={"members": birthday_members, "count": len(birthday_members)},
            )

        # 普通查询
        members = [self._row_to_dict(row, include_details) for row in rows]

        if member_id and len(members) == 1:
            # 返回单个成员详情
            member = members[0]
            output = f"👤 **{member['name']}** (ID: {member['id']})\n"
            output += f"关系：{member['relationship_display']}\n"
            if member.get("birthday"):
                output += f"🎂 生日：{member['birthday']}\n"
            if member.get("gender_display"):
                output += f"性别：{member['gender_display']}\n"
            if member.get("phone"):
                output += f"📱 电话：{member['phone']}\n"
            if member.get("wechat"):
                output += f"💬 微信：{member['wechat']}\n"
            if member.get("email"):
                output += f"📧 邮箱：{member['email']}\n"
            if member.get("address"):
                output += f"🏠 地址：{member['address']}\n"
            if member.get("occupation"):
                output += f"💼 职业：{member['occupation']}\n"
            if member.get("company"):
                output += f"🏢 公司：{member['company']}\n"
            output += f"重要级别：{_IMPORTANCE_ICONS.get(member.get('importance_level', 3), '⭐⭐⭐')}"
            if member.get("notes"):
                output += f"\n📝 备注：{member['notes']}"
        else:
            # 返回列表
            lines = [f"📋 家庭成员列表 ({len(members)} 人)"]
            for m in members:
                icon = _IMPORTANCE_ICONS.get(m.get("importance_level", 3), "⭐⭐⭐")
                rel = m["relationship_display"]
                bday = f" | 🎂{m['birthday'][5:]}" if m.get("birthday") else ""
                lines.append(f"  {icon} **{m['name']}** ({rel}){bday} - ID: {m['id']}")

            output = "\n".join(lines)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"members": members, "count": len(members)},
        )

    def _update_member(self, params: dict[str, Any]) -> ToolResult:
        member_id = params.get("member_id")
        if member_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少 member_id",
            )

        with self._conn() as conn:
            row = conn.execute("SELECT name FROM family_members WHERE id = ?", (member_id,)).fetchone()
            if not row:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"成员不存在：ID {member_id}",
                )

        updates: dict[str, Any] = {}
        update_fields = [
            "name",
            "relationship",
            "birthday",
            "gender",
            "phone",
            "wechat",
            "email",
            "address",
            "occupation",
            "company",
            "importance_level",
            "preferences",
            "notes",
            "is_minor",
            "guardian_id",
        ]

        for key in update_fields:
            if key in params and params[key] is not None:
                if key == "is_minor":
                    updates[key] = 1 if params[key] else 0
                else:
                    updates[key] = params[key]

        if not updates:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="没有提供任何更新内容",
            )

        # 验证生日格式
        if "birthday" in updates and updates["birthday"]:
            try:
                datetime.strptime(updates["birthday"], "%Y-%m-%d")
            except ValueError:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="生日格式错误，请使用 YYYY-MM-DD",
                )

        # 验证关系类型
        if "relationship" in updates and updates["relationship"]:
            if updates["relationship"] not in _RELATIONSHIP_MAP:
                valid_rels = ", ".join(_RELATIONSHIP_MAP.keys())
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"无效的关系类型。有效值：{valid_rels}",
                )

        # 验证性别
        if "gender" in updates and updates["gender"]:
            if updates["gender"] not in _GENDER_MAP:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="性别格式错误，请使用 male 或 female",
                )

        # 验证重要级别
        if "importance_level" in updates:
            level = updates["importance_level"]
            if not isinstance(level, int) or not 1 <= level <= 5:
                updates["importance_level"] = 3

        updates["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [member_id]

        with self._conn() as conn:
            conn.execute(
                f"UPDATE family_members SET {set_clause} WHERE id = ?",
                values,
            )
            conn.commit()

        member_name = row[0]
        output = f"✅ 成员信息已更新 (ID: {member_id})\n👤 {member_name}"
        if updates.get("name"):
            output += f" → {updates['name']}"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"member_id": member_id, "updated_fields": list(updates.keys())},
        )

    def _delete_member(self, params: dict[str, Any]) -> ToolResult:
        member_id = params.get("member_id")
        confirm = params.get("confirm")

        if member_id is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="缺少 member_id",
            )
        if confirm is not True:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="删除操作需要 confirm=true 确认",
            )

        with self._conn() as conn:
            row = conn.execute("SELECT name FROM family_members WHERE id = ?", (member_id,)).fetchone()
            if not row:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"成员不存在：ID {member_id}",
                )

            member_name = row[0]

            # 检查是否有成员以此人为监护人
            dependent_count = conn.execute(
                "SELECT COUNT(*) FROM family_members WHERE guardian_id = ?",
                (member_id,),
            ).fetchone()[0]

            if dependent_count > 0:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"无法删除：有 {dependent_count} 个成员以此人为监护人，请先修改这些成员的监护人设置",
                )

            # 执行删除
            conn.execute("DELETE FROM family_members WHERE id = ?", (member_id,))
            conn.commit()

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"🗑️ 已删除成员：**{member_name}** (ID: {member_id})",
            data={"member_id": member_id, "deleted_name": member_name},
        )

    def _get_family_tree(self, params: dict[str, Any]) -> ToolResult:
        root_id = params.get("root_member_id")
        max_depth = params.get("max_depth", 3)

        with self._conn() as conn:
            if root_id:
                root_row = conn.execute(
                    "SELECT id, name, relationship FROM family_members WHERE id = ?",
                    (root_id,),
                ).fetchone()
                if not root_row:
                    return ToolResult(
                        status=ToolResultStatus.ERROR,
                        error=f"根成员不存在：ID {root_id}",
                    )
                root_name = root_row[1]
            else:
                root_name = "家庭"

            # 简单实现：按关系分组显示
            rows = conn.execute(
                """
                SELECT id, name, relationship, birthday, gender, importance_level
                FROM family_members
                ORDER BY relationship, importance_level DESC, name
            """,
            ).fetchall()

        if not rows:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="📋 暂无家庭成员",
                data={"tree": {}, "count": 0},
            )

        # 按关系分组
        tree: dict[str, list[dict]] = {}
        for row in rows:
            rel = row[2]
            rel_display = self._get_relationship_display(rel)
            if rel_display not in tree:
                tree[rel_display] = []

            tree[rel_display].append(
                {
                    "id": row[0],
                    "name": row[1],
                    "birthday": row[3],
                    "gender": row[4],
                    "importance_level": row[5],
                }
            )

        # 生成输出
        lines = [f"🌳 {root_name}家庭关系图谱"]
        total = 0
        for rel_display, members in tree.items():
            lines.append(f"\n{rel_display} ({len(members)}人):")
            for m in members:
                icon = _IMPORTANCE_ICONS.get(m["importance_level"], "⭐⭐⭐")
                bday = f" | 🎂{m['birthday'][5:]}" if m.get("birthday") else ""
                lines.append(f"  {icon} **{m['name']}** (ID: {m['id']}){bday}")
            total += len(members)

        output = "\n".join(lines)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"tree": tree, "count": total},
        )

    def _get_relationship_display(self, relationship: str) -> str:
        """获取关系的中文显示。"""
        return _RELATIONSHIP_MAP.get(relationship, relationship)

    def _get_gender_display(self, gender: str) -> str:
        """获取性别的中文显示。"""
        return _GENDER_MAP.get(gender, gender)

    def _row_to_dict(self, row: tuple, include_details: bool = True) -> dict[str, Any]:
        """将数据库行转换为字典。"""
        columns = [
            "id",
            "name",
            "relationship",
            "birthday",
            "gender",
            "phone",
            "wechat",
            "email",
            "address",
            "occupation",
            "company",
            "importance_level",
            "preferences",
            "notes",
            "avatar_url",
            "is_minor",
            "guardian_id",
            "created_at",
            "updated_at",
        ]
        data = dict(zip(columns, row))
        data["relationship_display"] = self._get_relationship_display(data["relationship"])
        if data.get("gender"):
            data["gender_display"] = self._get_gender_display(data["gender"])
        data["importance_stars"] = _IMPORTANCE_ICONS.get(data.get("importance_level", 3), "⭐⭐⭐")

        if not include_details:
            # 移除敏感或详细信息
            for key in ["preferences", "notes", "address", "guardian_id"]:
                data.pop(key, None)

        return data

    def _calculate_days_until_birthday(self, birthday_str: str) -> int | None:
        """计算距离生日还有多少天。"""
        from datetime import timedelta

        try:
            birth_date = datetime.strptime(birthday_str, "%Y-%m-%d").date()
            today = datetime.now().date()

            # 今年的生日
            this_year_birthday = birth_date.replace(year=today.year)
            if this_year_birthday < today:
                # 今年的生日已过，计算明年的
                this_year_birthday = birth_date.replace(year=today.year + 1)

            delta = this_year_birthday - today
            return delta.days
        except Exception:
            return None
