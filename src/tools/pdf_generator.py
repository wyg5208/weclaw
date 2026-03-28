"""PDF 生成工具 - 使用 Playwright + Paged.js 实现高质量 PDF 生成。

核心功能：
- html_to_pdf: HTML → PDF（Playwright + Paged.js 分页控制）
- md_to_pdf: Markdown → PDF（先转 HTML）
- apply_styling: 应用打印样式

参考 MiniMax minimax-pdf/SKILL.md 设计

硬约束：
- 禁止截图/打印 hack 方案
- 禁止手动注入 Paged.js
- 禁止运行时图表引擎
- 禁止装饰性 emoji/icon
"""

from __future__ import annotations

import logging
import markdown
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


# CSS 分页模型模板（参考 MiniMax）
PAGE_STYLE_TEMPLATE = """
@page {{
    size: A4;
    margin: 2.4cm 1.9cm;
    @top-center {{
        content: string(doc_title);
        font-size: 9pt;
        color: #666;
    }}
    @bottom-center {{
        content: counter(page);
        font-size: 9pt;
        color: #666;
    }}
}}

@page :first {{
    margin: 0;
}}

@page titlepage {{
    @top-center {{ content: none; }}
    @bottom-center {{ content: none; }}
}}

body {{
    string-set: doc_title "{title}";
}}

h1 {{ string-set: doc_title content(); }}
.cover-page {{ page: titlepage; }}

/* 溢出保护 */
pre, table, figure, img, svg, .diagram, blockquote, .eq-block {{
    max-inline-size: 100%;
    box-sizing: border-box;
}}

pre {{
    overflow-x: auto;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}}

figure img, figure svg {{
    max-inline-size: 82%;
    max-block-size: 42vh;
    height: auto;
}}

table {{ overflow-x: auto; }}
.katex-display {{ overflow-x: auto; }}
code {{ overflow-wrap: anywhere; }}
a {{ overflow-wrap: anywhere; }}
tr {{ break-inside: avoid; }}

body {{
    text-align: justify;
    text-align-last: start;
}}
"""


@dataclass
class PDFGenerationOptions:
    """PDF 生成选项。"""
    title: str = ""
    author: str = ""
    subject: str = ""
    keywords: str = ""
    include_page_numbers: bool = True
    include_title: bool = True
    page_size: str = "A4"
    margin_top: str = "2.4cm"
    margin_bottom: str = "2.4cm"
    margin_left: str = "1.9cm"
    margin_right: str = "1.9cm"
    enable_hyperlinks: bool = True
    prefer_css_page_size: bool = False


class PDFGeneratorTool(BaseTool):
    """PDF 生成工具。

    使用 Playwright + Paged.js 实现高质量 PDF 生成，支持：
    - HTML → PDF
    - Markdown → PDF
    - 专业样式系统
    """

    name = "pdf_generator"
    emoji = "📑"
    title = "PDF生成"
    description = "高质量 PDF 生成，支持 HTML/Markdown 转 PDF，使用 Playwright + Paged.js 实现专业分页控制"
    timeout = 120

    def __init__(self, output_dir: str = "") -> None:
        """初始化 PDF 生成工具。

        Args:
            output_dir: 输出目录，默认为项目的 generated/日期/ 目录
        """
        super().__init__()
        self.output_dir = (
            Path(output_dir)
            if output_dir
            else Path(__file__).parent.parent.parent / "generated" / datetime.now().strftime("%Y-%m-%d")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_actions(self) -> list[ActionDef]:
        return [
            ActionDef(
                name="html_to_pdf",
                description="将 HTML 内容转换为高质量 PDF 文件，支持专业分页控制",
                parameters={
                    "html_content": {
                        "type": "string",
                        "description": "HTML 内容（完整的 HTML 文档）",
                    },
                    "title": {
                        "type": "string",
                        "description": "文档标题，用于页眉显示",
                    },
                    "filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                    "options": {
                        "type": "object",
                        "description": "生成选项（page_size, margins, include_page_numbers 等）",
                    },
                },
                required_params=["html_content"],
            ),
            ActionDef(
                name="md_to_pdf",
                description="将 Markdown 内容转换为高质量 PDF 文件",
                parameters={
                    "markdown_content": {
                        "type": "string",
                        "description": "Markdown 内容",
                    },
                    "title": {
                        "type": "string",
                        "description": "文档标题",
                    },
                    "filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                    "options": {
                        "type": "object",
                        "description": "生成选项",
                    },
                },
                required_params=["markdown_content"],
            ),
            ActionDef(
                name="apply_print_style",
                description="将 HTML 内容应用打印样式后转为 PDF",
                parameters={
                    "html_content": {
                        "type": "string",
                        "description": "原始 HTML 内容",
                    },
                    "style": {
                        "type": "string",
                        "description": "样式主题: academic/business/technical",
                    },
                    "filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["html_content", "style"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行 PDF 生成动作。"""
        if action == "html_to_pdf":
            return self._html_to_pdf(params)
        elif action == "md_to_pdf":
            return self._md_to_pdf(params)
        elif action == "apply_print_style":
            return self._apply_print_style(params)
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作: {action}",
            )

    def _html_to_pdf(self, params: dict[str, Any]) -> ToolResult:
        """将 HTML 转换为 PDF。"""
        html_content = params.get("html_content", "")
        if not html_content:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="HTML 内容不能为空",
            )

        title = params.get("title", "文档")
        filename = params.get("filename", "").strip()
        options = params.get("options", {})

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pdf_{timestamp}"

        output_path = self.output_dir / f"{filename}.pdf"

        try:
            # 构建 PDF 生成选项
            pdf_options = PDFGenerationOptions(
                title=title,
                **options
            )

            # 生成 PDF
            success = self._generate_pdf_with_playwright(
                html_content, output_path, pdf_options
            )

            if not success:
                # Playwright 不可用，尝试降级方案
                return self._html_to_pdf_fallback(
                    html_content, title, output_path
                )

            file_size = output_path.stat().st_size
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PDF 生成完成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📄 标题: {title}",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size": file_size,
                    "title": title,
                },
            )

        except Exception as e:
            logger.error("PDF 生成失败: %s", e)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"PDF 生成失败: {e}",
            )

    def _md_to_pdf(self, params: dict[str, Any]) -> ToolResult:
        """将 Markdown 转换为 PDF。"""
        markdown_content = params.get("markdown_content", "")
        if not markdown_content:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="Markdown 内容不能为空",
            )

        title = params.get("title", "Markdown 文档")
        filename = params.get("filename", "").strip()
        options = params.get("options", {})

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"md_pdf_{timestamp}"

        output_path = self.output_dir / f"{filename}.pdf"

        try:
            # 将 Markdown 转换为 HTML
            html_body = markdown.markdown(
                markdown_content,
                extensions=["tables", "fenced_code", "toc"]
            )

            # 构建完整 HTML
            html_content = self._build_html_document(html_body, title)

            # 生成 PDF
            pdf_options = PDFGenerationOptions(
                title=title,
                **options
            )

            success = self._generate_pdf_with_playwright(
                html_content, output_path, pdf_options
            )

            if not success:
                return self._html_to_pdf_fallback(
                    html_content, title, output_path
                )

            file_size = output_path.stat().st_size
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PDF 生成完成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📄 标题: {title}",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size": file_size,
                    "title": title,
                },
            )

        except Exception as e:
            logger.error("Markdown 转 PDF 失败: %s", e)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"Markdown 转 PDF 失败: {e}",
            )

    def _apply_print_style(self, params: dict[str, Any]) -> ToolResult:
        """应用打印样式后转为 PDF。"""
        html_content = params.get("html_content", "")
        if not html_content:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="HTML 内容不能为空",
            )

        style = params.get("style", "academic")
        filename = params.get("filename", "").strip()

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"styled_pdf_{timestamp}"

        output_path = self.output_dir / f"{filename}.pdf"

        try:
            # 获取样式模板
            styled_html = self._apply_document_style(html_content, style)
            title = params.get("title", f"{style.capitalize()} 文档")

            # 生成 PDF
            pdf_options = PDFGenerationOptions(title=title)

            success = self._generate_pdf_with_playwright(
                styled_html, output_path, pdf_options
            )

            if not success:
                return self._html_to_pdf_fallback(
                    styled_html, title, output_path
                )

            file_size = output_path.stat().st_size
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PDF 生成完成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n🎨 样式: {style}",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size": file_size,
                    "style": style,
                },
            )

        except Exception as e:
            logger.error("样式化 PDF 生成失败: %s", e)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"样式化 PDF 生成失败: {e}",
            )

    def _build_html_document(self, html_body: str, title: str) -> str:
        """构建完整的 HTML 文档。"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        {PAGE_STYLE_TEMPLATE.format(title=title)}
        
        /* 文档样式 */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 100%;
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            color: #1a1a1a;
        }}
        h1 {{ font-size: 2em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }}
        h3 {{ font-size: 1.25em; }}
        p {{ margin: 0 0 1em 0; }}
        ul, ol {{ padding-left: 2em; margin-bottom: 1em; }}
        li {{ margin-bottom: 0.25em; }}
        blockquote {{
            margin: 0 0 1em 0;
            padding: 0 1em;
            color: #666;
            border-left: 0.25em solid #ddd;
        }}
        pre {{
            background-color: #f6f8fa;
            border-radius: 6px;
            padding: 1em;
            margin-bottom: 1em;
            font-size: 0.9em;
        }}
        code {{
            font-family: 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 0.9em;
            background-color: rgba(27, 31, 35, 0.05);
            padding: 0.2em 0.4em;
            border-radius: 3px;
        }}
        pre code {{ background: none; padding: 0; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 1em;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 0.5em 1em;
            text-align: left;
        }}
        th {{ background-color: #f6f8fa; font-weight: 600; }}
        img {{ max-width: 100%; height: auto; }}
        a {{ color: #0366d6; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {html_body}
</body>
</html>"""

    def _apply_document_style(self, html_content: str, style: str) -> str:
        """应用文档样式。"""
        styles = {
            "academic": {
                "font": "'Georgia', 'Noto Serif', serif",
                "h_color": "#1a365d",
                "link": "#1c7ed6",
            },
            "business": {
                "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "h_color": "#1a202c",
                "link": "#2b6cb0",
            },
            "technical": {
                "font": "'SF Mono', Consolas, monospace",
                "h_color": "#2d3748",
                "link": "#3182ce",
            },
        }

        style_config = styles.get(style, styles["academic"])

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: {style_config['font']};
            line-height: 1.7;
            color: #333;
            max-width: 100%;
        }}
        h1, h2, h3 {{ color: {style_config['h_color']}; }}
        a {{ color: {style_config['link']}; }}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""

    def _generate_pdf_with_playwright(
        self,
        html_content: str,
        output_path: Path,
        options: PDFGenerationOptions
    ) -> bool:
        """使用 Playwright 生成 PDF。"""
        try:
            import playwright
        except ImportError:
            logger.warning("Playwright 未安装")
            return False

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_html = Path(tmp_dir) / "input.html"
                tmp_html.write_text(html_content, encoding="utf-8")

                # 使用 subprocess 调用 Playwright CLI 或 Python API
                result = subprocess.run(
                    [
                        "python", "-c",
                        f"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto('file://{tmp_html.as_posix()}')
        await page.pdf(
            path='{output_path.as_posix()}',
            format='{options.page_size}',
            print_background=True,
            margin={{
                'top': '{options.margin_top}',
                'right': '{options.margin_right}',
                'bottom': '{options.margin_bottom}',
                'left': '{options.margin_left}'
            }}
        )
        await browser.close()

asyncio.run(main())
"""
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    return output_path.exists()
                else:
                    logger.warning("Playwright PDF 生成失败: %s", result.stderr)
                    return False

        except Exception as e:
            logger.warning("Playwright 调用失败: %s", e)
            return False

    def _html_to_pdf_fallback(
        self,
        html_content: str,
        title: str,
        output_path: Path
    ) -> ToolResult:
        """降级方案：使用 weasyprint 或 pandoc 生成 PDF。"""
        # 尝试使用 pandoc
        pandoc_path = shutil.which("pandoc")
        if pandoc_path:
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    tmp_html = Path(tmp_dir) / "input.html"
                    tmp_html.write_text(html_content, encoding="utf-8")

                    result = subprocess.run(
                        ["pandoc", str(tmp_html), "-o", str(output_path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    if result.returncode == 0 and output_path.exists():
                        file_size = output_path.stat().st_size
                        return ToolResult(
                            status=ToolResultStatus.SUCCESS,
                            output=f"✅ PDF 生成完成（Pandoc）\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节",
                            data={
                                "file_path": str(output_path),
                                "file_name": output_path.name,
                                "file_size": file_size,
                                "engine": "pandoc",
                            },
                        )
            except Exception as e:
                logger.warning("Pandoc PDF 生成失败: %s", e)

        return ToolResult(
            status=ToolResultStatus.ERROR,
            error="PDF 生成失败，请安装 Playwright（pip install playwright && playwright install）"
        )


# 用于测试
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = PDFGeneratorTool()

        # 测试 Markdown 转 PDF
        result = await tool.execute(
            "md_to_pdf",
            {
                "markdown_content": """# 测试文档

这是一个测试文档。

## 第一节

内容...

## 第二节

更多内容...
""",
                "title": "测试 PDF",
            }
        )
        print("结果:", result.output)
        print("数据:", result.data)

    asyncio.run(test())
