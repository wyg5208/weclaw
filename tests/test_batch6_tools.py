"""Batch 6 工具综合测试：合同生成器、财务报告、简历生成器、思维导图。"""
import asyncio
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

# 确保项目根目录在 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 测试结果收集
PASSED = 0
FAILED = 0
ERRORS = []

def report(name: str, ok: bool, detail: str = ""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  ✅ {name}")
    else:
        FAILED += 1
        msg = f"  ❌ {name}" + (f" — {detail}" if detail else "")
        print(msg)
        ERRORS.append(msg)


# ============================================================
# 1. ContractGeneratorTool
# ============================================================
async def test_contract_generator():
    print("\n" + "=" * 60)
    print("1. ContractGeneratorTool 测试")
    print("=" * 60)

    # 1.1 导入和初始化
    try:
        from src.tools.contract_generator import ContractGeneratorTool
        report("导入 ContractGeneratorTool", True)
    except Exception as e:
        report("导入 ContractGeneratorTool", False, str(e))
        return

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = ContractGeneratorTool(output_dir=tmpdir)
            report("初始化 ContractGeneratorTool", True)

            # 1.2 list_templates
            result = await tool.execute("list_templates", {})
            ok = result.is_success and result.data.get("templates") is not None
            count = len(result.data.get("templates", []))
            report(f"list_templates 返回 {count} 种模板", ok and count == 4,
                   f"expected 4, got {count}" if count != 4 else "")

            # 1.3 generate_contract — 租赁合同
            result = await tool.execute("generate_contract", {
                "contract_type": "rental",
                "party_a": {"name": "张三", "address": "北京市朝阳区", "id_number": "110101199001011234"},
                "party_b": {"name": "李四", "address": "北京市海淀区", "id_number": "110102199201021234"},
                "terms": {
                    "property_location": "北京市朝阳区XX小区",
                    "start_date": "2026年4月1日",
                    "end_date": "2027年3月31日",
                    "duration": "12",
                    "rent": "5000",
                    "deposit": "10000",
                    "payment_method": "银行转账",
                },
                "title": "房屋租赁合同",
            })
            docx_path = result.data.get("file_path", "")
            docx_exists = Path(docx_path).exists() if docx_path else False
            docx_size = Path(docx_path).stat().st_size if docx_exists else 0
            report("generate_contract 生成租赁合同", result.is_success and docx_exists and docx_size > 0,
                   f"status={result.status}, exists={docx_exists}, size={docx_size}")

            # 1.4 customize_clause
            result = await tool.execute("customize_clause", {
                "contract_type": "rental",
                "clause_name": "特别约定条款",
                "content": "甲乙双方特别约定：{{ terms.special_terms | default('无') }}。",
            })
            report("customize_clause 自定义条款", result.is_success)

            # 1.5 export_contract — 导出为txt
            if docx_path and docx_exists:
                result = await tool.execute("export_contract", {
                    "input_file": docx_path,
                    "format": "txt",
                })
                txt_path = result.data.get("file_path", "")
                txt_exists = Path(txt_path).exists() if txt_path else False
                report("export_contract 导出 txt", result.is_success and txt_exists,
                       f"status={result.status}")
            else:
                report("export_contract 导出 txt", False, "无可用的 DOCX 文件")

            # 1.6 错误处理 — 缺少必需参数
            result = await tool.execute("generate_contract", {})
            report("缺少必需参数 → ERROR", not result.is_success)

            # 1.7 错误处理 — 未知 action
            result = await tool.execute("unknown_action", {})
            report("未知 action → ERROR", not result.is_success)

    except Exception as e:
        report("ContractGeneratorTool 运行测试", False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============================================================
# 2. FinancialReportTool
# ============================================================
async def test_financial_report():
    print("\n" + "=" * 60)
    print("2. FinancialReportTool 测试")
    print("=" * 60)

    try:
        from src.tools.financial_report import FinancialReportTool
        report("导入 FinancialReportTool", True)
    except Exception as e:
        report("导入 FinancialReportTool", False, str(e))
        return

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = FinancialReportTool(output_dir=tmpdir)
            report("初始化 FinancialReportTool", True)

            # 2.1 generate_balance_sheet
            result = await tool.execute("generate_balance_sheet", {
                "company_name": "测试科技有限公司",
                "date": "2025-12-31",
                "assets": {
                    "流动资产": {"货币资金": 1000000, "应收账款": 500000, "存货": 300000},
                    "非流动资产": {"固定资产": 2000000, "无形资产": 300000},
                },
                "liabilities": {
                    "流动负债": {"应付账款": 300000, "短期借款": 200000},
                    "非流动负债": {"长期借款": 500000},
                },
                "equity": {"实收资本": 2000000, "资本公积": 200000, "留存收益": 600000},
            })
            bs_path = result.data.get("file_path", "")
            bs_exists = Path(bs_path).exists() if bs_path else False
            report("generate_balance_sheet 资产负债表", result.is_success and bs_exists,
                   f"status={result.status}")

            # 2.2 generate_income_statement
            result = await tool.execute("generate_income_statement", {
                "company_name": "测试科技有限公司",
                "period": "2025年度",
                "revenue": {"主营业务收入": 5000000, "其他业务收入": 200000},
                "costs": {
                    "主营业务成本": 3000000,
                    "销售费用": 300000,
                    "管理费用": 400000,
                    "财务费用": 50000,
                    "研发费用": 200000,
                },
                "taxes": 250000,
            })
            is_path = result.data.get("file_path", "")
            is_exists = Path(is_path).exists() if is_path else False
            report("generate_income_statement 利润表", result.is_success and is_exists,
                   f"status={result.status}")

            # 2.3 generate_cash_flow
            result = await tool.execute("generate_cash_flow", {
                "company_name": "测试科技有限公司",
                "period": "2025年度",
                "operating": {
                    "销售商品收到的现金": 4800000,
                    "购买商品支付的现金": 2800000,
                    "支付给职工的现金": 800000,
                    "支付的各项税费": 300000,
                },
                "investing": {
                    "购建固定资产支付的现金": 500000,
                    "处置固定资产收到的现金": 100000,
                },
                "financing": {
                    "取得借款收到的现金": 1000000,
                    "偿还债务支付的现金": 500000,
                },
            })
            cf_path = result.data.get("file_path", "")
            cf_exists = Path(cf_path).exists() if cf_path else False
            report("generate_cash_flow 现金流量表", result.is_success and cf_exists,
                   f"status={result.status}")

            # 2.4 financial_analysis
            result = await tool.execute("financial_analysis", {
                "data": {
                    "总资产": 4100000,
                    "总负债": 1000000,
                    "所有者权益": 3100000,
                    "流动资产": 1800000,
                    "流动负债": 500000,
                    "净利润": 1000000,
                    "营业收入": 5200000,
                },
            })
            report("financial_analysis 财务分析", result.is_success,
                   f"status={result.status}")

            # 2.5 export_report — 导出为csv
            if bs_path and bs_exists:
                result = await tool.execute("export_report", {
                    "input_file": bs_path,
                    "format": "csv",
                })
                csv_path = result.data.get("file_path", "")
                csv_exists = Path(csv_path).exists() if csv_path else False
                report("export_report 导出 csv", result.is_success and csv_exists,
                       f"status={result.status}")
            else:
                report("export_report 导出 csv", False, "无可用的 xlsx 文件")

            # 2.6 错误处理
            result = await tool.execute("generate_balance_sheet", {})
            report("缺少必需参数 → ERROR", not result.is_success)

            result = await tool.execute("unknown_action", {})
            report("未知 action → ERROR", not result.is_success)

    except Exception as e:
        report("FinancialReportTool 运行测试", False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============================================================
# 3. ResumeBuilderTool
# ============================================================
async def test_resume_builder():
    print("\n" + "=" * 60)
    print("3. ResumeBuilderTool 测试")
    print("=" * 60)

    try:
        from src.tools.resume_builder import ResumeBuilderTool
        report("导入 ResumeBuilderTool", True)
    except Exception as e:
        report("导入 ResumeBuilderTool", False, str(e))
        return

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = ResumeBuilderTool(output_dir=tmpdir)
            report("初始化 ResumeBuilderTool", True)

            # 3.1 list_templates
            result = await tool.execute("list_templates", {})
            ok = result.is_success and result.data.get("templates") is not None
            count = len(result.data.get("templates", []))
            report(f"list_templates 返回 {count} 种模板", ok and count == 5,
                   f"expected 5, got {count}" if count != 5 else "")

            # 3.2 generate_resume — minimal 模板
            result = await tool.execute("generate_resume", {
                "template": "minimal",
                "personal_info": {
                    "name": "王五",
                    "phone": "13900139000",
                    "email": "wangwu@test.com",
                    "address": "上海市浦东新区",
                },
                "education": [{
                    "school": "复旦大学",
                    "degree": "本科",
                    "major": "软件工程",
                    "start_date": "2018.09",
                    "end_date": "2022.06",
                }],
                "experience": [{
                    "company": "阿里巴巴",
                    "title": "软件工程师",
                    "start_date": "2022.07",
                    "end_date": "至今",
                    "description": "负责电商平台后端开发",
                }],
                "skills": ["Python", "Java", "MySQL", "Redis"],
                "summary": "3年后端开发经验",
            })
            resume_path = result.data.get("file_path", "")
            resume_exists = Path(resume_path).exists() if resume_path else False
            resume_size = Path(resume_path).stat().st_size if resume_exists else 0
            report("generate_resume minimal 模板", result.is_success and resume_exists and resume_size > 0,
                   f"status={result.status}, exists={resume_exists}, size={resume_size}")

            # 3.3 export_resume — 导出为html
            if resume_path and resume_exists:
                result = await tool.execute("export_resume", {
                    "input_file": resume_path,
                    "format": "html",
                })
                html_path = result.data.get("file_path", "")
                html_exists = Path(html_path).exists() if html_path else False
                report("export_resume 导出 html", result.is_success and html_exists,
                       f"status={result.status}")
            else:
                report("export_resume 导出 html", False, "无可用的 DOCX 文件")

            # 3.4 错误处理 — 缺少姓名
            result = await tool.execute("generate_resume", {
                "template": "minimal",
                "personal_info": {},
                "education": [],
                "experience": [],
                "skills": [],
            })
            report("缺少姓名 → ERROR", not result.is_success)

            # 3.5 未知 action
            result = await tool.execute("unknown_action", {})
            report("未知 action → ERROR", not result.is_success)

    except Exception as e:
        report("ResumeBuilderTool 运行测试", False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============================================================
# 4. MindMapTool
# ============================================================
async def test_mind_map():
    print("\n" + "=" * 60)
    print("4. MindMapTool 测试")
    print("=" * 60)

    try:
        from src.tools.mind_map import MindMapTool
        report("导入 MindMapTool", True)
    except Exception as e:
        report("导入 MindMapTool", False, str(e))
        return

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tool = MindMapTool(output_dir=tmpdir)
            report("初始化 MindMapTool", True)

            # 4.1 generate_mindmap — 嵌套结构
            result = await tool.execute("generate_mindmap", {
                "title": "Python学习路线",
                "nodes": [
                    {
                        "name": "基础语法",
                        "children": [
                            {"name": "变量与类型"},
                            {"name": "控制流"},
                            {"name": "函数"},
                        ]
                    },
                    {
                        "name": "进阶知识",
                        "children": [
                            {"name": "面向对象"},
                            {"name": "装饰器"},
                            {"name": "生成器"},
                        ]
                    },
                    {
                        "name": "Web开发",
                        "children": ["Flask", "Django", "FastAPI"],
                    },
                ],
            })
            svg_path = result.data.get("output_path", "")
            svg_exists = Path(svg_path).exists() if svg_path else False
            report("generate_mindmap 生成思维导图", result.is_success and svg_exists,
                   f"status={result.status}, exists={svg_exists}")

            # 验证 SVG 内容有效
            if svg_exists:
                content = Path(svg_path).read_text(encoding="utf-8")
                has_svg_tag = "<svg" in content
                has_content = "Python" in content or len(content) > 100
                report("SVG 文件内容有效", has_svg_tag and has_content,
                       f"has_svg={has_svg_tag}, has_content={has_content}, size={len(content)}")
            else:
                report("SVG 文件内容有效", False, "SVG 文件不存在")

            # 4.2 text_to_mindmap — 从Markdown生成
            md_text = """# 项目管理
## 规划阶段
- 需求分析
- 可行性研究
## 执行阶段
- 开发
- 测试
## 收尾阶段
- 部署上线
- 项目总结
"""
            result = await tool.execute("text_to_mindmap", {
                "text": md_text,
            })
            md_svg_path = result.data.get("output_path", "")
            md_svg_exists = Path(md_svg_path).exists() if md_svg_path else False
            report("text_to_mindmap 从 Markdown 生成", result.is_success and md_svg_exists,
                   f"status={result.status}")

            # 4.3 export_mindmap — 导出为 SVG（复制）
            if svg_path and svg_exists:
                result = await tool.execute("export_mindmap", {
                    "input_file": svg_path,
                    "format": "svg",
                })
                export_path = result.data.get("output_path", result.data.get("file_path", ""))
                export_exists = Path(export_path).exists() if export_path else False
                report("export_mindmap 导出 svg", result.is_success and export_exists,
                       f"status={result.status}")
            else:
                report("export_mindmap 导出 svg", False, "无可用的 SVG 文件")

            # 4.4 export_mindmap — 导出为 HTML
            if svg_path and svg_exists:
                result = await tool.execute("export_mindmap", {
                    "input_file": svg_path,
                    "format": "html",
                })
                html_path = result.data.get("output_path", result.data.get("file_path", ""))
                html_exists = Path(html_path).exists() if html_path else False
                report("export_mindmap 导出 html", result.is_success and html_exists,
                       f"status={result.status}")
            else:
                report("export_mindmap 导出 html", False, "无可用的 SVG 文件")

            # 4.5 错误处理 — 缺少必需参数
            result = await tool.execute("generate_mindmap", {})
            report("缺少必需参数 → ERROR", not result.is_success)

            # 4.6 未知 action
            result = await tool.execute("unknown_action", {})
            report("未知 action → ERROR", not result.is_success)

    except Exception as e:
        report("MindMapTool 运行测试", False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============================================================
# 5. tools.json + registry 集成测试
# ============================================================
def test_registry():
    print("\n" + "=" * 60)
    print("5. tools.json + Registry 集成测试")
    print("=" * 60)

    try:
        from src.tools.registry import ToolRegistry
        report("导入 ToolRegistry", True)
    except Exception as e:
        report("导入 ToolRegistry", False, str(e))
        return

    try:
        registry = ToolRegistry()
        config_path = PROJECT_ROOT / "config" / "tools.json"
        report(f"tools.json 存在", config_path.exists())

        registry.load_config(config_path)

        # 检查 4 个工具是否在配置中
        target_tools = ["contract_generator", "financial_report", "resume_builder", "mind_map"]
        for tn in target_tools:
            in_config = tn in registry._tool_configs
            report(f"{tn} 在 tools.json 配置中", in_config)

        # auto_discover（非懒加载，立即实例化）
        registry.auto_discover(lazy=False)

        for tn in target_tools:
            tool = registry.get_tool(tn)
            loaded = tool is not None
            report(f"{tn} 可通过 registry 加载", loaded,
                   "" if loaded else "get_tool 返回 None")

        # 检查 schemas
        schemas = registry.get_all_schemas()
        schema_func_names = {s["function"]["name"] for s in schemas}
        expected_funcs = [
            "contract_generator_generate_contract",
            "contract_generator_list_templates",
            "financial_report_generate_balance_sheet",
            "financial_report_financial_analysis",
            "resume_builder_generate_resume",
            "resume_builder_list_templates",
            "mind_map_generate_mindmap",
            "mind_map_text_to_mindmap",
        ]
        for fn in expected_funcs:
            report(f"Schema 包含 {fn}", fn in schema_func_names)

    except Exception as e:
        report("Registry 集成测试", False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


# ============================================================
# 主入口
# ============================================================
async def main():
    print("=" * 60)
    print("  Batch 6 工具综合测试")
    print("  合同生成器 | 财务报告 | 简历生成器 | 思维导图")
    print("=" * 60)

    await test_contract_generator()
    await test_financial_report()
    await test_resume_builder()
    await test_mind_map()
    test_registry()

    # 汇总
    total = PASSED + FAILED
    print("\n" + "=" * 60)
    print(f"  测试汇总: {total} 个测试")
    print(f"  ✅ 通过: {PASSED}")
    print(f"  ❌ 失败: {FAILED}")
    if ERRORS:
        print("\n  失败详情:")
        for err in ERRORS:
            print(f"    {err}")
    print("=" * 60)

    if FAILED > 0:
        print("\n❌ 整体结果: FAIL")
        sys.exit(1)
    else:
        print("\n✅ 整体结果: PASS")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
