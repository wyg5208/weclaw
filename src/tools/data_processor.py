"""数据处理工具 — Excel/CSV 数据处理：读取、筛选、排序、聚合、合并、透视表、清洗、导出。

支持的操作：
- 读取 Excel/CSV/JSON 文件并返回数据摘要
- 数据筛选（支持多种操作符）
- 数据排序
- 数据聚合（分组统计）
- 数据合并（两个文件）
- 透视表
- 数据清洗（去重、填充/删除缺失值、去空格、类型转换）
- 数据导出（xlsx/csv/json/html）
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class DataProcessorTool(BaseTool):
    """数据处理工具。

    支持 Excel/CSV 数据处理：读取、筛选、排序、聚合、合并、透视表、清洗、导出。
    """

    name = "data_processor"
    emoji = "📊"
    title = "数据处理"
    description = "Excel/CSV 数据处理：读取、筛选、排序、聚合、合并、透视表、清洗、导出"
    timeout = 120

    def __init__(self, output_dir: str = "") -> None:
        """初始化数据处理工具。

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
                name="read_excel",
                description="读取 Excel/CSV 文件并返回数据摘要",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（支持 xlsx, csv, json）",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "工作表名称，默认第一个（仅 Excel）",
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "最大显示行数，默认20",
                    },
                },
                required_params=["file_path"],
            ),
            ActionDef(
                name="filter_data",
                description="数据筛选",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "文件路径",
                    },
                    "column": {
                        "type": "string",
                        "description": "筛选列名",
                    },
                    "operator": {
                        "type": "string",
                        "description": "操作符",
                        "enum": ["==", "!=", ">", "<", ">=", "<=", "contains", "not_contains"],
                    },
                    "value": {
                        "type": "string",
                        "description": "筛选值",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["file_path", "column", "operator", "value"],
            ),
            ActionDef(
                name="sort_data",
                description="数据排序",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "文件路径",
                    },
                    "column": {
                        "type": "string",
                        "description": "排序列名",
                    },
                    "ascending": {
                        "type": "boolean",
                        "description": "升序，默认true",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["file_path", "column"],
            ),
            ActionDef(
                name="aggregate_data",
                description="数据聚合",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "文件路径",
                    },
                    "group_by": {
                        "type": "string",
                        "description": "分组列名",
                    },
                    "agg_column": {
                        "type": "string",
                        "description": "聚合列名",
                    },
                    "agg_func": {
                        "type": "string",
                        "description": "聚合函数",
                        "enum": ["sum", "mean", "count", "min", "max", "median"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["file_path", "group_by", "agg_column", "agg_func"],
            ),
            ActionDef(
                name="merge_data",
                description="数据合并（两个文件）",
                parameters={
                    "file_path1": {
                        "type": "string",
                        "description": "第一个文件路径",
                    },
                    "file_path2": {
                        "type": "string",
                        "description": "第二个文件路径",
                    },
                    "on_column": {
                        "type": "string",
                        "description": "合并键列名",
                    },
                    "how": {
                        "type": "string",
                        "description": "合并方式",
                        "enum": ["inner", "left", "right", "outer"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["file_path1", "file_path2", "on_column"],
            ),
            ActionDef(
                name="pivot_table",
                description="透视表",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "文件路径",
                    },
                    "index": {
                        "type": "string",
                        "description": "行索引列",
                    },
                    "columns": {
                        "type": "string",
                        "description": "列索引列",
                    },
                    "values": {
                        "type": "string",
                        "description": "值列",
                    },
                    "agg_func": {
                        "type": "string",
                        "description": "聚合函数，默认mean",
                        "enum": ["sum", "mean", "count", "min", "max"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["file_path", "index", "columns", "values"],
            ),
            ActionDef(
                name="clean_data",
                description="数据清洗",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "文件路径",
                    },
                    "operations": {
                        "type": "string",
                        "description": "清洗操作，逗号分隔：remove_duplicates,fill_na,drop_na,strip_whitespace,convert_types",
                    },
                    "fill_value": {
                        "type": "string",
                        "description": "填充缺失值的值",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["file_path", "operations"],
            ),
            ActionDef(
                name="export_data",
                description="导出数据",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "文件路径",
                    },
                    "format": {
                        "type": "string",
                        "description": "导出格式",
                        "enum": ["xlsx", "csv", "json", "html"],
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（不含扩展名），可选",
                    },
                },
                required_params=["file_path", "format"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行数据处理动作。"""
        action_map = {
            "read_excel": self._read_excel,
            "filter_data": self._filter_data,
            "sort_data": self._sort_data,
            "aggregate_data": self._aggregate_data,
            "merge_data": self._merge_data,
            "pivot_table": self._pivot_table,
            "clean_data": self._clean_data,
            "export_data": self._export_data,
        }

        handler = action_map.get(action)
        if not handler:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"不支持的动作: {action}",
            )

        try:
            return handler(params)
        except Exception as e:
            logger.error("数据处理失败: %s", e, exc_info=True)
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"数据处理失败: {e}",
            )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _read_file(self, file_path: str, sheet_name: str | None = None) -> pd.DataFrame:
        """智能读取文件，支持 xlsx, xls, csv, json。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            if sheet_name:
                return pd.read_excel(path, sheet_name=sheet_name)
            return pd.read_excel(path)
        elif suffix == ".csv":
            return pd.read_csv(path, encoding="utf-8-sig")
        elif suffix == ".json":
            return pd.read_json(path)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")

    def _get_output_path(self, input_path: Path, output_filename: str | None, ext: str) -> Path:
        """生成输出文件路径。"""
        if output_filename:
            return self.output_dir / f"{output_filename}.{ext}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.output_dir / f"{input_path.stem}_{timestamp}.{ext}"

    def _save_dataframe(self, df: pd.DataFrame, output_path: Path) -> None:
        """保存 DataFrame 到文件。"""
        suffix = output_path.suffix.lower()
        if suffix == ".xlsx":
            df.to_excel(output_path, index=False)
        elif suffix == ".csv":
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
        elif suffix == ".json":
            df.to_json(output_path, orient="records", force_ascii=False, indent=2)
        elif suffix == ".html":
            df.to_html(output_path, index=False)
        else:
            raise ValueError(f"不支持的输出格式: {suffix}")

    def _build_result(
        self,
        output_path: Path,
        operation: str,
        row_count: int,
        col_count: int,
        extra_info: str = "",
    ) -> ToolResult:
        """构建成功的返回结果。"""
        file_size = output_path.stat().st_size if output_path.exists() else 0
        output = (
            f"✅ {operation}完成\n"
            f"📁 文件: {output_path.name}\n"
            f"📊 数据: {row_count} 行 × {col_count} 列\n"
            f"💾 大小: {file_size} 字节"
        )
        if extra_info:
            output += f"\n{extra_info}"
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=output,
            data={
                "file_path": str(output_path),
                "file_name": output_path.name,
                "file_size": file_size,
                "row_count": row_count,
                "col_count": col_count,
            },
        )

    # ------------------------------------------------------------------
    # 数据处理动作
    # ------------------------------------------------------------------

    def _read_excel(self, params: dict[str, Any]) -> ToolResult:
        """读取 Excel/CSV 文件并返回数据摘要。"""
        file_path = params["file_path"]
        sheet_name = params.get("sheet_name")
        max_rows = int(params.get("max_rows", 20))

        df = self._read_file(file_path, sheet_name)

        summary = f"📊 数据摘要\n"
        summary += f"行数: {len(df)}, 列数: {len(df.columns)}\n"
        summary += f"列名: {', '.join(df.columns.tolist())}\n\n"
        summary += f"数据类型:\n{df.dtypes.to_string()}\n\n"
        summary += f"前 {min(max_rows, len(df))} 行:\n{df.head(max_rows).to_string()}\n\n"

        # 只对数值列生成统计
        numeric_df = df.select_dtypes(include=["number"])
        if not numeric_df.empty:
            summary += f"基础统计:\n{numeric_df.describe().to_string()}"

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=summary,
            data={
                "row_count": len(df),
                "col_count": len(df.columns),
                "columns": df.columns.tolist(),
            },
        )

    def _filter_data(self, params: dict[str, Any]) -> ToolResult:
        """数据筛选。"""
        file_path = params["file_path"]
        column = params["column"]
        operator = params["operator"]
        value = params["value"]
        output_filename = params.get("output_filename")

        df = self._read_file(file_path)

        if column not in df.columns:
            raise ValueError(f"列 '{column}' 不存在，可用列: {', '.join(df.columns.tolist())}")

        # 尝试转换为数值
        try:
            value_num = float(value)
            use_numeric = True
        except ValueError:
            value_num = None
            use_numeric = False

        # 根据操作符筛选
        if operator == "==":
            if use_numeric:
                mask = df[column] == value_num
            else:
                mask = df[column].astype(str) == value
        elif operator == "!=":
            if use_numeric:
                mask = df[column] != value_num
            else:
                mask = df[column].astype(str) != value
        elif operator == ">":
            mask = df[column] > (value_num if use_numeric else value)
        elif operator == "<":
            mask = df[column] < (value_num if use_numeric else value)
        elif operator == ">=":
            mask = df[column] >= (value_num if use_numeric else value)
        elif operator == "<=":
            mask = df[column] <= (value_num if use_numeric else value)
        elif operator == "contains":
            mask = df[column].astype(str).str.contains(value, na=False)
        elif operator == "not_contains":
            mask = ~df[column].astype(str).str.contains(value, na=False)
        else:
            raise ValueError(f"不支持的操作符: {operator}")

        result_df = df[mask]
        input_path = Path(file_path)
        output_path = self._get_output_path(input_path, output_filename, input_path.suffix.lstrip(".") or "xlsx")
        self._save_dataframe(result_df, output_path)

        extra_info = f"🔍 筛选条件: {column} {operator} {value}\n📉 筛选后: {len(result_df)}/{len(df)} 行"
        return self._build_result(output_path, "数据筛选", len(result_df), len(result_df.columns), extra_info)

    def _sort_data(self, params: dict[str, Any]) -> ToolResult:
        """数据排序。"""
        file_path = params["file_path"]
        column = params["column"]
        ascending = params.get("ascending", True)
        output_filename = params.get("output_filename")

        df = self._read_file(file_path)

        if column not in df.columns:
            raise ValueError(f"列 '{column}' 不存在，可用列: {', '.join(df.columns.tolist())}")

        result_df = df.sort_values(by=column, ascending=ascending)
        input_path = Path(file_path)
        output_path = self._get_output_path(input_path, output_filename, input_path.suffix.lstrip(".") or "xlsx")
        self._save_dataframe(result_df, output_path)

        order = "升序" if ascending else "降序"
        extra_info = f"🔢 排序: 按 {column} {order}"
        return self._build_result(output_path, "数据排序", len(result_df), len(result_df.columns), extra_info)

    def _aggregate_data(self, params: dict[str, Any]) -> ToolResult:
        """数据聚合。"""
        file_path = params["file_path"]
        group_by = params["group_by"]
        agg_column = params["agg_column"]
        agg_func = params["agg_func"]
        output_filename = params.get("output_filename")

        df = self._read_file(file_path)

        if group_by not in df.columns:
            raise ValueError(f"分组列 '{group_by}' 不存在，可用列: {', '.join(df.columns.tolist())}")
        if agg_column not in df.columns:
            raise ValueError(f"聚合列 '{agg_column}' 不存在，可用列: {', '.join(df.columns.tolist())}")

        # 执行聚合
        if agg_func == "median":
            result_df = df.groupby(group_by)[agg_column].median().reset_index()
        else:
            result_df = df.groupby(group_by)[agg_column].agg(agg_func).reset_index()

        result_df.columns = [group_by, f"{agg_column}_{agg_func}"]

        input_path = Path(file_path)
        output_path = self._get_output_path(input_path, output_filename, input_path.suffix.lstrip(".") or "xlsx")
        self._save_dataframe(result_df, output_path)

        extra_info = f"📈 聚合: {group_by} → {agg_func}({agg_column})"
        return self._build_result(output_path, "数据聚合", len(result_df), len(result_df.columns), extra_info)

    def _merge_data(self, params: dict[str, Any]) -> ToolResult:
        """数据合并（两个文件）。"""
        file_path1 = params["file_path1"]
        file_path2 = params["file_path2"]
        on_column = params["on_column"]
        how = params.get("how", "inner")
        output_filename = params.get("output_filename")

        df1 = self._read_file(file_path1)
        df2 = self._read_file(file_path2)

        if on_column not in df1.columns:
            raise ValueError(f"文件1中列 '{on_column}' 不存在，可用列: {', '.join(df1.columns.tolist())}")
        if on_column not in df2.columns:
            raise ValueError(f"文件2中列 '{on_column}' 不存在，可用列: {', '.join(df2.columns.tolist())}")

        result_df = pd.merge(df1, df2, on=on_column, how=how)

        input_path = Path(file_path1)
        output_path = self._get_output_path(input_path, output_filename, input_path.suffix.lstrip(".") or "xlsx")
        self._save_dataframe(result_df, output_path)

        how_map = {"inner": "内连接", "left": "左连接", "right": "右连接", "outer": "全连接"}
        extra_info = f"🔗 合并: {how_map.get(how, how)} on {on_column}\n📋 文件1: {len(df1)} 行, 文件2: {len(df2)} 行"
        return self._build_result(output_path, "数据合并", len(result_df), len(result_df.columns), extra_info)

    def _pivot_table(self, params: dict[str, Any]) -> ToolResult:
        """透视表。"""
        file_path = params["file_path"]
        index = params["index"]
        columns = params["columns"]
        values = params["values"]
        agg_func = params.get("agg_func", "mean")
        output_filename = params.get("output_filename")

        df = self._read_file(file_path)

        for col in [index, columns, values]:
            if col not in df.columns:
                raise ValueError(f"列 '{col}' 不存在，可用列: {', '.join(df.columns.tolist())}")

        result_df = pd.pivot_table(
            df,
            index=index,
            columns=columns,
            values=values,
            aggfunc=agg_func,
        ).reset_index()

        # 将 MultiIndex 列名转换为字符串
        result_df.columns = [str(c) if not isinstance(c, str) else c for c in result_df.columns]

        input_path = Path(file_path)
        output_path = self._get_output_path(input_path, output_filename, input_path.suffix.lstrip(".") or "xlsx")
        self._save_dataframe(result_df, output_path)

        extra_info = f"📊 透视表: index={index}, columns={columns}, values={values}, func={agg_func}"
        return self._build_result(output_path, "透视表生成", len(result_df), len(result_df.columns), extra_info)

    def _clean_data(self, params: dict[str, Any]) -> ToolResult:
        """数据清洗。"""
        file_path = params["file_path"]
        operations = params["operations"]
        fill_value = params.get("fill_value", "")
        output_filename = params.get("output_filename")

        df = self._read_file(file_path)
        original_rows = len(df)
        ops_list = [op.strip() for op in operations.split(",")]
        ops_done = []

        for op in ops_list:
            if op == "remove_duplicates":
                before = len(df)
                df = df.drop_duplicates()
                ops_done.append(f"去重: {before - len(df)} 行")
            elif op == "fill_na":
                na_count = df.isna().sum().sum()
                df = df.fillna(fill_value if fill_value else 0)
                ops_done.append(f"填充缺失值: {na_count} 个")
            elif op == "drop_na":
                before = len(df)
                df = df.dropna()
                ops_done.append(f"删除缺失行: {before - len(df)} 行")
            elif op == "strip_whitespace":
                for col in df.select_dtypes(include=["object"]).columns:
                    df[col] = df[col].str.strip()
                ops_done.append("去除空格")
            elif op == "convert_types":
                for col in df.columns:
                    try:
                        df[col] = pd.to_numeric(df[col], errors="ignore")
                    except Exception:
                        pass
                ops_done.append("类型转换")

        input_path = Path(file_path)
        output_path = self._get_output_path(input_path, output_filename, input_path.suffix.lstrip(".") or "xlsx")
        self._save_dataframe(df, output_path)

        extra_info = f"🧹 清洗操作: {', '.join(ops_done)}\n📉 行数变化: {original_rows} → {len(df)}"
        return self._build_result(output_path, "数据清洗", len(df), len(df.columns), extra_info)

    def _export_data(self, params: dict[str, Any]) -> ToolResult:
        """导出数据。"""
        file_path = params["file_path"]
        export_format = params["format"]
        output_filename = params.get("output_filename")

        df = self._read_file(file_path)

        input_path = Path(file_path)
        output_path = self._get_output_path(input_path, output_filename, export_format)
        self._save_dataframe(df, output_path)

        format_map = {"xlsx": "Excel", "csv": "CSV", "json": "JSON", "html": "HTML"}
        extra_info = f"📤 导出格式: {format_map.get(export_format, export_format)}"
        return self._build_result(output_path, "数据导出", len(df), len(df.columns), extra_info)


# 用于测试
if __name__ == "__main__":
    import asyncio

    async def test():
        tool = DataProcessorTool()
        print("Actions:", [a.name for a in tool.get_actions()])
        print("Tool registered successfully!")

    asyncio.run(test())
