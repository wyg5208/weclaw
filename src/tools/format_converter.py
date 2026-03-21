"""格式转换工具 — 文档、数据、图片格式转换。

支持的转换：
- Pandoc 核心转换：Markdown ↔ Word/HTML/PDF/LaTeX
- 数据格式转换：CSV ↔ JSON, JSON → XML
- 图片格式转换：PNG/JPG/WebP/BMP/TIFF 相互转换
"""

from __future__ import annotations

import csv
import json
import logging
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class FormatConverterTool(BaseTool):
    """格式转换工具。

    支持文档、数据、图片格式转换，包括：
    - Markdown、Word、HTML、PDF、LaTeX 等文档格式
    - CSV、JSON、XML 等数据格式
    - PNG、JPG、WebP、BMP、TIFF 等图片格式
    """

    name = "format_converter"
    emoji = "🔄"
    title = "格式转换"
    description = "文档、数据、图片格式转换，支持 Markdown、Word、HTML、PDF、LaTeX、CSV、JSON、XML 等多种格式"
    timeout = 120

    def __init__(self, output_dir: str = "") -> None:
        """初始化格式转换工具。

        Args:
            output_dir: 输出目录，默认为项目的 generated/日期/ 目录
        """
        super().__init__()
        self.output_dir = Path(output_dir) if output_dir else Path(__file__).parent.parent.parent / "generated" / datetime.now().strftime("%Y-%m-%d")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_actions(self) -> list[ActionDef]:
        return [
            # Pandoc 核心转换
            ActionDef(
                name="convert_markdown_to_docx",
                description="Markdown 转 Word 文档",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="convert_markdown_to_html",
                description="Markdown 转 HTML 网页",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="convert_markdown_to_pdf",
                description="Markdown 转 PDF（通过 Pandoc + XeLaTeX，支持中文）",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="convert_markdown_to_latex",
                description="Markdown 转 LaTeX 源文件",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="convert_latex_to_pdf",
                description="LaTeX 转 PDF（通过 MiKTeX XeLaTeX）",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="convert_docx_to_markdown",
                description="Word 文档转 Markdown",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="convert_docx_to_html",
                description="Word 文档转 HTML 网页",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="convert_html_to_markdown",
                description="HTML 网页转 Markdown",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            # 数据格式转换
            ActionDef(
                name="convert_csv_to_json",
                description="CSV 转 JSON 数据格式",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="convert_json_to_csv",
                description="JSON 转 CSV 数据格式",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            ActionDef(
                name="convert_json_to_xml",
                description="JSON 转 XML 数据格式",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path"],
            ),
            # 图片格式转换
            ActionDef(
                name="convert_image_format",
                description="图片格式转换，支持 PNG/JPG/WebP/BMP/TIFF",
                parameters={
                    "input_path": {
                        "type": "string",
                        "description": "输入图片文件路径",
                    },
                    "target_format": {
                        "type": "string",
                        "description": "目标格式: png/jpg/webp/bmp/tiff",
                        "enum": ["png", "jpg", "webp", "bmp", "tiff"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["input_path", "target_format"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行格式转换动作。"""
        action_map = {
            "convert_markdown_to_docx": self._convert_markdown_to_docx,
            "convert_markdown_to_html": self._convert_markdown_to_html,
            "convert_markdown_to_pdf": self._convert_markdown_to_pdf,
            "convert_markdown_to_latex": self._convert_markdown_to_latex,
            "convert_latex_to_pdf": self._convert_latex_to_pdf,
            "convert_docx_to_markdown": self._convert_docx_to_markdown,
            "convert_docx_to_html": self._convert_docx_to_html,
            "convert_html_to_markdown": self._convert_html_to_markdown,
            "convert_csv_to_json": self._convert_csv_to_json,
            "convert_json_to_csv": self._convert_json_to_csv,
            "convert_json_to_xml": self._convert_json_to_xml,
            "convert_image_format": self._convert_image_format,
        }

        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作: {action}",
            )

        try:
            return handler(params)
        except Exception as e:
            logger.error("格式转换失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"格式转换失败: {e}",
            )

    # ------------------------------------------------------------------
    # Pandoc 通用封装
    # ------------------------------------------------------------------

    def _convert_with_pandoc(
        self,
        input_path: Path,
        output_path: Path,
        from_format: str | None = None,
        to_format: str | None = None,
        extra_args: list[str] | None = None,
    ) -> str:
        """Pandoc 通用转换封装。返回使用的引擎名称。"""
        if not shutil.which("pandoc"):
            raise RuntimeError("Pandoc 未安装，请先安装 Pandoc: https://pandoc.org/installing.html")

        cmd = ["pandoc", str(input_path), "-o", str(output_path)]
        if from_format:
            cmd.extend(["-f", from_format])
        if to_format:
            cmd.extend(["-t", to_format])
        if extra_args:
            cmd.extend(extra_args)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"Pandoc 转换失败: {result.stderr}")

        return "pandoc"

    def _validate_input_file(self, input_path: str) -> Path:
        """验证输入文件是否存在。"""
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        return path

    def _get_output_path(self, input_path: Path, output_filename: str | None, ext: str) -> Path:
        """生成输出文件路径。"""
        if output_filename:
            return self.output_dir / f"{output_filename}.{ext}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{input_path.stem}_{timestamp}.{ext}"

    def _build_result(
        self,
        output_path: Path,
        source_ext: str,
        target_ext: str,
        engine: str,
    ) -> ToolResult:
        """构建成功的返回结果。"""
        file_size = output_path.stat().st_size if output_path.exists() else 0
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=(
                f"✅ 格式转换完成\n"
                f"📁 文件: {output_path.name}\n"
                f"📊 大小: {file_size} 字节\n"
                f"🔄 转换: {source_ext} → {target_ext}\n"
                f"⚙️ 引擎: {engine}"
            ),
            data={
                "file_path": str(output_path),
                "file_name": output_path.name,
                "file_size": file_size,
                "source_format": source_ext,
                "target_format": target_ext,
                "engine_used": engine,
            },
        )

    # ------------------------------------------------------------------
    # Pandoc 核心转换
    # ------------------------------------------------------------------

    def _convert_markdown_to_docx(self, params: dict[str, Any]) -> ToolResult:
        """Markdown 转 Word 文档。"""
        input_path = self._validate_input_file(params["input_path"])
        output_path = self._get_output_path(input_path, params.get("output_filename"), "docx")

        engine = self._convert_with_pandoc(input_path, output_path)
        return self._build_result(output_path, ".md", ".docx", engine)

    def _convert_markdown_to_html(self, params: dict[str, Any]) -> ToolResult:
        """Markdown 转 HTML。"""
        input_path = self._validate_input_file(params["input_path"])
        output_path = self._get_output_path(input_path, params.get("output_filename"), "html")

        extra_args = ["--standalone"]  # 生成完整 HTML 文件（含 <html><head>）
        engine = self._convert_with_pandoc(input_path, output_path, extra_args=extra_args)
        return self._build_result(output_path, ".md", ".html", engine)

    def _convert_markdown_to_pdf(self, params: dict[str, Any]) -> ToolResult:
        """Markdown 转 PDF（通过 Pandoc + XeLaTeX，支持中文）。"""
        input_path = self._validate_input_file(params["input_path"])
        output_path = self._get_output_path(input_path, params.get("output_filename"), "pdf")

        # 关键参数：支持中文
        extra_args = [
            "--pdf-engine=xelatex",
            "-V", "CJKmainfont=SimSun",          # 中文宋体
            "-V", "geometry:margin=2.5cm",       # 页边距
            "-V", "mainfont=Times New Roman",    # 英文字体
        ]
        engine = self._convert_with_pandoc(input_path, output_path, extra_args=extra_args)
        return self._build_result(output_path, ".md", ".pdf", engine + "+xelatex")

    def _convert_markdown_to_latex(self, params: dict[str, Any]) -> ToolResult:
        """Markdown 转 LaTeX。"""
        input_path = self._validate_input_file(params["input_path"])
        output_path = self._get_output_path(input_path, params.get("output_filename"), "tex")

        engine = self._convert_with_pandoc(input_path, output_path, to_format="latex")
        return self._build_result(output_path, ".md", ".tex", engine)

    def _convert_latex_to_pdf(self, params: dict[str, Any]) -> ToolResult:
        """LaTeX 转 PDF（通过 XeLaTeX）。"""
        input_path = self._validate_input_file(params["input_path"])
        output_filename = params.get("output_filename")
        
        if not shutil.which("xelatex"):
            raise RuntimeError("XeLaTeX 未安装，请先安装 MiKTeX 或 TeX Live")

        # XeLaTeX 需要在临时目录中编译，然后复制结果
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_dir_path = Path(tmp_dir)
            
            # 复制源文件到临时目录
            tmp_input = tmp_dir_path / input_path.name
            shutil.copy(input_path, tmp_input)
            
            # 运行 XeLaTeX（两次编译以处理交叉引用）
            for _ in range(2):
                result = subprocess.run(
                    [
                        "xelatex",
                        "-interaction=nonstopmode",
                        f"-output-directory={str(tmp_dir_path)}",
                        str(tmp_input),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(tmp_dir_path),
                )
            
            # 检查是否成功生成 PDF
            tmp_pdf = tmp_dir_path / f"{input_path.stem}.pdf"
            if not tmp_pdf.exists():
                raise RuntimeError(f"XeLaTeX 编译失败: {result.stderr or result.stdout}")
            
            # 复制 PDF 到输出目录
            if output_filename:
                output_path = self.output_dir / f"{output_filename}.pdf"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = self.output_dir / f"{input_path.stem}_{timestamp}.pdf"
            
            shutil.copy(tmp_pdf, output_path)

        return self._build_result(output_path, ".tex", ".pdf", "xelatex")

    def _convert_docx_to_markdown(self, params: dict[str, Any]) -> ToolResult:
        """Word 转 Markdown。"""
        input_path = self._validate_input_file(params["input_path"])
        output_path = self._get_output_path(input_path, params.get("output_filename"), "md")

        engine = self._convert_with_pandoc(input_path, output_path, to_format="markdown")
        return self._build_result(output_path, ".docx", ".md", engine)

    def _convert_docx_to_html(self, params: dict[str, Any]) -> ToolResult:
        """Word 转 HTML。"""
        input_path = self._validate_input_file(params["input_path"])
        output_path = self._get_output_path(input_path, params.get("output_filename"), "html")

        extra_args = ["--standalone"]
        engine = self._convert_with_pandoc(input_path, output_path, extra_args=extra_args)
        return self._build_result(output_path, ".docx", ".html", engine)

    def _convert_html_to_markdown(self, params: dict[str, Any]) -> ToolResult:
        """HTML 转 Markdown。"""
        input_path = self._validate_input_file(params["input_path"])
        output_path = self._get_output_path(input_path, params.get("output_filename"), "md")

        engine = self._convert_with_pandoc(input_path, output_path, from_format="html", to_format="markdown")
        return self._build_result(output_path, ".html", ".md", engine)

    # ------------------------------------------------------------------
    # 数据格式转换
    # ------------------------------------------------------------------

    def _convert_csv_to_json(self, params: dict[str, Any]) -> ToolResult:
        """CSV 转 JSON。"""
        input_path = self._validate_input_file(params["input_path"])
        output_path = self._get_output_path(input_path, params.get("output_filename"), "json")

        with open(input_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            data = list(reader)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return self._build_result(output_path, ".csv", ".json", "python-csv")

    def _convert_json_to_csv(self, params: dict[str, Any]) -> ToolResult:
        """JSON 转 CSV。"""
        input_path = self._validate_input_file(params["input_path"])
        output_path = self._get_output_path(input_path, params.get("output_filename"), "csv")

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("JSON 数据必须是数组格式")
        if len(data) == 0:
            raise ValueError("JSON 数组不能为空")

        # 获取所有键作为列名
        keys = list(data[0].keys()) if isinstance(data[0], dict) else []
        if not keys:
            raise ValueError("JSON 对象必须包含键值对")

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)

        return self._build_result(output_path, ".json", ".csv", "python-csv")

    def _convert_json_to_xml(self, params: dict[str, Any]) -> ToolResult:
        """JSON 转 XML。"""
        input_path = self._validate_input_file(params["input_path"])
        output_path = self._get_output_path(input_path, params.get("output_filename"), "xml")

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 递归构建 XML
        def build_element(parent: ET.Element, data: Any, tag_name: str = "item") -> None:
            if isinstance(data, dict):
                for key, value in data.items():
                    child = ET.SubElement(parent, key)
                    build_element(child, value)
            elif isinstance(data, list):
                for item in data:
                    child = ET.SubElement(parent, tag_name)
                    build_element(child, item)
            else:
                parent.text = str(data) if data is not None else ""

        root = ET.Element("root")
        build_element(root, data)

        # 写入文件（添加 XML 声明）
        tree = ET.ElementTree(root)
        with open(output_path, "wb") as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)

        return self._build_result(output_path, ".json", ".xml", "python-xml")

    # ------------------------------------------------------------------
    # 图片格式转换
    # ------------------------------------------------------------------

    def _convert_image_format(self, params: dict[str, Any]) -> ToolResult:
        """图片格式转换。"""
        from PIL import Image

        input_path = self._validate_input_file(params["input_path"])
        target_format = params["target_format"].lower()
        
        # 验证目标格式
        valid_formats = {"png", "jpg", "webp", "bmp", "tiff"}
        if target_format not in valid_formats:
            raise ValueError(f"不支持的目标格式: {target_format}，支持: {', '.join(valid_formats)}")

        # 处理 jpg 扩展名
        ext = "jpeg" if target_format == "jpg" else target_format
        output_path = self._get_output_path(input_path, params.get("output_filename"), target_format)

        # 打开并转换图片
        img = Image.open(str(input_path))
        
        # 如果目标是 JPEG，需要去掉 alpha 通道
        if target_format == "jpg" and img.mode in ("RGBA", "LA", "P"):
            # 创建白色背景
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif target_format == "jpg":
            img = img.convert("RGB")

        # 保存图片
        save_kwargs = {}
        if target_format == "jpg":
            save_kwargs["quality"] = 95
        elif target_format == "webp":
            save_kwargs["quality"] = 90
            save_kwargs["lossless"] = False

        img.save(str(output_path), format=ext.upper(), **save_kwargs)

        return self._build_result(output_path, input_path.suffix, f".{target_format}", "pillow")


# 用于测试
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = FormatConverterTool()
        print("Actions:", [a.name for a in tool.get_actions()])
        print("Tool registered successfully!")

    asyncio.run(test())
