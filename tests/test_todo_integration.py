"""待办事项与每日任务系统端到端集成测试"""

import os
import sys
import unittest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.todo import TodoTool
from src.tools.daily_task import DailyTaskTool
from src.tools.todo_storage import TodoStorage, Todo, TaskCategory, TimeFrame


class TestTodoEndToEnd(unittest.TestCase):
    """端到端测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_e2e.db"
        self.todo_tool = TodoTool(str(self.db_path))
        self.daily_tool = DailyTaskTool(str(self.db_path))
        self.storage = TodoStorage(self.db_path)
        self.today = datetime.now().strftime("%Y-%m-%d")

    def tearDown(self):
        try:
            if self.todo_tool._storage:
                pass  # storage will be cleaned up
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    async def _execute(self, tool, action, params):
        return await tool.execute(action, params)

    def test_create_and_list(self):
        """测试创建和列出"""
        print("\n[TEST] Create and List")
        
        result = asyncio.run(self._execute(self.todo_tool, "create_todo", {
            "title": "E2E Test Task",
            "category": "work",
            "priority": 1,
        }))
        self.assertTrue(result.is_success)
        print(f"  [OK] Created: ID={result.data.get('id')}")
        
        result = asyncio.run(self._execute(self.todo_tool, "list_todos", {}))
        self.assertTrue(result.is_success)
        print(f"  [OK] Listed: {len(result.data)} tasks")
        print("  [PASS] Create and list")

    def test_complete_workflow(self):
        """测试完成工作流"""
        print("\n[TEST] Complete Workflow")
        
        result = asyncio.run(self._execute(self.todo_tool, "create_todo", {
            "title": "Workflow Test",
        }))
        todo_id = result.data.get("id")
        
        result = asyncio.run(self._execute(self.todo_tool, "complete_todo", {
            "id": todo_id,
            "completion_note": "Done",
        }))
        self.assertTrue(result.is_success)
        print("  [OK] Completed")
        
        result = asyncio.run(self._execute(self.todo_tool, "get_todo", {"id": todo_id}))
        self.assertEqual(result.data.get("status"), "completed")
        print("  [OK] Status verified")
        print("  [PASS] Complete workflow")

    def test_daily_task_workflow(self):
        """测试每日任务工作流"""
        print("\n[TEST] Daily Task Workflow")
        
        result = asyncio.run(self._execute(self.daily_tool, "add_daily_task", {
            "title": "Daily Test Task",
            "priority": 1,
        }))
        self.assertTrue(result.is_success)
        task_id = result.data.get("id")
        print(f"  [OK] Added: ID={task_id}")
        
        result = asyncio.run(self._execute(self.daily_tool, "get_daily_tasks", {
            "date": self.today,
        }))
        self.assertTrue(result.is_success)
        print(f"  [OK] Got: {len(result.data)} tasks")
        print("  [PASS] Daily task workflow")


def run_tests():
    print("=" * 60)
    print("[TEST SUITE] End-to-End Integration Tests")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestTodoEndToEnd)
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
