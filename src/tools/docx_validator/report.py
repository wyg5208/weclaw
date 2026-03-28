"""DOCX 验证报告生成模块。

参考 MiniMax check/report.py 设计
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Issue:
    """单个问题。"""
    issue_type: str  # 问题类型
    severity: str     # 严重程度: error | warning | info
    location: str     # 位置
    message: str      # 问题消息
    suggestion: str = ""  # 修复建议


@dataclass
class ValidationReport:
    """DOCX 验证报告。"""
    passed: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。"""
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "message": self.message,
            "details": self.details
        }

    def to_markdown(self) -> str:
        """转换为 Markdown 格式。"""
        lines = [
            f"# DOCX 验证报告",
            "",
            f"**状态**: {'✅ 通过' if self.passed else '❌ 失败'}",
            f"**消息**: {self.message}",
            "",
        ]
        
        if self.errors:
            lines.append("## ❌ 错误")
            for err in self.errors:
                lines.append(f"- {err}")
            lines.append("")
        
        if self.warnings:
            lines.append("## ⚠️ 警告")
            for warn in self.warnings:
                lines.append(f"- {warn}")
            lines.append("")
        
        if self.suggestions:
            lines.append("## 💡 建议")
            for sug in self.suggestions:
                lines.append(f"- {sug}")
            lines.append("")
        
        return "\n".join(lines)


def generate_report(docx_path: str, issues: list[Issue]) -> ValidationReport:
    """从问题列表生成验证报告。
    
    Args:
        docx_path: DOCX 文件路径
        issues: 检测到的问题列表
        
    Returns:
        ValidationReport: 验证报告
    """
    errors = []
    warnings = []
    suggestions = []
    
    for issue in issues:
        if issue.severity == "error":
            errors.append(f"[{issue.location}] {issue.message}")
        elif issue.severity == "warning":
            warnings.append(f"[{issue.location}] {issue.message}")
        
        if issue.suggestion:
            suggestions.append(f"{issue.message} → {issue.suggestion}")
    
    passed = len(errors) == 0
    
    if passed:
        if warnings:
            message = f"通过（有 {len(warnings)} 个警告）"
        else:
            message = "验证通过"
    else:
        message = f"验证失败（{len(errors)} 个错误）"
    
    return ValidationReport(
        passed=passed,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
        message=message,
        details={
            "file_path": docx_path,
            "total_issues": len(issues),
            "error_count": len(errors),
            "warning_count": len(warnings),
        }
    )


# 用于测试
if __name__ == "__main__":
    # 测试报告生成
    issues = [
        Issue(
            issue_type="grid_inconsistency",
            severity="error",
            location="word/document.xml",
            message="表格第 2 行有 3 个单元格，期望 4 个",
            suggestion="确保表格每行列数一致"
        ),
        Issue(
            issue_type="aspect_ratio",
            severity="info",
            location="word/document.xml",
            message="图片纵横比异常: 0.15",
            suggestion="检查图片是否被正确显示或裁剪"
        ),
    ]
    
    report = generate_report("test.docx", issues)
    print(report.to_markdown())
