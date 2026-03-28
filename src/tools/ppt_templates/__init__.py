"""PPT 模板模块 - 提供 PPT 生成所需的布局、内容和样式管理。

子模块：
- content_generator: 内容生成器
- style_definitions: 样式定义
- content_expander: 内容扩展器
"""

from .content_generator import RichContentGenerator
from .style_definitions import PPTStyleDefinition, STYLE_PRESETS, get_style, get_color_scheme, get_font_scheme
from .content_expander import ContentExpander

__all__ = [
    "RichContentGenerator",
    "PPTStyleDefinition",
    "STYLE_PRESETS",
    "get_style",
    "get_color_scheme",
    "get_font_scheme",
    "ContentExpander",
]
