"""PPT 生成工具 — AI 生成演示文稿 PPT，支持多种风格模板。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt, Emu

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


# 风格配色方案
STYLE_COLORS = {
    "business": {
        "primary": RGBColor(0x00, 0x52, 0x8A),
        "secondary": RGBColor(0x33, 0x33, 0x33),
        "accent": RGBColor(0x00, 0x96, 0xD6),
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
    },
    "academic": {
        "primary": RGBColor(0x1A, 0x23, 0x7E),
        "secondary": RGBColor(0x44, 0x44, 0x44),
        "accent": RGBColor(0xC6, 0x28, 0x28),
        "bg": RGBColor(0xFA, 0xFA, 0xFA),
    },
    "creative": {
        "primary": RGBColor(0xE9, 0x1E, 0x63),
        "secondary": RGBColor(0x33, 0x33, 0x33),
        "accent": RGBColor(0xFF, 0xC1, 0x07),
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
    },
    "minimal": {
        "primary": RGBColor(0x21, 0x21, 0x21),
        "secondary": RGBColor(0x75, 0x75, 0x75),
        "accent": RGBColor(0x42, 0x42, 0x42),
        "bg": RGBColor(0xFF, 0xFF, 0xFF),
    },
}


class PPTTool(BaseTool):
    """PPT 生成工具。

    支持 AI 生成演示文稿 PPT，包含多种风格模板。
    - generate_ppt: 根据主题和大纲生成完整 PPT
    - add_slide: 向已有 PPT 添加幻灯片
    - export_pdf: 将 PPT 导出为 PDF
    """

    name = "ppt_generator"
    emoji = "📊"
    title = "PPT生成"
    description = "AI 生成演示文稿 PPT，支持多种风格模板"
    timeout = 120

    def __init__(self, output_dir: str = "") -> None:
        """初始化 PPT 生成工具。

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
                name="generate_ppt",
                description="AI 生成完整 PPT 演示文稿，根据主题和大纲自动创建多页幻灯片",
                parameters={
                    "topic": {
                        "type": "string",
                        "description": "PPT 主题",
                    },
                    "outline": {
                        "type": "string",
                        "description": "大纲内容，每行一个要点",
                    },
                    "style": {
                        "type": "string",
                        "description": "风格: business/academic/creative/minimal",
                        "enum": ["business", "academic", "creative", "minimal"],
                    },
                    "slide_count": {
                        "type": "integer",
                        "description": "幻灯片数量，默认8",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名）",
                    },
                },
                required_params=["topic"],
            ),
            ActionDef(
                name="add_slide",
                description="向已有 PPT 文件添加新的幻灯片",
                parameters={
                    "ppt_path": {
                        "type": "string",
                        "description": "已有 PPT 文件路径",
                    },
                    "title": {
                        "type": "string",
                        "description": "幻灯片标题",
                    },
                    "content": {
                        "type": "string",
                        "description": "幻灯片内容，支持多行，每行一个要点",
                    },
                    "layout": {
                        "type": "string",
                        "description": "布局: title/content/two_column/blank",
                        "enum": ["title", "content", "two_column", "blank"],
                    },
                },
                required_params=["ppt_path", "title", "content"],
            ),
            ActionDef(
                name="export_pdf",
                description="将 PPT 文件导出为 PDF 格式",
                parameters={
                    "ppt_path": {
                        "type": "string",
                        "description": "PPT 文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出 PDF 文件名（不含扩展名）",
                    },
                },
                required_params=["ppt_path"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        if action == "generate_ppt":
            return self._generate_ppt(params)
        elif action == "add_slide":
            return self._add_slide(params)
        elif action == "export_pdf":
            return self._export_pdf(params)
        else:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作: {action}",
            )

    def _get_style_colors(self, style: str) -> dict[str, RGBColor]:
        """获取指定风格的配色方案。"""
        return STYLE_COLORS.get(style, STYLE_COLORS["business"])

    def _set_slide_background(self, slide, bg_color: RGBColor) -> None:
        """设置幻灯片背景色。"""
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = bg_color

    def _add_title_slide(self, prs: Presentation, topic: str, colors: dict[str, RGBColor]) -> None:
        """添加标题页。"""
        slide_layout = prs.slide_layouts[6]  # 空白布局
        slide = prs.slides.add_slide(slide_layout)
        self._set_slide_background(slide, colors["bg"])

        # 标题
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5)
        )
        title_frame = title_box.text_frame
        title_frame.word_wrap = True
        p = title_frame.paragraphs[0]
        p.text = topic
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = colors["primary"]
        p.alignment = PP_ALIGN.CENTER

        # 副标题/日期
        subtitle_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(4.2), Inches(12.333), Inches(0.8)
        )
        subtitle_frame = subtitle_box.text_frame
        p = subtitle_frame.paragraphs[0]
        p.text = datetime.now().strftime("%Y年%m月%d日")
        p.font.size = Pt(20)
        p.font.color.rgb = colors["secondary"]
        p.alignment = PP_ALIGN.CENTER

    def _add_content_slide(
        self,
        prs: Presentation,
        slide_title: str,
        subtitle: str,
        colors: dict[str, RGBColor],
        bullet_points: list[str] | None = None,
    ) -> None:
        """添加内容页。"""
        slide_layout = prs.slide_layouts[6]  # 空白布局
        slide = prs.slides.add_slide(slide_layout)
        self._set_slide_background(slide, colors["bg"])

        # 标题
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.4), Inches(12.333), Inches(1.0)
        )
        title_frame = title_box.text_frame
        title_frame.word_wrap = True
        p = title_frame.paragraphs[0]
        p.text = slide_title
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = colors["primary"]
        p.alignment = PP_ALIGN.LEFT

        # 副标题
        subtitle_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(1.3), Inches(12.333), Inches(0.5)
        )
        subtitle_frame = subtitle_box.text_frame
        p = subtitle_frame.paragraphs[0]
        p.text = subtitle
        p.font.size = Pt(18)
        p.font.color.rgb = colors["accent"]
        p.alignment = PP_ALIGN.LEFT

        # 内容区域（要点列表）
        content_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(2.0), Inches(11.733), Inches(4.5)
        )
        content_frame = content_box.text_frame
        content_frame.word_wrap = True

        if bullet_points:
            for i, point in enumerate(bullet_points):
                if i == 0:
                    p = content_frame.paragraphs[0]
                else:
                    p = content_frame.add_paragraph()
                p.text = f"• {point}"
                p.font.size = Pt(20)
                p.font.color.rgb = colors["secondary"]
                p.space_after = Pt(12)
        else:
            # 默认占位内容
            p = content_frame.paragraphs[0]
            p.text = "• 请在此处添加内容"
            p.font.size = Pt(20)
            p.font.color.rgb = colors["secondary"]

    def _add_thank_slide(self, prs: Presentation, colors: dict[str, RGBColor]) -> None:
        """添加感谢页。"""
        slide_layout = prs.slide_layouts[6]  # 空白布局
        slide = prs.slides.add_slide(slide_layout)
        self._set_slide_background(slide, colors["bg"])

        # 感谢文字
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(3.0), Inches(12.333), Inches(1.5)
        )
        title_frame = title_box.text_frame
        title_frame.word_wrap = True
        p = title_frame.paragraphs[0]
        p.text = "感谢聆听"
        p.font.size = Pt(48)
        p.font.bold = True
        p.font.color.rgb = colors["primary"]
        p.alignment = PP_ALIGN.CENTER

        # 副文字
        subtitle_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(4.5), Inches(12.333), Inches(0.8)
        )
        subtitle_frame = subtitle_box.text_frame
        p = subtitle_frame.paragraphs[0]
        p.text = "THANK YOU"
        p.font.size = Pt(24)
        p.font.color.rgb = colors["accent"]
        p.alignment = PP_ALIGN.CENTER

    def _generate_ppt(self, params: dict[str, Any]) -> ToolResult:
        """生成完整 PPT。"""
        topic = params.get("topic", "").strip()
        if not topic:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="PPT 主题不能为空",
            )

        outline = params.get("outline", "").strip()
        style = params.get("style", "business")
        slide_count = int(params.get("slide_count", 8))
        output_filename = params.get("output_filename", "").strip()

        # 验证风格
        if style not in STYLE_COLORS:
            style = "business"

        try:
            prs = Presentation()
            prs.slide_width = Inches(13.333)  # 16:9
            prs.slide_height = Inches(7.5)

            colors = self._get_style_colors(style)

            # 1. 标题页
            self._add_title_slide(prs, topic, colors)

            # 2. 内容页
            if outline:
                # 按大纲生成内容页
                points = [p.strip() for p in outline.split("\n") if p.strip()]
                for i, point in enumerate(points):
                    self._add_content_slide(
                        prs,
                        slide_title=point,
                        subtitle=f"第 {i + 1} 部分",
                        colors=colors,
                    )
            else:
                # 生成默认结构
                default_sections = [
                    "背景介绍",
                    "核心内容",
                    "关键要点",
                    "数据分析",
                    "案例展示",
                    "总结与展望",
                ]
                for i, section in enumerate(default_sections[: slide_count - 2]):
                    self._add_content_slide(
                        prs,
                        slide_title=section,
                        subtitle=f"第 {i + 1} 部分",
                        colors=colors,
                    )

            # 3. 感谢页
            self._add_thank_slide(prs, colors)

            # 生成文件名
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # 清理主题中的特殊字符
                safe_topic = "".join(c for c in topic[:20] if c.isalnum() or c in " _-")
                output_filename = f"ppt_{safe_topic}_{timestamp}"

            output_path = self.output_dir / f"{output_filename}.pptx"
            prs.save(str(output_path))

            file_size = output_path.stat().st_size
            actual_slide_count = len(prs.slides)

            logger.info("PPT 生成成功: %s (%d 页)", output_path, actual_slide_count)

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PPT 生成完成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📄 共 {actual_slide_count} 页\n🎨 风格: {style}",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size": file_size,
                    "slide_count": actual_slide_count,
                    "style": style,
                },
            )

        except Exception as e:
            logger.error("PPT 生成失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"PPT 生成失败: {e}",
            )

    def _add_slide(self, params: dict[str, Any]) -> ToolResult:
        """向已有 PPT 添加幻灯片。"""
        ppt_path = params.get("ppt_path", "").strip()
        title = params.get("title", "").strip()
        content = params.get("content", "").strip()
        layout = params.get("layout", "content")

        if not ppt_path:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="PPT 文件路径不能为空",
            )

        if not title:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="幻灯片标题不能为空",
            )

        if not content:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="幻灯片内容不能为空",
            )

        ppt_file = Path(ppt_path)
        if not ppt_file.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"PPT 文件不存在: {ppt_path}",
            )

        try:
            prs = Presentation(str(ppt_file))
            colors = self._get_style_colors("business")  # 默认使用商务风格

            # 解析内容为要点列表
            bullet_points = [p.strip() for p in content.split("\n") if p.strip()]

            if layout == "title":
                # 标题布局
                self._add_title_slide(prs, title, colors)
            elif layout == "blank":
                # 空白布局
                slide_layout = prs.slide_layouts[6]
                slide = prs.slides.add_slide(slide_layout)
                self._set_slide_background(slide, colors["bg"])
                # 只添加标题
                title_box = slide.shapes.add_textbox(
                    Inches(0.5), Inches(0.4), Inches(12.333), Inches(1.0)
                )
                title_frame = title_box.text_frame
                p = title_frame.paragraphs[0]
                p.text = title
                p.font.size = Pt(32)
                p.font.bold = True
                p.font.color.rgb = colors["primary"]
            elif layout == "two_column":
                # 两列布局
                slide_layout = prs.slide_layouts[6]
                slide = prs.slides.add_slide(slide_layout)
                self._set_slide_background(slide, colors["bg"])

                # 标题
                title_box = slide.shapes.add_textbox(
                    Inches(0.5), Inches(0.4), Inches(12.333), Inches(1.0)
                )
                title_frame = title_box.text_frame
                p = title_frame.paragraphs[0]
                p.text = title
                p.font.size = Pt(32)
                p.font.bold = True
                p.font.color.rgb = colors["primary"]

                # 分两列显示内容
                mid = len(bullet_points) // 2
                left_points = bullet_points[:mid] if mid > 0 else bullet_points
                right_points = bullet_points[mid:] if mid > 0 else []

                # 左列
                left_box = slide.shapes.add_textbox(
                    Inches(0.5), Inches(1.8), Inches(5.9), Inches(5.0)
                )
                left_frame = left_box.text_frame
                left_frame.word_wrap = True
                for i, point in enumerate(left_points):
                    if i == 0:
                        p = left_frame.paragraphs[0]
                    else:
                        p = left_frame.add_paragraph()
                    p.text = f"• {point}"
                    p.font.size = Pt(18)
                    p.font.color.rgb = colors["secondary"]
                    p.space_after = Pt(10)

                # 右列
                right_box = slide.shapes.add_textbox(
                    Inches(6.9), Inches(1.8), Inches(5.9), Inches(5.0)
                )
                right_frame = right_box.text_frame
                right_frame.word_wrap = True
                for i, point in enumerate(right_points):
                    if i == 0:
                        p = right_frame.paragraphs[0]
                    else:
                        p = right_frame.add_paragraph()
                    p.text = f"• {point}"
                    p.font.size = Pt(18)
                    p.font.color.rgb = colors["secondary"]
                    p.space_after = Pt(10)
            else:
                # 默认内容布局
                self._add_content_slide(
                    prs,
                    slide_title=title,
                    subtitle="",
                    colors=colors,
                    bullet_points=bullet_points,
                )

            # 保存回原文件
            prs.save(str(ppt_file))

            slide_count = len(prs.slides)
            logger.info("已向 PPT 添加幻灯片: %s (共 %d 页)", ppt_file, slide_count)

            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ 幻灯片添加成功\n📁 文件: {ppt_file.name}\n📄 当前共 {slide_count} 页\n📝 新增标题: {title}",
                data={
                    "file_path": str(ppt_file),
                    "file_name": ppt_file.name,
                    "slide_count": slide_count,
                    "new_slide_title": title,
                    "layout": layout,
                },
            )

        except Exception as e:
            logger.error("添加幻灯片失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"添加幻灯片失败: {e}",
            )

    def _export_pdf(self, params: dict[str, Any]) -> ToolResult:
        """导出 PPT 为 PDF。"""
        ppt_path = params.get("ppt_path", "").strip()
        output_filename = params.get("output_filename", "").strip()

        if not ppt_path:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="PPT 文件路径不能为空",
            )

        ppt_file = Path(ppt_path)
        if not ppt_file.exists():
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"PPT 文件不存在: {ppt_path}",
            )

        # 生成输出文件名
        if not output_filename:
            output_filename = ppt_file.stem

        output_path = self.output_dir / f"{output_filename}.pdf"

        # 尝试使用 LibreOffice 转换
        libreoffice_path = shutil.which("libreoffice") or shutil.which("soffice")
        
        if libreoffice_path:
            try:
                result = subprocess.run(
                    [
                        libreoffice_path,
                        "--headless",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        str(self.output_dir),
                        str(ppt_file),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    # LibreOffice 输出的文件名可能与输入同名
                    expected_output = self.output_dir / f"{ppt_file.stem}.pdf"
                    if expected_output.exists() and expected_output != output_path:
                        expected_output.rename(output_path)

                    if output_path.exists():
                        file_size = output_path.stat().st_size
                        logger.info("PDF 导出成功: %s", output_path)

                        return ToolResult(
                            status=ToolResultStatus.SUCCESS,
                            output=f"✅ PDF 导出成功\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节",
                            data={
                                "file_path": str(output_path),
                                "file_name": output_path.name,
                                "file_size": file_size,
                                "export_method": "libreoffice",
                            },
                        )
                else:
                    logger.warning("LibreOffice 转换失败: %s", result.stderr)
            except subprocess.TimeoutExpired:
                logger.warning("LibreOffice 转换超时")
            except Exception as e:
                logger.warning("LibreOffice 转换出错: %s", e)

        # LibreOffice 不可用或转换失败，返回手动导出提示
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"⚠️ 自动 PDF 导出需要安装 LibreOffice。\n请手动打开 PPT 后导出为 PDF。\n📁 PPT 文件: {ppt_file}",
            data={
                "ppt_path": str(ppt_file),
                "export_method": "manual",
                "suggestion": "请使用 PowerPoint 或 WPS 打开 PPT 文件后，选择「另存为」或「导出」为 PDF 格式。",
            },
        )


# 用于测试
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = PPTTool()
        
        # 测试生成 PPT
        result = await tool.execute(
            "generate_ppt",
            {
                "topic": "人工智能发展趋势",
                "outline": "AI 历史回顾\n当前技术突破\n应用场景分析\n未来发展预测",
                "style": "business",
            },
        )
        print("生成 PPT 结果:")
        print(result.output)
        print("Data:", result.data)
        
        if result.is_success:
            # 测试添加幻灯片
            ppt_path = result.data["file_path"]
            result2 = await tool.execute(
                "add_slide",
                {
                    "ppt_path": ppt_path,
                    "title": "补充说明",
                    "content": "第一个要点\n第二个要点\n第三个要点",
                    "layout": "content",
                },
            )
            print("\n添加幻灯片结果:")
            print(result2.output)

    asyncio.run(test())
