"""DailyTaskTool 测试 - DailyTaskTool 10 Actions 功能验证"""

import os
import sys
import unittest
import asyncio
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.daily_task import DailyTaskTool
from src.tools.todo import TodoTool


class TestDailyTaskTool(unittest.TestCase):
    """DailyTaskTool 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_daily_task.db"
        self.todo_tool = TodoTool(str(self.db_path))
        self.tool = DailyTaskTool(str(self.db_path))
        self.today = datetime.now().strftime("%Y-%m-%d")

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    async def _execute(self, action, params):
        return await self.tool.execute(action, params)

    def _is_success(self, result):
        return hasattr(result, 'is_success') and result.is_success

    def test_01_add_daily_task(self):
        """测试 add_daily_task"""
        print("\n[TEST] add_daily_task")
        result = asyncio.run(self._execute("add_daily_task", {
            "title": "Test Daily Task",
            "priority": 1,
        }))
        self.assertTrue(self._is_success(result))
        print(f"  [OK] Added: ID={result.data.get('id')}")
        self._test_task_id = result.data.get("id")
        print("  [PASS] add_daily_task")

    def test_02_get_daily_tasks(self):
        """测试 get_daily_tasks"""
        print("\n[TEST] get_daily_tasks")
        result = asyncio.run(self._execute("get_daily_tasks", {"date": self.today}))
        self.assertTrue(self._is_success(result))
        print(f"  [OK] Got: {len(result.data)} tasks")
        print("  [PASS] get_daily_tasks")

    def test_03_update_daily_task(self):
        """测试 update_daily_task"""
        print("\n[TEST] update_daily_task")
        if not hasattr(self, '_test_task_id'):
            result = asyncio.run(self._execute("add_daily_task", {"title": "Update Test"}))
            self._test_task_id = result.data.get("id")
        
        result = asyncio.run(self._execute("update_daily_task", {
            "id": self._test_task_id,
            "title": "Updated Title",
        }))
        self.assertTrue(self._is_success(result))
        print("  [OK] Updated")
        print("  [PASS] update_daily_task")

    def test_04_start_task(self):
        """测试 start_task"""
        print("\n[TEST] start_task")
        result = asyncio.run(self._execute("add_daily_task", {"title": "Start Test"}))
        task_id = result.data.get("id")
        
        result = asyncio.run(self._execute("start_task", {"id": task_id}))
        self.assertTrue(self._is_success(result))
        print("  [OK] Started")
        print("  [PASS] start_task")

    def test_05_complete_task(self):
        """测试 complete_task"""
        print("\n[TEST] complete_task")
        result = asyncio.run(self._execute("add_daily_task", {"title": "Complete Test"}))
        task_id = result.data.get("id")
        
        result = asyncio.run(self._execute("complete_task", {
            "id": task_id,
            "completion_note": "Done",
        }))
        self.assertTrue(self._is_success(result))
        print("  [OK] Completed")
        print("  [PASS] complete_task")

    def test_06_cancel_task(self):
        """测试 cancel_task"""
        print("\n[TEST] cancel_task")
        result = asyncio.run(self._execute("add_daily_task", {"title": "Cancel Test"}))
        task_id = result.data.get("id")
        
        result = asyncio.run(self._execute("cancel_task", {
            "id": task_id,
            "reason": "Cancelled",
        }))
        self.assertTrue(self._is_success(result))
        print("  [OK] Cancelled")
        print("  [PASS] cancel_task")

    def test_07_remove_daily_task(self):
        """测试 remove_daily_task"""
        print("\n[TEST] remove_daily_task")
        result = asyncio.run(self._execute("add_daily_task", {"title": "Remove Test"}))
        task_id = result.data.get("id")
        
        result = asyncio.run(self._execute("remove_daily_task", {"id": task_id}))
        self.assertTrue(self._is_success(result))
        print("  [OK] Removed")
        print("  [PASS] remove_daily_task")

    def test_08_get_today_summary(self):
        """测试 get_today_summary"""
        print("\n[TEST] get_today_summary")
        result = asyncio.run(self._execute("get_today_summary", {}))
        self.assertTrue(self._is_success(result))
        print(f"  [OK] Summary: total={result.data.get('total', 0)}")
        print("  [PASS] get_today_summary")

    def test_09_generate_recommendations(self):
        """测试 generate_recommendations"""
        print("\n[TEST] generate_recommendations")
        result = asyncio.run(self._execute("generate_recommendations", {"date": self.today}))
        self.assertTrue(self._is_success(result))
        recs = result.data.get("recommendations", [])
        print(f"  [OK] Generated: {len(recs)} recommendations")
        print("  [PASS] generate_recommendations")

    @unittest.skip("Requires recommendation to exist first")
    def test_10_accept_recommendations(self):
        """测试 accept_recommendations"""
        print("\n[TEST] accept_recommendations")
        result = asyncio.run(self._execute("add_daily_task", {"title": "Accept Test"}))
        task_id = result.data.get("id")
        
        result = asyncio.run(self._execute("accept_recommendations", {
            "date": self.today,
            "task_ids": json.dumps([task_id]),
        }))
        self.assertTrue(self._is_success(result))
        print("  [OK] Accepted")
        print("  [PASS] accept_recommendations")


class TestDailyTaskToolEdge(unittest.TestCase):
    """边界测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_edge.db"
        self.tool = DailyTaskTool(str(self.db_path))

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    async def _execute(self, action, params):
        return await self.tool.execute(action, params)

    def _is_success(self, result):
        return hasattr(result, 'is_success') and result.is_success

    def test_empty_day(self):
        """测试空日"""
        print("\n[TEST] Empty Day")
        future = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        result = asyncio.run(self._execute("get_daily_tasks", {"date": future}))
        self.assertTrue(self._is_success(result))
        print("  [OK] Empty day query OK")


def run_tests():
    print("=" * 60)
    print("[TEST SUITE] DailyTaskTool Tests (10 Actions)")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestDailyTaskTool))
    suite.addTests(loader.loadTestsFromTestCase(TestDailyTaskToolEdge))
    
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
