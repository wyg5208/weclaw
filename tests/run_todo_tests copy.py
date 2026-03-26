"""待办事项与每日任务系统测试套件运行器 (ASCII版本)

使用方法：
    python tests/run_todo_tests.py              # 运行所有测试
    python tests/run_todo_tests.py --storage    # 仅运行存储层测试
    python tests/run_todo_tests.py --tool       # 仅运行工具测试

测试模块：
1. test_todo_storage.py      - TodoStorage 数据存储层
2. test_todo_tool.py         - TodoTool 待办事项工具 (10 Actions)
3. test_daily_task_tool.py   - DailyTaskTool 每日任务工具 (10 Actions)
4. test_task_analyzer.py      - TaskAnalyzer 智能分析引擎
5. test_daily_task_scheduler.py - DailyTaskScheduler 任务调度器
6. test_todo_integration.py   - 端到端集成测试
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def print_header():
    """打印测试套件标题"""
    print("\n" + "=" * 70)
    print("[TEST SUITE] 待办事项与每日任务系统")
    print("=" * 70)


def run_test_module(module_name: str) -> bool:
    """运行单个测试模块"""
    print(f"\n{'=' * 70}")
    print(f"[RUN] {module_name}")
    print("=" * 70)
    
    module_path = PROJECT_ROOT / "tests" / f"{module_name}.py"
    
    if not module_path.exists():
        print(f"[ERROR] Module not found: {module_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(module_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            encoding='utf-8',
            errors='replace',
        )
        
        # 输出结果
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return False


def run_all_tests():
    """运行所有测试"""
    modules = [
        ("test_todo_storage", "Data Storage"),
        ("test_todo_tool", "TodoTool"),
        ("test_daily_task_tool", "DailyTaskTool"),
        ("test_task_analyzer", "TaskAnalyzer"),
        ("test_daily_task_scheduler", "DailyTaskScheduler"),
        ("test_todo_integration", "Integration"),
    ]
    
    print_header()
    
    results = {}
    total = len(modules)
    passed = 0
    
    for i, (module, description) in enumerate(modules, 1):
        print(f"\n[{i}/{total}] Progress")
        print("-" * 70)
        
        success = run_test_module(module)
        results[module] = success
        if success:
            passed += 1
        
        print(f"\n[{'PASS' if success else 'FAIL'}] {module}")
    
    # Summary
    print("\n" + "=" * 70)
    print("[SUMMARY]")
    print("=" * 70)
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Rate: {passed/total*100:.1f}%")
    print()
    
    for module, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {status} {module}")
    
    print("=" * 70)
    return passed == total


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Todo System Test Suite")
    parser.add_argument(
        "--module", "-m",
        choices=["storage", "tool", "daily_task", "analyzer", "scheduler", "integration"],
        help="Specify test module"
    )
    
    args = parser.parse_args()
    
    # Module mapping
    module_map = {
        "storage": "test_todo_storage",
        "tool": "test_todo_tool",
        "daily_task": "test_daily_task_tool",
        "analyzer": "test_task_analyzer",
        "scheduler": "test_daily_task_scheduler",
        "integration": "test_todo_integration",
    }
    
    if args.module:
        module_name = module_map[args.module]
        success = run_test_module(module_name)
        sys.exit(0 if success else 1)
    else:
        success = run_all_tests()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
