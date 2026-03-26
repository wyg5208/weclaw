"""待办事项存储层测试 — TodoStorage 数据持久化功能验证。

运行方式：
    python -m pytest tests/test_todo_storage.py -v
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.todo_storage import (
    TodoStorage,
    Todo,
    DailyTask,
    DailyRecommendation,
    TodoStatus,
    TimeFrame,
    TaskCategory,
    RecurrenceType,
    RecommendationStatus,
)


class TestTodoStorage(unittest.TestCase):
    """待办事项存储层测试"""

    def setUp(self):
        """测试前准备：创建临时数据库"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_todo.db"
        self.storage = TodoStorage(self.db_path)

    def tearDown(self):
        """测试后清理"""
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_01_database_initialization(self):
        """测试 1: 数据库初始化"""
        print("\n[TEST] Database Initialization")
        
        # 验证表已创建 - 直接使用 storage._conn()
        with self.storage._conn() as conn:
            cursor = conn.cursor()
            
            # 检查 todos 表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='todos'")
            self.assertIsNotNone(cursor.fetchone(), "todos table not created")
            print("  [OK] todos table created")
            
            # 检查 daily_tasks 表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_tasks'")
            self.assertIsNotNone(cursor.fetchone(), "daily_tasks table not created")
            print("  [OK] daily_tasks table created")
            
            # 检查 daily_recommendations 表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_recommendations'")
            self.assertIsNotNone(cursor.fetchone(), "daily_recommendations table not created")
            print("  [OK] daily_recommendations table created")
        
        print("  [PASS] Database initialization")

    def test_02_todo_crud_operations(self):
        """测试 2: Todo CRUD 操作"""
        print("\n[TEST] Todo CRUD Operations")
        
        # Create - 创建待办事项
        todo = Todo(
            title="Test Todo",
            description="Test description",
            category=TaskCategory.WORK,
            time_frame=TimeFrame.WEEK,
            priority=1,
        )
        todo_id = self.storage.create_todo(todo)
        self.assertIsNotNone(todo_id, "Failed to create todo")
        print(f"  [OK] Created todo: ID={todo_id}")
        
        # Read - 读取待办事项
        fetched = self.storage.get_todo(todo_id)
        self.assertIsNotNone(fetched, "Failed to get todo")
        self.assertEqual(fetched.title, "Test Todo")
        self.assertEqual(fetched.category, TaskCategory.WORK)
        print(f"  [OK] Retrieved todo: {fetched.title}")
        
        # Update - 更新待办事项
        updated = self.storage.update_todo(todo_id, {"priority": 2, "status": TodoStatus.IN_PROGRESS})
        self.assertTrue(updated, "Failed to update todo")
        fetched = self.storage.get_todo(todo_id)
        self.assertEqual(fetched.priority, 2)
        self.assertEqual(fetched.status, TodoStatus.IN_PROGRESS)
        print(f"  [OK] Updated todo: priority=2, status=in_progress")
        
        # Delete - 删除待办事项
        deleted = self.storage.delete_todo(todo_id)
        self.assertTrue(deleted, "Failed to delete todo")
        fetched = self.storage.get_todo(todo_id)
        self.assertIsNone(fetched, "Todo not deleted properly")
        print(f"  [OK] Deleted todo: ID={todo_id}")
        
        print("  [PASS] Todo CRUD operations")

    def test_03_todo_list_filtering(self):
        """测试 3: 待办事项列表筛选"""
        print("\n[TEST] Todo List Filtering")
        
        # 创建多个测试数据 - 使用 include_completed=True 来包含已完成的任务
        todos = [
            Todo(title="TaskA", category=TaskCategory.WORK, priority=1, status=TodoStatus.PENDING),
            Todo(title="TaskB", category=TaskCategory.WORK, priority=2, status=TodoStatus.IN_PROGRESS),  # 改为 WORK
            Todo(title="TaskC", category=TaskCategory.HEALTH, priority=3, status=TodoStatus.PENDING),
            Todo(title="TaskD", category=TaskCategory.WORK, priority=1, status=TodoStatus.COMPLETED),
        ]
        
        for todo in todos:
            self.storage.create_todo(todo)
        
        # 按类型筛选 - 包含所有状态
        work_todos = self.storage.list_todos(category=TaskCategory.WORK.value, include_completed=True)
        self.assertEqual(len(work_todos), 3, f"Category filter failed: {len(work_todos)} != 3")
        print(f"  [OK] Filter by category(work): {len(work_todos)}")
        
        # 按状态筛选
        pending_todos = self.storage.list_todos(status=TodoStatus.PENDING.value)
        self.assertEqual(len(pending_todos), 2, "Status filter failed")
        print(f"  [OK] Filter by status(pending): {len(pending_todos)}")
        
        # 按优先级筛选
        high_priority = self.storage.list_todos(priority=1, include_completed=True)
        self.assertEqual(len(high_priority), 2, "Priority filter failed")
        print(f"  [OK] Filter by priority(1): {len(high_priority)}")
        
        print("  [PASS] Todo list filtering")

    def test_04_todo_status_transitions(self):
        """测试 4: 待办事项状态转换"""
        print("\n[TEST] Todo Status Transitions")
        
        todo = Todo(title="Test Status", category=TaskCategory.GENERAL, time_frame=TimeFrame.TODAY, priority=3)
        todo_id = self.storage.create_todo(todo)
        
        # pending -> in_progress
        self.storage.update_todo(todo_id, {"status": TodoStatus.IN_PROGRESS})
        fetched = self.storage.get_todo(todo_id)
        self.assertEqual(fetched.status, TodoStatus.IN_PROGRESS)
        print("  [OK] pending -> in_progress")
        
        # in_progress -> completed
        self.storage.complete_todo(todo_id)
        fetched = self.storage.get_todo(todo_id)
        self.assertEqual(fetched.status, TodoStatus.COMPLETED)
        self.assertIsNotNone(fetched.completed_at)
        print("  [OK] in_progress -> completed")
        
        # 测试取消
        todo2 = Todo(title="Test Cancel", category=TaskCategory.GENERAL)
        todo_id2 = self.storage.create_todo(todo2)
        self.storage.cancel_todo(todo_id2)
        fetched2 = self.storage.get_todo(todo_id2)
        self.assertEqual(fetched2.status, TodoStatus.CANCELLED)
        print("  [OK] cancel_todo -> cancelled")
        
        print("  [PASS] Status transitions")

    def test_05_daily_task_crud(self):
        """测试 5: DailyTask CRUD 操作"""
        print("\n[TEST] DailyTask CRUD")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 创建关联的待办事项
        todo = Todo(title="Daily Task Link", category=TaskCategory.WORK, time_frame=TimeFrame.TODAY, priority=2)
        todo_id = self.storage.create_todo(todo)
        
        # 创建每日任务
        task = DailyTask(
            todo_id=todo_id,
            task_date=today,
            title="Write Report",
            description="Complete weekly report",
            scheduled_start="09:00",
            scheduled_end="10:00",
            priority=2,
            source="from_todo",
        )
        task_id = self.storage.create_daily_task(task)
        self.assertIsNotNone(task_id, "Failed to create daily task")
        print(f"  [OK] Created daily task: ID={task_id}")
        
        # 读取每日任务
        fetched = self.storage.get_daily_task(task_id)
        self.assertIsNotNone(fetched, "Failed to get daily task")
        self.assertEqual(fetched.title, "Write Report")
        print(f"  [OK] Retrieved daily task: {fetched.title}")
        
        # 获取今日任务列表
        tasks = self.storage.get_daily_tasks(today)
        self.assertEqual(len(tasks), 1, "Failed to get daily tasks")
        print(f"  [OK] Got daily tasks: {len(tasks)}")
        
        # 更新任务
        self.storage.update_daily_task(task_id, {"status": "in_progress"})
        fetched = self.storage.get_daily_task(task_id)
        self.assertEqual(fetched.status, "in_progress")
        print("  [OK] Updated daily task status")
        
        # 删除任务
        self.storage.delete_daily_task(task_id)
        fetched = self.storage.get_daily_task(task_id)
        self.assertIsNone(fetched, "Failed to delete daily task")
        print("  [OK] Deleted daily task")
        
        print("  [PASS] DailyTask CRUD")

    def test_06_daily_task_workflow(self):
        """测试 6: 每日任务工作流"""
        print("\n[TEST] DailyTask Workflow")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 创建任务
        task = DailyTask(task_date=today, title="Test Task", priority=3)
        task_id = self.storage.create_daily_task(task)
        print("  [OK] Created task")
        
        # 更新为进行中
        self.storage.update_daily_task(task_id, {
            "status": "in_progress",
            "actual_start": datetime.now().strftime("%H:%M")
        })
        fetched = self.storage.get_daily_task(task_id)
        self.assertEqual(fetched.status, "in_progress")
        print("  [OK] Started task")
        
        # 完成任务
        self.storage.update_daily_task(task_id, {
            "status": "completed",
            "actual_end": datetime.now().strftime("%H:%M"),
            "completion_note": "Test completed successfully"
        })
        fetched = self.storage.get_daily_task(task_id)
        self.assertEqual(fetched.status, "completed")
        self.assertEqual(fetched.completion_note, "Test completed successfully")
        print("  [OK] Completed task")
        
        print("  [PASS] DailyTask workflow")

    def test_07_recommendations_management(self):
        """测试 7: 推荐记录管理"""
        print("\n[TEST] Recommendations Management")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 创建推荐
        recommendations = [
            {"title": "Recommended Task 1", "priority": 1, "source": "ai_suggested"},
            {"title": "Recommended Task 2", "priority": 2, "source": "from_todo"},
        ]
        
        rec = DailyRecommendation(
            task_date=today,
            recommendations=recommendations,
            analysis_summary="Test analysis summary",
        )
        result = self.storage.create_recommendation(rec)
        self.assertIsNotNone(result, "Failed to save recommendation")
        print(f"  [OK] Saved recommendation: {len(recommendations)} tasks")
        
        # 读取推荐
        fetched = self.storage.get_recommendation(today)
        self.assertIsNotNone(fetched, "Failed to get recommendation")
        self.assertEqual(len(fetched.recommendations), 2)
        print(f"  [OK] Got recommendation: {fetched.task_date}")
        
        # 更新状态
        self.storage.update_recommendation_status(today, RecommendationStatus.PUSHED)
        fetched = self.storage.get_recommendation(today)
        self.assertEqual(fetched.status, RecommendationStatus.PUSHED)
        print("  [OK] Updated recommendation status: PUSHED")
        
        print("  [PASS] Recommendations management")

    def test_08_get_overdue_and_upcoming(self):
        """测试 8: 过期与即将到期任务"""
        print("\n[TEST] Overdue and Upcoming Tasks")
        
        # 创建已过期的任务
        overdue_todo = Todo(
            title="Overdue Task",
            category=TaskCategory.WORK,
            deadline=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
            status=TodoStatus.PENDING,
        )
        self.storage.create_todo(overdue_todo)
        
        # 创建即将到期的任务
        upcoming_todo = Todo(
            title="Upcoming Task",
            category=TaskCategory.STUDY,
            deadline=(datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
            status=TodoStatus.PENDING,
        )
        self.storage.create_todo(upcoming_todo)
        
        # 获取过期任务
        overdue = self.storage.get_overdue_todos()
        self.assertGreater(len(overdue), 0, "No overdue tasks found")
        print(f"  [OK] Overdue tasks: {len(overdue)}")
        
        # 获取即将到期的任务(3天内)
        upcoming = self.storage.get_upcoming_todos(days=3)
        self.assertGreater(len(upcoming), 0, "No upcoming tasks found")
        print(f"  [OK] Upcoming tasks (3 days): {len(upcoming)}")
        
        print("  [PASS] Overdue and upcoming")

    def test_09_todo_decomposition(self):
        """测试 9: 任务分解"""
        print("\n[TEST] Task Decomposition")
        
        parent = Todo(
            title="Project A",
            category=TaskCategory.WORK,
            time_frame=TimeFrame.MONTH,
            priority=1,
        )
        parent_id = self.storage.create_todo(parent)
        
        # 分解为子任务
        subtasks = [
            Todo(title="Subtask 1", priority=1, parent_id=parent_id),
            Todo(title="Subtask 2", priority=2, parent_id=parent_id),
            Todo(title="Subtask 3", priority=3, parent_id=parent_id),
        ]
        
        for subtask in subtasks:
            self.storage.create_todo(subtask)
        
        # 获取子任务
        children = self.storage.get_sub_todos(parent_id)
        self.assertEqual(len(children), 3, "Subtasks creation failed")
        print(f"  [OK] Created subtasks: {len(children)}")
        
        print("  [PASS] Task decomposition")

    def test_10_statistics(self):
        """测试 10: 统计信息"""
        print("\n[TEST] Statistics")
        
        # 创建一些任务
        todos = [
            Todo(title="Stats 1", category=TaskCategory.WORK, status=TodoStatus.PENDING),
            Todo(title="Stats 2", category=TaskCategory.STUDY, status=TodoStatus.COMPLETED),
            Todo(title="Stats 3", category=TaskCategory.HEALTH, status=TodoStatus.PENDING),
        ]
        
        for todo in todos:
            self.storage.create_todo(todo)
        
        stats = self.storage.get_statistics()
        
        self.assertGreaterEqual(stats["total_todos"], 3)
        self.assertGreaterEqual(stats["pending_todos"], 2)
        self.assertGreaterEqual(stats["completed_todos"], 1)
        
        print(f"  [OK] Total: {stats['total_todos']}")
        print(f"  [OK] Pending: {stats['pending_todos']}")
        print(f"  [OK] Completed: {stats['completed_todos']}")
        
        print("  [PASS] Statistics")


class TestTodoStorageEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_edge.db"
        self.storage = TodoStorage(self.db_path)

    def tearDown(self):
        """测试后清理"""
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_empty_database(self):
        """测试空数据库"""
        print("\n[TEST] Empty Database")
        
        todos = self.storage.list_todos(include_completed=True)
        self.assertEqual(len(todos), 0, "Empty DB should have no todos")
        print("  [OK] Empty DB query OK")
        
        overdue = self.storage.get_overdue_todos()
        self.assertEqual(len(overdue), 0, "Empty DB should have no overdue")
        print("  [OK] Empty DB overdue query OK")

    def test_invalid_id(self):
        """测试无效ID"""
        print("\n[TEST] Invalid ID")
        
        todo = self.storage.get_todo(99999)
        self.assertIsNone(todo, "Invalid ID should return None")
        print("  [OK] Invalid ID query returns None")
        
        daily_task = self.storage.get_daily_task(99999)
        self.assertIsNone(daily_task, "Invalid daily task ID should return None")
        print("  [OK] Invalid daily task ID returns None")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("[TEST SUITE] TodoStorage Test Suite")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestTodoStorage))
    suite.addTests(loader.loadTestsFromTestCase(TestTodoStorageEdgeCases))
    
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
