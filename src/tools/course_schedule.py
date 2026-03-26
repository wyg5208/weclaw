"""课程表工具 — 家庭成员周课程表管理。

支持动作：
- create_schedule: 为家庭成员创建课程表
- search_courses: 搜索/查询课程表（完整/按天）
- add_course: 添加课程项目
- edit_course: 编辑课程项目
- delete_course: 删除课程项目或整个课程表

存储位置：.qoder/data/schedules/{成员名}.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# 默认数据存储路径
_DEFAULT_SCHEDULES_DIR = Path(__file__).resolve().parent.parent.parent / ".qoder" / "data" / "schedules"

# 星期列表
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 课程类型
COURSE_TYPES = ["course", "break", "activity", "rest"]


def _calculate_pinyin_similarity(name1: str, name2: str) -> float:
    """计算两个姓名的拼音相似度（简单版：基于声母韵母）。
    
    Args:
        name1: 姓名 1
        name2: 姓名 2
        
    Returns:
        相似度分数 0.0-1.0
    """
    # 常见同音字映射（简化版，可扩展）
    pinyin_map = {
        '温': ['wen'], '文': ['wen'], '闻': ['wen'],
        '佳': ['jia'], '家': ['jia'], '加': ['jia'], '嘉': ['jia'],
        '露': ['lu'], '路': ['lu'], '陆': ['lu'], '鹿': ['lu'],
        '小': ['xiao'], '晓': ['xiao'], '笑': ['xiao'],
        '翁': ['weng'], '嗡': ['weng'],
        '迦': ['jia'], '加': ['jia'], '家': ['jia'], '佳': ['jia'],
        '鹿': ['lu'], '路': ['lu'], '露': ['lu'], '陆': ['lu'],
        '儿': ['er'], '而': ['er'], '尔': ['er'],
        '张': ['zhang'], '章': ['zhang'],
        '明': ['ming'], '名': ['ming'],
        '王': ['wang'], '汪': ['wang'],
        '芳': ['fang'], '方': ['fang'],
        '李': ['li'], '里': ['li'],
        '伟': ['wei'], '维': ['wei'],
        '溪': ['xi'], '西': ['xi'], '希': ['xi'],
    }
    
    # 获取每个字的拼音
    def get_pinyins(name):
        result = []
        for char in name:
            result.extend(pinyin_map.get(char, [char.lower()]))
        return result
    
    pinyin1 = get_pinyins(name1)
    pinyin2 = get_pinyins(name2)
    
    if not pinyin1 or not pinyin2:
        return 0.0
    
    # 简单的编辑距离相似度
    max_len = max(len(pinyin1), len(pinyin2))
    if max_len == 0:
        return 1.0
    
    matches = sum(1 for i in range(min(len(pinyin1), len(pinyin2))) if pinyin1[i] == pinyin2[i])
    return matches / max_len


def _calculate_string_similarity(s1: str, s2: str) -> float:
    """计算两个字符串的相似度（考虑长度差异和字符匹配）。
    
    Args:
        s1: 字符串 1
        s2: 字符串 2
        
    Returns:
        相似度分数 0.0-1.0
    """
    if s1 == s2:
        return 1.0
    
    # 检查是否包含关系
    if s1 in s2 or s2 in s1:
        return 0.8
    
    # 计算编辑距离
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    
    # 创建编辑距离矩阵
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1]) + 1
    
    edit_distance = dp[len1][len2]
    max_len = max(len1, len2)
    similarity = 1 - (edit_distance / max_len)
    
    return similarity


class CourseScheduleTool(BaseTool):
    """课程表管理工具。

    支持家庭成员周课程表的创建、查询、编辑和删除。
    每个成员一个 JSON 文件，存储在 .qoder/data/schedules/ 目录下。
    """

    name = "course_schedule"
    emoji = "📅"
    title = "课程表"
    description = "家庭成员课程表管理：创建、查询、编辑、删除周课程表"

    # 昵称映射表：昵称/小名 → 正式名称
    NICKNAME_MAP = {
        "小鹿儿": "翁迦鹿",  # 小鹿儿是翁迦鹿的昵称
        "小翁": "翁迦鹿",
        "迦迦": "翁迦鹿",
        "溪溪": "小溪溪",
        "小翁老师": "翁勇刚",  # 假设用户可能有这个称呼
    }

    def __init__(self, schedules_dir: str = ""):
        super().__init__()
        self._schedules_dir = Path(schedules_dir) if schedules_dir else _DEFAULT_SCHEDULES_DIR
        self._schedules_dir.mkdir(parents=True, exist_ok=True)
        # 缓存已知的家庭成员名单
        self._known_members_cache = set()
        self._refresh_members_cache()
    
    def _refresh_members_cache(self) -> None:
        """刷新已知家庭成员名单缓存"""
        self._known_members_cache.clear()
        if self._schedules_dir.exists():
            for file in self._schedules_dir.glob("*.json"):
                member_name = file.stem
                self._known_members_cache.add(member_name)
    
    def _find_best_matching_member(self, input_name: str) -> str | None:
        """查找最匹配的家庭成员名称（智能纠错 + 昵称映射）。
        
        Args:
            input_name: 用户输入的姓名（可能有语音识别错误或是昵称）
            
        Returns:
            最佳匹配的姓名，如果没有找到则返回 None
        """
        # 确保缓存是最新的
        self._refresh_members_cache()
        
        if not self._known_members_cache:
            return None
        
        # 0. 检查是否是昵称
        if input_name in self.NICKNAME_MAP:
            formal_name = self.NICKNAME_MAP[input_name]
            logger.info(f"昵称映射：'{input_name}' → '{formal_name}'")
            # 检查正式名称是否在缓存中
            if formal_name in self._known_members_cache:
                return formal_name
            else:
                logger.warning(f"昵称映射的正式名称 '{formal_name}' 不在已知成员中")
                return None
        
        # 1. 精确匹配（优先）
        if input_name in self._known_members_cache:
            logger.info(f"精确匹配姓名：{input_name}")
            return input_name
        
        # 2. 模糊匹配
        best_match = None
        best_score = 0.0
        
        for known_name in self._known_members_cache:
            # 综合相似度：字符串相似度 + 拼音相似度
            str_sim = _calculate_string_similarity(input_name, known_name)
            pinyin_sim = _calculate_pinyin_similarity(input_name, known_name)
            
            # 加权平均（拼音相似度权重更高，因为语音识别主要是同音字错误）
            combined_score = str_sim * 0.3 + pinyin_sim * 0.7
            
            logger.debug(f"姓名匹配度：'{input_name}' vs '{known_name}': {combined_score:.3f} (字符串:{str_sim:.3f}, 拼音:{pinyin_sim:.3f})")
            
            if combined_score > best_score:
                best_score = combined_score
                best_match = known_name
        
        # 3. 判断是否接受匹配结果
        if best_score >= 0.6:  # 阈值可调
            logger.info(f"模糊匹配成功：'{input_name}' → '{best_match}' (相似度：{best_score:.3f})")
            return best_match
        elif best_score >= 0.4:
            logger.warning(f"低置信度匹配：'{input_name}' → '{best_match}' (相似度：{best_score:.3f})")
            return best_match  # 仍然返回，但记录警告
        else:
            logger.warning(f"未找到匹配的家庭成员：'{input_name}'，已知成员：{self._known_members_cache}")
            return None

    def _get_schedule_path(self, member_name: str) -> Path:
        """获取课程表文件路径"""
        return self._schedules_dir / f"{member_name}.json"

    def _load_schedule(self, member_name: str) -> dict | None:
        """加载课程表数据"""
        path = self._get_schedule_path(member_name)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载课程表失败: {e}")
            return None

    def _save_schedule(self, data: dict) -> None:
        """保存课程表数据"""
        data["updated_at"] = datetime.now().isoformat()
        path = self._get_schedule_path(data["member_name"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _create_empty_schedule(self, member_name: str) -> dict:
        """创建空的课程表结构"""
        return {
            "member_name": member_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "schedule": {day: [] for day in WEEKDAYS}
        }

    def _validate_time_format(self, time_str: str) -> bool:
        """验证时间格式 HH:MM"""
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                return False
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, IndexError):
            return False

    def _check_time_conflict(self, day_schedule: list, start_time: str, end_time: str, exclude_id: str = None) -> str | None:
        """检查时间冲突"""
        for item in day_schedule:
            if exclude_id and item["id"] == exclude_id:
                continue
            if start_time < item["end_time"] and end_time > item["start_time"]:
                return f"时间冲突：{start_time}-{end_time} 与 {item['name']}({item['start_time']}-{item['end_time']})重叠"
        return None

    def _generate_course_id(self, course_type: str, index: int) -> str:
        """生成课程ID"""
        type_prefix = {"course": "course", "break": "break", "activity": "activity", "rest": "rest"}
        return f"{type_prefix.get(course_type, 'course')}_{index:03d}"

    def _format_schedule_output(self, data: dict, day: str = None) -> str:
        """格式化课程表输出"""
        member_name = data["member_name"]
        schedule = data["schedule"]

        lines = [f"📅 {member_name} 的{'周' if not day else ''}课程表"]
        lines.append("━" * 50)

        total_items = 0
        days_to_show = [day] if day else WEEKDAYS

        for d in days_to_show:
            day_schedule = schedule.get(d, [])
            if day_schedule:
                lines.append(f"\n📆 {d}")
                lines.append("-" * 50)
                sorted_items = sorted(day_schedule, key=lambda x: x["order"])
                for item in sorted_items:
                    order_label = self._get_order_label(item)
                    type_label = {"course": "课程", "break": "课间", "activity": "活动", "rest": "休息"}.get(item["type"], "其他")
                    note_str = f" ({item['note']})" if item.get("note") else ""
                    lines.append(f"  {order_label} │ {item['start_time']}-{item['end_time']} │ {item['name']}{note_str} │ {type_label}")
                total_items += len(day_schedule)
            elif day is None:
                # 完整查询时显示空课程的天
                pass

        if day is None:
            lines.append(f"\n📊 统计：共 {total_items} 个课程项目")
        else:
            lines.append(f"\n📊 共 {len(schedule.get(day, []))} 个项目")

        return "\n".join(lines)

    def _get_order_label(self, item: dict) -> str:
        """获取顺序标签"""
        order = item["order"]
        if item["type"] == "course":
            if order == int(order):
                return f"第{int(order)}节".ljust(6)
        return {"break": "课间 ", "activity": "活动 ", "rest": "休息 "}.get(item["type"], "     ")

    # ------------------------------------------------------------------
    # Action 定义
    # ------------------------------------------------------------------

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="create_schedule",
                description="为家庭成员创建新的周课程表",
                parameters={
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称，如：小溪溪",
                    },
                },
                required_params=["member_name"],
            ),
            ActionDef(
                name="search_courses",
                description="搜索/查询家庭成员的课程表，可指定星期查看当天课程",
                parameters={
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称",
                    },
                    "day": {
                        "type": "string",
                        "description": "星期（可选），如：周一、周二...周日，或不带星期的日期如：今天、明天",
                    },
                    "date": {
                        "type": "string",
                        "description": "日期（可选），格式：YYYY-MM-DD，如：2026-03-26",
                    },
                },
                required_params=["member_name"],
            ),
            ActionDef(
                name="add_course",
                description="添加课程项目到课程表",
                parameters={
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称",
                    },
                    "day": {
                        "type": "string",
                        "description": "星期，如：周一",
                    },
                    "name": {
                        "type": "string",
                        "description": "课程名称",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "开始时间，格式：HH:MM，如：08:30",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "结束时间，格式：HH:MM，如：09:00",
                    },
                    "order": {
                        "type": "number",
                        "description": "课程顺序（可选），如：1、2、3",
                    },
                    "type": {
                        "type": "string",
                        "description": "类型（可选）：course(课程)、break(课间)、activity(活动)、rest(休息)",
                        "enum": COURSE_TYPES,
                    },
                    "note": {
                        "type": "string",
                        "description": "备注（可选）",
                    },
                },
                required_params=["member_name", "day", "name", "start_time", "end_time"],
            ),
            ActionDef(
                name="edit_course",
                description="编辑课程项目",
                parameters={
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称",
                    },
                    "day": {
                        "type": "string",
                        "description": "星期",
                    },
                    "order": {
                        "type": "number",
                        "description": "课程顺序（用于定位），如：1、2",
                    },
                    "course_name": {
                        "type": "string",
                        "description": "课程名称（用于定位，与order二选一）",
                    },
                    "new_name": {
                        "type": "string",
                        "description": "新课程名称（可选）",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "新开始时间（可选）",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "新结束时间（可选）",
                    },
                    "note": {
                        "type": "string",
                        "description": "新备注（可选，传空字符串清除）",
                    },
                },
                required_params=["member_name", "day"],
            ),
            ActionDef(
                name="delete_course",
                description="删除课程项目或整个课程表",
                parameters={
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称",
                    },
                    "day": {
                        "type": "string",
                        "description": "星期（删除单个课程时需要）",
                    },
                    "order": {
                        "type": "number",
                        "description": "课程顺序（用于定位）",
                    },
                    "course_name": {
                        "type": "string",
                        "description": "课程名称（用于定位，与order二选一）",
                    },
                    "delete_all": {
                        "type": "boolean",
                        "description": "是否删除整个课程表",
                    },
                },
                required_params=["member_name"],
            ),
        ]

    # ------------------------------------------------------------------
    # Action 实现
    # ------------------------------------------------------------------

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定动作"""
    
        if action == "create_schedule":
            return await self._create_schedule(params)
        elif action == "search_courses":
            return await self._search_courses(params)
        elif action == "add_course":
            return await self._add_course(params)
        elif action == "edit_course":
            return await self._edit_course(params)
        elif action == "delete_course":
            return await self._delete_course(params)
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未知的动作：{action}",
            )

    async def _create_schedule(self, params: dict) -> ToolResult:
        """创建课程表"""
        member_name = params["member_name"]
        path = self._get_schedule_path(member_name)

        if path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"【{member_name}】的课程表已存在",
            )

        schedule_data = self._create_empty_schedule(member_name)
        self._save_schedule(schedule_data)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 已为【{member_name}】创建空课程表\n📁 文件：{path}\n\n请告诉我课程安排，我可以帮你添加课程。",
            data={"member_name": member_name, "file_path": str(path)},
        )

    async def _search_courses(self, params: dict) -> ToolResult:
        """搜索/查询课程表"""
        input_name = params["member_name"]
        
        # 智能姓名匹配（语音识别纠错）
        matched_name = self._find_best_matching_member(input_name)
        
        if not matched_name:
            # 如果未找到匹配，尝试直接加载（可能是新用户）
            data = self._load_schedule(input_name)
            if not data:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"未找到家庭成员【{input_name}】的课程表。\n💡 可能的原因：\n"
                          f"  1. 姓名输入错误（语音识别问题）\n"
                          f"  2. 尚未为该成员创建课程表\n"
                          f"💡 建议：使用 create_schedule 创建新课程表，或检查姓名是否正确。",
                )
            # 如果能加载，说明是新用户
            matched_name = input_name
            logger.info(f"使用原始姓名（新用户）：{input_name}")
        elif matched_name != input_name:
            logger.info(f"姓名已自动纠正：'{input_name}' → '{matched_name}'")
        
        day = params.get("day")
        date = params.get("date")

        # 如果提供了日期，转换为星期
        if date and not day:
            try:
                parsed_date = datetime.strptime(date, "%Y-%m-%d")
                weekday_idx = parsed_date.weekday()
                if 0 <= weekday_idx <= 6:
                    day = WEEKDAYS[weekday_idx]
                    logger.info(f"日期 {date} 转换为星期 {day}")
            except ValueError:
                logger.warning(f"无效的日期格式：{date}，应为 YYYY-MM-DD")

        # 验证星期（如果已转换）
        if day and day not in WEEKDAYS:
            # 尝试处理"今天"、"明天"等表达
            today = datetime.now()
            if "今天" in day or "今天" in str(day):
                day = WEEKDAYS[today.weekday()]
            elif "明天" in day:
                tomorrow = today + timedelta(days=1)
                day = WEEKDAYS[tomorrow.weekday()]
            elif "后天" in day:
                day_after = today + timedelta(days=2)
                day = WEEKDAYS[day_after.weekday()]
            elif day not in WEEKDAYS:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"无效的星期：{day}。可选：{', '.join(WEEKDAYS)} 或 今天、明天、后天",
                )

        data = self._load_schedule(matched_name)
        if not data:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到【{matched_name}】的课程表。\n💡 使用 create_schedule 创建新课程表。",
            )

        output = self._format_schedule_output(data, day)
        
        # 在输出中说明姓名纠正情况
        if matched_name != input_name:
            output = f"🔍 已自动纠正姓名：'{input_name}' → '{matched_name}'\n\n{output}"
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data=data,
        )

    async def _add_course(self, params: dict) -> ToolResult:
        """添加课程"""
        input_name = params["member_name"]
            
        # 智能姓名匹配
        member_name = self._find_best_matching_member(input_name) or input_name
        if member_name != input_name:
            logger.info(f"添加课程 - 姓名已纠正：'{input_name}' → '{member_name}'")
            
        day = params["day"]
        name = params["name"]
        start_time = params["start_time"]
        end_time = params["end_time"]
        order = params.get("order")
        course_type = params.get("type", "course")
        note = params.get("note", "")
    
        # 验证星期
        if day not in WEEKDAYS:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无效的星期：{day}。可选：{', '.join(WEEKDAYS)}",
            )
    
        # 验证时间格式
        if not self._validate_time_format(start_time) or not self._validate_time_format(end_time):
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无效的时间格式，请使用 HH:MM 格式（如 08:30）",
            )
    
        # 加载或创建课程表
        data = self._load_schedule(member_name)
        if not data:
            data = self._create_empty_schedule(member_name)
    
        day_schedule = data["schedule"][day]
    
        # 检查时间冲突
        conflict = self._check_time_conflict(day_schedule, start_time, end_time)
        if conflict:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=conflict,
            )
    
        # 计算 order
        if order is None:
            orders = [item["order"] for item in day_schedule if item["type"] == "course"]
            order = max(orders) + 1 if orders else 1
    
        # 生成 ID
        new_id = self._generate_course_id(course_type, len(day_schedule) + 1)
    
        new_course = {
            "id": new_id,
            "order": order,
            "start_time": start_time,
            "end_time": end_time,
            "name": name,
            "type": course_type,
            "note": note,
        }
    
        day_schedule.append(new_course)
        self._save_schedule(data)
    
        type_label = {"course": "课程", "break": "课间", "activity": "活动", "rest": "休息"}.get(course_type, "课程")
        output = f"✅ 已添加{type_label}到【{member_name}】的{day}\n📝 {name} {start_time}-{end_time}"
            
        # 如果姓名被纠正，在输出中说明
        if member_name != input_name:
            output = f"🔍 已自动纠正姓名：'{input_name}' → '{member_name}'\n\n{output}"
            
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"course": new_course, "day": day},
        )

    async def _edit_course(self, params: dict) -> ToolResult:
        """编辑课程"""
        input_name = params["member_name"]
        
        # 智能姓名匹配
        member_name = self._find_best_matching_member(input_name) or input_name
        if member_name != input_name:
            logger.info(f"编辑课程 - 姓名已纠正：'{input_name}' → '{member_name}'")
        
        day = params["day"]
        order = params.get("order")
        course_name = params.get("course_name")
        new_name = params.get("new_name")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        note = params.get("note")

        # 验证星期
        if day not in WEEKDAYS:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无效的星期：{day}",
            )

        data = self._load_schedule(member_name)
        if not data:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到【{member_name}】的课程表",
            )

        day_schedule = data["schedule"][day]

        # 查找目标课程
        target = None
        for item in day_schedule:
            if (order is not None and item["order"] == order) or (course_name and item["name"] == course_name):
                target = item
                break

        if not target:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到指定的课程项目",
            )

        old_name = target["name"]

        # 更新字段
        if new_name:
            target["name"] = new_name
        if start_time:
            if not self._validate_time_format(start_time):
                return ToolResult(status=ToolResultStatus.ERROR, error=f"无效的开始时间格式：{start_time}")
            target["start_time"] = start_time
        if end_time:
            if not self._validate_time_format(end_time):
                return ToolResult(status=ToolResultStatus.ERROR, error=f"无效的结束时间格式：{end_time}")
            target["end_time"] = end_time
        if note is not None:
            target["note"] = note

        # 检查时间冲突
        conflict = self._check_time_conflict(day_schedule, target["start_time"], target["end_time"], target["id"])
        if conflict:
            return ToolResult(status=ToolResultStatus.ERROR, error=conflict)

        self._save_schedule(data)

        output = f"✅ 已修改【{member_name}】的课程表\n📝 变更内容：{day} {old_name} → {target['name']}\n   时间：{target['start_time']}-{target['end_time']}"
        
        # 如果姓名被纠正，在输出中说明
        if member_name != input_name:
            output = f"🔍 已自动纠正姓名：'{input_name}' → '{member_name}'\n\n{output}"
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"course": target, "day": day},
        )

    async def _delete_course(self, params: dict) -> ToolResult:
        """删除课程"""
        input_name = params["member_name"]
        
        # 智能姓名匹配
        member_name = self._find_best_matching_member(input_name) or input_name
        if member_name != input_name:
            logger.info(f"删除课程 - 姓名已纠正：'{input_name}' → '{member_name}'")
        
        day = params.get("day")
        order = params.get("order")
        course_name = params.get("course_name")
        delete_all = params.get("delete_all", False)

        data = self._load_schedule(member_name)
        if not data:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到【{member_name}】的课程表",
            )

        # 删除整个课程表
        if delete_all:
            path = self._get_schedule_path(member_name)
            total = sum(len(items) for items in data["schedule"].values())
            path.unlink()
            
            output = f"✅ 已删除【{member_name}】的课程表\n🗑️ 共删除 {total} 个课程项目"
            
            # 如果姓名被纠正，在输出中说明
            if member_name != input_name:
                output = f"🔍 已自动纠正姓名：'{input_name}' → '{member_name}'\n\n{output}"
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=output,
                data={"deleted_count": total},
            )

        # 删除单个课程
        if day not in WEEKDAYS:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无效的星期：{day}",
            )

        day_schedule = data["schedule"][day]

        # 查找要删除的课程
        target_idx = None
        for i, item in enumerate(day_schedule):
            if (order is not None and item["order"] == order) or (course_name and item["name"] == course_name):
                target_idx = i
                break

        if target_idx is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到指定的课程项目",
            )

        deleted = day_schedule.pop(target_idx)
        self._save_schedule(data)

        output = f"✅ 已删除【{member_name}】的课程项目\n🗑️ 删除内容：{day} {deleted['name']} ({deleted['start_time']}-{deleted['end_time']})\n📊 {day}剩余 {len(day_schedule)} 个课程项目"
        
        # 如果姓名被纠正，在输出中说明
        if member_name != input_name:
            output = f"🔍 已自动纠正姓名：'{input_name}' → '{member_name}'\n\n{output}"
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={"deleted": deleted, "day": day, "remaining": len(day_schedule)},
        )
