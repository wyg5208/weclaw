"""数据可视化工具 — 生成柱状图、折线图、饼图、散点图、热力图和仪表盘。

支持从 xlsx/csv/json 文件读取数据，生成 PNG 图片或 HTML 仪表盘。
"""

from __future__ import annotations

import base64
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')  # 非交互模式，必须在 import pyplot 之前
import matplotlib.pyplot as plt
import pandas as pd

from src.tools.base import ActionDef, BaseTool, ToolResult, ToolResultStatus

logger = logging.getLogger(__name__)


class DataVisualizationTool(BaseTool):
    """数据可视化工具 — 支持多种图表类型和仪表盘生成。"""

    name = "data_visualization"
    emoji = "📈"
    title = "数据可视化"
    description = "数据可视化分析：柱状图、折线图、饼图、散点图、热力图、仪表盘"
    timeout = 120

    def __init__(self, output_dir: str = "") -> None:
        """初始化数据可视化工具。

        Args:
            output_dir: 输出目录路径，为空则使用默认目录 generated/YYYY-MM-DD
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = (
                Path(__file__).parent.parent.parent
                / "generated"
                / datetime.now().strftime("%Y-%m-%d")
            )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_actions(self) -> list[ActionDef]:
        """返回支持的动作列表。"""
        return [
            ActionDef(
                name="plot_bar",
                description="生成柱状图：展示分类数据的数值比较",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "数据文件路径(xlsx/csv/json)",
                    },
                    "x": {
                        "type": "string",
                        "description": "X轴列名（分类变量）",
                    },
                    "y": {
                        "type": "string",
                        "description": "Y轴列名（数值变量）",
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题（可选）",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（可选，默认自动生成）",
                    },
                },
                required_params=["file_path", "x", "y"],
            ),
            ActionDef(
                name="plot_line",
                description="生成折线图：展示数据随时间或顺序的变化趋势",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "数据文件路径(xlsx/csv/json)",
                    },
                    "x": {
                        "type": "string",
                        "description": "X轴列名",
                    },
                    "y": {
                        "type": "string",
                        "description": "Y轴列名",
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题（可选）",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（可选，默认自动生成）",
                    },
                },
                required_params=["file_path", "x", "y"],
            ),
            ActionDef(
                name="plot_pie",
                description="生成饼图：展示各部分占整体的比例",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "数据文件路径(xlsx/csv/json)",
                    },
                    "values": {
                        "type": "string",
                        "description": "数值列名（各部分的数值）",
                    },
                    "labels": {
                        "type": "string",
                        "description": "标签列名（各部分的名称）",
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题（可选）",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（可选，默认自动生成）",
                    },
                },
                required_params=["file_path", "values", "labels"],
            ),
            ActionDef(
                name="plot_scatter",
                description="生成散点图：展示两个变量之间的关系",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "数据文件路径(xlsx/csv/json)",
                    },
                    "x": {
                        "type": "string",
                        "description": "X轴列名",
                    },
                    "y": {
                        "type": "string",
                        "description": "Y轴列名",
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题（可选）",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（可选，默认自动生成）",
                    },
                },
                required_params=["file_path", "x", "y"],
            ),
            ActionDef(
                name="plot_heatmap",
                description="生成热力图：展示数值列之间的相关性矩阵",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "数据文件路径(xlsx/csv/json)",
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题（可选）",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（可选，默认自动生成）",
                    },
                },
                required_params=["file_path"],
            ),
            ActionDef(
                name="generate_dashboard",
                description="生成数据分析仪表盘：包含数据概览、多个图表的 HTML 页面",
                parameters={
                    "file_path": {
                        "type": "string",
                        "description": "数据文件路径(xlsx/csv/json)",
                    },
                    "title": {
                        "type": "string",
                        "description": "仪表盘标题（可选）",
                    },
                    "output_filename": {
                        "type": "string",
                        "description": "输出文件名（可选，默认自动生成）",
                    },
                },
                required_params=["file_path"],
            ),
        ]

    async def execute(self, action: str, params: dict[str, Any]) -> ToolResult:
        """执行指定的可视化动作。"""
        try:
            if action == "plot_bar":
                return self._plot_bar(params)
            elif action == "plot_line":
                return self._plot_line(params)
            elif action == "plot_pie":
                return self._plot_pie(params)
            elif action == "plot_scatter":
                return self._plot_scatter(params)
            elif action == "plot_heatmap":
                return self._plot_heatmap(params)
            elif action == "generate_dashboard":
                return self._generate_dashboard(params)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    error=f"未知的动作: {action}",
                )
        except FileNotFoundError as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"文件不存在: {e}",
            )
        except ValueError as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"数据错误: {e}",
            )
        except Exception as e:
            logger.exception("数据可视化执行错误")
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"执行错误: {type(e).__name__}: {e}",
            )

    def _read_file(self, file_path: str) -> pd.DataFrame:
        """读取数据文件。

        Args:
            file_path: 数据文件路径

        Returns:
            pandas DataFrame

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件格式
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()
        if suffix in (".xlsx", ".xls"):
            return pd.read_excel(path)
        elif suffix == ".csv":
            return pd.read_csv(path, encoding="utf-8-sig")
        elif suffix == ".json":
            return pd.read_json(path)
        else:
            raise ValueError(f"不支持的文件格式: {suffix}，支持 xlsx/csv/json")

    def _setup_chinese_font(self) -> None:
        """设置中文字体支持。"""
        plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False

    def _get_output_path(self, params: dict[str, Any], suffix: str, default_prefix: str) -> Path:
        """获取输出文件路径。

        Args:
            params: 参数字典
            suffix: 文件后缀（如 .png, .html）
            default_prefix: 默认文件名前缀

        Returns:
            输出文件的完整路径
        """
        output_filename = params.get("output_filename", "")
        if output_filename:
            # 确保有正确的后缀
            if not output_filename.endswith(suffix):
                output_filename = output_filename.rsplit(".", 1)[0] + suffix
            return self.output_dir / output_filename
        else:
            timestamp = datetime.now().strftime("%H%M%S")
            return self.output_dir / f"{default_prefix}_{timestamp}{suffix}"

    def _plot_bar(self, params: dict[str, Any]) -> ToolResult:
        """生成柱状图。"""
        df = self._read_file(params["file_path"])
        x, y = params["x"], params["y"]

        if x not in df.columns:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"列 '{x}' 不存在于数据中，可用列: {list(df.columns)}",
            )
        if y not in df.columns:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"列 '{y}' 不存在于数据中，可用列: {list(df.columns)}",
            )

        title = params.get("title", f"{y} by {x}")
        output_path = self._get_output_path(params, ".png", "bar_chart")

        self._setup_chinese_font()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(df[x].astype(str), df[y])
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        ax.set_title(title)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
        plt.close(fig)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"柱状图已生成: {output_path}",
            data={"output_path": str(output_path), "chart_type": "bar"},
        )

    def _plot_line(self, params: dict[str, Any]) -> ToolResult:
        """生成折线图。"""
        df = self._read_file(params["file_path"])
        x, y = params["x"], params["y"]

        if x not in df.columns:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"列 '{x}' 不存在于数据中，可用列: {list(df.columns)}",
            )
        if y not in df.columns:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"列 '{y}' 不存在于数据中，可用列: {list(df.columns)}",
            )

        title = params.get("title", f"{y} vs {x}")
        output_path = self._get_output_path(params, ".png", "line_chart")

        self._setup_chinese_font()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df[x], df[y], marker="o", linewidth=2, markersize=4)
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        ax.set_title(title)
        ax.grid(True, linestyle="--", alpha=0.7)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
        plt.close(fig)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"折线图已生成: {output_path}",
            data={"output_path": str(output_path), "chart_type": "line"},
        )

    def _plot_pie(self, params: dict[str, Any]) -> ToolResult:
        """生成饼图。"""
        df = self._read_file(params["file_path"])
        values_col = params["values"]
        labels_col = params["labels"]

        if values_col not in df.columns:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"列 '{values_col}' 不存在于数据中，可用列: {list(df.columns)}",
            )
        if labels_col not in df.columns:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"列 '{labels_col}' 不存在于数据中，可用列: {list(df.columns)}",
            )

        title = params.get("title", f"{values_col} 分布")
        output_path = self._get_output_path(params, ".png", "pie_chart")

        self._setup_chinese_font()
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.pie(
            df[values_col],
            labels=df[labels_col],
            autopct="%1.1f%%",
            startangle=90,
            shadow=True,
        )
        ax.set_title(title)
        ax.axis("equal")
        plt.tight_layout()

        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
        plt.close(fig)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"饼图已生成: {output_path}",
            data={"output_path": str(output_path), "chart_type": "pie"},
        )

    def _plot_scatter(self, params: dict[str, Any]) -> ToolResult:
        """生成散点图。"""
        df = self._read_file(params["file_path"])
        x, y = params["x"], params["y"]

        if x not in df.columns:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"列 '{x}' 不存在于数据中，可用列: {list(df.columns)}",
            )
        if y not in df.columns:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"列 '{y}' 不存在于数据中，可用列: {list(df.columns)}",
            )

        title = params.get("title", f"{y} vs {x} 散点图")
        output_path = self._get_output_path(params, ".png", "scatter_chart")

        self._setup_chinese_font()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(df[x], df[y], alpha=0.6, edgecolors="w", linewidth=0.5)
        ax.set_xlabel(x)
        ax.set_ylabel(y)
        ax.set_title(title)
        ax.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()

        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
        plt.close(fig)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"散点图已生成: {output_path}",
            data={"output_path": str(output_path), "chart_type": "scatter"},
        )

    def _plot_heatmap(self, params: dict[str, Any]) -> ToolResult:
        """生成热力图（相关性矩阵）。"""
        df = self._read_file(params["file_path"])

        # 只选数值列
        numeric_df = df.select_dtypes(include=["number"])
        if numeric_df.empty:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error="数据中没有数值列，无法生成热力图",
            )
        if len(numeric_df.columns) < 2:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                error=f"需要至少2个数值列才能生成热力图，当前只有: {list(numeric_df.columns)}",
            )

        corr = numeric_df.corr()
        title = params.get("title", "相关性热力图")
        output_path = self._get_output_path(params, ".png", "heatmap")

        self._setup_chinese_font()
        fig, ax = plt.subplots(figsize=(10, 8))
        im = ax.imshow(corr, cmap="coolwarm", aspect="auto", vmin=-1, vmax=1)

        # 设置标签
        ax.set_xticks(range(len(corr.columns)))
        ax.set_yticks(range(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=45, ha="right")
        ax.set_yticklabels(corr.columns)

        # 添加数值标注
        for i in range(len(corr)):
            for j in range(len(corr)):
                text_color = "white" if abs(corr.iloc[i, j]) > 0.5 else "black"
                ax.text(
                    j, i, f"{corr.iloc[i, j]:.2f}",
                    ha="center", va="center", fontsize=8, color=text_color
                )

        ax.set_title(title)
        fig.colorbar(im, label="相关系数")
        plt.tight_layout()

        fig.savefig(str(output_path), dpi=150, bbox_inches="tight")
        plt.close(fig)

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"热力图已生成: {output_path}\n包含列: {', '.join(corr.columns)}",
            data={"output_path": str(output_path), "chart_type": "heatmap", "columns": list(corr.columns)},
        )

    def _generate_dashboard(self, params: dict[str, Any]) -> ToolResult:
        """生成数据分析仪表盘（HTML 页面）。"""
        df = self._read_file(params["file_path"])
        title = params.get("title", "数据分析仪表盘")
        output_path = self._get_output_path(params, ".html", "dashboard")

        self._setup_chinese_font()
        charts_html = []

        # 1. 数据概览表格
        overview_html = f"""
        <div class="section">
            <h2>📊 数据概览</h2>
            <p><strong>数据维度:</strong> {len(df)} 行 × {len(df.columns)} 列</p>
            <p><strong>列名:</strong> {', '.join(df.columns)}</p>
            <h3>统计摘要</h3>
            {df.describe().to_html(classes='table')}
        </div>
        """
        charts_html.append(overview_html)

        # 2. 为每个数值列生成图表
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

        for col in numeric_cols[:4]:  # 最多4个
            fig, ax = plt.subplots(figsize=(8, 4))
            if len(df) <= 20:
                ax.bar(range(len(df)), df[col])
                ax.set_xticks(range(len(df)))
                if df.index.dtype == "object" or len(str(df.index[0])) > 10:
                    ax.set_xticklabels(range(len(df)))
                else:
                    ax.set_xticklabels(df.index, rotation=45, ha="right")
            else:
                ax.plot(df[col], linewidth=1.5)
            ax.set_title(f"{col} 分布")
            ax.set_ylabel(col)
            ax.grid(True, linestyle="--", alpha=0.5)
            plt.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            img_b64 = base64.b64encode(buf.read()).decode()
            charts_html.append(
                f'<div class="chart"><h3>{col}</h3>'
                f'<img src="data:image/png;base64,{img_b64}" alt="{col} 图表"></div>'
            )

        # 3. 相关性热力图
        if len(numeric_cols) >= 2:
            numeric_df = df[numeric_cols]
            corr = numeric_df.corr()

            fig, ax = plt.subplots(figsize=(8, 6))
            im = ax.imshow(corr, cmap="coolwarm", aspect="auto", vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr.columns)))
            ax.set_yticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns, rotation=45, ha="right")
            ax.set_yticklabels(corr.columns)

            for i in range(len(corr)):
                for j in range(len(corr)):
                    text_color = "white" if abs(corr.iloc[i, j]) > 0.5 else "black"
                    ax.text(
                        j, i, f"{corr.iloc[i, j]:.2f}",
                        ha="center", va="center", fontsize=8, color=text_color
                    )

            ax.set_title("相关性热力图")
            fig.colorbar(im)
            plt.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            img_b64 = base64.b64encode(buf.read()).decode()
            charts_html.append(
                '<div class="chart"><h3>相关性分析</h3>'
                f'<img src="data:image/png;base64,{img_b64}" alt="相关性热力图"></div>'
            )

        # 组装 HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        h1 {{
            text-align: center;
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
        }}
        .section {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .chart {{
            background: white;
            margin: 20px 0;
            padding: 20px;
            text-align: center;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .chart img {{
            max-width: 100%;
            height: auto;
        }}
        .chart h3 {{
            color: #2c3e50;
            margin-top: 0;
        }}
        .table {{
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
            font-size: 14px;
        }}
        .table th, .table td {{
            border: 1px solid #ddd;
            padding: 10px 8px;
            text-align: right;
        }}
        .table th {{
            background: #3498db;
            color: white;
            font-weight: bold;
        }}
        .table tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        .table tr:hover {{
            background: #e8f4fc;
        }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <h1>📈 {title}</h1>
    {''.join(charts_html)}
    <div class="footer">
        由 Weclaw 数据可视化工具生成 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>"""

        output_path.write_text(html, encoding="utf-8")

        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            output=f"数据分析仪表盘已生成: {output_path}\n"
                   f"包含: 数据概览 + {min(len(numeric_cols), 4)} 个图表"
                   + (" + 相关性热力图" if len(numeric_cols) >= 2 else ""),
            data={
                "output_path": str(output_path),
                "chart_type": "dashboard",
                "rows": len(df),
                "columns": len(df.columns),
                "numeric_columns": numeric_cols,
            },
        )
