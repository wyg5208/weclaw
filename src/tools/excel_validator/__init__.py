"""Excel 公式验证模块 - 提供 Excel 文件的零容错验证能力。

模块功能：
- recalc: 使用 LibreOffice headless 重新计算公式
- refcheck: 引用异常检查（范围溢出、表头误包含等）
- check: OpenXML 结构验证
- styles: 专业样式系统

零容错原则：任何公式错误必须修复，不允许"Excel会自动修复"的假设

主要API：
- recalc_workbook: 公式重计算
- refcheck_workbook: 引用检查
- validate_xlsx: 完整验证管线
- apply_professional_style: 应用专业样式
"""

from src.tools.excel_validator.recalc import (
    EXCEL_ERRORS,
    FormulaError,
    RecalcResult,
    ValidationError,
    recalc_workbook,
    validate_with_recalc,
)
from src.tools.excel_validator.refcheck import (
    FORBIDDEN_FUNCTIONS,
    RefcheckResult,
    ReferenceIssue,
    check_compatibility,
    refcheck_workbook,
)
from src.tools.excel_validator.check import (
    ValidationReport,
    quick_validate,
    validate_xlsx,
)
from src.tools.excel_validator.styles import (
    STYLE_THEMES,
    ColorPalette,
    apply_professional_style,
    apply_theme,
    freeze_panes,
    format_currency_column,
    format_percentage_column,
    set_column_widths,
)

__all__ = [
    # recalc
    "EXCEL_ERRORS",
    "FormulaError",
    "RecalcResult",
    "ValidationError",
    "recalc_workbook",
    "validate_with_recalc",
    # refcheck
    "FORBIDDEN_FUNCTIONS",
    "RefcheckResult",
    "ReferenceIssue",
    "check_compatibility",
    "refcheck_workbook",
    # check
    "ValidationReport",
    "quick_validate",
    "validate_xlsx",
    # styles
    "STYLE_THEMES",
    "ColorPalette",
    "apply_professional_style",
    "apply_theme",
    "freeze_panes",
    "format_currency_column",
    "format_percentage_column",
    "set_column_widths",
]
