"""待办事项工具测试 — TodoTool 10个Actions功能验证。

运行方式：
    python -m pytest tests/test_todo_tool.py -v
"""

import os
import sys
import unittest
import tempfile
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.todo import TodoTool


class TestTodoTool(unittest.TestCase):
    """待办事项工具测试"""

    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_todo_tool.db"
        self.tool = TodoTool(str(self.db_path))

    def tearDown(self):
        """测试后清理"""
        try:
            if self.tool._storage:
                self.tool._storage.close()
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    async def _execute(self, action, params):
        """执行工具动作"""
        return await self.tool.execute(action, params)

    def _is_success(self, result):
        """检查结果是否成功"""
        return hasattr(result, 'is_success') and result.is_success

    def test_01_create_todo(self):
        """测试 1: create_todo"""
        print("\n[TEST] create_todo")

        result = asyncio.run(self._execute("create_todo", {
            "title": "Test Todo",
            "description": "Test description",
            "category": "work",
            "time_frame": "week",
            "priority": 1,
        }))

        self.assertTrue(self._is_success(result), f"Create failed: {result.error if hasattr(result, 'error') else result}")
        self.assertIn("id", result.data, "Missing id in result")
        print(f"  [OK] Created: ID={result.data.get('id')}")
        self._test_todo_id = result.data.get("id")
        print("  [PASS] create_todo")

    def test_02_get_todo(self):
        """测试 2: get_todo"""
        print("\n[TEST] get_todo")

        if not hasattr(self, '_test_todo_id'):
            result = asyncio.run(self._execute("create_todo", {"title": "Get Test"}))
            self._test_todo_id = result.data.get("id")

        result = asyncio.run(self._execute("get_todo", {"id": self._test_todo_id}))

        self.assertTrue(self._is_success(result), f"Get failed: {result.error if hasattr(result, 'error') else result}")
        self.assertEqual(result.data.get("id"), self._test_todo_id)
        print(f"  [OK] Retrieved: {result.data.get('title')}")
        print("  [PASS] get_todo")

    def test_03_update_todo(self):
        """测试 3: update_todo"""
        print("\n[TEST] update_todo")

        result = asyncio.run(self._execute("create_todo", {
            "title": "Update Test",
            "category": "general",
            "priority": 3,
        }))
        todo_id = result.data.get("id")

        result = asyncio.run(self._execute("update_todo", {
            "id": todo_id,
            "title": "Updated Title",
            "priority": 1,
            "status": "in_progress",
        }))

        self.assertTrue(self._is_success(result), f"Update failed: {result.error if hasattr(result, 'error') else result}")

        get_result = asyncio.run(self._execute("get_todo", {"id": todo_id}))
        self.assertEqual(get_result.data.get("title"), "Updated Title")
        self.assertEqual(get_result.data.get("priority"), 1)
        self.assertEqual(get_result.data.get("status"), "in_progress")
        print("  [OK] Title updated")
        print("  [OK] Priority updated")
        print("  [OK] Status updated")
        print("  [PASS] update_todo")

    def test_04_list_todos(self):
        """测试 4: list_todos"""
        print("\n[TEST] list_todos")

        tasks = [
            {"title": "List-Work1", "category": "work", "priority": 1},
            {"title": "List-Work2", "category": "work", "priority": 2},
            {"title": "List-Study1", "category": "study", "priority": 1},
            {"title": "List-Health1", "category": "health", "priority": 3},
        ]
        for task in tasks:
            asyncio.run(self._execute("create_todo", task))

        result = asyncio.run(self._execute("list_todos", {"category": "work"}))
        self.assertTrue(self._is_success(result))
        self.assertEqual(len(result.data), 2)
        print(f"  [OK] Filter by work: {len(result.data)}")

        result = asyncio.run(self._execute("list_todos", {"priority": 1}))
        self.assertTrue(self._is_success(result))
        self.assertGreaterEqual(len(result.data), 2)
        print(f"  [OK] Filter by priority: {len(result.data)}")

        print("  [PASS] list_todos")

    def test_05_complete_todo(self):
        """测试 5: complete_todo"""
        print("\n[TEST] complete_todo")

        result = asyncio.run(self._execute("create_todo", {"title": "Complete Test"}))
        todo_id = result.data.get("id")

        result = asyncio.run(self._execute("complete_todo", {
            "id": todo_id,
            "completion_note": "Test completed",
        }))

        self.assertTrue(self._is_success(result), f"Complete failed: {result.error if hasattr(result, 'error') else result}")

        get_result = asyncio.run(self._execute("get_todo", {"id": todo_id}))
        self.assertEqual(get_result.data.get("status"), "completed")
        print("  [OK] Status: completed")
        print("  [PASS] complete_todo")

    def test_06_cancel_todo(self):
        """测试 6: cancel_todo"""
        print("\n[TEST] cancel_todo")

        result = asyncio.run(self._execute("create_todo", {"title": "Cancel Test"}))
        todo_id = result.data.get("id")

        result = asyncio.run(self._execute("cancel_todo", {
            "id": todo_id,
            "reason": "Changed plans",
        }))

        self.assertTrue(self._is_success(result), f"Cancel failed: {result.error if hasattr(result, 'error') else result}")

        get_result = asyncio.run(self._execute("get_todo", {"id": todo_id}))
        self.assertEqual(get_result.data.get("status"), "cancelled")
        print("  [OK] Status: cancelled")
        print("  [PASS] cancel_todo")

    def test_07_delete_todo(self):
        """测试 7: delete_todo"""
        print("\n[TEST] delete_todo")

        result = asyncio.run(self._execute("create_todo", {"title": "Delete Test"}))
        todo_id = result.data.get("id")

        result = asyncio.run(self._execute("delete_todo", {"id": todo_id}))
        self.assertTrue(self._is_success(result), f"Delete failed: {result.error if hasattr(result, 'error') else result}")

        get_result = asyncio.run(self._execute("get_todo", {"id": todo_id}))
        self.assertIsNone(get_result.data.get("id"))
        print("  [OK] Deleted")
        print("  [PASS] delete_todo")

    def test_08_decompose_todo(self):
        """测试 8: decompose_todo"""
        print("\n[TEST] decompose_todo")

        result = asyncio.run(self._execute("create_todo", {
            "title": "Project A",
            "category": "work",
            "time_frame": "month",
            "priority": 1,
        }))
        parent_id = result.data.get("id")

        # decompose_todo 需要 JSON 字符串
        import json
        subtasks = [
            {"title": "Subtask 1", "priority": 1},
            {"title": "Subtask 2", "priority": 2},
            {"title": "Subtask 3", "priority": 3},
        ]

        result = asyncio.run(self._execute("decompose_todo", {
            "id": parent_id,
            "subtasks": json.dumps(subtasks),
        }))

        self.assertTrue(self._is_success(result), f"Decompose failed: {result.error if hasattr(result, 'error') else result}")

        # decompose_todo 返回的是 subtask_ids
        subtask_ids = result.data.get("subtask_ids", [])
        self.assertEqual(len(subtask_ids), 3)
        print(f"  [OK] Created {len(subtask_ids)} subtasks: {subtask_ids}")
        print("  [PASS] decompose_todo")

    def test_09_get_overdue_todos(self):
        """测试 9: get_overdue_todos"""
        print("\n[TEST] get_overdue_todos")

        # Create overdue task
        asyncio.run(self._execute("create_todo", {
            "title": "Overdue Task",
            "deadline": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
        }))

        result = asyncio.run(self._execute("get_overdue_todos", {}))
        self.assertTrue(self._is_success(result), f"Get overdue failed: {result.error if hasattr(result, 'error') else result}")
        self.assertGreaterEqual(len(result.data), 1)
        print(f"  [OK] Found {len(result.data)} overdue tasks")
        print("  [PASS] get_overdue_todos")

    def test_10_get_upcoming_todos(self):
        """测试 10: get_upcoming_todos"""
        print("\n[TEST] get_upcoming_todos")

        asyncio.run(self._execute("create_todo", {
            "title": "Upcoming Task",
            "deadline": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
        }))

        result = asyncio.run(self._execute("get_upcoming_todos", {"days": 3}))
        self.assertTrue(self._is_success(result), f"Get upcoming failed: {result.error if hasattr(result, 'error') else result}")
        self.assertGreaterEqual(len(result.data), 1)
        print(f"  [OK] Found {len(result.data)} upcoming tasks")
        print("  [PASS] get_upcoming_todos")


class TestTodoToolEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_edge.db"
        self.tool = TodoTool(str(self.db_path))

    def tearDown(self):
        try:
            if self.tool._storage:
                self.tool._storage.close()
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    async def _execute(self, action, params):
        return await self.tool.execute(action, params)

    def _is_success(self, result):
        return hasattr(result, 'is_success') and result.is_success

    def test_empty_title(self):
        """测试空标题"""
        print("\n[TEST] Empty Title")
        result = asyncio.run(self._execute("create_todo", {"title": ""}))
        self.assertFalse(self._is_success(result), "Empty title should fail")
        print("  [OK] Empty title rejected")

    def test_invalid_action(self):
        """测试无效动作"""
        print("\n[TEST] Invalid Action")
        result = asyncio.run(self._execute("invalid_action", {}))
        self.assertFalse(self._is_success(result), "Invalid action should fail")
        print("  [OK] Invalid action rejected")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("[TEST SUITE] TodoTool Tests")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestTodoTool))
    suite.addTests(loader.loadTestsFromTestCase(TestTodoToolEdgeCases))

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
