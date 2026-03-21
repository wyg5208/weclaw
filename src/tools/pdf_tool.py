"""PDF 处理工具 — 合并、拆分、提取页面、压缩、加密解密。
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class PDFTool(BaseTool):
    """PDF 处理工具。

    支持 PDF 文件的合并、拆分、提取页面、压缩、加密和解密操作。
    """

    name = "pdf_tool"
    emoji = "📑"
    title = "PDF处理"
    description = "PDF 文件处理：合并、拆分、提取页面、压缩、加密解密"
    timeout = 120

    def __init__(self, output_dir: str = "") -> None:
        """初始化 PDF 处理工具。

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
                name="merge_pdfs",
                description="合并多个 PDF 文件为一个",
                parameters={
                    "file_paths": {
                        "type": "string",
                        "description": "要合并的 PDF 文件路径，多个路径用逗号分隔",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），默认自动生成",
                    },
                },
                required_params=["file_paths"],
            ),
            ActionDef(
                name="split_pdf",
                description="拆分 PDF 文件（按页范围）",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "要拆分的 PDF 文件路径",
                    },
                    "page_ranges": {
                        "type": "string",
                        "description": "页面范围，如 '1-3,5,7-9'（页码从1开始）",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），默认自动生成",
                    },
                },
                required_params=["file_path", "page_ranges"],
            ),
            ActionDef(
                name="extract_pages",
                description="从 PDF 中提取指定页面",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "PDF 文件路径",
                    },
                    "pages": {
                        "type": "string",
                        "description": "要提取的页码，如 '1,3,5'（页码从1开始）",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），默认自动生成",
                    },
                },
                required_params=["file_path", "pages"],
            ),
            ActionDef(
                name="compress_pdf",
                description="压缩 PDF 文件（移除冗余对象）",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "要压缩的 PDF 文件路径",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），默认自动生成",
                    },
                },
                required_params=["file_path"],
            ),
            ActionDef(
                name="add_password",
                description="为 PDF 文件添加密码保护",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "PDF 文件路径",
                    },
                    "password": {
                        "type": "string",
                        "description": "要设置的密码",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），默认自动生成",
                    },
                },
                required_params=["file_path", "password"],
            ),
            ActionDef(
                name="remove_password",
                description="移除 PDF 文件的密码保护",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "加密的 PDF 文件路径",
                    },
                    "password": {
                        "type": "string",
                        "description": "当前密码",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），默认自动生成",
                    },
                },
                required_params=["file_path", "password"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定的 PDF 操作。"""
        action_map = {
            "merge_pdfs": self._merge_pdfs,
            "split_pdf": self._split_pdf,
            "extract_pages": self._extract_pages,
            "compress_pdf": self._compress_pdf,
            "add_password": self._add_password,
            "remove_password": self._remove_password,
        }

        handler = action_map.get(action)
        if handler is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作: {action}",
            )

        return handler(params)

    def _merge_pdfs(self, params: dict[str, Any]) -> ToolResult:
        """合并多个 PDF 文件。"""
        file_paths_str = params.get("file_paths", "").strip()
        if not file_paths_str:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少必需参数: file_paths")

        output_filename = params.get("output_filename", "").strip()

        # 解析文件路径列表
        file_paths = [Path(p.strip()) for p in file_paths_str.split(",") if p.strip()]
        if len(file_paths) < 2:
            return ToolResult(status=ToolResultStatus.ERROR, error="至少需要两个 PDF 文件才能合并")

        # 检查文件是否存在
        for fp in file_paths:
            if not fp.exists():
                return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {fp}")
            if fp.suffix.lower() != ".pdf":
                return ToolResult(status=ToolResultStatus.ERROR, error=f"不是 PDF 文件: {fp}")

        try:
            writer = PdfWriter()
            total_pages = 0

            for fp in file_paths:
                reader = PdfReader(str(fp))
                for page in reader.pages:
                    writer.add_page(page)
                    total_pages += 1

            # 生成输出文件名
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"merged_{timestamp}"
            output_path = self.output_dir / f"{output_filename}.pdf"

            with open(output_path, "wb") as f:
                writer.write(f)

            file_size = output_path.stat().st_size

            logger.info("PDF 合并完成: %s (%d 页)", output_path, total_pages)
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PDF合并完成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📄 共 {total_pages} 页",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size": file_size,
                    "page_count": total_pages,
                    "source_files": [str(fp) for fp in file_paths],
                },
            )
        except Exception as e:
            logger.error("PDF 合并失败: %s", e, exc_info=True)
            return ToolResult(status=ToolResultStatus.ERROR, error=f"PDF 合并失败: {e}")

    def _split_pdf(self, params: dict[str, Any]) -> ToolResult:
        """拆分 PDF 文件（按页范围）。"""
        file_path_str = params.get("file_path", "").strip()
        page_ranges_str = params.get("page_ranges", "").strip()
        output_filename = params.get("output_filename", "").strip()

        if not file_path_str:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少必需参数: file_path")
        if not page_ranges_str:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少必需参数: page_ranges")

        file_path = Path(file_path_str)
        if not file_path.exists():
            return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {file_path}")

        try:
            reader = PdfReader(str(file_path))
            total_pages = len(reader.pages)

            # 解析页面范围
            pages_to_extract = self._parse_page_ranges(page_ranges_str, total_pages)
            if not pages_to_extract:
                return ToolResult(status=ToolResultStatus.ERROR, error=f"无效的页面范围: {page_ranges_str}")

            writer = PdfWriter()
            for page_num in pages_to_extract:
                writer.add_page(reader.pages[page_num - 1])  # 转换为 0-based 索引

            # 生成输出文件名
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"split_{timestamp}"
            output_path = self.output_dir / f"{output_filename}.pdf"

            with open(output_path, "wb") as f:
                writer.write(f)

            file_size = output_path.stat().st_size
            extracted_count = len(pages_to_extract)

            logger.info("PDF 拆分完成: %s (%d 页)", output_path, extracted_count)
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PDF拆分完成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📄 提取了 {extracted_count} 页",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size": file_size,
                    "page_count": extracted_count,
                    "extracted_pages": pages_to_extract,
                    "source_file": str(file_path),
                },
            )
        except Exception as e:
            logger.error("PDF 拆分失败: %s", e, exc_info=True)
            return ToolResult(status=ToolResultStatus.ERROR, error=f"PDF 拆分失败: {e}")

    def _extract_pages(self, params: dict[str, Any]) -> ToolResult:
        """提取指定页面。"""
        file_path_str = params.get("file_path", "").strip()
        pages_str = params.get("pages", "").strip()
        output_filename = params.get("output_filename", "").strip()

        if not file_path_str:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少必需参数: file_path")
        if not pages_str:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少必需参数: pages")

        file_path = Path(file_path_str)
        if not file_path.exists():
            return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {file_path}")

        try:
            reader = PdfReader(str(file_path))
            total_pages = len(reader.pages)

            # 解析页码列表
            pages_to_extract = self._parse_page_list(pages_str, total_pages)
            if not pages_to_extract:
                return ToolResult(status=ToolResultStatus.ERROR, error=f"无效的页码: {pages_str}")

            writer = PdfWriter()
            for page_num in pages_to_extract:
                writer.add_page(reader.pages[page_num - 1])  # 转换为 0-based 索引

            # 生成输出文件名
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"extracted_{timestamp}"
            output_path = self.output_dir / f"{output_filename}.pdf"

            with open(output_path, "wb") as f:
                writer.write(f)

            file_size = output_path.stat().st_size
            extracted_count = len(pages_to_extract)

            logger.info("PDF 页面提取完成: %s (%d 页)", output_path, extracted_count)
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PDF页面提取完成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📄 提取了 {extracted_count} 页",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size": file_size,
                    "page_count": extracted_count,
                    "extracted_pages": pages_to_extract,
                    "source_file": str(file_path),
                },
            )
        except Exception as e:
            logger.error("PDF 页面提取失败: %s", e, exc_info=True)
            return ToolResult(status=ToolResultStatus.ERROR, error=f"PDF 页面提取失败: {e}")

    def _compress_pdf(self, params: dict[str, Any]) -> ToolResult:
        """压缩 PDF 文件。"""
        file_path_str = params.get("file_path", "").strip()
        output_filename = params.get("output_filename", "").strip()

        if not file_path_str:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少必需参数: file_path")

        file_path = Path(file_path_str)
        if not file_path.exists():
            return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {file_path}")

        try:
            original_size = file_path.stat().st_size
            reader = PdfReader(str(file_path))
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            # 压缩：移除冗余对象
            writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)

            # 生成输出文件名
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"compressed_{timestamp}"
            output_path = self.output_dir / f"{output_filename}.pdf"

            with open(output_path, "wb") as f:
                writer.write(f)

            file_size = output_path.stat().st_size
            page_count = len(reader.pages)
            compression_ratio = (1 - file_size / original_size) * 100 if original_size > 0 else 0

            logger.info("PDF 压缩完成: %s (压缩率 %.1f%%)", output_path, compression_ratio)
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PDF压缩完成\n📁 文件: {output_path.name}\n📊 原始大小: {original_size} 字节\n📊 压缩后: {file_size} 字节\n📉 压缩率: {compression_ratio:.1f}%\n📄 共 {page_count} 页",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size": file_size,
                    "original_size": original_size,
                    "compression_ratio": round(compression_ratio, 1),
                    "page_count": page_count,
                    "source_file": str(file_path),
                },
            )
        except Exception as e:
            logger.error("PDF 压缩失败: %s", e, exc_info=True)
            return ToolResult(status=ToolResultStatus.ERROR, error=f"PDF 压缩失败: {e}")

    def _add_password(self, params: dict[str, Any]) -> ToolResult:
        """为 PDF 添加密码保护。"""
        file_path_str = params.get("file_path", "").strip()
        password = params.get("password", "").strip()
        output_filename = params.get("output_filename", "").strip()

        if not file_path_str:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少必需参数: file_path")
        if not password:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少必需参数: password")

        file_path = Path(file_path_str)
        if not file_path.exists():
            return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {file_path}")

        try:
            reader = PdfReader(str(file_path))
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            # 添加加密
            writer.encrypt(password)

            # 生成输出文件名
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"encrypted_{timestamp}"
            output_path = self.output_dir / f"{output_filename}.pdf"

            with open(output_path, "wb") as f:
                writer.write(f)

            file_size = output_path.stat().st_size
            page_count = len(reader.pages)

            logger.info("PDF 加密完成: %s", output_path)
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PDF加密完成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📄 共 {page_count} 页\n🔐 已添加密码保护",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size": file_size,
                    "page_count": page_count,
                    "encrypted": True,
                    "source_file": str(file_path),
                },
            )
        except Exception as e:
            logger.error("PDF 加密失败: %s", e, exc_info=True)
            return ToolResult(status=ToolResultStatus.ERROR, error=f"PDF 加密失败: {e}")

    def _remove_password(self, params: dict[str, Any]) -> ToolResult:
        """移除 PDF 的密码保护。"""
        file_path_str = params.get("file_path", "").strip()
        password = params.get("password", "").strip()
        output_filename = params.get("output_filename", "").strip()

        if not file_path_str:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少必需参数: file_path")
        if not password:
            return ToolResult(status=ToolResultStatus.ERROR, error="缺少必需参数: password")

        file_path = Path(file_path_str)
        if not file_path.exists():
            return ToolResult(status=ToolResultStatus.ERROR, error=f"文件不存在: {file_path}")

        try:
            # 使用密码打开加密的 PDF
            reader = PdfReader(str(file_path), password=password)
            writer = PdfWriter()

            for page in reader.pages:
                writer.add_page(page)

            # 生成输出文件名（不加密）
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"decrypted_{timestamp}"
            output_path = self.output_dir / f"{output_filename}.pdf"

            with open(output_path, "wb") as f:
                writer.write(f)

            file_size = output_path.stat().st_size
            page_count = len(reader.pages)

            logger.info("PDF 解密完成: %s", output_path)
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=f"✅ PDF解密完成\n📁 文件: {output_path.name}\n📊 大小: {file_size} 字节\n📄 共 {page_count} 页\n🔓 已移除密码保护",
                data={
                    "file_path": str(output_path),
                    "file_name": output_path.name,
                    "file_size": file_size,
                    "page_count": page_count,
                    "encrypted": False,
                    "source_file": str(file_path),
                },
            )
        except Exception as e:
            error_msg = str(e)
            if "password" in error_msg.lower() or "decrypt" in error_msg.lower():
                return ToolResult(status=ToolResultStatus.ERROR, error="密码错误或文件未加密")
            logger.error("PDF 解密失败: %s", e, exc_info=True)
            return ToolResult(status=ToolResultStatus.ERROR, error=f"PDF 解密失败: {e}")

    def _parse_page_ranges(self, ranges_str: str, total_pages: int) -> list[int]:
        """解析页面范围字符串，如 '1-3,5,7-9'。

        Args:
            ranges_str: 页面范围字符串
            total_pages: PDF 总页数

        Returns:
            页码列表（1-based）
        """
        pages = []
        parts = ranges_str.split(",")

        for part in parts:
            part = part.strip()
            if "-" in part:
                # 范围：如 1-3
                try:
                    start, end = part.split("-", 1)
                    start = int(start.strip())
                    end = int(end.strip())
                    if start < 1 or end > total_pages or start > end:
                        continue
                    pages.extend(range(start, end + 1))
                except ValueError:
                    continue
            else:
                # 单个页码
                try:
                    page = int(part)
                    if 1 <= page <= total_pages:
                        pages.append(page)
                except ValueError:
                    continue

        # 去重并排序
        return sorted(set(pages))

    def _parse_page_list(self, pages_str: str, total_pages: int) -> list[int]:
        """解析页码列表字符串，如 '1,3,5'。

        Args:
            pages_str: 页码列表字符串
            total_pages: PDF 总页数

        Returns:
            页码列表（1-based）
        """
        pages = []
        parts = pages_str.split(",")

        for part in parts:
            part = part.strip()
            try:
                page = int(part)
                if 1 <= page <= total_pages:
                    pages.append(page)
            except ValueError:
                continue

        # 去重但保持顺序
        seen = set()
        result = []
        for p in pages:
            if p not in seen:
                seen.add(p)
                result.append(p)
        return result


# 用于测试
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = PDFTool()
        print(f"工具名称: {tool.name}")
        print(f"工具标题: {tool.title}")
        print(f"工具描述: {tool.description}")
        print(f"支持的动作: {[a.name for a in tool.get_actions()]}")

    asyncio.run(test())
