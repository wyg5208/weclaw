"""TaskAnalyzer 测试"""

import os
import sys
import unittest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.todo_storage import TodoStorage, Todo, TaskCategory, TimeFrame, TodoStatus
from src.core.task_analyzer import TaskAnalyzer


class TestTaskAnalyzer(unittest.TestCase):
    """TaskAnalyzer 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_analyzer.db"
        self.storage = TodoStorage(self.db_path)
        self.analyzer = TaskAnalyzer(self.db_path)
        self.today = datetime.now().strftime("%Y-%m-%d")

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_analyzer_initialization(self):
        """测试分析器初始化"""
        print("\n[TEST] Analyzer Initialization")
        self.assertIsNotNone(self.analyzer)
        print("  [OK] Analyzer initialized")
        print("  [PASS] Initialization")

    def test_analyze_overdue(self):
        """测试过期分析"""
        print("\n[TEST] Overdue Analysis")
        todo = Todo(
            title="Overdue Task",
            category=TaskCategory.WORK,
            priority=1,
            deadline=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
            status=TodoStatus.PENDING,
        )
        self.storage.create_todo(todo)
        
        # 通过 analyze_and_recommend 测试
        async def run():
            return await self.analyzer.analyze_and_recommend(self.today)
        
        result = asyncio.run(run())
        overdue_recs = [r for r in result["recommendations"] if r.get("source") == "todo_overdue"]
        self.assertGreaterEqual(len(overdue_recs), 1)
        print(f"  [OK] Found {len(overdue_recs)} overdue recommendations")
        print("  [PASS] Overdue analysis")

    def test_analyze_recommendations(self):
        """测试分析生成推荐"""
        print("\n[TEST] Analyze Recommendations")
        todo = Todo(
            title="Analysis Test Task",
            category=TaskCategory.WORK,
            priority=1,
        )
        self.storage.create_todo(todo)
        
        async def run():
            return await self.analyzer.analyze_and_recommend(self.today)
        
        result = asyncio.run(run())
        
        self.assertIn("date", result)
        self.assertIn("recommendations", result)
        self.assertEqual(result["date"], self.today)
        print(f"  [OK] Analysis date: {result['date']}")
        print(f"  [OK] Recommendations: {len(result['recommendations'])}")
        print("  [PASS] Analyze recommendations")

    def test_full_analysis(self):
        """测试完整分析流程"""
        print("\n[TEST] Full Analysis")
        todo = Todo(
            title="Full Test Task",
            category=TaskCategory.WORK,
            priority=1,
        )
        self.storage.create_todo(todo)
        
        async def run():
            return await self.analyzer.analyze_and_recommend(self.today)
        
        result = asyncio.run(run())
        
        self.assertIn("date", result)
        self.assertIn("recommendations", result)
        self.assertEqual(result["date"], self.today)
        print(f"  [OK] Analysis date: {result['date']}")
        print(f"  [OK] Recommendations: {len(result['recommendations'])}")
        print("  [PASS] Full analysis")


def run_tests():
    print("=" * 60)
    print("[TEST SUITE] TaskAnalyzer Tests")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestTaskAnalyzer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("[PASS] All tests passed!")
    else:
        print(f"[FAIL] {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
