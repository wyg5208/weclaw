"""PPT 内容扩展器 - 根据主题和大纲自动生成幻灯片配置。

功能：
- 将简单的大纲扩展为完整的幻灯片配置
- 智能建议配图描述
- 智能建议图表数据
- 提供预设模板
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ContentExpander:
    """PPT 内容扩展器"""

    # 预设模板
    TEMPLATES = {
        "business_report": {
            "name": "商务汇报",
            "description": "适合工作汇报、项目汇报等商务场景",
            "structure": [
                {"type": "title", "layout": "single"},
                {"type": "content", "layout": "single", "title_prefix": "目录"},
                {"type": "section", "layout": "single"},
                {"type": "content", "layout": "left_img"},
                {"type": "icon_cards", "layout": "cards_3"},
                {"type": "chart", "layout": "single"},
                {"type": "grid_images", "layout": "grid_2x2"},
                {"type": "section", "layout": "single"},
                {"type": "content", "layout": "double"},
                {"type": "icon_cards", "layout": "cards_3"},
                {"type": "thank", "layout": "single"},
            ],
        },
        "academic_presentation": {
            "name": "学术报告",
            "description": "适合学术答辩、研究汇报等学术场景",
            "structure": [
                {"type": "title", "layout": "single"},
                {"type": "content", "layout": "single", "title_prefix": "目录"},
                {"type": "section", "layout": "single"},
                {"type": "content", "layout": "single"},
                {"type": "icon_cards", "layout": "cards_3"},
                {"type": "chart", "layout": "single"},
                {"type": "table", "layout": "single"},
                {"type": "section", "layout": "single"},
                {"type": "content", "layout": "double"},
                {"type": "icon_cards", "layout": "cards_3"},
                {"type": "thank", "layout": "single"},
            ],
        },
        "product_intro": {
            "name": "产品介绍",
            "description": "适合产品发布、功能介绍等场景",
            "structure": [
                {"type": "title", "layout": "single"},
                {"type": "grid_images", "layout": "grid_2"},
                {"type": "section", "layout": "single"},
                {"type": "icon_cards", "layout": "cards_4"},
                {"type": "content", "layout": "left_img"},
                {"type": "content", "layout": "right_img"},
                {"type": "grid_images", "layout": "grid_2x2"},
                {"type": "chart", "layout": "single"},
                {"type": "content", "layout": "double"},
                {"type": "thank", "layout": "single"},
            ],
        },
    }

    def __init__(self):
        """初始化内容扩展器"""
        pass

    def expand_outline(self, topic: str, outline: list[str], style: str = "business") -> list[dict[str, Any]]:
        """根据主题和大纲扩展为幻灯片配置

        Args:
            topic: PPT 主题
            outline: 大纲列表
            style: 风格类型

        Returns:
            幻灯片配置列表
        """
        slides = []

        # 1. 标题页
        slides.append({
            "type": "title",
            "title": topic,
            "subtitle": f"{self._get_style_name(style)}报告",
            "layout": "single",
        })

        # 2. 目录页
        if len(outline) > 2:
            slides.append({
                "type": "content",
                "title": "目录",
                "subtitle": "内容概览",
                "content": [f"{i+1}. {item}" for i, item in enumerate(outline)],
                "layout": "single",
                "icons": ["chart", "rocket", "globe", "light", "target", "star"],
            })

        # 3. 内容页
        for i, section in enumerate(outline):
            # 章节分隔页（每3个章节后插入）
            if i > 0 and i % 3 == 0:
                slides.append({
                    "type": "section",
                    "title": f"第 {len([s for s in slides if s['type'] == 'section']) + 1} 部分",
                    "subtitle": section,
                    "layout": "single",
                })

            # 根据索引选择不同的页面类型增加多样性
            if i % 5 == 0 and len(outline) >= 4:
                # 每5个章节插入一个图标卡片页
                slides.append({
                    "type": "icon_cards",
                    "title": f"{section} - 核心要点",
                    "cards": self._generate_icon_cards(section),
                    "layout": "cards_3",
                })
            elif i % 4 == 0 and len(outline) >= 3:
                # 每4个章节插入一个图片网格页
                slides.append({
                    "type": "grid_images",
                    "title": f"{section} - 相关图片",
                    "image_count": 4 if i % 8 == 0 else 2,
                    "layout": "grid_2x2" if i % 8 == 0 else "grid_2",
                })
            else:
                # 内容页
                slide_config = {
                    "type": "content",
                    "title": section,
                    "subtitle": f"第 {i + 1} 部分",
                    "content": self._generate_content_points(topic, section),
                    "layout": self._suggest_layout(i, len(outline)),
                    "icons": self._generate_icons(i),
                    "image_prompt": self._suggest_image_prompt(topic, section),
                }
                slides.append(slide_config)

            # 数据类内容自动添加图表页（每4个章节后）
            if i > 0 and i % 4 == 0:
                slides.append({
                    "type": "chart",
                    "title": f"{section} - 数据分析",
                    "subtitle": "关键指标",
                    "chart": self._suggest_chart_data(section),
                    "layout": "single",
                })

        # 4. 总结页 - 使用图标卡片
        slides.append({
            "type": "icon_cards",
            "title": "总结与展望",
            "cards": self._generate_summary_cards(outline),
            "layout": "cards_3",
        })

        # 5. 感谢页
        slides.append({
            "type": "thank",
            "title": "感谢聆听",
            "subtitle": "THANK YOU",
            "layout": "single",
        })

        return slides

    def parse_slides_config(self, config_str: str) -> list[dict[str, Any]]:
        """解析 slides_config JSON 字符串

        Args:
            config_str: JSON 格式的幻灯片配置

        Returns:
            幻灯片配置列表

        Raises:
            json.JSONDecodeError: JSON 解析失败
        """
        try:
            config = json.loads(config_str)
            if isinstance(config, list):
                return config
            elif isinstance(config, dict) and "slides" in config:
                return config["slides"]
            else:
                logger.warning(f"slides_config 格式异常，尝试作为单页处理: {config}")
                return [config]
        except json.JSONDecodeError as e:
            logger.error(f"slides_config JSON 解析失败: {e}")
            raise

    def validate_slides_config(self, slides: list[dict[str, Any]]) -> tuple[bool, str]:
        """验证幻灯片配置

        Args:
            slides: 幻灯片配置列表

        Returns:
            (是否有效, 错误信息)
        """
        valid_types = {"title", "section", "content", "chart", "table", "icon_cards", "grid_images", "thank", "blank"}
        valid_layouts = {"single", "double", "left_img", "right_img", "full_img", "center", 
                        "grid_2", "grid_3", "grid_2x2", "grid_3x2", "cards_3", "cards_4"}

        for i, slide in enumerate(slides):
            # 检查类型
            slide_type = slide.get("type", "content")
            if slide_type not in valid_types:
                return False, f"第 {i+1} 页：无效的类型 '{slide_type}'"

            # 检查布局
            layout = slide.get("layout", "single")
            if layout not in valid_layouts:
                return False, f"第 {i+1} 页：无效的布局 '{layout}'"

            # 图表页需要 chart 数据
            if slide_type == "chart" and not slide.get("chart"):
                return False, f"第 {i+1} 页：图表页缺少 chart 数据"

            # 表格页需要 table 数据
            if slide_type == "table" and not slide.get("table"):
                return False, f"第 {i+1} 页：表格页缺少 table 数据"

            # 图标卡片页需要 cards 数据
            if slide_type == "icon_cards" and not slide.get("cards"):
                return False, f"第 {i+1} 页：图标卡片页缺少 cards 数据"

        return True, ""

    def get_template(self, template_name: str) -> dict[str, Any] | None:
        """获取预设模板

        Args:
            template_name: 模板名称

        Returns:
            模板配置，不存在返回 None
        """
        return self.TEMPLATES.get(template_name)

    def list_templates(self) -> list[dict[str, str]]:
        """列出所有可用模板

        Returns:
            模板信息列表 [(name, description), ...]
        """
        return [
            {"name": name, "description": info["description"]}
            for name, info in self.TEMPLATES.items()
        ]

    def _get_style_name(self, style: str) -> str:
        """获取风格显示名称"""
        names = {
            "business": "商务",
            "academic": "学术",
            "creative": "创意",
            "minimal": "简约",
        }
        return names.get(style, "商务")

    def _generate_content_points(self, topic: str, section: str) -> list[str]:
        """生成内容要点

        Args:
            topic: 主题
            section: 章节标题

        Returns:
            内容要点列表
        """
        # 根据章节标题生成默认要点
        return [
            f"{section} - 要点一",
            f"{section} - 要点二",
            f"{section} - 要点三",
        ]

    def _suggest_layout(self, index: int, total: int) -> str:
        """建议布局类型

        Args:
            index: 当前索引
            total: 总数

        Returns:
            布局类型
        """
        # 交替使用不同布局增加视觉多样性
        layouts = ["single", "left_img", "right_img", "double", "single"]
        return layouts[index % len(layouts)]

    def _suggest_image_prompt(self, topic: str, section: str) -> str:
        """建议配图描述

        Args:
            topic: 主题
            section: 章节标题

        Returns:
            图片生成提示词
        """
        return f"{topic} - {section}，专业简洁风格，高质量插图"

    def _suggest_chart_data(self, section: str) -> dict[str, Any]:
        """建议图表数据

        Args:
            section: 章节标题

        Returns:
            图表数据配置
        """
        return {
            "type": "bar",
            "labels": ["指标A", "指标B", "指标C", "指标D"],
            "values": [75, 85, 60, 90],
            "series_name": "数据对比",
        }

    def _generate_icon_cards(self, section: str) -> list[dict[str, str]]:
        """生成图标卡片数据

        Args:
            section: 章节标题

        Returns:
            卡片列表
        """
        icons = ["star", "rocket", "light"]
        return [
            {
                "icon": icons[0],
                "title": f"{section} - 核心优势",
                "description": f"详细介绍{section}的核心优势和独特价值",
            },
            {
                "icon": icons[1],
                "title": f"{section} - 技术特点",
                "description": f"深入解析{section}的技术实现和原理",
            },
            {
                "icon": icons[2],
                "title": f"{section} - 应用场景",
                "description": f"展示{section}在实际中的应用案例",
            },
        ]

    def _generate_summary_cards(self, outline: list[str]) -> list[dict[str, str]]:
        """生成总结卡片数据

        Args:
            outline: 大纲列表

        Returns:
            卡片列表
        """
        return [
            {
                "icon": "star",
                "title": "核心要点回顾",
                "description": f"回顾{outline[0] if outline else '主要内容'}的关键收获" if outline else "回顾核心内容的关键收获",
            },
            {
                "icon": "rocket",
                "title": "未来发展方向",
                "description": "展望发展趋势和未来机遇",
            },
            {
                "icon": "light",
                "title": "行动建议",
                "description": "提出具体的实施建议和行动计划",
            },
        ]

    def _generate_icons(self, index: int) -> list[str]:
        """生成图标列表

        Args:
            index: 当前索引

        Returns:
            图标列表
        """
        all_icons = [
            ["chart", "rocket", "globe"],
            ["light", "target", "star"],
            ["tech", "people", "idea"],
            ["fire", "money", "warning"],
        ]
        return all_icons[index % len(all_icons)]
