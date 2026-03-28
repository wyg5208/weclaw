"""DOCX OpenXML 验证模块 - 提供 Word 文档的零容错验证能力。

模块功能：
- pipeline: 验证管线编排
- detectors: 问题检测规则
- report: 结构化报告生成
- ns: XML 命名空间常量
- ooxml_order: OOXML 元素顺序规则（MUST/SHOULD/MAY/VENDOR 分层）

参考 MiniMax docx check/ 设计
"""

from src.tools.docx_validator.pipeline import (
    ValidationPipeline,
    run_validation,
)
from src.tools.docx_validator.detectors import (
    DETECTORS,
    BaseDetector,
    GridConsistencyDetector,
    AspectRatioDetector,
    AnnotationLinkDetector,
    BookmarkIntegrityDetector,
    DrawingIdUniquenessDetector,
    HyperlinkValidityDetector,
)
from src.tools.docx_validator.report import (
    ValidationReport,
    Issue,
    generate_report,
)

__all__ = [
    # pipeline
    "ValidationPipeline",
    "run_validation",
    # detectors
    "DETECTORS",
    "BaseDetector",
    "GridConsistencyDetector",
    "AspectRatioDetector",
    "AnnotationLinkDetector",
    "BookmarkIntegrityDetector",
    "DrawingIdUniquenessDetector",
    "HyperlinkValidityDetector",
    # report
    "ValidationReport",
    "Issue",
    "generate_report",
]
