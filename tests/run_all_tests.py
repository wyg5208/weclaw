"""WinClaw 完整测试套件运行器。

测试套件：
1. test_registry_unit.py     - 工具注册器单元测试
2. test_tool_exposure.py     - 工具暴露引擎测试
3. test_tools_smoke.py       - 核心工具冒烟测试
4. test_prompts_intent.py    - 意图识别与工具映射测试

运行方式：
    python tests/run_all_tests.py           # 运行所有测试
    python tests/run_all_tests.py --unit    # 只运行单元测试
    python tests/run_all_tests.py --smoke   # 只运行冒烟测试
    python tests/run_all_tests.py --verbose # 详细输出

作者：WinClaw 开发团队
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ============================================================================
# 配置
# ============================================================================

TEST_SUITES = {
    "registry": {
        "name": "工具注册器单元测试",
        "file": "test_registry_unit.py",
        "description": "测试 ToolRegistry 初始化、注册、Schema 生成、函数名解析",
    },
    "exposure": {
        "name": "工具暴露引擎测试",
        "file": "test_tool_exposure.py",
        "description": "测试渐进式暴露、层级判定、优先级标注、失败升级",
    },
    "smoke": {
        "name": "核心工具冒烟测试",
        "file": "test_tools_smoke.py",
        "description": "测试 Shell、File、Screen、Calculator、DateTime 等工具",
    },
    "intent": {
        "name": "意图识别与工具映射测试",
        "file": "test_prompts_intent.py",
        "description": "测试 INTENT_TOOL_MAPPING、INTENT_PRIORITY_MAP 一致性",
    },
}

ALL_SUITES = list(TEST_SUITES.keys())


# ============================================================================
# 测试运行
# ============================================================================

def run_test_suite(suite_key: str, verbose: bool = False) -> tuple[bool, float]:
    """运行单个测试套件。"""
    suite = TEST_SUITES[suite_key]
    test_file = Path(__file__).parent / suite["file"]

    if not test_file.exists():
        print(f"  ⚠️  测试文件不存在: {test_file}")
        return False, 0.0

    print(f"\n运行: {suite['name']}")
    print(f"文件: {suite['file']}")
    print(f"说明: {suite['description']}")
    print("-" * 50)

    start_time = time.time()

    # 运行测试
    cmd = [sys.executable, str(test_file)]
    if verbose:
        cmd.append("--verbose")

    result = subprocess.run(
        cmd,
        cwd=str(Path(__file__).parent.parent),
        capture_output=False,
    )

    elapsed = time.time() - start_time
    success = result.returncode == 0

    return success, elapsed


def run_all_tests(suites: list = None, verbose: bool = False) -> dict:
    """运行所有测试套件。"""
    if suites is None:
        suites = ALL_SUITES

    print("=" * 70)
    print("  WinClaw 完整测试套件")
    print("=" * 70)
    print(f"  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  测试套件: {len(suites)} 个")
    print("=" * 70)

    results = {}
    total_time = 0
    passed_count = 0
    failed_count = 0

    for i, suite_key in enumerate(suites):
        print(f"\n[{i+1}/{len(suites)}] ", end="")

        success, elapsed = run_test_suite(suite_key, verbose)
        results[suite_key] = {
            "success": success,
            "elapsed": elapsed,
        }
        total_time += elapsed

        if success:
            passed_count += 1
            status = "✅ 通过"
        else:
            failed_count += 1
            status = "❌ 失败"

        print(f"\n[{suite_key}] {status} ({elapsed:.2f}秒)")

    return {
        "results": results,
        "total_time": total_time,
        "passed": passed_count,
        "failed": failed_count,
    }


def print_summary(results: dict) -> None:
    """打印测试摘要。"""
    print("\n" + "=" * 70)
    print("  测试结果摘要")
    print("=" * 70)

    for key, result in results["results"].items():
        suite = TEST_SUITES[key]
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {suite['name']:<20} {result['elapsed']:>6.2f}秒")

    print("-" * 70)
    print(f"  总计: {len(results['results'])} 个测试套件")
    print(f"  通过: {results['passed']} 个")
    print(f"  失败: {results['failed']} 个")
    print(f"  总耗时: {results['total_time']:.2f}秒")
    print("=" * 70)

    if results["failed"] == 0:
        print("\n  🎉 所有测试通过！")
    else:
        print(f"\n  ⚠️  {results['failed']} 个测试套件失败")


# ============================================================================
# CLI
# ============================================================================

def parse_args():
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="WinClaw 完整测试套件运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python tests/run_all_tests.py              # 运行所有测试
  python tests/run_all_tests.py --unit       # 只运行单元测试
  python tests/run_all_tests.py --smoke      # 只运行冒烟测试
  python tests/run_all_tests.py registry     # 只运行注册器测试
  python tests/run_all_tests.py --list       # 列出所有测试套件

可用测试套件:
  registry  - 工具注册器单元测试
  exposure  - 工具暴露引擎测试
  smoke     - 核心工具冒烟测试
  intent    - 意图识别与工具映射测试
        """,
    )

    parser.add_argument(
        "--unit",
        action="store_true",
        help="只运行单元测试 (registry + exposure)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="只运行冒烟测试 (smoke)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有测试套件",
    )
    parser.add_argument(
        "suites",
        nargs="*",
        help="指定要运行的测试套件",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # 列出测试套件
    if args.list:
        print("=" * 50)
        print("  可用测试套件")
        print("=" * 50)
        for key, suite in TEST_SUITES.items():
            print(f"\n  {key}:")
            print(f"    名称: {suite['name']}")
            print(f"    文件: {suite['file']}")
            print(f"    说明: {suite['description']}")
        print("\n" + "=" * 50)
        return

    # 确定要运行的测试套件
    suites = None
    if args.unit:
        suites = ["registry", "exposure", "intent"]
    elif args.smoke:
        suites = ["smoke"]
    elif args.suites:
        # 验证套件名称
        invalid = [s for s in args.suites if s not in TEST_SUITES]
        if invalid:
            print(f"⚠️  未知的测试套件: {invalid}")
            print(f"可用套件: {list(TEST_SUITES.keys())}")
            sys.exit(1)
        suites = args.suites

    # 运行测试
    results = run_all_tests(suites=suites, verbose=args.verbose)
    print_summary(results)

    # 退出码
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
