"""思维导图工具 — 生成思维导图图片（SVG/PNG）。

支持从结构化数据或文本自动解析生成思维导图。
采用双引擎策略：优先使用 graphviz（如可用），否则使用纯 SVG 引擎。
"""

from __future__ import annotations

import logging
import math
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)

# 检查 graphviz 是否可用
_GRAPHVIZ_AVAILABLE = False
_graphviz = None

try:
    import graphviz as _graphviz
    # 检查 dot 命令是否可用
    if shutil.which("dot"):
        _GRAPHVIZ_AVAILABLE = True
        logger.info("Graphviz 引擎可用")
    else:
        logger.info("graphviz 包已安装，但 dot 命令不可用，使用纯 SVG 引擎")
except ImportError:
    logger.info("graphviz 包未安装，使用纯 SVG 引擎")


@dataclass
class MindMapNode:
    """思维导图节点。"""
    name: str
    children: list["MindMapNode"] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MindMapNode":
        """从字典创建节点树。"""
        children = []
        for child_data in data.get("children", []):
            if isinstance(child_data, dict):
                children.append(cls.from_dict(child_data))
            elif isinstance(child_data, str):
                children.append(cls(name=child_data))
        return cls(name=data.get("name", ""), children=children)


# ==================== 颜色主题定义 ====================

THEMES = {
    "colorful": {
        "background": "#ffffff",
        "center_fill": "#4A90D9",
        "center_text": "#ffffff",
        "branch_colors": [
            "#5B8C5A",  # 绿色
            "#E67E22",  # 橙色
            "#9B59B6",  # 紫色
            "#E74C3C",  # 红色
            "#1ABC9C",  # 青色
            "#F39C12",  # 黄色
        ],
        "branch_text": "#ffffff",
        "leaf_fill": "#f8f9fa",
        "leaf_text": "#333333",
        "leaf_stroke": "#dee2e6",
        "line_color": "#adb5bd",
    },
    "monochrome": {
        "background": "#ffffff",
        "center_fill": "#333333",
        "center_text": "#ffffff",
        "branch_colors": ["#555555", "#666666", "#777777", "#888888", "#999999", "#aaaaaa"],
        "branch_text": "#ffffff",
        "leaf_fill": "#f5f5f5",
        "leaf_text": "#333333",
        "leaf_stroke": "#cccccc",
        "line_color": "#999999",
    },
    "dark": {
        "background": "#1a1a2e",
        "center_fill": "#e94560",
        "center_text": "#ffffff",
        "branch_colors": [
            "#0f3460",
            "#16213e",
            "#533483",
            "#e94560",
            "#0f4c75",
            "#1b262c",
        ],
        "branch_text": "#ffffff",
        "leaf_fill": "#16213e",
        "leaf_text": "#eaeaea",
        "leaf_stroke": "#0f3460",
        "line_color": "#533483",
    },
}


class MindMapTool(BaseTool):
    """思维导图生成工具 — 支持从结构化数据或文本生成思维导图。"""

    name = "mind_map"
    emoji = "🧠"
    title = "思维导图"
    description = "思维导图生成工具"
    timeout = 120

    def __init__(self, output_dir: str | None = None) -> None:
        """初始化思维导图工具。

        Args:
            output_dir: 输出目录路径，为空则使用默认目录 generated/YYYY-MM-DD
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = (
                Path(__file__).parent.parent.parent
                / "generated"
                / datetime.now().strftime("%Y-%m-%d")
            )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_actions(self) -> list[ActionDef]:
        """返回支持的动作列表。"""
        return [
            ActionDef(
                name="generate_mindmap",
                description="从结构化数据生成思维导图",
                parameters={
                    "title": {
                        "type": "string",
                        "description": "中心主题标题",
                    },
                    "nodes": {
                        "type": "object",
                        "description": "嵌套结构的节点数据，格式: {name: string, children: [...]}",
                    },
                    "style": {
                        "type": "string",
                        "description": "颜色主题（可选）: colorful/monochrome/dark，默认 colorful",
                        "enum": ["colorful", "monochrome", "dark"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（可选，默认自动生成）",
                    },
                },
                required_params=["title", "nodes"],
            ),
            ActionDef(
                name="text_to_mindmap",
                description="从文本自动解析生成思维导图，支持 Markdown 大纲格式或纯文本",
                parameters={
                    "text": {
                        "type": "string",
                        "description": "支持 Markdown 大纲格式（# ## ### 或 - *）或纯文本",
                    },
                    "title": {
                        "type": "string",
                        "description": "中心主题标题（可选，自动从文本提取）",
                    },
                    "style": {
                        "type": "string",
                        "description": "颜色主题（可选）: colorful/monochrome/dark，默认 colorful",
                        "enum": ["colorful", "monochrome", "dark"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（可选，默认自动生成）",
                    },
                },
                required_params=["text"],
            ),
            ActionDef(
                name="export_mindmap",
                description="导出思维导图为不同格式",
                parameters={
                    "input_file": {
                        "type": "string",
                        "description": "输入文件路径（SVG 或 PNG）",
                    },
                    "format": {
                        "type": "string",
                        "description": "导出格式: svg/png/pdf/html",
                        "enum": ["svg", "png", "pdf", "html"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（可选，默认自动生成）",
                    },
                },
                required_params=["input_file", "format"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定的思维导图动作。"""
        try:
            if action == "generate_mindmap":
                return self._generate_mindmap(params)
            elif action == "text_to_mindmap":
                return self._text_to_mindmap(params)
            elif action == "export_mindmap":
                return self._export_mindmap(params)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"未知的动作: {action}",
                )
        except FileNotFoundError as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"文件不存在: {e}",
            )
        except ValueError as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"数据错误: {e}",
            )
        except Exception as e:
            logger.exception("思维导图工具执行错误")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"执行错误: {type(e).__name__}: {e}",
            )

    def _get_output_path(self, params: dict[str, Any], suffix: str, default_prefix: str) -> Path:
        """获取输出文件路径。"""
        output_filename = params.get("output_filename", "")
        if output_filename:
            if not output_filename.endswith(suffix):
                output_filename = output_filename.rsplit(".", 1)[0] + suffix
            return self.output_dir / output_filename
        else:
            timestamp = datetime.now().strftime("%H%M%S")
            return self.output_dir / f"{default_prefix}_{timestamp}{suffix}"

    def _generate_mindmap(self, params: dict[str, Any]) -> ToolResult:
        """从结构化数据生成思维导图。"""
        title = params["title"]
        nodes_data = params["nodes"]
        style = params.get("style", "colorful")
        
        if style not in THEMES:
            style = "colorful"
        
        # 构建节点树
        root = MindMapNode(name=title)
        if isinstance(nodes_data, dict):
            # 单个节点对象
            root.children = [MindMapNode.from_dict(nodes_data)]
        elif isinstance(nodes_data, list):
            # 多个子节点
            for item in nodes_data:
                if isinstance(item, dict):
                    root.children.append(MindMapNode.from_dict(item))
                elif isinstance(item, str):
                    root.children.append(MindMapNode(name=item))
        
        # 生成思维导图
        output_path = self._get_output_path(params, ".svg", "mindmap")
        
        if _GRAPHVIZ_AVAILABLE:
            self._generate_with_graphviz(root, output_path, style)
            engine_used = "graphviz"
        else:
            self._generate_svg(root, output_path, style)
            engine_used = "pure_svg"
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"思维导图已生成: {output_path}\n引擎: {engine_used}",
            data={
                "output_path": str(output_path),
                "engine": engine_used,
                "style": style,
                "node_count": self._count_nodes(root),
            },
        )

    def _text_to_mindmap(self, params: dict[str, Any]) -> ToolResult:
        """从文本自动解析生成思维导图。"""
        text = params["text"]
        title = params.get("title", "")
        style = params.get("style", "colorful")
        
        if style not in THEMES:
            style = "colorful"
        
        # 解析文本为节点树
        root = self._parse_text_to_tree(text, title)
        
        if not root.name:
            root.name = "思维导图"
        
        # 生成思维导图
        output_path = self._get_output_path(params, ".svg", "mindmap")
        
        if _GRAPHVIZ_AVAILABLE:
            self._generate_with_graphviz(root, output_path, style)
            engine_used = "graphviz"
        else:
            self._generate_svg(root, output_path, style)
            engine_used = "pure_svg"
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"思维导图已生成: {output_path}\n引擎: {engine_used}",
            data={
                "output_path": str(output_path),
                "engine": engine_used,
                "style": style,
                "node_count": self._count_nodes(root),
            },
        )

    def _export_mindmap(self, params: dict[str, Any]) -> ToolResult:
        """导出思维导图为不同格式。"""
        input_file = Path(params["input_file"])
        export_format = params["format"].lower()
        
        if not input_file.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_file}")
        
        suffix = f".{export_format}"
        output_path = self._get_output_path(params, suffix, f"mindmap_export")
        
        input_suffix = input_file.suffix.lower()
        
        if export_format == "svg":
            if input_suffix == ".svg":
                # 直接复制
                shutil.copy(input_file, output_path)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"不支持从 {input_suffix} 转换为 SVG",
                )
        
        elif export_format == "png":
            if input_suffix == ".svg":
                # 尝试使用 cairosvg 或 Pillow
                try:
                    import cairosvg
                    cairosvg.svg2png(url=str(input_file), write_to=str(output_path))
                except ImportError:
                    # 尝试使用 Inkscape
                    if shutil.which("inkscape"):
                        subprocess.run(
                            ["inkscape", str(input_file), "-o", str(output_path)],
                            check=True,
                            capture_output=True,
                        )
                    else:
                        return ToolResult(
                            status=ToolResultStatus.ERROR,
                            error="SVG 转 PNG 需要 cairosvg 或 inkscape",
                        )
            elif input_suffix == ".png":
                shutil.copy(input_file, output_path)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"不支持从 {input_suffix} 转换为 PNG",
                )
        
        elif export_format == "pdf":
            if input_suffix == ".svg":
                try:
                    import cairosvg
                    cairosvg.svg2pdf(url=str(input_file), write_to=str(output_path))
                except ImportError:
                    if shutil.which("inkscape"):
                        subprocess.run(
                            ["inkscape", str(input_file), "-o", str(output_path)],
                            check=True,
                            capture_output=True,
                        )
                    else:
                        return ToolResult(
                            status=ToolResultStatus.ERROR,
                            error="SVG 转 PDF 需要 cairosvg 或 inkscape",
                        )
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"不支持从 {input_suffix} 转换为 PDF",
                )
        
        elif export_format == "html":
            # 生成包含 SVG 的 HTML 页面
            if input_suffix == ".svg":
                svg_content = input_file.read_text(encoding="utf-8")
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"不支持从 {input_suffix} 转换为 HTML",
                )
            
            html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>思维导图</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
        }}
        h1 {{
            color: #333;
            margin-bottom: 20px;
        }}
        .container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 100%;
            overflow: auto;
        }}
        svg {{
            display: block;
            max-width: 100%;
            height: auto;
        }}
        .footer {{
            margin-top: 20px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>🧠 思维导图</h1>
    <div class="container">
        {svg_content}
    </div>
    <div class="footer">
        由 Weclaw 思维导图工具生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>"""
            output_path.write_text(html_content, encoding="utf-8")
        
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的导出格式: {export_format}",
            )
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"思维导图已导出: {output_path}",
            data={
                "input_path": str(input_file),
                "output_path": str(output_path),
                "format": export_format,
            },
        )

    def _parse_text_to_tree(self, text: str, title: str = "") -> MindMapNode:
        """将文本解析为节点树。
        
        支持的格式：
        - Markdown 标题（# ## ###）
        - 无序列表（- / *）
        - 缩进层级
        """
        lines = text.strip().split("\n")
        root = MindMapNode(name=title)
        
        # 尝试检测格式
        has_headers = any(line.strip().startswith("#") for line in lines)
        has_list = any(re.match(r"^\s*[-*]\s", line) for line in lines)
        
        if has_headers:
            root = self._parse_markdown_headers(lines, title)
        elif has_list:
            root = self._parse_markdown_list(lines, title)
        else:
            root = self._parse_plain_text(lines, title)
        
        return root

    def _parse_markdown_headers(self, lines: list[str], title: str) -> MindMapNode:
        """解析 Markdown 标题格式。"""
        root = MindMapNode(name=title)
        stack: list[tuple[int, MindMapNode]] = [(0, root)]
        
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            
            # 匹配 # 标题
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if header_match:
                level = len(header_match.group(1))
                text = header_match.group(2).strip()
                
                # 第一个 # 作为根标题
                if level == 1 and not root.name:
                    root.name = text
                    continue
                
                node = MindMapNode(name=text)
                
                # 找到合适的父节点
                while stack and stack[-1][0] >= level:
                    stack.pop()
                
                if stack:
                    stack[-1][1].children.append(node)
                else:
                    root.children.append(node)
                
                stack.append((level, node))
            else:
                # 非标题行作为当前节点的子节点（如果是列表项）
                list_match = re.match(r"^\s*[-*]\s+(.+)$", line)
                if list_match and stack:
                    text = list_match.group(1).strip()
                    stack[-1][1].children.append(MindMapNode(name=text))
        
        if not root.name:
            root.name = title or "思维导图"
        
        return root

    def _parse_markdown_list(self, lines: list[str], title: str) -> MindMapNode:
        """解析 Markdown 列表格式。"""
        root = MindMapNode(name=title or "思维导图")
        stack: list[tuple[int, MindMapNode]] = [(-1, root)]
        
        for line in lines:
            if not line.strip():
                continue
            
            # 计算缩进级别
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            
            # 匹配列表项
            list_match = re.match(r"^[-*]\s+(.+)$", stripped)
            if list_match:
                text = list_match.group(1).strip()
                node = MindMapNode(name=text)
                
                # 找到合适的父节点
                while len(stack) > 1 and stack[-1][0] >= indent:
                    stack.pop()
                
                stack[-1][1].children.append(node)
                stack.append((indent, node))
        
        return root

    def _parse_plain_text(self, lines: list[str], title: str) -> MindMapNode:
        """解析纯文本格式（按句子分割）。"""
        root = MindMapNode(name=title or "思维导图")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否有缩进（tab 或 4 空格）
            original = line
            indent_level = 0
            temp_line = line
            while temp_line.startswith("\t") or temp_line.startswith("    "):
                indent_level += 1
                temp_line = temp_line[1:] if temp_line.startswith("\t") else temp_line[4:]
            
            # 简单处理：直接作为子节点
            node = MindMapNode(name=line)
            root.children.append(node)
        
        return root

    def _count_nodes(self, node: MindMapNode) -> int:
        """计算节点总数。"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    # ==================== Graphviz 引擎 ====================

    def _generate_with_graphviz(self, root: MindMapNode, output_path: Path, style: str) -> None:
        """使用 Graphviz 生成思维导图。"""
        if not _graphviz:
            raise RuntimeError("Graphviz 不可用")
        
        theme = THEMES[style]
        
        dot = _graphviz.Digraph(
            format="svg",
            engine="dot",
            graph_attr={
                "bgcolor": theme["background"],
                "rankdir": "LR",
                "splines": "curved",
                "nodesep": "0.5",
                "ranksep": "1.0",
            },
            node_attr={
                "shape": "box",
                "style": "rounded,filled",
                "fontname": "Microsoft YaHei",
                "fontsize": "12",
            },
            edge_attr={
                "color": theme["line_color"],
                "penwidth": "1.5",
            },
        )
        
        # 添加中心节点
        dot.node(
            "root",
            root.name,
            fillcolor=theme["center_fill"],
            fontcolor=theme["center_text"],
            fontsize="16",
            penwidth="2",
        )
        
        # 递归添加子节点
        self._add_graphviz_nodes(dot, root, "root", theme, 0)
        
        # 渲染
        output_stem = str(output_path.with_suffix(""))
        dot.render(output_stem, cleanup=True)

    def _add_graphviz_nodes(
        self, 
        dot: Any, 
        parent: MindMapNode, 
        parent_id: str, 
        theme: dict, 
        depth: int
    ) -> None:
        """递归添加 Graphviz 节点。"""
        branch_colors = theme["branch_colors"]
        
        for i, child in enumerate(parent.children):
            child_id = f"{parent_id}_{i}"
            
            if depth == 0:
                # 一级节点用分支颜色
                fill_color = branch_colors[i % len(branch_colors)]
                text_color = theme["branch_text"]
                fontsize = "14"
            else:
                # 更深层节点用叶子样式
                fill_color = theme["leaf_fill"]
                text_color = theme["leaf_text"]
                fontsize = "11"
            
            dot.node(
                child_id,
                child.name,
                fillcolor=fill_color,
                fontcolor=text_color,
                fontsize=fontsize,
            )
            
            # 连接线颜色
            edge_color = branch_colors[i % len(branch_colors)] if depth == 0 else theme["line_color"]
            dot.edge(parent_id, child_id, color=edge_color)
            
            # 递归处理子节点
            self._add_graphviz_nodes(dot, child, child_id, theme, depth + 1)

    # ==================== 纯 SVG 引擎 ====================

    def _generate_svg(self, root: MindMapNode, output_path: Path, style: str) -> None:
        """使用纯 SVG 生成思维导图。"""
        theme = THEMES[style]
        
        # 计算布局
        layout = self._calculate_layout(root)
        
        # 计算画布大小
        min_x = min(n["x"] - n["width"] / 2 for n in layout.values())
        max_x = max(n["x"] + n["width"] / 2 for n in layout.values())
        min_y = min(n["y"] - n["height"] / 2 for n in layout.values())
        max_y = max(n["y"] + n["height"] / 2 for n in layout.values())
        
        padding = 50
        width = max_x - min_x + padding * 2
        height = max_y - min_y + padding * 2
        
        # 调整坐标（居中）
        offset_x = -min_x + padding
        offset_y = -min_y + padding
        
        for node_data in layout.values():
            node_data["x"] += offset_x
            node_data["y"] += offset_y
        
        # 创建 SVG
        svg = ET.Element(
            "svg",
            xmlns="http://www.w3.org/2000/svg",
            width=str(int(width)),
            height=str(int(height)),
            viewBox=f"0 0 {int(width)} {int(height)}",
        )
        
        # 添加样式
        defs = ET.SubElement(svg, "defs")
        style_elem = ET.SubElement(defs, "style")
        style_elem.text = f"""
            .node-text {{ 
                font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; 
                text-anchor: middle; 
                dominant-baseline: middle;
            }}
        """
        
        # 背景
        ET.SubElement(
            svg,
            "rect",
            width="100%",
            height="100%",
            fill=theme["background"],
        )
        
        # 绘制连接线（先画线，再画节点）
        self._draw_svg_lines(svg, root, layout, theme)
        
        # 绘制节点
        self._draw_svg_nodes(svg, root, layout, theme)
        
        # 保存
        tree = ET.ElementTree(svg)
        ET.indent(tree, space="  ")
        tree.write(str(output_path), encoding="utf-8", xml_declaration=True)

    def _calculate_layout(self, root: MindMapNode) -> dict[str, dict[str, Any]]:
        """计算节点布局。
        
        使用放射状布局：中心节点在中央，子节点向外扩展。
        """
        layout: dict[str, dict[str, Any]] = {}
        
        # 计算每个节点的文本宽度（估算）
        def estimate_text_width(text: str) -> float:
            # 中文字符约 14px，英文约 8px
            width = 0
            for char in text:
                if ord(char) > 127:
                    width += 14
                else:
                    width += 8
            return max(width + 20, 60)  # 最小宽度 60
        
        # 计算子树高度
        def calc_subtree_height(node: MindMapNode, depth: int) -> float:
            node_height = 36 if depth == 0 else 30
            if not node.children:
                return node_height + 10
            children_height = sum(
                calc_subtree_height(child, depth + 1) for child in node.children
            )
            return max(node_height + 10, children_height)
        
        # 中心节点
        center_x = 0
        center_y = 0
        root_width = estimate_text_width(root.name)
        root_height = 44
        
        layout["root"] = {
            "x": center_x,
            "y": center_y,
            "width": root_width,
            "height": root_height,
            "node": root,
            "depth": 0,
            "branch_index": -1,
        }
        
        if not root.children:
            return layout
        
        # 计算子节点布局
        h_spacing = 180  # 水平间距
        v_spacing = 15   # 垂直间距
        
        # 将子节点分成左右两组
        n_children = len(root.children)
        left_children = root.children[: (n_children + 1) // 2]
        right_children = root.children[(n_children + 1) // 2:]
        
        def layout_branch(
            children: list[MindMapNode],
            start_x: float,
            direction: int,  # 1 = 右, -1 = 左
            branch_start_index: int,
        ) -> None:
            """布局一个分支的所有子节点。"""
            total_height = sum(calc_subtree_height(c, 1) for c in children)
            current_y = -total_height / 2
            
            for i, child in enumerate(children):
                branch_index = branch_start_index + i
                child_height = calc_subtree_height(child, 1)
                child_y = current_y + child_height / 2
                child_x = start_x + direction * h_spacing
                
                child_id = f"node_{branch_index}"
                child_width = estimate_text_width(child.name)
                
                layout[child_id] = {
                    "x": child_x,
                    "y": child_y,
                    "width": child_width,
                    "height": 36,
                    "node": child,
                    "depth": 1,
                    "branch_index": branch_index,
                    "parent_id": "root",
                }
                
                # 递归布局子节点
                if child.children:
                    layout_children(
                        child.children,
                        child_id,
                        child_x,
                        child_y - child_height / 2 + 18,
                        child_height,
                        direction,
                        branch_index,
                        2,
                    )
                
                current_y += child_height
        
        def layout_children(
            children: list[MindMapNode],
            parent_id: str,
            parent_x: float,
            start_y: float,
            available_height: float,
            direction: int,
            branch_index: int,
            depth: int,
        ) -> None:
            """递归布局子节点。"""
            if not children:
                return
            
            n = len(children)
            child_height_each = available_height / n if n > 0 else 30
            current_y = start_y
            
            for i, child in enumerate(children):
                child_id = f"{parent_id}_{i}"
                child_x = parent_x + direction * (120 + depth * 10)
                child_y = current_y + child_height_each / 2
                child_width = estimate_text_width(child.name)
                
                layout[child_id] = {
                    "x": child_x,
                    "y": child_y,
                    "width": child_width,
                    "height": 28,
                    "node": child,
                    "depth": depth,
                    "branch_index": branch_index,
                    "parent_id": parent_id,
                }
                
                if child.children:
                    layout_children(
                        child.children,
                        child_id,
                        child_x,
                        child_y - child_height_each / 2 + 14,
                        child_height_each,
                        direction,
                        branch_index,
                        depth + 1,
                    )
                
                current_y += child_height_each
        
        # 布局左右两侧
        layout_branch(right_children, center_x, 1, 0)
        layout_branch(left_children, center_x, -1, len(right_children))
        
        return layout

    def _draw_svg_lines(
        self, 
        svg: ET.Element, 
        root: MindMapNode, 
        layout: dict[str, dict[str, Any]], 
        theme: dict
    ) -> None:
        """绘制 SVG 连接线。"""
        branch_colors = theme["branch_colors"]
        
        for node_id, node_data in layout.items():
            if node_id == "root":
                continue
            
            parent_id = node_data.get("parent_id", "root")
            parent_data = layout.get(parent_id)
            
            if not parent_data:
                continue
            
            # 确定线条颜色
            branch_index = node_data.get("branch_index", 0)
            if node_data["depth"] == 1:
                line_color = branch_colors[branch_index % len(branch_colors)]
            else:
                line_color = theme["line_color"]
            
            # 贝塞尔曲线
            x1, y1 = parent_data["x"], parent_data["y"]
            x2, y2 = node_data["x"], node_data["y"]
            
            # 调整起点和终点到节点边缘
            if x2 > x1:
                x1 += parent_data["width"] / 2
                x2 -= node_data["width"] / 2
            else:
                x1 -= parent_data["width"] / 2
                x2 += node_data["width"] / 2
            
            # 控制点
            cx1 = x1 + (x2 - x1) * 0.4
            cx2 = x1 + (x2 - x1) * 0.6
            
            path_d = f"M {x1} {y1} C {cx1} {y1}, {cx2} {y2}, {x2} {y2}"
            
            ET.SubElement(
                svg,
                "path",
                d=path_d,
                fill="none",
                stroke=line_color,
                **{"stroke-width": "2", "stroke-linecap": "round"},
            )

    def _draw_svg_nodes(
        self, 
        svg: ET.Element, 
        root: MindMapNode, 
        layout: dict[str, dict[str, Any]], 
        theme: dict
    ) -> None:
        """绘制 SVG 节点。"""
        branch_colors = theme["branch_colors"]
        
        for node_id, node_data in layout.items():
            x = node_data["x"]
            y = node_data["y"]
            width = node_data["width"]
            height = node_data["height"]
            node = node_data["node"]
            depth = node_data["depth"]
            branch_index = node_data.get("branch_index", 0)
            
            # 确定节点样式
            if depth == 0:
                # 中心节点
                fill_color = theme["center_fill"]
                text_color = theme["center_text"]
                font_size = 16
                stroke_color = "none"
            elif depth == 1:
                # 一级节点
                fill_color = branch_colors[branch_index % len(branch_colors)]
                text_color = theme["branch_text"]
                font_size = 13
                stroke_color = "none"
            else:
                # 叶子节点
                fill_color = theme["leaf_fill"]
                text_color = theme["leaf_text"]
                font_size = 11
                stroke_color = theme["leaf_stroke"]
            
            # 绘制圆角矩形
            rx = 8 if depth == 0 else 6
            rect_attrs = {
                "x": str(x - width / 2),
                "y": str(y - height / 2),
                "width": str(width),
                "height": str(height),
                "rx": str(rx),
                "ry": str(rx),
                "fill": fill_color,
            }
            if stroke_color != "none":
                rect_attrs["stroke"] = stroke_color
                rect_attrs["stroke-width"] = "1"
            
            ET.SubElement(svg, "rect", **rect_attrs)
            
            # 绘制文本
            text_elem = ET.SubElement(
                svg,
                "text",
                x=str(x),
                y=str(y),
                fill=text_color,
                **{
                    "class": "node-text",
                    "font-size": str(font_size),
                },
            )
            text_elem.text = node.name
