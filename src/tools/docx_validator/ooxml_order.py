"""OOXML 元素顺序规则 - MUST/SHOULD/MAY/VENDOR 分层。

参考 MiniMax spec/ooxml_order.py 设计

规则级别：
- MUST: 严格 schema 锚点（必须遵守）
- SHOULD: 高兼容性提示（建议遵守）
- MAY: 低风险可选
- VENDOR: 厂商特定
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class RuleLevel(StrEnum):
    """规则级别。"""
    MUST = "must"       # 严格 schema 锚点
    SHOULD = "should"   # 高兼容性提示
    MAY = "may"          # 低风险可选
    VENDOR = "vendor"    # 厂商特定


# 配置文件级别
PROFILE_LEVELS = {
    "minimal": (RuleLevel.MUST,),                              # 最严格
    "repair": (RuleLevel.MUST, RuleLevel.SHOULD),             # 默认
    "compat": (RuleLevel.MUST, RuleLevel.SHOULD, RuleLevel.MAY),  # 兼容模式
    "strict": (RuleLevel.MUST, RuleLevel.SHOULD, RuleLevel.MAY, RuleLevel.VENDOR),  # 最宽松
}

# 默认检查级别
DEFAULT_PROFILE = "repair"


# OOXML 元素顺序规则
# 每个条目: (元素名, 级别, 允许的前一个元素列表)
OOXML_ELEMENT_ORDER = {
    # w:p (段落) 子元素顺序
    "w:p": [
        # MUST: 必须在特定位置
        ("w:pPr", RuleLevel.MUST, []),
        ("w:bookmarkStart", RuleLevel.SHOULD, []),
        ("w:bookmarkEnd", RuleLevel.SHOULD, ["w:bookmarkStart"]),
        ("w:commentRangeStart", RuleLevel.SHOULD, []),
        ("w:commentRangeEnd", RuleLevel.SHOULD, ["w:commentRangeStart", "w:commentRangeEnd"]),
        ("w:r", RuleLevel.MUST, ["w:pPr", "w:bookmarkStart", "w:bookmarkEnd", 
                                   "w:commentRangeStart", "w:commentRangeEnd"]),
        ("w:hyperlink", RuleLevel.MAY, ["w:pPr", "w:r"]),
    ],
    
    # w:r (运行) 子元素顺序
    "w:r": [
        ("w:rPr", RuleLevel.MUST, []),
        ("w:t", RuleLevel.MUST, ["w:rPr"]),
        ("w:drawing", RuleLevel.MAY, ["w:rPr", "w:t"]),
        ("w:noProof", RuleLevel.VENDOR, ["w:rPr"]),
    ],
    
    # w:tbl (表格) 子元素顺序
    "w:tbl": [
        ("w:tblPr", RuleLevel.MUST, []),
        ("w:tblGrid", RuleLevel.MUST, ["w:tblPr"]),
        ("w:tr", RuleLevel.MUST, ["w:tblPr", "w:tblGrid", "w:tr"]),
    ],
    
    # w:tr (表格行) 子元素顺序
    "w:tr": [
        ("w:trPr", RuleLevel.SHOULD, []),
        ("w:tc", RuleLevel.MUST, ["w:trPr", "w:tc"]),
    ],
    
    # w:tc (表格单元格) 子元素顺序
    "w:tc": [
        ("w:tcPr", RuleLevel.MUST, []),
        ("w:p", RuleLevel.MUST, ["w:tcPr", "w:p"]),
    ],
}


def check_element_order(
    parent_tag: str,
    child_tags: list[str],
    profile: str = DEFAULT_PROFILE
) -> list[dict[str, Any]]:
    """检查子元素顺序是否正确。
    
    Args:
        parent_tag: 父元素标签（如 "w:p"）
        child_tags: 子元素标签列表
        profile: 检查级别
        
    Returns:
        问题列表
    """
    if parent_tag not in OOXML_ELEMENT_ORDER:
        return []
    
    rules = OOXML_ELEMENT_ORDER[parent_tag]
    allowed_levels = PROFILE_LEVELS.get(profile, PROFILE_LEVELS[DEFAULT_PROFILE])
    
    issues = []
    expected_tag: str | None = None
    
    for i, child_tag in enumerate(child_tags):
        # 查找匹配规则
        matched_rule = None
        for rule_tag, level, prev_allowed in rules:
            if child_tag == rule_tag:
                matched_rule = (rule_tag, level, prev_allowed)
                break
        
        if matched_rule:
            rule_tag, level, prev_allowed = matched_rule
            
            # 检查级别是否需要检查
            if level not in allowed_levels:
                continue
            
            # 检查前一个元素是否允许
            if expected_tag and expected_tag not in prev_allowed:
                issues.append({
                    "type": "element_order",
                    "level": level.value,
                    "location": f"{parent_tag}[{i}]",
                    "message": f"{child_tag} 不应该在 {expected_tag} 之后出现",
                    "suggestion": f"参考 OOXML 规范调整元素顺序"
                })
            
            # 更新期望的元素
            expected_tag = rule_tag
    
    return issues


# 用于验证表格网格一致性
def validate_table_grid(table_element: Any) -> list[dict[str, Any]]:
    """验证表格网格一致性。
    
    Args:
        table_element: 表格 XML 元素
        
    Returns:
        问题列表
    """
    issues = []
    
    # 获取 tblGrid
    tbl_grid = table_element.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tblGrid")
    if tbl_grid is not None:
        grid_cols = tbl_grid.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}gridCol")
        expected_cols = len(grid_cols)
        
        # 检查每一行
        rows = table_element.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr")
        for i, row in enumerate(rows):
            cells = row.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc")
            actual_cols = len(cells)
            
            if actual_cols != expected_cols:
                issues.append({
                    "type": "grid_inconsistency",
                    "level": "error",
                    "location": f"w:tbl[{i}]",
                    "message": f"表格第 {i+1} 行有 {actual_cols} 个单元格，期望 {expected_cols} 个",
                    "suggestion": "确保每行列数与 tblGrid 定义的列数一致"
                })
    
    return issues


# 用于测试
if __name__ == "__main__":
    # 测试段落元素顺序
    test_tags = ["w:r", "w:bookmarkStart", "w:t"]
    issues = check_element_order("w:p", test_tags)
    print("测试段落顺序:")
    for issue in issues:
        print(f"  [{issue['level']}] {issue['message']}")
    
    # 测试表格网格验证
    print("\n测试表格网格:")
    print("需要传入实际的表格元素进行测试")
