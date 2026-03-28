"""XML 命名空间常量。

参考 MiniMax check/ns.py 设计
"""

# WordprocessingML 命名空间
NAMESPACE_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

# DrawingML 命名空间
NAMESPACE_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NAMESPACE_DRAWING_WORD = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
NAMESPACE_DRAWING_PKG = "http://schemas.openxmlformats.org/drawingml/2006/picture"

# OfficeDocument 命名空间
NAMESPACE_OFFICE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# Package 命名空间
NAMESPACE_PKG = "http://schemas.openxmlformats.org/package/2006/content-types"
NAMESPACE_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"

# 常用前缀映射
PREFIX_MAP = {
    "w": NAMESPACE_W,
    "a": NAMESPACE_A,
    "wp": NAMESPACE_DRAWING_WORD,
    "pic": NAMESPACE_DRAWING_PKG,
    "r": NAMESPACE_OFFICE,
    "ct": NAMESPACE_PKG,
    "rels": NAMESPACE_RELS,
}

# 常用标签
TAG_DOCUMENT = f"{{{NAMESPACE_W}}}document"
TAG_BODY = f"{{{NAMESPACE_W}}}body"
TAG_PARAGRAPH = f"{{{NAMESPACE_W}}}p"
TAG_RUN = f"{{{NAMESPACE_W}}}r"
TAG_TEXT = f"{{{NAMESPACE_W}}}t"
TAG_TABLE = f"{{{NAMESPACE_W}}}tbl"
TAG_ROW = f"{{{NAMESPACE_W}}}tr"
TAG_CELL = f"{{{NAMESPACE_W}}}tc"
TAG_HYPERLINK = f"{{{NAMESPACE_W}}}hyperlink"
TAG_BOOKMARK_START = f"{{{NAMESPACE_W}}}bookmarkStart"
TAG_BOOKMARK_END = f"{{{NAMESPACE_W}}}bookmarkEnd"
TAG_COMMENT_RANGE_START = f"{{{NAMESPACE_W}}}commentRangeStart"
TAG_COMMENT_RANGE_END = f"{{{NAMESPACE_W}}}commentRangeEnd"
TAG_COMMENT_REFERENCE = f"{{{NAMESPACE_W}}}commentReference"
TAG_DRAWING = f"{{{NAMESPACE_W}}}drawing"
