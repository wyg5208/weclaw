"""PPT 样式定义 - 定义不同场景的配色和字体样式。

提供 4 种预设风格：
- business: 商务风格（深蓝主色调）
- academic: 学术风格（正式、简洁）
- creative: 创意风格（活泼、多彩）
- minimal: 简约风格（黑白灰）
"""

from dataclasses import dataclass
from typing import Any
from pptx.dml.color import RGBColor
from pptx.util import Pt


@dataclass
class ColorScheme:
    """配色方案"""
    primary: RGBColor      # 主色
    secondary: RGBColor    # 辅色
    accent: RGBColor       # 强调色
    bg: RGBColor           # 背景色
    text: RGBColor         # 文字色
    light: RGBColor        # 浅色


@dataclass
class FontScheme:
    """字体方案"""
    title: str
    body: str
    title_size: int
    body_size: int
    subtitle_size: int


@dataclass
class PPTStyleDefinition:
    """PPT 样式定义"""
    name: str
    display_name: str
    colors: ColorScheme
    fonts: FontScheme
    spacing: dict[str, int]  # 间距配置

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PPTStyleDefinition":
        """从字典创建样式定义"""
        colors = ColorScheme(**data["colors"])
        fonts = FontScheme(**data["fonts"])
        return cls(
            name=data["name"],
            display_name=data["display_name"],
            colors=colors,
            fonts=fonts,
            spacing=data.get("spacing", {}),
        )


# ==================== 样式预设 ====================

STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "business": {
        "name": "business",
        "display_name": "商务风格",
        "colors": {
            "primary": RGBColor(0x00, 0x52, 0x8A),      # 深蓝
            "secondary": RGBColor(0x33, 0x33, 0x33),   # 深灰
            "accent": RGBColor(0x00, 0x96, 0xD6),     # 亮蓝
            "bg": RGBColor(0xFF, 0xFF, 0xFF),         # 白色
            "text": RGBColor(0x33, 0x33, 0x33),       # 深灰文字
            "light": RGBColor(0xE8, 0xF4, 0xFC),     # 浅蓝背景
        },
        "fonts": {
            "title": "微软雅黑",
            "body": "微软雅黑",
            "title_size": 44,
            "body_size": 20,
            "subtitle_size": 24,
        },
        "spacing": {
            "title_top": 60,
            "content_top": 120,
            "paragraph_spacing": 12,
        },
    },
    "academic": {
        "name": "academic",
        "display_name": "学术风格",
        "colors": {
            "primary": RGBColor(0x1A, 0x23, 0x7E),    # 深蓝
            "secondary": RGBColor(0x44, 0x44, 0x44),   # 灰色
            "accent": RGBColor(0xC6, 0x28, 0x28),     # 红色强调
            "bg": RGBColor(0xFA, 0xFA, 0xFA),         # 浅灰
            "text": RGBColor(0x33, 0x33, 0x33),       # 深灰文字
            "light": RGBColor(0xE8, 0xE8, 0xE8),     # 更浅的灰
        },
        "fonts": {
            "title": "Times New Roman",
            "body": "Arial",
            "title_size": 40,
            "body_size": 18,
            "subtitle_size": 22,
        },
        "spacing": {
            "title_top": 50,
            "content_top": 100,
            "paragraph_spacing": 10,
        },
    },
    "creative": {
        "name": "creative",
        "display_name": "创意风格",
        "colors": {
            "primary": RGBColor(0xE9, 0x1E, 0x63),     # 粉色
            "secondary": RGBColor(0x33, 0x33, 0x33),   # 深灰
            "accent": RGBColor(0xFF, 0xC1, 0x07),     # 黄色强调
            "bg": RGBColor(0xFF, 0xFF, 0xFF),         # 白色
            "text": RGBColor(0x33, 0x33, 0x33),       # 深灰文字
            "light": RGBColor(0xFF, 0xF3, 0xE5),     # 浅粉背景
        },
        "fonts": {
            "title": "微软雅黑",
            "body": "微软雅黑",
            "title_size": 46,
            "body_size": 20,
            "subtitle_size": 26,
        },
        "spacing": {
            "title_top": 70,
            "content_top": 130,
            "paragraph_spacing": 14,
        },
    },
    "minimal": {
        "name": "minimal",
        "display_name": "简约风格",
        "colors": {
            "primary": RGBColor(0x21, 0x21, 0x21),    # 近黑
            "secondary": RGBColor(0x75, 0x75, 0x75),   # 中灰
            "accent": RGBColor(0x42, 0x42, 0x42),     # 深灰强调
            "bg": RGBColor(0xFF, 0xFF, 0xFF),         # 白色
            "text": RGBColor(0x33, 0x33, 0x33),       # 深灰文字
            "light": RGBColor(0xF5, 0xF5, 0xF5),     # 浅灰背景
        },
        "fonts": {
            "title": "Helvetica",
            "body": "Helvetica",
            "title_size": 42,
            "body_size": 18,
            "subtitle_size": 22,
        },
        "spacing": {
            "title_top": 55,
            "content_top": 110,
            "paragraph_spacing": 8,
        },
    },
}


def get_style(name: str) -> PPTStyleDefinition:
    """获取指定名称的样式定义"""
    if name not in STYLE_PRESETS:
        name = "business"
    return PPTStyleDefinition.from_dict(STYLE_PRESETS[name])


def get_color_scheme(name: str) -> ColorScheme:
    """获取指定名称的配色方案"""
    style = get_style(name)
    return style.colors


def get_font_scheme(name: str) -> FontScheme:
    """获取指定名称的字体方案"""
    style = get_style(name)
    return style.fonts
