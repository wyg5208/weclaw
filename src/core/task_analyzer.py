"""任务智能分析引擎 — 多维度分析用户信息，生成每日任务推荐。

分析维度：
1. 待办事项分析 — 优先级排序、截止时间压力、时间周期匹配、重复任务识别
2. 家庭成员关联分析 — 生日提醒、纪念日、子女课程接送、配偶工作安排
3. 对话记录分析 — NLP提取潜在任务、用户承诺事项、关注话题
4. 健康与上下文分析 — 用药提醒、运动计划、体检安排、天气影响任务

使用示例：
    analyzer = TaskAnalyzer()
    result = await analyzer.analyze_and_recommend("2026-03-25")
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Generator

from src.tools.todo_storage import (
    DailyRecommendation,
    DailyTask,
    RecommendationStatus,
    TaskCategory,
    TimeFrame,
    Todo,
    TodoStatus,
    TodoStorage,
)

logger = logging.getLogger(__name__)

# 默认数据库路径
_DEFAULT_DB = Path.home() / ".winclaw" / "winclaw_tools.db"


# ----------------------------------------------------------------------
# 对话记录分析相关常量
# ----------------------------------------------------------------------

# 潜在任务关键词
_TASK_KEYWORDS = [
    "需要", "要", "得", "必须", "应该", "计划", "安排", "准备",
    "记得", "别忘了", "别忘了", "提醒我", "记得提醒",
    "明天", "后天", "下周", "周末", "月底", "下个月",
    "去", "买", "做", "完成", "提交", "发送", "参加",
    "会议", "约会", "面试", "考试", "课程", "培训",
    "接", "送", "预约", "挂号", "体检",
]

# 承诺性关键词
_COMMITMENT_KEYWORDS = [
    "我会", "我将", "我来", "我会去", "我来做",
    "保证", "承诺", "答应", "说好",
]

# 健康/运动关键词
_HEALTH_KEYWORDS = [
    "吃药", "用药", "服药", "复诊", "复查",
    "运动", "锻炼", "跑步", "健身", "游泳",
    "体检", "检查", "预约",
]


class TaskAnalyzer:
    """任务智能分析引擎。

    综合分析用户的待办事项、家庭成员、对话记录、健康数据等多维度信息，
    智能生成每日任务推荐。
    """

    def __init__(self, db_path: Path | str | None = None):
        """初始化分析引擎。

        Args:
            db_path: 数据库路径
        """
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._storage = TodoStorage(self._db_path)

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        """获取数据库连接。"""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    async def analyze_and_recommend(self, target_date: str) -> dict[str, Any]:
        """综合分析生成每日任务推荐。

        Args:
            target_date: 目标日期 YYYY-MM-DD

        Returns:
            包含推荐任务和分析摘要的字典
        """
        logger.info("开始分析生成每日任务推荐: %s", target_date)

        # 收集上下文信息
        context = await self._gather_context(target_date)

        recommendations = []

        # 1. 待办事项分析
        todo_tasks = await self._analyze_todos(context)
        recommendations.extend(todo_tasks)
        logger.debug("待办事项分析: %d 条推荐", len(todo_tasks))

        # 2. 家庭成员关联分析
        family_tasks = await self._analyze_family_members(context)
        recommendations.extend(family_tasks)
        logger.debug("家庭成员分析: %d 条推荐", len(family_tasks))

        # 3. 对话记录分析
        conversation_tasks = await self._analyze_conversations(context)
        recommendations.extend(conversation_tasks)
        logger.debug("对话记录分析: %d 条推荐", len(conversation_tasks))

        # 4. 健康与上下文分析
        context_tasks = await self._analyze_health_context(context)
        recommendations.extend(context_tasks)
        logger.debug("健康上下文分析: %d 条推荐", len(context_tasks))

        # 5. 去重与排序
        final_tasks = self._rank_and_filter(recommendations)

        # 6. 生成分析摘要
        analysis_summary = self._generate_summary(context, final_tasks)

        # 7. 存储推荐记录
        rec = DailyRecommendation(
            task_date=target_date,
            recommendations=final_tasks,
            analysis_summary=analysis_summary,
        )
        self._storage.create_recommendation(rec)

        logger.info("分析完成，生成 %d 条推荐任务", len(final_tasks))

        return {
            "date": target_date,
            "recommendations": final_tasks,
            "analysis_summary": analysis_summary,
            "context_summary": {
                "todos_count": len(context.get("todos", [])),
                "overdue_count": len(context.get("overdue", [])),
                "upcoming_count": len(context.get("upcoming", [])),
                "family_events_count": len(context.get("family_events", [])),
                "conversation_tasks_count": len(context.get("conversation_tasks", [])),
            }
        }

    async def _gather_context(self, target_date: str) -> dict[str, Any]:
        """收集分析所需的上下文信息。"""
        context: dict[str, Any] = {
            "target_date": target_date,
            "todos": [],
            "overdue": [],
            "upcoming": [],
            "family_members": [],
            "family_events": [],
            "recent_conversations": [],
            "conversation_tasks": [],
            "health_data": {},
            "weather": None,
            "holidays": [],
        }

        # 1. 获取待办事项
        try:
            context["todos"] = self._storage.list_todos(include_completed=False, limit=50)
            context["overdue"] = self._storage.get_overdue_todos()
            context["upcoming"] = self._storage.get_upcoming_todos(days=7)
        except Exception as e:
            logger.warning("获取待办事项失败: %s", e)

        # 2. 获取家庭成员信息
        try:
            context["family_members"] = self._get_family_members()
            context["family_events"] = self._get_family_events(target_date)
        except Exception as e:
            logger.warning("获取家庭成员信息失败: %s", e)

        # 3. 获取近期对话记录
        try:
            context["recent_conversations"] = self._get_recent_conversations(days=7)
            context["conversation_tasks"] = self._extract_tasks_from_conversations(
                context["recent_conversations"]
            )
        except Exception as e:
            logger.warning("获取对话记录失败: %s", e)

        # 4. 获取健康数据（从用户档案）
        try:
            context["health_data"] = self._get_health_data()
        except Exception as e:
            logger.warning("获取健康数据失败: %s", e)

        return context

    # ------------------------------------------------------------------
    # 待办事项分析
    # ------------------------------------------------------------------

    async def _analyze_todos(self, context: dict) -> list[dict]:
        """分析待办事项数据。"""
        recommendations = []
        today = context["target_date"]

        # 1. 过期任务 - 最高优先级
        for todo in context.get("overdue", []):
            recommendations.append({
                "source": "todo_overdue",
                "todo_id": todo.id,
                "title": todo.title,
                "description": todo.description,
                "category": todo.category.value,
                "priority": todo.priority,
                "deadline": todo.deadline,
                "ai_confidence": 0.95,
                "ai_reason": "任务已过期，建议优先处理",
                "score": 100,
            })

        # 2. 今日到期任务
        today_todos = [
            t for t in context.get("upcoming", [])
            if t.deadline and t.deadline.startswith(today)
        ]
        for todo in today_todos:
            recommendations.append({
                "source": "todo_today",
                "todo_id": todo.id,
                "title": todo.title,
                "description": todo.description,
                "category": todo.category.value,
                "priority": todo.priority,
                "deadline": todo.deadline,
                "ai_confidence": 0.90,
                "ai_reason": "任务今日到期",
                "score": 90,
            })

        # 3. 本周到期任务
        week_later = (datetime.strptime(today, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
        week_todos = [
            t for t in context.get("upcoming", [])
            if t.deadline and t.deadline <= week_later and t.deadline > today
        ]
        for todo in week_todos[:5]:  # 限制数量
            recommendations.append({
                "source": "todo_week",
                "todo_id": todo.id,
                "title": todo.title,
                "description": todo.description,
                "category": todo.category.value,
                "priority": todo.priority,
                "deadline": todo.deadline,
                "ai_confidence": 0.75,
                "ai_reason": "任务本周内到期",
                "score": 70,
            })

        # 4. 高优先级待办
        high_priority = [t for t in context.get("todos", []) if t.priority <= 2][:3]
        for todo in high_priority:
            if todo.id not in [r.get("todo_id") for r in recommendations]:
                recommendations.append({
                    "source": "todo_priority",
                    "todo_id": todo.id,
                    "title": todo.title,
                    "description": todo.description,
                    "category": todo.category.value,
                    "priority": todo.priority,
                    "deadline": todo.deadline,
                    "ai_confidence": 0.70,
                    "ai_reason": "高优先级任务",
                    "score": 60,
                })

        # 5. 重复任务检测
        recurring = [t for t in context.get("todos", []) if t.recurrence.value != "none"]
        for todo in recurring:
            if self._should_trigger_recurring(todo, today):
                recommendations.append({
                    "source": "todo_recurring",
                    "todo_id": todo.id,
                    "title": todo.title,
                    "description": todo.description,
                    "category": todo.category.value,
                    "priority": todo.priority,
                    "ai_confidence": 0.85,
                    "ai_reason": f"重复任务: {todo.recurrence.value}",
                    "score": 80,
                })

        return recommendations

    # ------------------------------------------------------------------
    # 家庭成员关联分析
    # ------------------------------------------------------------------

    async def _analyze_family_members(self, context: dict) -> list[dict]:
        """分析家庭成员关联信息。"""
        recommendations = []
        today = context["target_date"]

        # 1. 家庭成员生日提醒
        for event in context.get("family_events", []):
            if event.get("type") == "birthday":
                days_until = event.get("days_until", 0)
                member_name = event.get("name", "")

                if days_until == 0:
                    recommendations.append({
                        "source": "family_birthday",
                        "title": f"🎂 {member_name}的生日",
                        "description": f"今天是{member_name}的生日，记得送上祝福",
                        "category": "family",
                        "priority": 1,
                        "ai_confidence": 0.95,
                        "ai_reason": "家庭成员生日提醒",
                        "score": 95,
                        "related_member_id": event.get("id"),
                    })
                elif days_until <= 3:
                    recommendations.append({
                        "source": "family_birthday",
                        "title": f"🎂 准备{member_name}的生日礼物",
                        "description": f"{member_name}的生日还有{days_until}天",
                        "category": "family",
                        "priority": 2,
                        "ai_confidence": 0.85,
                        "ai_reason": "家庭成员生日即将到来",
                        "score": 85,
                        "related_member_id": event.get("id"),
                    })

        # 2. 子女接送任务（根据课程表）
        # 这部分需要与 course_schedule 工具集成
        # 这里先做简化处理

        return recommendations

    # ------------------------------------------------------------------
    # 对话记录分析
    # ------------------------------------------------------------------

    async def _analyze_conversations(self, context: dict) -> list[dict]:
        """分析对话记录，提取潜在任务。"""
        recommendations = []

        for task in context.get("conversation_tasks", []):
            recommendations.append({
                "source": "conversation",
                "title": task.get("title", ""),
                "description": task.get("context", ""),
                "category": task.get("category", "general"),
                "priority": task.get("priority", 3),
                "ai_confidence": task.get("confidence", 0.5),
                "ai_reason": f"从对话中识别: {task.get('reason', '')}",
                "score": 40 + int(task.get("confidence", 0.5) * 30),
            })

        return recommendations

    def _get_recent_conversations(self, days: int = 7) -> list[dict]:
        """获取近期对话记录。"""
        conversations = []

        try:
            history_db = Path.home() / ".winclaw" / "history.db"
            if not history_db.exists():
                return conversations

            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            with sqlite3.connect(str(history_db)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT s.id, s.title, s.updated_at,
                           m.role, m.content, m.created_at
                    FROM sessions s
                    LEFT JOIN messages m ON s.id = m.session_id
                    WHERE s.updated_at >= ?
                    AND m.role = 'user'
                    ORDER BY m.created_at DESC
                    LIMIT 100
                """, (start_date,)).fetchall()

                for row in rows:
                    conversations.append({
                        "session_id": row["id"],
                        "title": row["title"],
                        "role": row["role"],
                        "content": row["content"],
                        "created_at": row["created_at"],
                    })
        except Exception as e:
            logger.warning("获取对话记录失败: %s", e)

        return conversations

    def _extract_tasks_from_conversations(self, conversations: list[dict]) -> list[dict]:
        """从对话中提取潜在任务。"""
        tasks = []

        for conv in conversations:
            content = conv.get("content", "")
            if not content or len(content) < 5:
                continue

            # 1. 检测任务关键词
            for keyword in _TASK_KEYWORDS:
                if keyword in content:
                    # 尝试提取任务描述
                    sentences = re.split(r'[。！？\n]', content)
                    for sentence in sentences:
                        if keyword in sentence and len(sentence) > 3:
                            # 简单截取作为任务标题
                            title = sentence.strip()[:50]
                            if title:
                                tasks.append({
                                    "title": title,
                                    "context": f"来源对话: {conv.get('title', '未知')}",
                                    "category": self._guess_category(sentence),
                                    "priority": 3,
                                    "confidence": 0.6,
                                    "reason": "对话中提到任务相关内容",
                                })
                            break
                    break

            # 2. 检测承诺性关键词
            for keyword in _COMMITMENT_KEYWORDS:
                if keyword in content:
                    sentences = re.split(r'[。！？\n]', content)
                    for sentence in sentences:
                        if keyword in sentence and len(sentence) > 3:
                            title = sentence.strip()[:50]
                            if title:
                                tasks.append({
                                    "title": title,
                                    "context": f"承诺事项: {conv.get('title', '未知')}",
                                    "category": "general",
                                    "priority": 2,
                                    "confidence": 0.8,
                                    "reason": "对话中的承诺事项",
                                })
                            break
                    break

        # 去重
        seen_titles = set()
        unique_tasks = []
        for task in tasks:
            if task["title"] not in seen_titles:
                seen_titles.add(task["title"])
                unique_tasks.append(task)

        return unique_tasks[:10]

    def _guess_category(self, text: str) -> str:
        """根据文本内容猜测任务类型。"""
        if any(kw in text for kw in ["工作", "会议", "报告", "项目", "deadline"]):
            return "work"
        if any(kw in text for kw in ["学习", "课程", "作业", "考试", "复习"]):
            return "study"
        if any(kw in text for kw in ["运动", "健身", "体检", "吃药", "医院"]):
            return "health"
        if any(kw in text for kw in ["孩子", "接送", "家长", "配偶", "家人"]):
            return "family"
        if any(kw in text for kw in ["朋友", "聚会", "约会", "见面"]):
            return "social"
        return "general"

    # ------------------------------------------------------------------
    # 健康与上下文分析
    # ------------------------------------------------------------------

    async def _analyze_health_context(self, context: dict) -> list[dict]:
        """分析健康与上下文信息。"""
        recommendations = []
        today = context["target_date"]
        today_dt = datetime.strptime(today, "%Y-%m-%d")
        weekday = today_dt.weekday()  # 0=周一, 6=周日

        # 1. 用药提醒（从健康数据提取）
        health_data = context.get("health_data", {})
        medications = health_data.get("medications", [])
        for med in medications:
            if med.get("time"):
                recommendations.append({
                    "source": "health_medication",
                    "title": f"💊 服药提醒: {med.get('name', '药品')}",
                    "description": f"服药时间: {med.get('time', '')}",
                    "category": "health",
                    "priority": 2,
                    "scheduled_start": med.get("time"),
                    "ai_confidence": 0.90,
                    "ai_reason": "每日用药提醒",
                    "score": 85,
                })

        # 2. 运动计划（工作日推荐）
        if weekday < 5:  # 周一到周五
            exercise_plan = health_data.get("exercise_plan")
            if exercise_plan:
                recommendations.append({
                    "source": "health_exercise",
                    "title": f"🏃 {exercise_plan.get('name', '运动计划')}",
                    "description": exercise_plan.get("description", ""),
                    "category": "health",
                    "priority": 3,
                    "scheduled_start": exercise_plan.get("time", "18:00"),
                    "ai_confidence": 0.70,
                    "ai_reason": "工作日运动计划",
                    "score": 60,
                })

        return recommendations

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _get_family_members(self) -> list[dict]:
        """获取家庭成员列表。"""
        members = []

        try:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT id, name, relationship, birthday FROM family_members"
                ).fetchall()
                for row in rows:
                    members.append({
                        "id": row["id"],
                        "name": row["name"],
                        "relationship": row["relationship"],
                        "birthday": row["birthday"],
                    })
        except Exception as e:
            logger.warning("获取家庭成员失败: %s", e)

        return members

    def _get_family_events(self, target_date: str) -> list[dict]:
        """获取家庭成员相关事件。"""
        events = []

        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            target_md = target_date[5:]  # MM-DD

            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT id, name, relationship, birthday FROM family_members WHERE birthday IS NOT NULL"
                ).fetchall()

                for row in rows:
                    birthday = row["birthday"] or ""
                    if birthday:
                        birthday_md = birthday[5:] if len(birthday) >= 5 else ""

                        # 计算距离生日的天数
                        try:
                            birth_this_year = datetime(
                                target_dt.year,
                                int(birthday_md[:2]),
                                int(birthday_md[3:5])
                            )
                            days_until = (birth_this_year - target_dt).days

                            if days_until < 0:
                                # 已过今年生日，计算明年
                                birth_next_year = datetime(
                                    target_dt.year + 1,
                                    int(birthday_md[:2]),
                                    int(birthday_md[3:5])
                                )
                                days_until = (birth_next_year - target_dt).days

                            events.append({
                                "type": "birthday",
                                "id": row["id"],
                                "name": row["name"],
                                "relationship": row["relationship"],
                                "birthday": birthday,
                                "days_until": days_until,
                            })
                        except (ValueError, IndexError):
                            pass
        except Exception as e:
            logger.warning("获取家庭成员事件失败: %s", e)

        return events

    def _get_health_data(self) -> dict[str, Any]:
        """获取用户健康数据。"""
        health_data: dict[str, Any] = {
            "medications": [],
            "exercise_plan": None,
        }

        try:
            with self._conn() as conn:
                # 尝试从用户档案获取健康相关信息
                rows = conn.execute("""
                    SELECT key, value FROM user_profiles
                    WHERE category = 'health'
                """).fetchall()

                for row in rows:
                    key = row["key"]
                    value = row["value"]
                    if key == "medications":
                        try:
                            health_data["medications"] = json.loads(value)
                        except json.JSONDecodeError:
                            pass
                    elif key == "exercise_plan":
                        try:
                            health_data["exercise_plan"] = json.loads(value)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.debug("获取健康数据失败: %s", e)

        return health_data

    def _should_trigger_recurring(self, todo: Todo, target_date: str) -> bool:
        """判断重复任务是否应该在目标日期触发。"""
        if not todo.start_date:
            return False

        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            start_dt = datetime.strptime(todo.start_date, "%Y-%m-%d")

            if todo.recurrence.value == "daily":
                return (target_dt - start_dt).days >= 0
            elif todo.recurrence.value == "weekly":
                return (target_dt - start_dt).days % 7 == 0 and (target_dt - start_dt).days >= 0
            elif todo.recurrence.value == "monthly":
                return target_dt.day == start_dt.day
            elif todo.recurrence.value == "yearly":
                return target_dt.month == start_dt.month and target_dt.day == start_dt.day
        except ValueError:
            pass

        return False

    def _rank_and_filter(self, recommendations: list[dict]) -> list[dict]:
        """排序与筛选推荐任务。"""
        if not recommendations:
            return []

        # 计算综合评分
        for task in recommendations:
            score = task.get("score", 0)

            # 优先级加权
            priority = task.get("priority", 3)
            score += (6 - priority) * 15

            # AI置信度加权
            confidence = task.get("ai_confidence", 0.5)
            score += int(confidence * 30)

            # 时效性加权
            if task.get("deadline"):
                score += 10

            task["final_score"] = score

        # 按评分排序
        sorted_tasks = sorted(
            recommendations,
            key=lambda x: x.get("final_score", 0),
            reverse=True
        )

        # 去重（基于 todo_id 或 title）
        seen = set()
        unique_tasks = []
        for task in sorted_tasks:
            key = task.get("todo_id") or task.get("title")
            if key not in seen:
                seen.add(key)
                unique_tasks.append(task)

        return unique_tasks[:10]

    def _generate_summary(self, context: dict, recommendations: list[dict]) -> str:
        """生成分析摘要。"""
        parts = []

        overdue_count = len(context.get("overdue", []))
        if overdue_count > 0:
            parts.append(f"有 {overdue_count} 个过期任务需优先处理")

        upcoming_count = len(context.get("upcoming", []))
        if upcoming_count > 0:
            parts.append(f"{upcoming_count} 个任务本周到期")

        family_events = context.get("family_events", [])
        birthday_count = sum(1 for e in family_events if e.get("type") == "birthday" and e.get("days_until", 99) <= 7)
        if birthday_count > 0:
            parts.append(f"{birthday_count} 位家庭成员生日即将到来")

        conv_tasks = len(context.get("conversation_tasks", []))
        if conv_tasks > 0:
            parts.append(f"从对话中识别 {conv_tasks} 个潜在任务")

        if parts:
            return "；".join(parts) + "。"
        return "今日暂无特别需要关注的任务。"
