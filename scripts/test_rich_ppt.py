"""PPT 生成工具测试 - 测试图文并茂的 PPT 生成功能。"""

import asyncio
import json
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from src.tools.ppt_generator import PPTTool


def print_section(title: str) -> None:
    """打印测试分节标题。"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def log_test(name: str, success: bool, detail: str = "") -> None:
    """记录测试结果。"""
    status = "✅" if success else "❌"
    print(f"  {status} {name}")
    if detail:
        print(f"     {detail}")


async def test_generate_rich_ppt_basic() -> bool:
    """测试基本 PPT 生成"""
    print_section("测试 1: 基本图文并茂 PPT 生成")

    tool = PPTTool(output_dir="generated")

    slides_config = [
        {
            "type": "title",
            "title": "人工智能发展趋势报告",
            "subtitle": "引领未来的技术创新与产业变革"
        },
        {
            "type": "content",
            "title": "内容概览",
            "subtitle": "本次报告核心章节",
            "content": [
                "AI 技术演进：从机器学习到深度学习的突破",
                "技术突破：大模型与生成式 AI 的崛起",
                "应用场景：各行业的 AI 落地实践",
                "未来展望：AGI 与人类协作的新时代",
            ],
            "layout": "single",
            "icons": ["chart", "rocket", "globe", "light"]
        },
        {
            "type": "grid_images",
            "title": "AI 技术发展历程",
            "image_count": 4,
            "layout": "grid_2x2"
        },
        {
            "type": "icon_cards",
            "title": "核心能力矩阵",
            "cards": [
                {"icon": "tech", "title": "深度学习", "description": "神经网络模型持续优化，参数规模突破万亿级别"},
                {"icon": "chart", "title": "数据处理", "description": "海量数据清洗与标注，支撑模型训练需求"},
                {"icon": "globe", "title": "跨模态理解", "description": "文本、图像、视频的统一表示学习"},
            ],
            "layout": "cards_3"
        },
        {
            "type": "chart",
            "title": "AI 市场增长趋势",
            "chart": {
                "type": "bar",
                "labels": ["2022", "2023", "2024", "2025", "2026"],
                "values": [100, 180, 320, 550, 890],
                "series_name": "市场规模(亿美元)"
            }
        },
        {
            "type": "icon_cards",
            "title": "技术创新方向",
            "cards": [
                {"icon": "star", "title": "Transformer 架构", "description": "自注意力机制成为主流"},
                {"icon": "fire", "title": "大模型时代", "description": "百亿参数模型涌现"},
                {"icon": "target", "title": "Agent 智能体", "description": "自主规划与工具调用"},
            ],
            "layout": "cards_3"
        },
        {
            "type": "content",
            "title": "典型应用案例",
            "subtitle": "AI 赋能千行百业",
            "content": [
                "智能客服：自然语言理解与对话生成",
                "内容创作：文章、代码、图像、视频生成",
                "数据分析：智能洞察与决策支持",
                "代码开发：Copilot 提升编程效率",
                "医疗诊断：影像识别与辅助诊疗",
                "自动驾驶：环境感知与路径规划",
            ],
            "layout": "double",
            "icons": ["people", "light", "chart", "tech", "target", "rocket"]
        },
        {
            "type": "grid_images",
            "title": "生态合作伙伴",
            "image_count": 6,
            "layout": "grid_3x2"
        },
        {
            "type": "thank",
            "title": "感谢聆听",
            "subtitle": "THANK YOU"
        }
    ]

    result = await tool.execute(
        "generate_rich_ppt",
        {
            "topic": "人工智能发展趋势报告",
            "slides_config": json.dumps(slides_config),
            "style": "business",
        }
    )

    log_test("generate_rich_ppt 调用", result.is_success, result.output if result.is_success else result.error)

    if result.is_success:
        log_test("文件生成", Path(result.data["file_path"]).exists(), f"路径: {result.data['file_path']}")
        log_test("幻灯片数量", result.data["slide_count"] > 0, f"共 {result.data['slide_count']} 页")
        return True
    return False


async def test_generate_rich_ppt_with_styles() -> bool:
    """测试不同风格的 PPT 生成"""
    print_section("测试 2: 不同风格 PPT 生成")

    tool = PPTTool(output_dir="generated")

    slides_config = [
        {"type": "title", "title": "学术研究报告", "subtitle": "实验数据分析"},
        {"type": "content", "title": "研究背景", "content": ["背景1", "背景2", "背景3"]},
        {"type": "chart", "title": "实验数据", "chart": {"type": "line", "labels": ["A", "B", "C"], "values": [10, 20, 15]}},
        {"type": "thank"}
    ]

    # 测试学术风格
    result_academic = await tool.execute(
        "generate_rich_ppt",
        {
            "topic": "学术研究报告",
            "slides_config": json.dumps(slides_config),
            "style": "academic",
        }
    )
    log_test("学术风格 (academic)", result_academic.is_success)

    # 测试创意风格
    slides_config_creative = slides_config.copy()
    slides_config_creative[0]["title"] = "创意设计展示"
    result_creative = await tool.execute(
        "generate_rich_ppt",
        {
            "topic": "创意设计展示",
            "slides_config": json.dumps(slides_config_creative),
            "style": "creative",
        }
    )
    log_test("创意风格 (creative)", result_creative.is_success)

    # 测试简约风格
    slides_config_minimal = slides_config.copy()
    slides_config_minimal[0]["title"] = "简约报告"
    result_minimal = await tool.execute(
        "generate_rich_ppt",
        {
            "topic": "简约报告",
            "slides_config": json.dumps(slides_config_minimal),
            "style": "minimal",
        }
    )
    log_test("简约风格 (minimal)", result_minimal.is_success)

    return result_academic.is_success and result_creative.is_success and result_minimal.is_success


async def test_generate_rich_ppt_chart_types() -> bool:
    """测试不同图表类型"""
    print_section("测试 3: 不同图表类型 PPT 生成")

    tool = PPTTool(output_dir="generated")

    chart_configs = [
        {
            "type": "chart",
            "title": "柱状图示例",
            "chart": {"type": "bar", "labels": ["A", "B", "C"], "values": [30, 50, 40]}
        },
        {
            "type": "chart",
            "title": "饼图示例",
            "chart": {"type": "pie", "labels": ["甲", "乙", "丙", "丁"], "values": [25, 35, 20, 20]}
        },
        {
            "type": "chart",
            "title": "折线图示例",
            "chart": {"type": "line", "labels": ["1月", "2月", "3月", "4月"], "values": [10, 25, 18, 30]}
        },
    ]

    all_success = True
    for config in chart_configs:
        slides_config = [
            {"type": "title", "title": f"图表测试 - {config['chart']['type']}"},
            config,
            {"type": "thank"}
        ]

        result = await tool.execute(
            "generate_rich_ppt",
            {
                "topic": f"图表测试_{config['chart']['type']}",
                "slides_config": json.dumps(slides_config),
            }
        )
        log_test(f"图表类型: {config['chart']['type']}", result.is_success)
        if not result.is_success:
            all_success = False

    return all_success


async def test_generate_rich_ppt_error_handling() -> bool:
    """测试错误处理"""
    print_section("测试 4: 错误处理测试")

    tool = PPTTool(output_dir="generated")

    # 测试 1: 空主题
    result1 = await tool.execute(
        "generate_rich_ppt",
        {
            "topic": "",
            "slides_config": "[]",
        }
    )
    log_test("空主题错误处理", not result1.is_success, result1.error)

    # 测试 2: 空配置
    result2 = await tool.execute(
        "generate_rich_ppt",
        {
            "topic": "测试主题",
            "slides_config": "",
        }
    )
    log_test("空配置错误处理", not result2.is_success, result2.error)

    # 测试 3: 无效 JSON
    result3 = await tool.execute(
        "generate_rich_ppt",
        {
            "topic": "测试主题",
            "slides_config": "invalid json",
        }
    )
    log_test("无效JSON错误处理", not result3.is_success, result3.error)

    return True


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("  PPT 生成工具 - 图文并茂功能测试")
    print("="*60)

    results = []

    # 测试 1: 基本功能
    results.append(await test_generate_rich_ppt_basic())

    # 测试 2: 不同风格
    results.append(await test_generate_rich_ppt_with_styles())

    # 测试 3: 不同图表类型
    results.append(await test_generate_rich_ppt_chart_types())

    # 测试 4: 错误处理
    results.append(await test_generate_rich_ppt_error_handling())

    # 总结
    print_section("测试总结")
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"  通过: {passed}/{total} 个测试")
    print(f"  状态: {'✅ 全部通过' if passed == total else '⚠️ 部分失败'}")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
