"""DOCX 验证管线 - 编排所有检测器执行验证任务。

验证流程：
1. 解压 DOCX（ZIP 格式）
2. 构建扫描上下文
3. 运行所有检测器
4. 汇总报告

参考 MiniMax check/pipeline.py 设计
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lxml import etree

from src.tools.docx_validator.report import Issue, ValidationReport, generate_report

logger = logging.getLogger(__name__)


# DOCX 文件结构
_DOCX_REQUIRED_PARTS = [
    "[Content_Types].xml",
    "_rels/.rels",
    "word/document.xml",
]


@dataclass
class ScanContext:
    """扫描上下文。"""
    docx_path: str
    temp_dir: Path | None = None
    xml_trees: dict[str, etree._ElementTree] = field(default_factory=dict)
    content_types_xml: etree._ElementTree | None = None
    document_xml: etree._ElementTree | None = None
    relationships: dict[str, dict[str, str]] = field(default_factory=dict)


class ValidationPipeline:
    """DOCX 验证管线。"""

    def __init__(self, detectors: list[Any] | None = None) -> None:
        """初始化验证管线。
        
        Args:
            detectors: 检测器列表，None 则使用默认检测器
        """
        from src.tools.docx_validator.detectors import DETECTORS
        self.detectors = detectors if detectors is not None else DETECTORS

    def run(self, docx_path: str) -> ValidationReport:
        """执行验证。
        
        Args:
            docx_path: DOCX 文件路径
            
        Returns:
            ValidationReport: 验证报告
        """
        file_path = Path(docx_path)
        
        # 基本检查
        if not file_path.exists():
            return ValidationReport(
                passed=False,
                errors=[f"文件不存在: {docx_path}"],
                message="文件不存在"
            )
        
        if file_path.suffix.lower() not in (".docx", ".docm"):
            return ValidationReport(
                passed=False,
                errors=[f"不支持的文件格式: {file_path.suffix}"],
                message="不支持的文件格式"
            )
        
        # 创建临时目录
        temp_dir = None
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix="docx_validate_"))
            
            # 解压 DOCX
            logger.info("解压 DOCX 文件...")
            self._extract_docx(file_path, temp_dir)
            
            # 构建扫描上下文
            context = self._build_context(docx_path, temp_dir)
            
            # 执行所有检测器
            all_issues: list[Issue] = []
            for detector in self.detectors:
                try:
                    logger.info("运行检测器: %s", detector.__class__.__name__)
                    issues = detector.detect(context)
                    if issues:
                        all_issues.extend(issues)
                except Exception as e:
                    logger.warning("检测器 %s 执行失败: %s", detector.__class__.__name__, e)
            
            # 生成报告
            report = generate_report(docx_path, all_issues)
            return report
            
        finally:
            # 清理临时目录
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _extract_docx(self, docx_path: Path, output_dir: Path) -> None:
        """解压 DOCX 文件。"""
        with zipfile.ZipFile(docx_path, "r") as zip_ref:
            zip_ref.extractall(output_dir)

    def _build_context(self, docx_path: str, temp_dir: Path) -> ScanContext:
        """构建扫描上下文。"""
        context = ScanContext(docx_path=docx_path, temp_dir=temp_dir)
        
        # 加载 Content_Types.xml
        content_types_path = temp_dir / "[Content_Types].xml"
        if content_types_path.exists():
            context.content_types_xml = etree.parse(str(content_types_path))
        
        # 加载 document.xml
        document_path = temp_dir / "word" / "document.xml"
        if document_path.exists():
            context.document_xml = etree.parse(str(document_path))
            context.xml_trees["document"] = context.document_xml
        
        # 加载其他 XML 文件
        for xml_file in temp_dir.rglob("*.xml"):
            rel_path = xml_file.relative_to(temp_dir)
            context.xml_trees[str(rel_path)] = etree.parse(str(xml_file))
        
        # 加载关系文件
        rels_dir = temp_dir / "word" / "_rels"
        if rels_dir.exists():
            for rels_file in rels_dir.glob("*.xml.rels"):
                rels_path = f"word/_rels/{rels_file.name}"
                context.relationships[rels_path] = self._parse_relationships(rels_file)
        
        return context

    def _parse_relationships(self, rels_file: Path) -> dict[str, str]:
        """解析 .rels 文件。"""
        relationships = {}
        try:
            tree = etree.parse(str(rels_file))
            root = tree.getroot()
            # 跳过命名空间
            for rel in root.iter():
                if rel.tag.endswith("Relationship"):
                    rel_id = rel.get("Id", "")
                    target = rel.get("Target", "")
                    if rel_id and target:
                        relationships[rel_id] = target
        except Exception as e:
            logger.warning("解析关系文件失败 %s: %s", rels_file, e)
        return relationships


def run_validation(docx_path: str, detectors: list[Any] | None = None) -> ValidationReport:
    """运行 DOCX 验证的便捷函数。
    
    Args:
        docx_path: DOCX 文件路径
        detectors: 可选的检测器列表
        
    Returns:
        ValidationReport: 验证报告
    """
    pipeline = ValidationPipeline(detectors)
    return pipeline.run(docx_path)


# 用于测试
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"正在验证: {file_path}")
        print("=" * 50)
        
        report = run_validation(file_path)
        
        print(f"状态: {'✅ 通过' if report.passed else '❌ 失败'}")
        print(f"消息: {report.message}")
        
        if report.errors:
            print("\n❌ 错误:")
            for issue in report.errors:
                print(f"  - {issue}")
        
        if report.warnings:
            print("\n⚠️  警告:")
            for issue in report.warnings:
                print(f"  - {issue}")
        
        if report.suggestions:
            print("\n💡 建议:")
            for sug in report.suggestions[:5]:
                print(f"  - {sug}")
    else:
        print("用法: python pipeline.py <docx_file.docx>")
