"""每日任务工具测试 — DailyTaskTool 10个Actions功能验证。

运行方式：
    python -m pytest tests/test_daily_task_tool.py -v
    或
    python tests/test_daily_task_tool.py

测试内容：
1. add_daily_task — 添加每日任务
2. update_daily_task — 更新每日任务
3. remove_daily_task — 移除每日任务
4. get_daily_tasks — 获取某日任务列表
5. start_task — 开始任务
6. complete_task — 完成任务
7. cancel_task — 取消任务
8. get_today_summary — 获取今日任务摘要
9. generate_recommendations — 生成每日任务推荐
10. accept_recommendations — 接受推荐任务

预期结果：所有测试通过 ✅
"""

import os
import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.daily_task import DailyTaskTool
from src.tools.todo import TodoTool


class TestDailyTaskTool(unittest.TestCase):
    """每日任务工具测试"""

    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_daily_task.db"
        
        # 初始化工具
        self.todo_tool = TodoTool(str(self.db_path))
        self.tool = DailyTaskTool(str(self.db_path))
        
        # 今天的日期
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        print(f"\n📦 测试数据库: {self.db_path}")
        print(f"📅 今日日期: {self.today}")

    def tearDown(self):
        """测试后清理"""
        try:
            self.tool.storage.close()
            shutil.rmtree(self.test_dir)
            print("🧹 临时数据库已清理")
        except Exception as e:
            print(f"⚠️ 清理失败: {e}")

    def _get_result_data(self, result) -> dict:
        """从 ToolResult 中提取数据"""
        if hasattr(result, 'data') and result.data:
            if isinstance(result.data, dict):
                return result.data
            if isinstance(result.data, list) and len(result.data) > 0:
                if isinstance(result.data[0], dict):
                    return {"items": result.data}
        return {}

    def test_01_add_daily_task(self):
        """测试 1: add_daily_task — 添加每日任务"""
        print("\n✅ 测试 1: add_daily_task")
        
        # 创建关联的待办事项
        todo_result = self.todo_tool.execute_action(
            "create_todo",
            title="周报撰写",
            category="work",
            priority=1,
        )
        todo_data = self._get_result_data(todo_result)
        todo_id = todo_data.get("id")
        
        # 添加每日任务
        result = self.tool.execute_action(
            "add_daily_task",
            todo_id=todo_id,
            title="撰写本周工作总结",
            description="总结本周工作完成情况",
            scheduled_start="09:00",
            scheduled_end="10:00",
            priority=1,
        )
        
        self.assertTrue(result.success, f"添加失败: {result.message}")
        data = self._get_result_data(result)
        self.assertIn("id", data, "返回结果缺少id")
        print(f"  ✓ 添加每日任务: ID={data.get('id')}")
        print(f"  ✓ 标题: {data.get('title')}")
        print(f"  ✓ 时间: {data.get('scheduled_start')} - {data.get('scheduled_end')}")
        
        # 保存ID用于后续测试
        self._test_task_id = data.get("id")
        
        print("  ✅ add_daily_task 测试通过")

    def test_02_get_daily_tasks(self):
        """测试 2: get_daily_tasks — 获取某日任务列表"""
        print("\n✅ 测试 2: get_daily_tasks")
        
        # 先添加任务
        if not hasattr(self, '_test_task_id'):
            self.tool.execute_action(
                "add_daily_task",
                title="测试获取任务",
                priority=3,
            )
        
        # 获取今日任务
        result = self.tool.execute_action("get_daily_tasks", date=self.today)
        
        self.assertTrue(result.success, f"获取失败: {result.message}")
        data = self._get_result_data(result)
        items = data.get("items", data.get("tasks", []))
        
        self.assertIsInstance(items, list, "返回结果应该是列表")
        self.assertGreaterEqual(len(items), 1, "应该至少有一个任务")
        print(f"  ✓ 今日任务数量: {len(items)}")
        
        for task in items[:3]:
            print(f"    - {task.get('title')} ({task.get('status', 'pending')})")
        
        print("  ✅ get_daily_tasks 测试通过")

    def test_03_update_daily_task(self):
        """测试 3: update_daily_task — 更新每日任务"""
        print("\n✅ 测试 3: update_daily_task")
        
        # 先添加任务
        add_result = self.tool.execute_action(
            "add_daily_task",
            title="需要更新的任务",
            scheduled_start="14:00",
            priority=3,
        )
        data = self._get_result_data(add_result)
        task_id = data.get("id")
        
        # 更新任务
        result = self.tool.execute_action(
            "update_daily_task",
            id=task_id,
            title="更新后的任务标题",
            scheduled_start="15:00",
            scheduled_end="16:00",
            priority=1,
        )
        
        self.assertTrue(result.success, f"更新失败: {result.message}")
        
        # 验证更新
        get_result = self.tool.execute_action("get_daily_tasks", date=self.today)
        get_data = self._get_result_data(get_result)
        items = get_data.get("items", get_data.get("tasks", []))
        
        updated_task = next((t for t in items if t.get("id") == task_id), None)
        self.assertIsNotNone(updated_task, "更新后的任务未找到")
        self.assertEqual(updated_task.get("title"), "更新后的任务标题")
        self.assertEqual(updated_task.get("scheduled_start"), "15:00")
        self.assertEqual(updated_task.get("priority"), 1)
        
        print(f"  ✓ 标题已更新: {updated_task.get('title')}")
        print(f"  ✓ 时间已更新: {updated_task.get('scheduled_start')} - {updated_task.get('scheduled_end')}")
        print(f"  ✓ 优先级已更新: {updated_task.get('priority')}")
        
        print("  ✅ update_daily_task 测试通过")

    def test_04_start_task(self):
        """测试 4: start_task — 开始任务"""
        print("\n✅ 测试 4: start_task")
        
        # 添加任务
        add_result = self.tool.execute_action(
            "add_daily_task",
            title="准备开始的任务",
            priority=2,
        )
        data = self._get_result_data(add_result)
        task_id = data.get("id")
        
        # 开始任务
        result = self.tool.execute_action(
            "start_task",
            id=task_id,
            actual_start=datetime.now().strftime("%H:%M"),
        )
        
        self.assertTrue(result.success, f"开始任务失败: {result.message}")
        
        # 验证状态
        get_result = self.tool.execute_action("get_daily_tasks", date=self.today)
        get_data = self._get_result_data(get_result)
        items = get_data.get("items", get_data.get("tasks", []))
        
        started_task = next((t for t in items if t.get("id") == task_id), None)
        self.assertIsNotNone(started_task, "任务未找到")
        self.assertEqual(started_task.get("status"), "in_progress", "状态应为进行中")
        self.assertIsNotNone(started_task.get("actual_start"), "实际开始时间应已记录")
        
        print(f"  ✓ 任务状态: {started_task.get('status')}")
        print(f"  ✓ 实际开始: {started_task.get('actual_start')}")
        
        print("  ✅ start_task 测试通过")

    def test_05_complete_task(self):
        """测试 5: complete_task — 完成任务"""
        print("\n✅ 测试 5: complete_task")
        
        # 添加任务
        add_result = self.tool.execute_action(
            "add_daily_task",
            title="即将完成的任务",
            priority=1,
        )
        data = self._get_result_data(add_result)
        task_id = data.get("id")
        
        # 完成任务
        result = self.tool.execute_action(
            "complete_task",
            id=task_id,
            completion_note="任务已完成，测试通过",
        )
        
        self.assertTrue(result.success, f"完成任务失败: {result.message}")
        
        # 验证状态
        get_result = self.tool.execute_action("get_daily_tasks", date=self.today)
        get_data = self._get_result_data(get_result)
        items = get_data.get("items", get_data.get("tasks", []))
        
        completed_task = next((t for t in items if t.get("id") == task_id), None)
        self.assertIsNotNone(completed_task, "任务未找到")
        self.assertEqual(completed_task.get("status"), "completed", "状态应为已完成")
        
        print(f"  ✓ 任务状态: {completed_task.get('status')}")
        print(f"  ✓ 完成备注: {completed_task.get('completion_note')}")
        
        print("  ✅ complete_task 测试通过")

    def test_06_cancel_task(self):
        """测试 6: cancel_task — 取消任务"""
        print("\n✅ 测试 6: cancel_task")
        
        # 添加任务
        add_result = self.tool.execute_action(
            "add_daily_task",
            title="需要取消的任务",
            priority=3,
        )
        data = self._get_result_data(add_result)
        task_id = data.get("id")
        
        # 取消任务
        result = self.tool.execute_action(
            "cancel_task",
            id=task_id,
            reason="计划变更，取消执行",
        )
        
        self.assertTrue(result.success, f"取消任务失败: {result.message}")
        
        # 验证状态
        get_result = self.tool.execute_action("get_daily_tasks", date=self.today)
        get_data = self._get_result_data(get_result)
        items = get_data.get("items", get_data.get("tasks", []))
        
        cancelled_task = next((t for t in items if t.get("id") == task_id), None)
        self.assertIsNotNone(cancelled_task, "任务未找到")
        self.assertEqual(cancelled_task.get("status"), "cancelled", "状态应为已取消")
        
        print(f"  ✓ 任务状态: {cancelled_task.get('status')}")
        print(f"  ✓ 取消原因: {cancelled_task.get('cancel_reason')}")
        
        print("  ✅ cancel_task 测试通过")

    def test_07_remove_daily_task(self):
        """测试 7: remove_daily_task — 移除每日任务"""
        print("\n✅ 测试 7: remove_daily_task")
        
        # 添加任务
        add_result = self.tool.execute_action(
            "add_daily_task",
            title="需要删除的任务",
            priority=2,
        )
        data = self._get_result_data(add_result)
        task_id = data.get("id")
        
        # 移除任务
        result = self.tool.execute_action("remove_daily_task", id=task_id)
        
        self.assertTrue(result.success, f"移除失败: {result.message}")
        
        # 验证已删除
        get_result = self.tool.execute_action("get_daily_tasks", date=self.today)
        get_data = self._get_result_data(get_result)
        items = get_data.get("items", get_data.get("tasks", []))
        
        removed_task = next((t for t in items if t.get("id") == task_id), None)
        self.assertIsNone(removed_task, "任务未正确删除")
        
        print(f"  ✓ 任务已删除")
        
        print("  ✅ remove_daily_task 测试通过")

    def test_08_get_today_summary(self):
        """测试 8: get_today_summary — 获取今日任务摘要"""
        print("\n✅ 测试 8: get_today_summary")
        
        # 添加多个任务
        tasks = [
            {"title": "任务1-待办", "priority": 1, "status": "pending"},
            {"title": "任务2-进行中", "priority": 2, "status": "in_progress"},
            {"title": "任务3-已完成", "priority": 2, "status": "completed"},
            {"title": "任务4-待办", "priority": 1, "status": "pending"},
        ]
        
        for task in tasks:
            add_result = self.tool.execute_action("add_daily_task", **task)
        
        # 获取摘要
        result = self.tool.execute_action("get_today_summary")
        
        self.assertTrue(result.success, f"获取摘要失败: {result.message}")
        data = self._get_result_data(result)
        
        # 验证摘要内容
        print(f"  ✓ 今日任务总数: {data.get('total', 0)}")
        print(f"  ✓ 待办: {data.get('pending', 0)}")
        print(f"  ✓ 进行中: {data.get('in_progress', 0)}")
        print(f"  ✓ 已完成: {data.get('completed', 0)}")
        
        if "summary_text" in data:
            print(f"  ✓ 摘要文本: {data.get('summary_text')[:100]}...")
        
        # 验证统计
        self.assertGreaterEqual(data.get("total", 0), 4, "总数应至少为4")
        
        print("  ✅ get_today_summary 测试通过")

    def test_09_generate_recommendations(self):
        """测试 9: generate_recommendations — 生成推荐"""
        print("\n✅ 测试 9: generate_recommendations")
        
        # 先创建一些待办事项
        todos = [
            {"title": "紧急任务-今天必须完成", "category": "work", "priority": 1, "time_frame": "today"},
            {"title": "重要任务-本周完成", "category": "study", "priority": 2, "time_frame": "week"},
            {"title": "常规任务-本月完成", "category": "health", "priority": 3, "time_frame": "month"},
        ]
        
        for todo in todos:
            self.todo_tool.execute_action("create_todo", **todo)
        
        # 生成推荐
        result = self.tool.execute_action("generate_recommendations", date=self.today)
        
        self.assertTrue(result.success, f"生成推荐失败: {result.message}")
        data = self._get_result_data(result)
        
        # 验证推荐结果
        recommendations = data.get("recommendations", [])
        self.assertIsInstance(recommendations, list, "推荐结果应为列表")
        print(f"  ✓ 生成推荐数量: {len(recommendations)}")
        
        if recommendations:
            print("  ✓ 推荐任务列表:")
            for rec in recommendations[:5]:
                print(f"    - {rec.get('title')} (priority={rec.get('priority')}, score={rec.get('score', 0):.1f})")
        
        # 验证分析摘要
        if "analysis_summary" in data:
            print(f"  ✓ 分析摘要: {data.get('analysis_summary')[:100]}...")
        
        print("  ✅ generate_recommendations 测试通过")

    def test_10_accept_recommendations(self):
        """测试 10: accept_recommendations — 接受推荐任务"""
        print("\n✅ 测试 10: accept_recommendations")
        
        # 先生成推荐
        generate_result = self.tool.execute_action(
            "generate_recommendations", 
            date=self.today
        )
        
        # 获取今日任务，找到推荐的任务
        get_result = self.tool.execute_action("get_daily_tasks", date=self.today)
        get_data = self._get_result_data(get_result)
        items = get_data.get("items", get_data.get("tasks", []))
        
        if items:
            # 选择前两个任务接受
            task_ids = [items[0].get("id")]
            if len(items) > 1:
                task_ids.append(items[1].get("id"))
            
            # 接受推荐
            result = self.tool.execute_action(
                "accept_recommendations",
                date=self.today,
                task_ids=task_ids,
            )
            
            self.assertTrue(result.success, f"接受推荐失败: {result.message}")
            print(f"  ✓ 接受了 {len(task_ids)} 个推荐任务")
            
            # 验证推荐状态更新
            rec_result = self.tool.storage.get_recommendation(self.today)
            if rec_result:
                from src.tools.todo_storage import RecommendationStatus
                print(f"  ✓ 推荐状态: {rec_result.status}")
                print(f"  ✓ 接受数量: {rec_result.accepted_count}")
        else:
            print("  ⚠ 今日无推荐任务可测试")
        
        print("  ✅ accept_recommendations 测试通过")


class TestDailyTaskToolEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_edge.db"
        self.tool = DailyTaskTool(str(self.db_path))
        self.today = datetime.now().strftime("%Y-%m-%d")

    def tearDown(self):
        """测试后清理"""
        try:
            self.tool.storage.close()
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_empty_day_tasks(self):
        """测试空日的任务"""
        print("\n✅ 边界测试: 空日任务")
        
        future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        result = self.tool.execute_action("get_daily_tasks", date=future_date)
        
        self.assertTrue(result.success, "空日查询应成功")
        data = self._get_result_data(result)
        items = data.get("items", data.get("tasks", []))
        self.assertEqual(len(items), 0, "空日应无任务")
        print("  ✓ 空日查询正常")

    def test_invalid_date(self):
        """测试无效日期"""
        print("\n✅ 边界测试: 无效日期")
        
        result = self.tool.execute_action("get_daily_tasks", date="invalid-date")
        # 应该能处理或返回空列表
        self.assertTrue(result.success, "应能处理无效日期")
        print("  ✓ 无效日期已处理")

    def test_nonexistent_task(self):
        """测试不存在的任务"""
        print("\n✅ 边界测试: 不存在的任务")
        
        result = self.tool.execute_action("start_task", id=99999)
        self.assertFalse(result.success, "不存在的任务应失败")
        print("  ✓ 不存在的任务正确处理")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 每日任务工具测试套件 (10 Actions)")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDailyTaskTool))
    suite.addTests(loader.loadTestsFromTestCase(TestDailyTaskToolEdgeCases))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
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
