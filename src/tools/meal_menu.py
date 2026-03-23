"""食谱工具 — 家庭成员营养食谱管理。

支持动作：
- create_menu: 创建学校食谱或家庭食谱
- query_menu: 查询食谱（完整/按天/按餐次）
- add_dish: 添加菜品到食谱
- edit_dish: 编辑菜品信息
- delete_dish: 删除菜品或整个食谱
- parse_image: 解析食谱图片（GLM-4.6V）

存储位置：.qoder/data/menus/
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# 默认数据存储路径
_DEFAULT_MENUS_DIR = Path(__file__).resolve().parent.parent.parent / ".qoder" / "data" / "menus"

# 星期列表
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 餐次列表
MEAL_TIMES = ["早餐", "午餐", "晚餐", "加餐"]

# 食谱类型
MENU_TYPES = ["school", "family"]


class MealMenuTool(BaseTool):
    """食谱管理工具。

    支持家庭成员学校食谱和家庭食谱的创建、查询、编辑和删除。
    学校食谱：每个成员每周一个文件
    家庭食谱：每周或每天一个文件
    存储在 .qoder/data/menus/ 目录下。
    """

    name = "meal_menu"
    emoji = "🍽️"
    title = "食谱管理"
    description = "家庭成员营养食谱管理：创建、查询、编辑、删除学校食谱和家庭食谱"

    def __init__(self, menus_dir: str = ""):
        super().__init__()
        self._menus_dir = Path(menus_dir) if menus_dir else _DEFAULT_MENUS_DIR
        self._menus_dir.mkdir(parents=True, exist_ok=True)

    def _get_current_week(self) -> str:
        """获取当前周的 ISO 周标识。"""
        now = datetime.now()
        return f"{now.year}-W{now.isocalendar()[1]:02d}"

    def _get_menu_path(
        self,
        menu_type: str,
        week: str,
        member_name: str = None,
        date: str = None,
    ) -> Path:
        """获取食谱文件路径。"""
        if menu_type == "school":
            if not member_name:
                raise ValueError("学校食谱必须提供 member_name")
            return self._menus_dir / f"{member_name}_school_{week}.json"
        else:  # family
            if date:
                return self._menus_dir / f"family_{date}.json"
            return self._menus_dir / f"family_{week}.json"

    def _load_menu(self, path: Path) -> dict | None:
        """加载食谱数据。"""
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载食谱失败: {e}")
            return None

    def _save_menu(self, data: dict, path: Path) -> None:
        """保存食谱数据。"""
        data["updated_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _create_empty_menu(
        self,
        menu_type: str,
        week: str,
        member_name: str = None,
    ) -> dict:
        """创建空的食谱结构。"""
        data = {
            "source": menu_type,
            "week_identifier": week,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "menu": {day: {meal: [] for meal in MEAL_TIMES} for day in WEEKDAYS},
        }
        if menu_type == "school":
            data["member_name"] = member_name
            data["source_image"] = ""
        else:
            data["notes"] = ""
        return data

    def _generate_dish_id(self, existing_ids: list[str]) -> str:
        """生成新的菜品ID。"""
        max_id = 0
        for id_str in existing_ids:
            if id_str.startswith("dish_"):
                try:
                    num = int(id_str.split("_")[1])
                    max_id = max(max_id, num)
                except (IndexError, ValueError):
                    continue
        return f"dish_{max_id + 1:03d}"

    def _format_menu_output(self, data: dict, day: str = None, meal: str = None) -> str:
        """格式化食谱输出。"""
        lines = []
        menu = data.get("menu", {})

        # 标题
        if data.get("source") == "school":
            title = f"🍽️ {data.get('member_name', '')} 的学校食谱"
        else:
            title = "🍽️ 家庭食谱"

        week = data.get("week_identifier", "")
        if week:
            title += f"（{week}）"

        lines.append(title)
        lines.append("━" * 50)

        total_dishes = 0
        days_to_show = [day] if day else WEEKDAYS

        for d in days_to_show:
            day_menu = menu.get(d, {})
            if not day_menu:
                continue

            has_content = any(day_menu.get(m, []) for m in MEAL_TIMES)
            if not has_content:
                continue

            lines.append(f"\n📆 {d}")

            meals_to_show = [meal] if meal else MEAL_TIMES
            for m in meals_to_show:
                dishes = day_menu.get(m, [])
                if dishes:
                    meal_emoji = {"早餐": "🍳", "午餐": "🍱", "晚餐": "🍲", "加餐": "🥤"}.get(m, "🍴")
                    lines.append(f"\n  {meal_emoji} {m}")
                    for dish in dishes:
                        name = dish.get("name", "")
                        quantity = dish.get("quantity", "")
                        desc = dish.get("description", "")
                        qty_str = f"（{quantity}）" if quantity else ""
                        desc_str = f" - {desc}" if desc else ""
                        lines.append(f"    • {name}{qty_str}{desc_str}")
                    total_dishes += len(dishes)

        lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📊 共 {total_dishes} 道菜品")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Action 定义
    # ------------------------------------------------------------------

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="create_menu",
                description="创建学校食谱或家庭食谱",
                parameters={
                    "menu_type": {
                        "type": "string",
                        "description": "食谱类型：school（学校食谱）或 family（家庭食谱）",
                        "enum": MENU_TYPES,
                    },
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称（学校食谱必填），如：小溪溪、小鹿儿",
                    },
                    "week": {
                        "type": "string",
                        "description": "周标识（可选），格式：YYYY-Www，如：2026-W13。默认当前周",
                    },
                },
                required_params=["menu_type"],
            ),
            ActionDef(
                name="query_menu",
                description="查询食谱，可按天、按餐次筛选",
                parameters={
                    "menu_type": {
                        "type": "string",
                        "description": "食谱类型：school 或 family",
                        "enum": MENU_TYPES,
                    },
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称（学校食谱必填）",
                    },
                    "week": {
                        "type": "string",
                        "description": "周标识（可选），默认当前周",
                    },
                    "day": {
                        "type": "string",
                        "description": "星期（可选），如：周一、周二...周日",
                    },
                    "meal": {
                        "type": "string",
                        "description": "餐次（可选），如：早餐、午餐、晚餐、加餐",
                    },
                },
                required_params=["menu_type"],
            ),
            ActionDef(
                name="add_dish",
                description="添加菜品到食谱",
                parameters={
                    "menu_type": {
                        "type": "string",
                        "description": "食谱类型：school 或 family",
                        "enum": MENU_TYPES,
                    },
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称（学校食谱必填）",
                    },
                    "week": {
                        "type": "string",
                        "description": "周标识（可选），默认当前周",
                    },
                    "day": {
                        "type": "string",
                        "description": "星期，如：周一",
                    },
                    "meal": {
                        "type": "string",
                        "description": "餐次，如：早餐、午餐、晚餐",
                    },
                    "name": {
                        "type": "string",
                        "description": "菜名（必填）",
                    },
                    "quantity": {
                        "type": "string",
                        "description": "数量（可选），如：一碗、一份、一个",
                    },
                    "description": {
                        "type": "string",
                        "description": "描述（可选），如：配土豆、小溪溪最爱",
                    },
                },
                required_params=["menu_type", "day", "meal", "name"],
            ),
            ActionDef(
                name="edit_dish",
                description="编辑菜品信息",
                parameters={
                    "menu_type": {
                        "type": "string",
                        "description": "食谱类型：school 或 family",
                        "enum": MENU_TYPES,
                    },
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称（学校食谱必填）",
                    },
                    "week": {
                        "type": "string",
                        "description": "周标识（可选），默认当前周",
                    },
                    "day": {
                        "type": "string",
                        "description": "星期",
                    },
                    "meal": {
                        "type": "string",
                        "description": "餐次",
                    },
                    "dish_name": {
                        "type": "string",
                        "description": "原菜名（用于定位菜品）",
                    },
                    "new_name": {
                        "type": "string",
                        "description": "新菜名（可选）",
                    },
                    "quantity": {
                        "type": "string",
                        "description": "新数量（可选）",
                    },
                    "description": {
                        "type": "string",
                        "description": "新描述（可选，传空字符串清除）",
                    },
                },
                required_params=["menu_type", "day", "meal"],
            ),
            ActionDef(
                name="delete_dish",
                description="删除菜品或整个食谱",
                parameters={
                    "menu_type": {
                        "type": "string",
                        "description": "食谱类型：school 或 family",
                        "enum": MENU_TYPES,
                    },
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称（学校食谱必填）",
                    },
                    "week": {
                        "type": "string",
                        "description": "周标识（可选），默认当前周",
                    },
                    "day": {
                        "type": "string",
                        "description": "星期（删除单个菜品时需要）",
                    },
                    "meal": {
                        "type": "string",
                        "description": "餐次（删除单个菜品时需要）",
                    },
                    "dish_name": {
                        "type": "string",
                        "description": "菜名（用于定位菜品）",
                    },
                    "delete_all": {
                        "type": "boolean",
                        "description": "是否删除整个食谱文件",
                    },
                },
                required_params=["menu_type"],
            ),
            ActionDef(
                name="parse_image",
                description="解析食谱图片，自动创建食谱",
                parameters={
                    "image_path": {
                        "type": "string",
                        "description": "图片文件路径",
                    },
                    "menu_type": {
                        "type": "string",
                        "description": "食谱类型：school 或 family",
                        "enum": MENU_TYPES,
                    },
                    "member_name": {
                        "type": "string",
                        "description": "家庭成员名称（学校食谱必填）",
                    },
                    "week": {
                        "type": "string",
                        "description": "周标识（可选），默认当前周",
                    },
                },
                required_params=["image_path", "menu_type"],
            ),
            ActionDef(
                name="list_menus",
                description="列出所有已创建的食谱",
                parameters={},
                required_params=[],
            ),
        ]

    # ------------------------------------------------------------------
    # Action 实现
    # ------------------------------------------------------------------

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定动作。"""
        if action == "create_menu":
            return await self._create_menu(params)
        elif action == "query_menu":
            return await self._query_menu(params)
        elif action == "add_dish":
            return await self._add_dish(params)
        elif action == "edit_dish":
            return await self._edit_dish(params)
        elif action == "delete_dish":
            return await self._delete_dish(params)
        elif action == "parse_image":
            return await self._parse_image(params)
        elif action == "list_menus":
            return await self._list_menus(params)
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未知的动作: {action}",
            )

    async def _create_menu(self, params: dict) -> ToolResult:
        """创建食谱。"""
        menu_type = params["menu_type"]
        member_name = params.get("member_name")
        week = params.get("week") or self._get_current_week()

        if menu_type == "school" and not member_name:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="学校食谱必须指定家庭成员名称",
            )

        path = self._get_menu_path(menu_type, week, member_name)
        if path.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"食谱已存在: {path.name}",
            )

        data = self._create_empty_menu(menu_type, week, member_name)
        self._save_menu(data, path)

        type_label = "学校食谱" if menu_type == "school" else "家庭食谱"
        member_str = f"【{member_name}】的" if member_name else ""
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 已创建{member_str}{type_label}\n📁 文件：{path}\n📅 周期：{week}",
            data={"file": str(path), "week": week, "menu_type": menu_type},
        )

    async def _query_menu(self, params: dict) -> ToolResult:
        """查询食谱。"""
        menu_type = params["menu_type"]
        member_name = params.get("member_name")
        week = params.get("week") or self._get_current_week()
        day = params.get("day")
        meal = params.get("meal")

        if menu_type == "school" and not member_name:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="查询学校食谱必须指定家庭成员名称",
            )

        if day and day not in WEEKDAYS:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无效的星期：{day}。可选：{', '.join(WEEKDAYS)}",
            )

        if meal and meal not in MEAL_TIMES:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无效的餐次：{meal}。可选：{', '.join(MEAL_TIMES)}",
            )

        path = self._get_menu_path(menu_type, week, member_name)
        data = self._load_menu(path)
        if not data:
            type_label = "学校食谱" if menu_type == "school" else "家庭食谱"
            member_str = f"【{member_name}】的" if member_name else ""
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到{member_str}{type_label}（{week}）\n💡 使用 create_menu 创建新食谱",
            )

        output = self._format_menu_output(data, day, meal)
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data=data,
        )

    async def _add_dish(self, params: dict) -> ToolResult:
        """添加菜品。"""
        menu_type = params["menu_type"]
        member_name = params.get("member_name")
        week = params.get("week") or self._get_current_week()
        day = params["day"]
        meal = params["meal"]
        name = params["name"]
        quantity = params.get("quantity", "")
        description = params.get("description", "")

        if menu_type == "school" and not member_name:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="学校食谱必须指定家庭成员名称",
            )

        if day not in WEEKDAYS:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无效的星期：{day}",
            )

        if meal not in MEAL_TIMES:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"无效的餐次：{meal}",
            )

        path = self._get_menu_path(menu_type, week, member_name)
        data = self._load_menu(path)
        if not data:
            # 自动创建食谱
            data = self._create_empty_menu(menu_type, week, member_name)

        # 收集所有现有ID
        existing_ids = []
        for d in data["menu"].values():
            for m in d.values():
                for dish in m:
                    if "id" in dish:
                        existing_ids.append(dish["id"])

        new_dish = {
            "id": self._generate_dish_id(existing_ids),
            "name": name,
            "quantity": quantity,
            "description": description,
        }

        data["menu"][day][meal].append(new_dish)
        self._save_menu(data, path)

        member_str = f"【{member_name}】" if member_name else "家庭"
        qty_str = f"（{quantity}）" if quantity else ""
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 已添加菜品到{member_str}的{day} {meal}\n📝 {name}{qty_str}",
            data={"dish": new_dish, "day": day, "meal": meal},
        )

    async def _edit_dish(self, params: dict) -> ToolResult:
        """编辑菜品。"""
        menu_type = params["menu_type"]
        member_name = params.get("member_name")
        week = params.get("week") or self._get_current_week()
        day = params["day"]
        meal = params["meal"]
        dish_name = params.get("dish_name")
        new_name = params.get("new_name")
        quantity = params.get("quantity")
        description = params.get("description")

        if menu_type == "school" and not member_name:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="学校食谱必须指定家庭成员名称",
            )

        path = self._get_menu_path(menu_type, week, member_name)
        data = self._load_menu(path)
        if not data:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="未找到食谱",
            )

        dishes = data["menu"].get(day, {}).get(meal, [])

        # 查找目标菜品
        target = None
        for dish in dishes:
            if dish.get("name") == dish_name:
                target = dish
                break

        if not target:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到菜品：{dish_name}",
            )

        old_name = target["name"]

        # 更新字段
        if new_name:
            target["name"] = new_name
        if quantity is not None:
            target["quantity"] = quantity
        if description is not None:
            target["description"] = description

        self._save_menu(data, path)

        member_str = f"【{member_name}】" if member_name else "家庭"
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 已修改{member_str}的食谱\n📝 变更：{day} {meal} {old_name} → {target['name']}",
            data={"dish": target, "day": day, "meal": meal},
        )

    async def _delete_dish(self, params: dict) -> ToolResult:
        """删除菜品或食谱。"""
        menu_type = params["menu_type"]
        member_name = params.get("member_name")
        week = params.get("week") or self._get_current_week()
        day = params.get("day")
        meal = params.get("meal")
        dish_name = params.get("dish_name")
        delete_all = params.get("delete_all", False)

        if menu_type == "school" and not member_name:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="学校食谱必须指定家庭成员名称",
            )

        path = self._get_menu_path(menu_type, week, member_name)

        if delete_all:
            if not path.exists():
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="食谱不存在",
                )
            data = self._load_menu(path)
            total = sum(
                len(dishes)
                for day_menu in data.get("menu", {}).values()
                for dishes in day_menu.values()
            )
            path.unlink()
            member_str = f"【{member_name}】" if member_name else "家庭"
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ 已删除{member_str}的食谱\n🗑️ 共删除 {total} 道菜品",
                data={"deleted_count": total},
            )

        # 删除单个菜品
        if not day or not meal or not dish_name:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="删除单个菜品需要指定 day、meal 和 dish_name",
            )

        data = self._load_menu(path)
        if not data:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="食谱不存在",
            )

        dishes = data["menu"].get(day, {}).get(meal, [])
        target_idx = None
        for i, dish in enumerate(dishes):
            if dish.get("name") == dish_name:
                target_idx = i
                break

        if target_idx is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"未找到菜品：{dish_name}",
            )

        deleted = dishes.pop(target_idx)
        self._save_menu(data, path)

        member_str = f"【{member_name}】" if member_name else "家庭"
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"✅ 已删除{member_str}的菜品\n🗑️ {day} {meal} {deleted['name']}",
            data={"deleted": deleted},
        )

    async def _parse_image(self, params: dict) -> ToolResult:
        """解析食谱图片。"""
        import os

        image_path = params["image_path"]
        menu_type = params["menu_type"]
        member_name = params.get("member_name")
        week = params.get("week") or self._get_current_week()

        if not os.path.exists(image_path):
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"图片文件不存在：{image_path}",
            )

        if menu_type == "school" and not member_name:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="学校食谱必须指定家庭成员名称",
            )

        # 检查 API Key
        api_key = os.environ.get("GLM_API_KEY")
        if not api_key:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="未配置 GLM_API_KEY，无法解析图片",
            )

        try:
            # 调用 GLM-4.6V 解析图片
            result = await self._call_vision_model(image_path, api_key)

            if not result:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error="图片解析失败，无法识别食谱内容",
                )

            # 创建食谱并保存
            path = self._get_menu_path(menu_type, week, member_name)
            data = self._create_empty_menu(menu_type, week, member_name)
            data["menu"] = result.get("menu", {})
            data["source_image"] = Path(image_path).name
            self._save_menu(data, path)

            # 统计菜品数量
            dish_count = sum(
                len(dishes)
                for day_menu in result.get("menu", {}).values()
                for dishes in day_menu.values()
                if isinstance(dishes, list)
            )

            type_label = "学校食谱" if menu_type == "school" else "家庭食谱"
            member_str = f"【{member_name}】的" if member_name else ""
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ 已从图片创建{member_str}{type_label}\n📁 文件：{path}\n📊 共识别 {dish_count} 道菜品",
                data={"file": str(path), "dish_count": dish_count},
            )

        except Exception as e:
            logger.error(f"图片解析失败: {e}")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"图片解析失败：{str(e)}",
            )

    async def _call_vision_model(self, image_path: str, api_key: str) -> dict | None:
        """调用 GLM-4.6V 视觉模型解析食谱图片。"""
        try:
            from zhipuai import ZhipuAI

            client = ZhipuAI(api_key=api_key)

            with open(image_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode()

            response = client.chat.completions.create(
                model="glm-4.6v-flash",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                            },
                            {
                                "type": "text",
                                "text": """请解析这张食谱图片，提取以下信息：
1. 识别是一周食谱还是单日食谱
2. 按日期（周一到周日）和餐次（早餐/午餐/晚餐）整理菜品
3. 每道菜提取：菜名、数量（如有）

返回严格的JSON格式，不要有额外文字：
{"menu": {"周一": {"早餐": [{"name": "菜名", "quantity": "数量"}], "午餐": [], "晚餐": []}}}
如果某天某餐没有菜品，用空数组 [] 表示。""",
                            },
                        ],
                    }
                ],
            )

            content = response.choices[0].message.content
            # 尝试提取 JSON
            import re

            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                return json.loads(json_match.group())
            return None

        except Exception as e:
            logger.error(f"调用视觉模型失败: {e}")
            return None

    async def _list_menus(self, params: dict) -> ToolResult:
        """列出所有食谱。"""
        menus = []
        for path in self._menus_dir.glob("*.json"):
            data = self._load_menu(path)
            if data:
                dish_count = sum(
                    len(dishes)
                    for day_menu in data.get("menu", {}).values()
                    for dishes in day_menu.values()
                    if isinstance(dishes, list)
                )
                menus.append({
                    "file": path.name,
                    "source": data.get("source", ""),
                    "member_name": data.get("member_name", ""),
                    "week": data.get("week_identifier", ""),
                    "dish_count": dish_count,
                })

        if not menus:
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output="📋 暂无食谱记录\n💡 使用 create_menu 创建新食谱",
                data={"menus": []},
            )

        lines = ["📋 已创建的食谱：", "━" * 50]
        for m in sorted(menus, key=lambda x: x.get("week", ""), reverse=True):
            member = m.get("member_name") or "家庭"
            source = "学校" if m.get("source") == "school" else "家庭"
            lines.append(f"  • {member}（{source}）- {m.get('week')} - {m.get('dish_count')}道菜")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="\n".join(lines),
            data={"menus": menus},
        )
