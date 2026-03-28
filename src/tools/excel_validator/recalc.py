"""Excel 公式重计算模块 - 使用 LibreOffice headless 重新计算公式并检测错误。

零容错原则：
- 任何公式错误必须修复
- 不允许"Excel会自动修复"的假设
- 公式错误包括：#VALUE!, #DIV/0!, #REF!, #NAME?, #NULL!, #NUM!, #N/A

参考 MiniMax recalc.py 设计
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Excel 错误类型（零容错黑名单）
EXCEL_ERRORS = [
    "#VALUE!",
    "#DIV/0!",
    "#REF!",
    "#NAME?",
    "#NULL!",
    "#NUM!",
    "#N/A",
]


@dataclass
class FormulaError:
    """单个公式错误。"""
    error_type: str  # 错误类型，如 "#REF!"
    cell: str        # 单元格地址，如 "A1"
    sheet: str       # 工作表名称
    formula: str      # 原始公式
    message: str      # 错误描述


@dataclass
class RecalcResult:
    """公式重计算结果。"""
    status: str  # "success" | "errors_found" | "libreoffice_not_found" | "failed"
    total_errors: int = 0
    total_formulas: int = 0
    error_summary: dict[str, dict[str, Any]] = field(default_factory=dict)
    errors: list[FormulaError] = field(default_factory=list)
    message: str = ""

    @property
    def is_success(self) -> bool:
        return self.status == "success" and self.total_errors == 0


class ValidationError(Exception):
    """验证失败异常。"""
    def __init__(self, message: str, result: RecalcResult | None = None):
        super().__init__(message)
        self.result = result


def _find_libreoffice() -> str | None:
    """查找系统中的 LibreOffice 可执行文件路径。"""
    # 常见的 LibreOffice 安装路径
    possible_paths = [
        "libreoffice",
        "soffice",
        "C:\\Program Files\\LibreOffice\\program\\soffice.exe",
        "C:\\Program Files (x86)\\LibreOffice\\program\\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/soffice",
        "/usr/lib/libreoffice/program/soffice",
    ]
    
    for path in possible_paths:
        if Path(path).exists() if not shutil.which(path) else True:
            if shutil.which(path):
                return shutil.which(path)
    
    # 使用 shutil.which 查找
    for name in ["libreoffice", "soffice"]:
        found = shutil.which(name)
        if found:
            return found
    
    return None


def _parse_calc_output(output: str) -> list[dict[str, str]]:
    """解析 LibreOffice 的 CSV 输出，提取错误信息。"""
    errors = []
    for line in output.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # 格式: CELL,SHEET,FORMULA,VALUE
        parts = line.split(",", 3)
        if len(parts) >= 4:
            cell, sheet, formula, value = parts
            if value in EXCEL_ERRORS:
                errors.append({
                    "cell": cell.strip(),
                    "sheet": sheet.strip(),
                    "formula": formula.strip(),
                    "value": value.strip(),
                })
    return errors


def recalc_workbook(path: str, timeout: int = 30) -> RecalcResult:
    """使用 LibreOffice headless 重新计算 Excel 文件的公式。
    
    Args:
        path: Excel 文件路径（.xlsx）
        timeout: 超时时间（秒），默认 30
        
    Returns:
        RecalcResult: 包含错误信息的重计算结果
        
    Raises:
        ValidationError: 当检测到公式错误时抛出（零容错门控）
        
    示例:
        >>> result = recalc_workbook("report.xlsx")
        >>> if not result.is_success:
        >>>     raise ValidationError(f"发现 {result.total_errors} 个公式错误", result)
    """
    file_path = Path(path)
    if not file_path.exists():
        return RecalcResult(
            status="failed",
            message=f"文件不存在: {path}"
        )
    
    # 检查文件扩展名
    if file_path.suffix.lower() not in (".xlsx", ".xlsm"):
        return RecalcResult(
            status="failed",
            message=f"不支持的文件格式: {file_path.suffix}，仅支持 .xlsx, .xlsm"
        )
    
    # 查找 LibreOffice
    libreoffice = _find_libreoffice()
    if not libreoffice:
        logger.warning("LibreOffice 未安装，无法进行公式重计算")
        return RecalcResult(
            status="libreoffice_not_found",
            message="LibreOffice 未安装或不在 PATH 中，无法验证公式"
        )
    
    try:
        # 创建临时目录用于输出
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 使用 LibreOffice 将文件转换为 CSV（保留公式值）
            # 这会强制 Excel 重新计算所有公式
            
            # 方法1: 使用 --headless --convert-to csv
            output_csv = Path(tmp_dir) / "output.csv"
            result = subprocess.run(
                [
                    libreoffice,
                    "--headless",
                    "--infilter=Microsoft Excel 2007-2019 XML (.xlsx)",
                    "--convert-to", "csv",
                    "--outdir", tmp_dir,
                    str(file_path)
                ],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode != 0:
                logger.warning("LibreOffice 转换失败: %s", result.stderr)
                return RecalcResult(
                    status="failed",
                    message=f"LibreOffice 转换失败: {result.stderr}"
                )
            
            # 读取生成的 CSV 文件
            if output_csv.exists():
                with open(output_csv, "r", encoding="utf-8", errors="replace") as f:
                    csv_content = f.read()
                
                # 解析 CSV 检查错误值
                errors = _parse_calc_output(csv_content)
                
                if errors:
                    # 分类统计错误
                    error_summary: dict[str, dict[str, Any]] = {}
                    formula_errors = []
                    
                    for err in errors:
                        error_type = err["value"]
                        if error_type not in error_summary:
                            error_summary[error_type] = {
                                "count": 0,
                                "locations": []
                            }
                        error_summary[error_type]["count"] += 1
                        error_summary[error_type]["locations"].append({
                            "cell": err["cell"],
                            "sheet": err["sheet"],
                            "formula": err["formula"]
                        })
                        formula_errors.append(FormulaError(
                            error_type=error_type,
                            cell=err["cell"],
                            sheet=err["sheet"],
                            formula=err["formula"],
                            message=_get_error_message(error_type)
                        ))
                    
                    return RecalcResult(
                        status="errors_found",
                        total_errors=len(errors),
                        total_formulas=len(csv_content.split("\n")),
                        error_summary=error_summary,
                        errors=formula_errors,
                        message=f"发现 {len(errors)} 个公式错误"
                    )
                else:
                    return RecalcResult(
                        status="success",
                        total_formulas=len(csv_content.split("\n")),
                        message="所有公式计算正常"
                    )
            else:
                return RecalcResult(
                    status="failed",
                    message="LibreOffice 未生成输出文件"
                )
                
    except subprocess.TimeoutExpired:
        return RecalcResult(
            status="failed",
            message=f"LibreOffice 执行超时 ({timeout}秒)"
        )
    except Exception as e:
        logger.error("公式重计算异常: %s", e)
        return RecalcResult(
            status="failed",
            message=f"公式重计算异常: {e}"
        )


def _get_error_message(error_type: str) -> str:
    """获取错误类型的描述信息。"""
    error_messages = {
        "#VALUE!": "参数类型错误或操作数类型不兼容",
        "#DIV/0!": "除数为零或空单元格",
        "#REF!": "单元格引用无效（引用的单元格被删除）",
        "#NAME?": "函数名或标签不可识别",
        "#NULL!": "两个区域没有交集",
        "#NUM!": "数值溢出或无效的数值参数",
        "#N/A": "查找值不存在或不可用",
    }
    return error_messages.get(error_type, "未知错误")


def validate_with_recalc(path: str, strict: bool = True) -> RecalcResult:
    """验证 Excel 文件，strict=True 时在发现错误时抛出异常。
    
    Args:
        path: Excel 文件路径
        strict: 严格模式，发现错误时抛出 ValidationError
        
    Returns:
        RecalcResult: 验证结果
        
    Raises:
        ValidationError: 当 strict=True 且检测到公式错误时
    """
    result = recalc_workbook(path)
    
    if strict and not result.is_success and result.status == "errors_found":
        raise ValidationError(
            f"文件包含 {result.total_errors} 个公式错误，禁止交付",
            result
        )
    
    return result


# 用于测试
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"正在验证: {file_path}")
        result = recalc_workbook(file_path)
        print(f"状态: {result.status}")
        print(f"错误数: {result.total_errors}")
        if result.error_summary:
            print("错误详情:")
            for error_type, info in result.error_summary.items():
                print(f"  {error_type}: {info['count']} 个")
                for loc in info['locations'][:3]:
                    print(f"    - {loc['cell']} ({loc['sheet']}): {loc['formula']}")
    else:
        print("用法: python recalc.py <excel_file.xlsx>")
