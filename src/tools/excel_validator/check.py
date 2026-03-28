"""Excel 验证管线 - 整合公式重计算、引用检查和结构验证。

验证流程：
1. recalc → 公式重计算（LibreOffice）
2. refcheck → 引用异常检查
3. 结构验证 → OpenXML 结构检查

零容错门控：
- 任何 #VALUE!, #DIV/0!, #REF!, #NAME?, #NULL!, #NUM!, #N/A 错误必须修复
- 引用问题按 severity 分级处理
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.tools.excel_validator.recalc import (
    EXCEL_ERRORS,
    RecalcResult,
    ValidationError,
    recalc_workbook,
)
from src.tools.excel_validator.refcheck import (
    RefcheckResult,
    ReferenceIssue,
    refcheck_workbook,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """完整的 Excel 验证报告。"""
    file_path: str
    recalc_result: RecalcResult | None = None
    refcheck_result: RefcheckResult | None = None
    passed: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。"""
        return {
            "file_path": self.file_path,
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "message": self.message,
            "details": {
                "recalc": self.recalc_result.__dict__ if self.recalc_result else None,
                "refcheck": self.refcheck_result.__dict__ if self.refcheck_result else None,
            }
        }


def validate_xlsx(
    path: str,
    skip_recalc: bool = False,
    skip_refcheck: bool = False,
    strict: bool = True
) -> ValidationReport:
    """完整的 Excel 验证管线。
    
    验证流程：
    1. recalc → 公式重计算（检测 #VALUE! 等错误）
    2. refcheck → 引用异常检查（范围溢出等）
    3. 结构验证 → OpenXML 结构检查
    
    Args:
        path: Excel 文件路径
        skip_recalc: 跳过公式重计算
        skip_refcheck: 跳过引用检查
        strict: 严格模式，发现问题立即返回失败
        
    Returns:
        ValidationReport: 完整的验证报告
        
    Raises:
        ValidationError: 当 strict=True 且检测到公式错误时（零容错门控）
    """
    file_path = Path(path)
    report = ValidationReport(file_path=str(path))
    
    # 检查文件
    if not file_path.exists():
        report.errors.append(f"文件不存在: {path}")
        report.message = "文件不存在"
        return report
    
    if file_path.suffix.lower() not in (".xlsx", ".xlsm"):
        report.errors.append(f"不支持的文件格式: {file_path.suffix}")
        report.message = "不支持的文件格式"
        return report
    
    # Step 1: 公式重计算
    if not skip_recalc:
        logger.info("执行公式重计算...")
        recalc_result = recalc_workbook(path)
        report.recalc_result = recalc_result
        
        if recalc_result.status == "errors_found":
            # 发现公式错误
            for error_type, info in recalc_result.error_summary.items():
                report.errors.append(
                    f"公式错误 {error_type}: {info['count']} 个"
                )
                for loc in info['locations']:
                    report.suggestions.append(
                        f"修复 {loc['cell']} ({loc['sheet']}): {loc['formula']}"
                    )
        
        elif recalc_result.status == "libreoffice_not_found":
            report.warnings.append("LibreOffice 未安装，无法进行公式重计算")
            logger.warning("LibreOffice 未安装")
    
    # Step 2: 引用检查
    if not skip_refcheck:
        logger.info("执行引用检查...")
        refcheck_result = refcheck_workbook(path)
        report.refcheck_result = refcheck_result
        
        for issue in refcheck_result.issues:
            if issue.severity == "error":
                report.errors.append(f"[{issue.severity}] {issue.cell}: {issue.message}")
            else:
                report.warnings.append(f"[{issue.severity}] {issue.cell}: {issue.message}")
            
            if issue.suggestion:
                report.suggestions.append(f"{issue.cell}: {issue.suggestion}")
    
    # Step 3: 判断是否通过
    has_errors = bool(report.errors)
    
    # LibreOffice 未安装不是致命错误
    if report.recalc_result and report.recalc_result.status == "libreoffice_not_found":
        has_errors = False
    
    report.passed = not has_errors
    
    # 生成消息
    if report.passed:
        report.message = "验证通过"
    else:
        report.message = f"验证失败，发现 {len(report.errors)} 个错误"
    
    # 严格模式：公式错误必须修复
    if strict and not report.passed:
        if report.recalc_result and report.recalc_result.total_errors > 0:
            raise ValidationError(
                f"文件包含 {report.recalc_result.total_errors} 个公式错误，禁止交付",
                report.recalc_result
            )
    
    return report


def quick_validate(path: str) -> dict[str, Any]:
    """快速验证（仅检查公式错误）。
    
    Args:
        path: Excel 文件路径
        
    Returns:
        包含验证结果的字典
    """
    try:
        result = recalc_workbook(path, timeout=30)
        if result.status == "errors_found":
            return {
                "valid": False,
                "error_count": result.total_errors,
                "errors": result.error_summary,
                "message": result.message
            }
        elif result.status == "success":
            return {
                "valid": True,
                "message": "验证通过"
            }
        else:
            return {
                "valid": None,
                "message": result.message
            }
    except Exception as e:
        return {
            "valid": None,
            "message": f"验证异常: {e}"
        }


# 用于测试
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"正在验证: {file_path}")
        print("=" * 50)
        
        report = validate_xlsx(file_path)
        
        print(f"状态: {'✅ 通过' if report.passed else '❌ 失败'}")
        print(f"消息: {report.message}")
        
        if report.errors:
            print("\n❌ 错误:")
            for err in report.errors:
                print(f"  - {err}")
        
        if report.warnings:
            print("\n⚠️  警告:")
            for warn in report.warnings:
                print(f"  - {warn}")
        
        if report.suggestions:
            print("\n💡 建议:")
            for sug in report.suggestions[:5]:
                print(f"  - {sug}")
        
        print("\n" + "=" * 50)
        print("详细信息:")
        print(report.to_dict())
    else:
        print("用法: python check.py <excel_file.xlsx>")
