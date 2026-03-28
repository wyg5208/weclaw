"""DOCX 问题检测器 - 检测文档中的各类问题。

检测器列表：
- GridConsistencyDetector: 表格网格一致性
- AspectRatioDetector: 图片纵横比
- AnnotationLinkDetector: 批注链接
- BookmarkIntegrityDetector: 书签完整性
- DrawingIdUniquenessDetector: 绘图ID唯一性
- HyperlinkValidityDetector: 超链接有效性

参考 MiniMax check/detectors.py 设计
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from lxml import etree

from src.tools.docx_validator.pipeline import ScanContext
from src.tools.docx_validator.report import Issue

logger = logging.getLogger(__name__)


class BaseDetector(ABC):
    """检测器基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """检测器名称。"""
        ...

    @property
    def severity(self) -> str:
        """问题严重程度: error | warning | info"""
        return "warning"

    @abstractmethod
    def detect(self, context: ScanContext) -> list[Issue]:
        """执行检测。
        
        Args:
            context: 扫描上下文
            
        Returns:
            检测到的问题列表
        """
        ...


class GridConsistencyDetector(BaseDetector):
    """表格网格一致性检测器。
    
    检测表格单元格数量不一致的问题。
    """

    @property
    def name(self) -> str:
        return "GridConsistencyDetector"

    @property
    def severity(self) -> str:
        return "warning"

    def detect(self, context: ScanContext) -> list[Issue]:
        issues = []
        
        if not context.document_xml:
            return issues
        
        root = context.document_xml.getroot()
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        
        # 查找所有表格
        tables = root.findall(".//w:tbl", ns)
        
        for table in tables:
            rows = table.findall("w:tr", ns)
            expected_cols = None
            
            for i, row in enumerate(rows):
                cells = row.findall("w:tc", ns)
                num_cols = len(cells)
                
                if expected_cols is None:
                    expected_cols = num_cols
                elif num_cols != expected_cols:
                    issues.append(Issue(
                        issue_type="grid_inconsistency",
                        severity=self.severity,
                        location="word/document.xml",
                        message=f"表格第 {i+1} 行有 {num_cols} 个单元格，期望 {expected_cols} 个",
                        suggestion="确保表格每行列数一致"
                    ))
        
        return issues


class AspectRatioDetector(BaseDetector):
    """图片纵横比检测器。
    
    检测图片纵横比是否异常（可能表示图片裁剪问题）。
    """

    @property
    def name(self) -> str:
        return "AspectRatioDetector"

    @property
    def severity(self) -> str:
        return "info"

    def detect(self, context: ScanContext) -> list[Issue]:
        issues = []
        
        if not context.document_xml:
            return issues
        
        root = context.document_xml.getroot()
        ns = {
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
            "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        }
        
        # 查找所有图片
        drawings = root.findall(".//w:drawing", ns)
        
        for drawing in drawings:
            extent = drawing.find(".//wp:extent", ns)
            if extent is not None:
                cx = extent.get("cx")
                cy = extent.get("cy")
                
                if cx and cy:
                    try:
                        cx_val = int(cx)
                        cy_val = int(cy)
                        
                        if cy_val > 0:
                            ratio = cx_val / cy_val
                            
                            if ratio < 0.2 or ratio > 5.0:
                                issues.append(Issue(
                                    issue_type="aspect_ratio",
                                    severity=self.severity,
                                    location="word/document.xml",
                                    message=f"图片纵横比异常: {ratio:.2f}",
                                    suggestion="检查图片是否被正确显示或裁剪"
                                ))
                    except (ValueError, ZeroDivisionError):
                        pass
        
        return issues


class AnnotationLinkDetector(BaseDetector):
    """批注链接检测器。
    
    检测批注是否正确链接到目标元素。
    """

    @property
    def name(self) -> str:
        return "AnnotationLinkDetector"

    @property
    def severity(self) -> str:
        return "warning"

    def detect(self, context: ScanContext) -> list[Issue]:
        issues = []
        
        if not context.document_xml:
            return issues
        
        if context.temp_dir:
            comments_path = context.temp_dir / "word" / "comments.xml"
            if not comments_path.exists():
                return issues
        
        root = context.document_xml.getroot()
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        
        comment_starts = root.findall(".//w:commentRangeStart", ns)
        comment_ends = root.findall(".//w:commentRangeEnd", ns)
        comment_refs = root.findall(".//w:commentReference", ns)
        
        start_ids = {c.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id") 
                     for c in comment_starts if c.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id")}
        end_ids = {c.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id") 
                   for c in comment_ends if c.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id")}
        ref_ids = {c.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id") 
                   for c in comment_refs if c.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id")}
        
        all_ids = start_ids | end_ids | ref_ids
        for cid in all_ids:
            if cid not in start_ids:
                issues.append(Issue(
                    issue_type="orphan_comment_end",
                    severity=self.severity,
                    location="word/document.xml",
                    message=f"批注 ID {cid} 缺少起始标记",
                    suggestion="检查批注是否正确闭合"
                ))
            if cid not in end_ids:
                issues.append(Issue(
                    issue_type="orphan_comment_reference",
                    severity=self.severity,
                    location="word/document.xml",
                    message=f"批注 ID {cid} 缺少结束标记",
                    suggestion="确保批注有正确的范围标记"
                ))
        
        return issues


class BookmarkIntegrityDetector(BaseDetector):
    """书签完整性检测器。"""

    @property
    def name(self) -> str:
        return "BookmarkIntegrityDetector"

    @property
    def severity(self) -> str:
        return "warning"

    def detect(self, context: ScanContext) -> list[Issue]:
        issues = []
        
        if not context.document_xml:
            return issues
        
        root = context.document_xml.getroot()
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        
        bookmark_starts = root.findall(".//w:bookmarkStart", ns)
        bookmark_ends = root.findall(".//w:bookmarkEnd", ns)
        
        start_ids: dict[str, list[str]] = {}
        for bs in bookmark_starts:
            bid = bs.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id")
            bname = bs.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}name", "")
            if bid:
                if bid not in start_ids:
                    start_ids[bid] = []
                start_ids[bid].append(bname)
        
        end_ids: set[str] = set()
        for be in bookmark_ends:
            bid = be.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id")
            if bid:
                end_ids.add(bid)
        
        for bid, names in start_ids.items():
            if bid not in end_ids:
                issues.append(Issue(
                    issue_type="orphan_bookmark",
                    severity=self.severity,
                    location="word/document.xml",
                    message=f"书签 '{names[0]}' (ID: {bid}) 缺少结束标记",
                    suggestion="确保书签有正确的开始和结束"
                ))
        
        return issues


class DrawingIdUniquenessDetector(BaseDetector):
    """绘图ID唯一性检测器。"""

    @property
    def name(self) -> str:
        return "DrawingIdUniquenessDetector"

    @property
    def severity(self) -> str:
        return "warning"

    def detect(self, context: ScanContext) -> list[Issue]:
        issues = []
        
        if not context.document_xml:
            return issues
        
        root = context.document_xml.getroot()
        
        doc_prs = root.findall(
            ".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}inline/"
            "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr"
        )
        
        seen_ids: set[int] = set()
        duplicate_ids: set[int] = set()
        
        for doc_pr in doc_prs:
            nid = doc_pr.get("id")
            if nid:
                try:
                    nid_val = int(nid)
                    if nid_val in seen_ids:
                        duplicate_ids.add(nid_val)
                    else:
                        seen_ids.add(nid_val)
                except ValueError:
                    pass
        
        if duplicate_ids:
            issues.append(Issue(
                issue_type="duplicate_drawing_id",
                severity=self.severity,
                location="word/document.xml",
                message=f"发现 {len(duplicate_ids)} 个重复的绘图 ID",
                suggestion="确保所有 docPr 元素有唯一的 ID"
            ))
        
        return issues


class HyperlinkValidityDetector(BaseDetector):
    """超链接有效性检测器。"""

    @property
    def name(self) -> str:
        return "HyperlinkValidityDetector"

    @property
    def severity(self) -> str:
        return "info"

    def detect(self, context: ScanContext) -> list[Issue]:
        issues = []
        
        if not context.document_xml:
            return issues
        
        root = context.document_xml.getroot()
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        
        hyperlinks = root.findall(".//w:hyperlink", ns)
        
        for hyperlink in hyperlinks:
            rel_id = hyperlink.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            
            if rel_id:
                rels = context.relationships.get("word/_rels/document.xml.rels", {})
                target = rels.get(rel_id, "")
                
                if target:
                    if target.startswith("http://") or target.startswith("https://"):
                        try:
                            parsed = urllib.parse.urlparse(target)
                            if not parsed.netloc:
                                issues.append(Issue(
                                    issue_type="invalid_hyperlink",
                                    severity=self.severity,
                                    location="word/document.xml",
                                    message=f"超链接目标无效: {target}",
                                    suggestion="检查 URL 是否正确"
                                ))
                        except Exception:
                            pass
        
        return issues


# 默认检测器列表
DETECTORS = [
    GridConsistencyDetector(),
    AspectRatioDetector(),
    AnnotationLinkDetector(),
    BookmarkIntegrityDetector(),
    DrawingIdUniquenessDetector(),
    HyperlinkValidityDetector(),
]


if __name__ == "__main__":
    from src.tools.docx_validator.pipeline import run_validation
    
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"正在检测: {file_path}")
        
        report = run_validation(file_path)
        print(f"\n状态: {'通过' if report.passed else '失败'}")
        
        if report.errors:
            print("\n错误:")
            for issue in report.errors:
                print(f"  - {issue}")
        
        if report.warnings:
            print("\n警告:")
            for issue in report.warnings:
                print(f"  - {issue}")
    else:
        print("用法: python detectors.py <docx_file.docx>")
