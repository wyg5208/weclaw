"""待办事项存储层测试 — TodoStorage 数据持久化功能验证。

运行方式：
    python -m pytest tests/test_todo_storage.py -v
    或
    python tests/test_todo_storage.py

测试内容：
1. 数据库初始化与连接
2. Todo 待办事项 CRUD 操作
3. DailyTask 每日任务 CRUD 操作
4. DailyRecommendation 推荐记录管理
5. 多条件筛选与查询
6. 状态转换与时间过滤

预期结果：所有测试通过 ✅
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
        # 创建临时数据库
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_todo.db"
        self.storage = TodoStorage(self.db_path)
        print(f"\n📦 测试数据库: {self.db_path}")

    def tearDown(self):
        """测试后清理"""
        try:
            self.storage.close()
            shutil.rmtree(self.test_dir)
            print("🧹 临时数据库已清理")
        except Exception as e:
            print(f"⚠️ 清理失败: {e}")

    def test_01_database_initialization(self):
        """测试 1: 数据库初始化"""
        print("\n✅ 测试 1: 数据库初始化")
        
        # 验证表已创建
        conn = self.storage._conn()
        cursor = conn.cursor()
        
        # 检查 todos 表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='todos'")
        self.assertIsNotNone(cursor.fetchone(), "todos 表未创建")
        print("  ✓ todos 表已创建")
        
        # 检查 daily_tasks 表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_tasks'")
        self.assertIsNotNone(cursor.fetchone(), "daily_tasks 表未创建")
        print("  ✓ daily_tasks 表已创建")
        
        # 检查 daily_recommendations 表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_recommendations'")
        self.assertIsNotNone(cursor.fetchone(), "daily_recommendations 表未创建")
        print("  ✓ daily_recommendations 表已创建")
        
        conn.close()
        print("  ✅ 数据库初始化测试通过")

    def test_02_todo_crud_operations(self):
        """测试 2: Todo CRUD 操作"""
        print("\n✅ 测试 2: Todo CRUD 操作")
        
        # Create - 创建待办事项
        todo_data = {
            "title": "完成项目报告",
            "description": "需要在本周五前完成",
            "category": TaskCategory.WORK,
            "time_frame": TimeFrame.WEEK,
            "priority": 1,
            "deadline": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
        }
        todo_id = self.storage.create_todo(**todo_data)
        self.assertIsNotNone(todo_id, "创建待办事项失败")
        print(f"  ✓ 创建待办事项: ID={todo_id}")
        
        # Read - 读取待办事项
        todo = self.storage.get_todo(todo_id)
        self.assertIsNotNone(todo, "获取待办事项失败")
        self.assertEqual(todo.title, "完成项目报告")
        self.assertEqual(todo.category, TaskCategory.WORK)
        print(f"  ✓ 读取待办事项: {todo.title}")
        
        # Update - 更新待办事项
        updated = self.storage.update_todo(todo_id, priority=2, status=TodoStatus.IN_PROGRESS)
        self.assertTrue(updated, "更新待办事项失败")
        todo = self.storage.get_todo(todo_id)
        self.assertEqual(todo.priority, 2)
        self.assertEqual(todo.status, TodoStatus.IN_PROGRESS)
        print(f"  ✓ 更新待办事项: priority=2, status=in_progress")
        
        # Delete - 删除待办事项
        deleted = self.storage.delete_todo(todo_id)
        self.assertTrue(deleted, "删除待办事项失败")
        todo = self.storage.get_todo(todo_id)
        self.assertIsNone(todo, "待办事项未正确删除")
        print(f"  ✓ 删除待办事项: ID={todo_id}")
        
        print("  ✅ Todo CRUD 测试通过")

    def test_03_todo_list_filtering(self):
        """测试 3: 待办事项列表筛选"""
        print("\n✅ 测试 3: 待办事项列表筛选")
        
        # 创建多个测试数据
        todos = [
            {"title": "任务A", "category": TaskCategory.WORK, "priority": 1, "status": TodoStatus.PENDING},
            {"title": "任务B", "category": TaskCategory.STUDY, "priority": 2, "status": TodoStatus.IN_PROGRESS},
            {"title": "任务C", "category": TaskCategory.HEALTH, "priority": 3, "status": TodoStatus.PENDING},
            {"title": "任务D", "category": TaskCategory.WORK, "priority": 1, "status": TodoStatus.COMPLETED},
        ]
        
        for todo in todos:
            self.storage.create_todo(**todo)
        
        # 按类型筛选
        work_todos = self.storage.list_todos(category=TaskCategory.WORK)
        self.assertEqual(len(work_todos), 2, "按类型筛选失败")
        print(f"  ✓ 按类型筛选(工作): {len(work_todos)} 个")
        
        # 按状态筛选
        pending_todos = self.storage.list_todos(status=TodoStatus.PENDING)
        self.assertEqual(len(pending_todos), 2, "按状态筛选失败")
        print(f"  ✓ 按状态筛选(待办): {len(pending_todos)} 个")
        
        # 按优先级筛选
        high_priority = self.storage.list_todos(priority=1)
        self.assertEqual(len(high_priority), 2, "按优先级筛选失败")
        print(f"  ✓ 按优先级筛选(最高): {len(high_priority)} 个")
        
        # 搜索
        search_results = self.storage.list_todos(search="任务A")
        self.assertEqual(len(search_results), 1, "搜索失败")
        print(f"  ✓ 搜索「任务A」: {len(search_results)} 个")
        
        print("  ✅ 待办事项筛选测试通过")

    def test_04_todo_status_transitions(self):
        """测试 4: 待办事项状态转换"""
        print("\n✅ 测试 4: 待办事项状态转换")
        
        todo_id = self.storage.create_todo(
            title="测试状态转换",
            category=TaskCategory.GENERAL,
            time_frame=TimeFrame.TODAY,
            priority=3,
        )
        
        # pending -> in_progress
        self.storage.update_todo(todo_id, status=TodoStatus.IN_PROGRESS)
        todo = self.storage.get_todo(todo_id)
        self.assertEqual(todo.status, TodoStatus.IN_PROGRESS)
        print("  ✓ pending → in_progress")
        
        # in_progress -> completed
        self.storage.complete_todo(todo_id)
        todo = self.storage.get_todo(todo_id)
        self.assertEqual(todo.status, TodoStatus.COMPLETED)
        self.assertIsNotNone(todo.completed_at)
        print("  ✓ in_progress → completed")
        
        # 测试取消
        todo_id2 = self.storage.create_todo(title="测试取消", category=TaskCategory.GENERAL)
        self.storage.cancel_todo(todo_id2, "不需要了")
        todo2 = self.storage.get_todo(todo_id2)
        self.assertEqual(todo2.status, TodoStatus.CANCELLED)
        print("  ✓ cancel_todo → cancelled")
        
        print("  ✅ 状态转换测试通过")

    def test_05_daily_task_crud(self):
        """测试 5: DailyTask CRUD 操作"""
        print("\n✅ 测试 5: DailyTask CRUD 操作")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 创建关联的待办事项
        todo_id = self.storage.create_todo(
            title="今日任务关联测试",
            category=TaskCategory.WORK,
            time_frame=TimeFrame.TODAY,
            priority=2,
        )
        
        # 创建每日任务
        task_data = {
            "todo_id": todo_id,
            "task_date": today,
            "title": "撰写周报",
            "description": "完成本周工作总结",
            "scheduled_start": "09:00",
            "scheduled_end": "10:00",
            "priority": 2,
            "source": "from_todo",
        }
        task_id = self.storage.create_daily_task(**task_data)
        self.assertIsNotNone(task_id, "创建每日任务失败")
        print(f"  ✓ 创建每日任务: ID={task_id}")
        
        # 读取每日任务
        task = self.storage.get_daily_task(task_id)
        self.assertIsNotNone(task, "获取每日任务失败")
        self.assertEqual(task.title, "撰写周报")
        print(f"  ✓ 读取每日任务: {task.title}")
        
        # 获取今日任务列表
        tasks = self.storage.get_daily_tasks(today)
        self.assertEqual(len(tasks), 1, "获取今日任务失败")
        print(f"  ✓ 获取今日任务: {len(tasks)} 个")
        
        # 更新任务
        self.storage.update_daily_task(task_id, status="in_progress")
        task = self.storage.get_daily_task(task_id)
        self.assertEqual(task.status, "in_progress")
        print("  ✓ 更新每日任务状态")
        
        # 删除任务
        self.storage.delete_daily_task(task_id)
        task = self.storage.get_daily_task(task_id)
        self.assertIsNone(task, "删除每日任务失败")
        print("  ✓ 删除每日任务")
        
        print("  ✅ DailyTask CRUD 测试通过")

    def test_06_daily_task_start_complete(self):
        """测试 6: 每日任务开始/完成"""
        print("\n✅ 测试 6: 每日任务开始/完成")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        task_id = self.storage.create_daily_task(
            task_date=today,
            title="测试任务",
            priority=3,
        )
        
        # 开始任务
        self.storage.start_daily_task(task_id)
        task = self.storage.get_daily_task(task_id)
        self.assertEqual(task.status, "in_progress")
        self.assertIsNotNone(task.actual_start)
        print("  ✓ 开始任务")
        
        # 完成任务
        self.storage.complete_daily_task(task_id, completion_note="已完成测试")
        task = self.storage.get_daily_task(task_id)
        self.assertEqual(task.status, "completed")
        self.assertEqual(task.completion_note, "已完成测试")
        print("  ✓ 完成任务")
        
        print("  ✅ 任务开始/完成测试通过")

    def test_07_recommendations_management(self):
        """测试 7: 推荐记录管理"""
        print("\n✅ 测试 7: 推荐记录管理")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 保存推荐
        recommendations = [
            {"title": "推荐任务1", "priority": 1, "source": "ai_suggested"},
            {"title": "推荐任务2", "priority": 2, "source": "from_todo"},
        ]
        
        result = self.storage.save_recommendation(
            task_date=today,
            recommendations=recommendations,
            analysis_summary="测试分析摘要",
        )
        self.assertTrue(result, "保存推荐失败")
        print(f"  ✓ 保存推荐: {len(recommendations)} 个任务")
        
        # 读取推荐
        rec = self.storage.get_recommendation(today)
        self.assertIsNotNone(rec, "获取推荐失败")
        self.assertEqual(len(rec.recommendations), 2)
        print(f"  ✓ 获取推荐: {rec.task_date}")
        
        # 更新状态
        self.storage.update_recommendation_status(today, RecommendationStatus.PUSHED)
        rec = self.storage.get_recommendation(today)
        self.assertEqual(rec.status, RecommendationStatus.PUSHED)
        print("  ✓ 更新推荐状态: PUSHED")
        
        print("  ✅ 推荐记录测试通过")

    def test_08_get_overdue_and_upcoming(self):
        """测试 8: 过期与即将到期任务"""
        print("\n✅ 测试 8: 过期与即将到期任务")
        
        # 创建已过期的任务
        self.storage.create_todo(
            title="已过期任务",
            category=TaskCategory.WORK,
            deadline=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
            status=TodoStatus.PENDING,
        )
        
        # 创建即将到期的任务
        self.storage.create_todo(
            title="即将到期任务",
            category=TaskCategory.STUDY,
            deadline=(datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
            status=TodoStatus.PENDING,
        )
        
        # 获取过期任务
        overdue = self.storage.get_overdue_todos()
        self.assertGreater(len(overdue), 0, "未找到过期任务")
        print(f"  ✓ 过期任务: {len(overdue)} 个")
        
        # 获取即将到期的任务(3天内)
        upcoming = self.storage.get_upcoming_todos(days=3)
        self.assertGreater(len(upcoming), 0, "未找到即将到期任务")
        print(f"  ✓ 即将到期(3天内): {len(upcoming)} 个")
        
        print("  ✅ 过期与到期测试通过")

    def test_09_todo_decomposition(self):
        """测试 9: 任务分解"""
        print("\n✅ 测试 9: 任务分解")
        
        parent_id = self.storage.create_todo(
            title="项目A",
            category=TaskCategory.WORK,
            time_frame=TimeFrame.MONTH,
            priority=1,
        )
        
        # 分解为子任务
        subtasks = [
            {"title": "子任务1", "priority": 1},
            {"title": "子任务2", "priority": 2},
            {"title": "子任务3", "priority": 3},
        ]
        
        created = self.storage.create_subtasks(parent_id, subtasks)
        self.assertEqual(len(created), 3, "子任务创建失败")
        print(f"  ✓ 创建子任务: {len(created)} 个")
        
        # 获取子任务
        children = self.storage.get_subtasks(parent_id)
        self.assertEqual(len(children), 3, "获取子任务失败")
        print(f"  ✓ 获取子任务: {len(children)} 个")
        
        print("  ✅ 任务分解测试通过")

    def test_10_batch_operations(self):
        """测试 10: 批量操作"""
        print("\n✅ 测试 10: 批量操作")
        
        # 批量创建
        batch_todos = [
            {"title": f"批量任务{i}", "priority": (i % 5) + 1, "category": TaskCategory.WORK}
            for i in range(10)
        ]
        
        created = self.storage.batch_create_todos(batch_todos)
        self.assertEqual(len(created), 10, "批量创建失败")
        print(f"  ✓ 批量创建: {len(created)} 个")
        
        # 批量更新状态
        ids = [t.id for t in self.storage.list_todos(category=TaskCategory.WORK)]
        updated = self.storage.batch_update_todos(ids, status=TodoStatus.COMPLETED)
        self.assertEqual(updated, 10, "批量更新失败")
        print(f"  ✓ 批量更新: {updated} 个")
        
        print("  ✅ 批量操作测试通过")


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
            self.storage.close()
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_empty_database(self):
        """测试空数据库"""
        print("\n✅ 边界测试: 空数据库")
        
        todos = self.storage.list_todos()
        self.assertEqual(len(todos), 0, "空数据库应无数据")
        print("  ✓ 空数据库查询正常")
        
        overdue = self.storage.get_overdue_todos()
        self.assertEqual(len(overdue), 0, "空数据库无过期任务")
        print("  ✓ 空数据库过期查询正常")

    def test_invalid_id(self):
        """测试无效ID"""
        print("\n✅ 边界测试: 无效ID")
        
        todo = self.storage.get_todo(99999)
        self.assertIsNone(todo, "无效ID应返回None")
        print("  ✓ 无效ID查询返回None")
        
        deleted = self.storage.delete_todo(99999)
        self.assertFalse(deleted, "删除无效ID应返回False")
        print("  ✓ 删除无效ID返回False")

    def test_special_characters_in_title(self):
        """测试特殊字符"""
        print("\n✅ 边界测试: 特殊字符")
        
        special_title = "测试<>\"'&字符!@#$%^&*()"
        todo_id = self.storage.create_todo(
            title=special_title,
            category=TaskCategory.GENERAL,
        )
        
        todo = self.storage.get_todo(todo_id)
        self.assertEqual(todo.title, special_title, "特殊字符未正确保存")
        print("  ✓ 特殊字符保存正常")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 待办事项存储层测试套件")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestTodoStorage))
    suite.addTests(loader.loadTestsFromTestCase(TestTodoStorageEdgeCases))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 所有测试通过！")
    else:
        print(f"❌ {len(result.failures)} 个失败, {len(result.errors)} 个错误")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
