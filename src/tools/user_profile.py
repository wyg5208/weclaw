"""UserProfile 工具 — 用户档案管理。

支持动作：
- update_profile: 更新用户基础信息
- query_profile: 查询用户信息
- add_family_member: 添加家庭成员
- update_family_member: 更新家庭成员信息
- add_social_contact: 添加VIP社交联系人
- query_contacts: 查询联系人
- get_upcoming_birthdays: 获取即将到来的生日
- record_child_growth: 记录儿童生长发育数据

存储位置：~/.winclaw/winclaw_tools.db（user_profiles/family_members/social_contacts 表）
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

_DEFAULT_DB = Path.home() / ".winclaw" / "winclaw_tools.db"

# 关系类型映射（中英文）
_RELATIONSHIP_MAP = {
    "spouse": "配偶", "child": "子女", "parent": "父母", "sibling": "兄弟姐妹",
    "grandparent": "祖父母", "grandchild": "孙辈", "other": "其他",
    "friend": "朋友", "colleague": "同事", "mentor": "导师", "student": "学生",
    "partner": "合作伙伴", "client": "客户", "neighbor": "邻居",
}

# 重要级别图标
_IMPORTANCE_ICONS = {
    1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐",
}


class UserProfileTool(BaseTool):
    """用户档案管理工具。

    管理用户个人信息、家庭成员、VIP社交联系人档案。
    数据存储到 ~/.winclaw/winclaw_tools.db 的相关表。
    """

    name = "user_profile"
    emoji = "👤"
    title = "用户档案"
    description = "管理用户个人信息、家庭成员、VIP社交联系人档案"

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
            # 用户基础档案（key-value模式）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    source TEXT DEFAULT 'user_input',
                    confidence REAL DEFAULT 1.0,
                    needs_confirmation INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_profiles_key
                ON user_profiles(key)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_profiles_category
                ON user_profiles(category)
            """)

            # 家庭成员
            conn.execute("""
                CREATE TABLE IF NOT EXISTS family_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    relationship TEXT NOT NULL,
                    birthday TEXT,
                    gender TEXT,
                    notes TEXT,
                    growth_data TEXT DEFAULT '[]',
                    health_notes TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_family_members_name
                ON family_members(name)
            """)

            # VIP社交联系人
            conn.execute("""
                CREATE TABLE IF NOT EXISTS social_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    relationship TEXT,
                    birthday TEXT,
                    contact_info TEXT DEFAULT '{}',
                    importance_level INTEGER DEFAULT 3,
                    last_contact_date TEXT,
                    interaction_notes TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_social_contacts_name
                ON social_contacts(name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_social_contacts_importance
                ON social_contacts(importance_level DESC)
            """)
            conn.commit()

    # ------------------------------------------------------------------

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="update_profile",
                description="更新用户基础信息（UPSERT模式）",
                parameters={
                    "key": {
                        "type": "string",
                        "description": "信息键名，如 name/age/occupation/city/phone 等",
                    },
                    "value": {
                        "type": "string",
                        "description": "信息值",
                    },
                    "category": {
                        "type": "string",
                        "description": "分类: basic/health/preference，默认 basic",
                    },
                    "source": {
                        "type": "string",
                        "description": "信息来源: user_input/inferred/tool_result/confirmed，默认 user_input",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "置信度 0.0-1.0，默认 1.0",
                    },
                },
                required_params=["key", "value"],
            ),
            ActionDef(
                name="query_profile",
                description="查询用户信息，可按 key 精确查或按 category 查全部",
                parameters={
                    "key": {
                        "type": "string",
                        "description": "信息键名（可选，精确查询）",
                    },
                    "category": {
                        "type": "string",
                        "description": "分类: basic/health/preference（可选）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="add_family_member",
                description="添加家庭成员",
                parameters={
                    "name": {
                        "type": "string",
                        "description": "成员姓名",
                    },
                    "relationship": {
                        "type": "string",
                        "description": "关系: spouse/child/parent/sibling/grandparent/grandchild/other",
                    },
                    "birthday": {
                        "type": "string",
                        "description": "生日 YYYY-MM-DD（可选）",
                    },
                    "gender": {
                        "type": "string",
                        "description": "性别: male/female（可选）",
                    },
                    "notes": {
                        "type": "string",
                        "description": "备注（可选）",
                    },
                },
                required_params=["name", "relationship"],
            ),
            ActionDef(
                name="update_family_member",
                description="更新家庭成员信息",
                parameters={
                    "id": {
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
                    "notes": {
                        "type": "string",
                        "description": "新备注（可选）",
                    },
                },
                required_params=["id"],
            ),
            ActionDef(
                name="add_social_contact",
                description="添加VIP社交联系人",
                parameters={
                    "name": {
                        "type": "string",
                        "description": "联系人姓名",
                    },
                    "relationship": {
                        "type": "string",
                        "description": "关系: friend/colleague/mentor/student/partner/client/neighbor/other（可选）",
                    },
                    "birthday": {
                        "type": "string",
                        "description": "生日 YYYY-MM-DD（可选）",
                    },
                    "contact_info": {
                        "type": "string",
                        "description": "联系方式，JSON格式如 {\"phone\":\"xxx\",\"wechat\":\"xxx\"}（可选）",
                    },
                    "importance_level": {
                        "type": "integer",
                        "description": "重要程度 1-5，默认 3",
                    },
                },
                required_params=["name"],
            ),
            ActionDef(
                name="query_contacts",
                description="查询联系人，支持多条件组合筛选",
                parameters={
                    "name": {
                        "type": "string",
                        "description": "姓名关键词（模糊搜索，可选）",
                    },
                    "relationship": {
                        "type": "string",
                        "description": "关系类型（可选）",
                    },
                    "importance_level": {
                        "type": "integer",
                        "description": "最低重要级别 1-5（可选）",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="get_upcoming_birthdays",
                description="获取即将到来的生日（家庭成员+社交联系人）",
                parameters={
                    "days": {
                        "type": "integer",
                        "description": "未来天数范围，默认 30",
                    },
                },
                required_params=[],
            ),
            ActionDef(
                name="record_child_growth",
                description="记录儿童生长发育数据",
                parameters={
                    "member_id": {
                        "type": "integer",
                        "description": "家庭成员 ID",
                    },
                    "height_cm": {
                        "type": "number",
                        "description": "身高(cm)（可选）",
                    },
                    "weight_kg": {
                        "type": "number",
                        "description": "体重(kg)（可选）",
                    },
                    "note": {
                        "type": "string",
                        "description": "备注（可选）",
                    },
                    "date": {
                        "type": "string",
                        "description": "记录日期 YYYY-MM-DD（可选，默认今天）",
                    },
                },
                required_params=["member_id"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        handlers = {
            "update_profile": self._update_profile,
            "query_profile": self._query_profile,
            "add_family_member": self._add_family_member,
            "update_family_member": self._update_family_member,
            "add_social_contact": self._add_social_contact,
            "query_contacts": self._query_contacts,
            "get_upcoming_birthdays": self._get_upcoming_birthdays,
            "record_child_growth": self._record_child_growth,
        }
        handler = handlers.get(action)
        if handler is None:
            return ToolResult(status=ToolResultStatus.ERROR, error=f"不支持的动作: {action}")
        try:
            return handler(params)
        except Exception as e:
            logger.error("用户档案操作失败: %s", e)
            return ToolResult(status=ToolResultStatus.ERROR, error=str(e))

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _get_relationship_display(self, rel: str | None) -> str:
        """获取关系的中文显示"""
        if not rel:
            return ""
        return _RELATIONSHIP_MAP.get(rel, rel)

    def _calculate_days_until_birthday(self, birthday_str: str | None) -> int | None:
        """计算距离下一次生日的天数"""
        if not birthday_str:
            return None
        try:
            birthday = datetime.strptime(birthday_str, "%Y-%m-%d")
            today = datetime.now().date()
            this_year_birthday = birthday.replace(year=today.year).date()
            if this_year_birthday < today:
                this_year_birthday = birthday.replace(year=today.year + 1).date()
            return (this_year_birthday - today).days
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # 动作实现
    # ------------------------------------------------------------------

    def _update_profile(self, params: dict[str, Any]) -> ToolResult:
        key = params.get("key", "").strip()
        value = params.get("value", "").strip()
        category = params.get("category", "basic").strip()
        source = params.get("source", "user_input").strip()
        confidence = params.get("confidence", 1.0)

        if not key or not value:
            return ToolResult(status=ToolResultStatus.ERROR, error="key 和 value 不能为空")

        if category not in ("basic", "health", "preference"):
            return ToolResult(status=ToolResultStatus.ERROR, error="category 必须是 basic/health/preference")

        if source not in ("user_input", "inferred", "tool_result", "confirmed"):
            return ToolResult(status=ToolResultStatus.ERROR, error="source 必须是 user_input/inferred/tool_result/confirmed")

        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            return ToolResult(status=ToolResultStatus.ERROR, error="confidence 必须是 0.0-1.0 之间的数值")

        now = datetime.now().isoformat()

        with self._conn() as conn:
            # UPSERT: 先尝试更新，如果不存在则插入
            cursor = conn.execute("""
                INSERT INTO user_profiles (key, value, category, source, confidence, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    category = excluded.category,
                    source = excluded.source,
                    confidence = excluded.confidence,
                    updated_at = excluded.updated_at
            """, (key, value, category, source, confidence, now))
            conn.commit()

        category_icons = {"basic": "📋", "health": "🏥", "preference": "⚙️"}
        icon = category_icons.get(category, "📝")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 用户信息已更新\n{icon} {key}: {value}\n📂 分类: {category} | 来源: {source}",
            data={"key": key, "value": value, "category": category, "source": source},
        )

    def _query_profile(self, params: dict[str, Any]) -> ToolResult:
        key = params.get("key", "").strip()
        category = params.get("category", "").strip()

        clauses: list[str] = []
        values: list[Any] = []

        if key:
            clauses.append("key = ?")
            values.append(key)
        if category:
            clauses.append("category = ?")
            values.append(category)

        where = " AND ".join(clauses) if clauses else "1=1"
        sql = f"SELECT key, value, category, source, confidence, updated_at FROM user_profiles WHERE {where} ORDER BY category, key"

        with self._conn() as conn:
            rows = conn.execute(sql, values).fetchall()

        if not rows:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="未找到用户档案信息。",
                data={"profiles": [], "count": 0},
            )

        # 按分类组织输出
        category_icons = {"basic": "📋", "health": "🏥", "preference": "⚙️"}
        category_names = {"basic": "基础信息", "health": "健康信息", "preference": "偏好设置"}

        profiles_by_category: dict[str, list[dict]] = {}
        data_list = []

        for row in rows:
            k, v, cat, src, conf, updated = row
            if cat not in profiles_by_category:
                profiles_by_category[cat] = []
            profiles_by_category[cat].append({"key": k, "value": v, "source": src, "confidence": conf})
            data_list.append({
                "key": k, "value": v, "category": cat,
                "source": src, "confidence": conf, "updated_at": updated,
            })

        lines = [f"👤 用户档案 ({len(rows)} 项)"]
        for cat, items in profiles_by_category.items():
            icon = category_icons.get(cat, "📝")
            name = category_names.get(cat, cat)
            lines.append(f"\n{icon} **{name}**")
            for item in items:
                conf_str = f" ({item['confidence']*100:.0f}%)" if item['confidence'] < 1.0 else ""
                lines.append(f"  • {item['key']}: {item['value']}{conf_str}")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"profiles": data_list, "count": len(data_list)},
        )

    def _add_family_member(self, params: dict[str, Any]) -> ToolResult:
        name = params.get("name", "").strip()
        relationship = params.get("relationship", "").strip()
        birthday = params.get("birthday", "").strip() or None
        gender = params.get("gender", "").strip() or None
        notes = params.get("notes", "").strip() or None

        if not name or not relationship:
            return ToolResult(status=ToolResultStatus.ERROR, error="name 和 relationship 不能为空")

        # 验证生日格式
        if birthday:
            try:
                datetime.strptime(birthday, "%Y-%m-%d")
            except ValueError:
                return ToolResult(status=ToolResultStatus.ERROR, error="生日格式错误，请使用 YYYY-MM-DD")

        now = datetime.now().isoformat()

        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO family_members (name, relationship, birthday, gender, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, relationship, birthday, gender, notes, now, now))
            conn.commit()
            member_id = cursor.lastrowid

        rel_display = self._get_relationship_display(relationship)
        gender_icon = "👦" if gender == "male" else "👧" if gender == "female" else "👤"

        output = f"✅ 家庭成员已添加 (ID: {member_id})\n{gender_icon} {name} | 关系: {rel_display}"
        if birthday:
            output += f"\n🎂 生日: {birthday}"
        if notes:
            output += f"\n📝 备注: {notes}"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"member_id": member_id, "name": name, "relationship": relationship},
        )

    def _update_family_member(self, params: dict[str, Any]) -> ToolResult:
        member_id = params.get("id")
        if member_id is None:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少 id")

        with self._conn() as conn:
            row = conn.execute(
                "SELECT name FROM family_members WHERE id = ?", (member_id,)
            ).fetchone()
            if not row:
                return ToolResult(status=ToolResultStatus.ERROR, error=f"成员不存在: ID {member_id}")

        updates: dict[str, Any] = {}
        for key in ("name", "relationship", "birthday", "gender", "notes"):
            if key in params and params[key] is not None:
                updates[key] = params[key] if params[key] else None

        if not updates:
            return ToolResult(status=ToolResultStatus.ERROR, error="没有可更新的字段")

        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [member_id]

        with self._conn() as conn:
            conn.execute(f"UPDATE family_members SET {set_clause} WHERE id = ?", values)
            conn.commit()

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 已更新家庭成员 ID: {member_id}",
            data={"member_id": member_id, "updated_fields": list(updates.keys())},
        )

    def _add_social_contact(self, params: dict[str, Any]) -> ToolResult:
        name = params.get("name", "").strip()
        relationship = params.get("relationship", "").strip() or None
        birthday = params.get("birthday", "").strip() or None
        contact_info_str = params.get("contact_info", "").strip()
        importance_level = params.get("importance_level", 3)

        if not name:
            return ToolResult(status=ToolResultStatus.ERROR, error="name 不能为空")

        # 验证生日格式
        if birthday:
            try:
                datetime.strptime(birthday, "%Y-%m-%d")
            except ValueError:
                return ToolResult(status=ToolResultStatus.ERROR, error="生日格式错误，请使用 YYYY-MM-DD")

        # 验证重要级别
        if not isinstance(importance_level, int) or importance_level < 1 or importance_level > 5:
            return ToolResult(status=ToolResultStatus.ERROR, error="importance_level 必须是 1-5 之间的整数")

        # 解析联系方式 JSON
        contact_info = "{}"
        if contact_info_str:
            try:
                parsed = json.loads(contact_info_str)
                if isinstance(parsed, dict):
                    contact_info = json.dumps(parsed, ensure_ascii=False)
                else:
                    return ToolResult(status=ToolResultStatus.ERROR, error="contact_info 必须是 JSON 对象格式")
            except json.JSONDecodeError:
                return ToolResult(status=ToolResultStatus.ERROR, error="contact_info JSON 格式错误")

        now = datetime.now().isoformat()

        with self._conn() as conn:
            cursor = conn.execute("""
                INSERT INTO social_contacts
                (name, relationship, birthday, contact_info, importance_level, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, relationship, birthday, contact_info, importance_level, now, now))
            conn.commit()
            contact_id = cursor.lastrowid

        rel_display = self._get_relationship_display(relationship) if relationship else "联系人"
        importance_icon = _IMPORTANCE_ICONS.get(importance_level, "⭐⭐⭐")

        output = f"✅ 联系人已添加 (ID: {contact_id})\n👤 {name} | {rel_display}\n{importance_icon} 重要程度: {importance_level}/5"
        if birthday:
            output += f"\n🎂 生日: {birthday}"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"contact_id": contact_id, "name": name, "importance_level": importance_level},
        )

    def _query_contacts(self, params: dict[str, Any]) -> ToolResult:
        name = params.get("name", "").strip()
        relationship = params.get("relationship", "").strip()
        importance_level = params.get("importance_level")

        clauses: list[str] = []
        values: list[Any] = []

        if name:
            clauses.append("name LIKE ?")
            values.append(f"%{name}%")
        if relationship:
            clauses.append("relationship = ?")
            values.append(relationship)
        if importance_level is not None:
            clauses.append("importance_level >= ?")
            values.append(importance_level)

        where = " AND ".join(clauses) if clauses else "1=1"
        sql = f"""
            SELECT id, name, relationship, birthday, contact_info, importance_level, last_contact_date
            FROM social_contacts WHERE {where}
            ORDER BY importance_level DESC, name
        """

        with self._conn() as conn:
            rows = conn.execute(sql, values).fetchall()

        if not rows:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="未找到符合条件的联系人。",
                data={"contacts": [], "count": 0},
            )

        lines = [f"📇 联系人列表 ({len(rows)} 人)"]
        data_list = []

        for row in rows:
            cid, cname, crel, cbday, cinfo, cimp, clast = row
            rel_display = self._get_relationship_display(crel) if crel else ""
            imp_icon = _IMPORTANCE_ICONS.get(cimp, "⭐⭐⭐")

            line = f"  {imp_icon} **{cname}**"
            if rel_display:
                line += f" ({rel_display})"
            line += f" [ID:{cid}]"
            lines.append(line)

            if cbday:
                days = self._calculate_days_until_birthday(cbday)
                days_str = f" (还有{days}天)" if days is not None else ""
                lines.append(f"      🎂 {cbday}{days_str}")

            data_list.append({
                "id": cid, "name": cname, "relationship": crel,
                "birthday": cbday, "importance_level": cimp,
                "last_contact_date": clast,
            })

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"contacts": data_list, "count": len(data_list)},
        )

    def _get_upcoming_birthdays(self, params: dict[str, Any]) -> ToolResult:
        days = params.get("days", 30)
        if not isinstance(days, int) or days < 1:
            days = 30

        today = datetime.now().date()
        end_date = today + timedelta(days=days)

        birthdays: list[dict] = []

        with self._conn() as conn:
            # 查询家庭成员生日
            family_rows = conn.execute(
                "SELECT id, name, relationship, birthday FROM family_members WHERE birthday IS NOT NULL"
            ).fetchall()

            for fid, fname, frel, fbday in family_rows:
                days_until = self._calculate_days_until_birthday(fbday)
                if days_until is not None and days_until <= days:
                    birthdays.append({
                        "type": "family",
                        "id": fid,
                        "name": fname,
                        "relationship": self._get_relationship_display(frel),
                        "birthday": fbday,
                        "days_until": days_until,
                    })

            # 查询社交联系人生日
            contact_rows = conn.execute(
                "SELECT id, name, relationship, birthday, importance_level FROM social_contacts WHERE birthday IS NOT NULL"
            ).fetchall()

            for cid, cname, crel, cbday, cimp in contact_rows:
                days_until = self._calculate_days_until_birthday(cbday)
                if days_until is not None and days_until <= days:
                    birthdays.append({
                        "type": "contact",
                        "id": cid,
                        "name": cname,
                        "relationship": self._get_relationship_display(crel) if crel else "联系人",
                        "birthday": cbday,
                        "days_until": days_until,
                        "importance_level": cimp,
                    })

        # 按天数排序
        birthdays.sort(key=lambda x: x["days_until"])

        if not birthdays:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"🎂 未来 {days} 天内没有生日。",
                data={"birthdays": [], "count": 0},
            )

        lines = [f"🎂 未来 {days} 天内的生日 ({len(birthdays)} 人)"]
        for b in birthdays:
            icon = "👨‍👩‍👧‍👦" if b["type"] == "family" else "👤"
            days_str = "今天🎉" if b["days_until"] == 0 else f"还有 {b['days_until']} 天"
            # 提取月-日显示
            bday_md = b["birthday"][5:] if b["birthday"] else ""
            lines.append(f"  {icon} **{b['name']}** ({b['relationship']}) - {bday_md} ({days_str})")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"birthdays": birthdays, "count": len(birthdays)},
        )

    def _record_child_growth(self, params: dict[str, Any]) -> ToolResult:
        member_id = params.get("member_id")
        height_cm = params.get("height_cm")
        weight_kg = params.get("weight_kg")
        note = params.get("note", "").strip() or None
        date = params.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")

        if member_id is None:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少 member_id")

        if height_cm is None and weight_kg is None and not note:
            return ToolResult(status=ToolResultStatus.ERROR, error="至少需要记录身高、体重或备注中的一项")

        # 验证日期格式
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return ToolResult(status=ToolResultStatus.ERROR, error="日期格式错误，请使用 YYYY-MM-DD")

        with self._conn() as conn:
            # 查找成员
            row = conn.execute(
                "SELECT name, relationship, growth_data FROM family_members WHERE id = ?",
                (member_id,)
            ).fetchone()
            if not row:
                return ToolResult(status=ToolResultStatus.ERROR, error=f"成员不存在: ID {member_id}")

            name, relationship, growth_data_str = row

            # 解析现有数据
            try:
                growth_data = json.loads(growth_data_str) if growth_data_str else []
            except json.JSONDecodeError:
                growth_data = []

            # 添加新记录
            new_record: dict[str, Any] = {"date": date}
            if height_cm is not None:
                new_record["height_cm"] = float(height_cm)
            if weight_kg is not None:
                new_record["weight_kg"] = float(weight_kg)
            if note:
                new_record["note"] = note

            growth_data.append(new_record)

            # 写回数据库
            now = datetime.now().isoformat()
            conn.execute("""
                UPDATE family_members SET growth_data = ?, updated_at = ? WHERE id = ?
            """, (json.dumps(growth_data, ensure_ascii=False), now, member_id))
            conn.commit()

        rel_display = self._get_relationship_display(relationship)
        output = f"✅ 成长记录已添加\n👶 {name} ({rel_display}) - {date}"
        if height_cm is not None:
            output += f"\n📏 身高: {height_cm} cm"
        if weight_kg is not None:
            output += f"\n⚖️ 体重: {weight_kg} kg"
        if note:
            output += f"\n📝 备注: {note}"

        # 显示最近的成长趋势
        if len(growth_data) >= 2:
            recent = sorted(growth_data, key=lambda x: x.get("date", ""), reverse=True)[:3]
            output += "\n\n📊 最近记录:"
            for r in recent:
                parts = [r.get("date", "")]
                if "height_cm" in r:
                    parts.append(f"{r['height_cm']}cm")
                if "weight_kg" in r:
                    parts.append(f"{r['weight_kg']}kg")
                output += f"\n  • {' | '.join(parts)}"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={
                "member_id": member_id,
                "name": name,
                "record": new_record,
                "total_records": len(growth_data),
            },
        )
