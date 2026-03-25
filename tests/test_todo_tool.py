"""待办事项工具测试 — TodoTool 10个Actions功能验证。

运行方式：
    python -m pytest tests/test_todo_tool.py -v
    或
    python tests/test_todo_tool.py

测试内容：
1. create_todo — 创建待办事项
2. update_todo — 更新待办事项
3. delete_todo — 删除待办事项
4. get_todo — 获取单个待办事项详情
5. list_todos — 列出待办事项（支持筛选）
6. complete_todo — 完成待办事项
7. cancel_todo — 取消待办事项
8. decompose_todo — 分解任务为子任务
9. get_overdue_todos — 获取过期未完成任务
10. get_upcoming_todos — 获取即将到期任务

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

from src.tools.todo import TodoTool


class TestTodoTool(unittest.TestCase):
    """待办事项工具测试"""

    def setUp(self):
        """测试前准备：创建临时数据库"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_todo_tool.db"
        self.tool = TodoTool(str(self.db_path))
        print(f"\n📦 测试数据库: {self.db_path}")

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

    def test_01_create_todo(self):
        """测试 1: create_todo — 创建待办事项"""
        print("\n✅ 测试 1: create_todo")
        
        result = self.tool.execute_action(
            "create_todo",
            title="完成项目报告",
            description="需要在本周五前完成季度总结",
            category="work",
            time_frame="week",
            priority=1,
            deadline=(datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M"),
            tags=["重要", "季度"],
        )
        
        self.assertTrue(result.success, f"创建失败: {result.message}")
        data = self._get_result_data(result)
        self.assertIn("id", data, "返回结果缺少id")
        self.assertEqual(data.get("title"), "完成项目报告")
        print(f"  ✓ 创建待办事项: ID={data.get('id')}")
        print(f"  ✓ 返回消息: {result.message}")
        
        # 保存ID用于后续测试
        self._test_todo_id = data.get("id")
        
        print("  ✅ create_todo 测试通过")

    def test_02_get_todo(self):
        """测试 2: get_todo — 获取单个待办事项详情"""
        print("\n✅ 测试 2: get_todo")
        
        # 先创建
        if not hasattr(self, '_test_todo_id'):
            create_result = self.tool.execute_action(
                "create_todo",
                title="获取测试任务",
                category="study",
            )
            data = self._get_result_data(create_result)
            self._test_todo_id = data.get("id")
        
        # 获取
        result = self.tool.execute_action("get_todo", id=self._test_todo_id)
        
        self.assertTrue(result.success, f"获取失败: {result.message}")
        data = self._get_result_data(result)
        self.assertEqual(data.get("id"), self._test_todo_id)
        self.assertEqual(data.get("title"), "获取测试任务")
        print(f"  ✓ 获取待办事项: {data.get('title')}")
        print(f"  ✓ 详情: category={data.get('category')}, priority={data.get('priority')}")
        
        print("  ✅ get_todo 测试通过")

    def test_03_update_todo(self):
        """测试 3: update_todo — 更新待办事项"""
        print("\n✅ 测试 3: update_todo")
        
        # 先创建
        create_result = self.tool.execute_action(
            "create_todo",
            title="更新测试任务",
            category="general",
            priority=3,
        )
        data = self._get_result_data(create_result)
        todo_id = data.get("id")
        
        # 更新
        result = self.tool.execute_action(
            "update_todo",
            id=todo_id,
            title="更新后的标题",
            priority=1,
            status="in_progress",
            description="这是更新后的描述",
        )
        
        self.assertTrue(result.success, f"更新失败: {result.message}")
        
        # 验证更新
        get_result = self.tool.execute_action("get_todo", id=todo_id)
        updated_data = self._get_result_data(get_result)
        
        self.assertEqual(updated_data.get("title"), "更新后的标题")
        self.assertEqual(updated_data.get("priority"), 1)
        self.assertEqual(updated_data.get("status"), "in_progress")
        print("  ✓ 标题已更新")
        print("  ✓ 优先级已更新为1")
        print("  ✓ 状态已更新为进行中")
        
        print("  ✅ update_todo 测试通过")

    def test_04_list_todos(self):
        """测试 4: list_todos — 列出待办事项"""
        print("\n✅ 测试 4: list_todos")
        
        # 创建多个测试任务
        test_tasks = [
            {"title": "列表测试-工作1", "category": "work", "priority": 1},
            {"title": "列表测试-工作2", "category": "work", "priority": 2},
            {"title": "列表测试-学习1", "category": "study", "priority": 1},
            {"title": "列表测试-健康1", "category": "health", "priority": 3},
        ]
        
        for task in test_tasks:
            self.tool.execute_action("create_todo", **task)
        
        # 按类型筛选
        result = self.tool.execute_action("list_todos", category="work")
        self.assertTrue(result.success, f"筛选失败: {result.message}")
        data = self._get_result_data(result)
        items = data.get("items", data.get("todos", []))
        work_count = len(items)
        self.assertEqual(work_count, 2, f"工作类型筛选失败，期望2个，实际{work_count}个")
        print(f"  ✓ 按类型筛选(work): {work_count} 个")
        
        # 按优先级筛选
        result = self.tool.execute_action("list_todos", priority=1)
        data = self._get_result_data(result)
        items = data.get("items", data.get("todos", []))
        high_priority_count = len(items)
        self.assertEqual(high_priority_count, 2, f"优先级筛选失败")
        print(f"  ✓ 按优先级筛选(最高): {high_priority_count} 个")
        
        # 搜索
        result = self.tool.execute_action("list_todos", search="列表测试-工作")
        data = self._get_result_data(result)
        items = data.get("items", data.get("todos", []))
        search_count = len(items)
        self.assertEqual(search_count, 2, f"搜索失败")
        print(f"  ✓ 搜索「列表测试-工作」: {search_count} 个")
        
        # 全部列出
        result = self.tool.execute_action("list_todos")
        data = self._get_result_data(result)
        items = data.get("items", data.get("todos", []))
        print(f"  ✓ 全部待办事项: {len(items)} 个")
        
        print("  ✅ list_todos 测试通过")

    def test_05_complete_todo(self):
        """测试 5: complete_todo — 完成待办事项"""
        print("\n✅ 测试 5: complete_todo")
        
        # 创建任务
        create_result = self.tool.execute_action(
            "create_todo",
            title="需要完成的任务",
            category="work",
        )
        data = self._get_result_data(create_result)
        todo_id = data.get("id")
        
        # 完成任务
        result = self.tool.execute_action(
            "complete_todo",
            id=todo_id,
            completion_note="已完成，测试通过",
        )
        
        self.assertTrue(result.success, f"完成失败: {result.message}")
        
        # 验证状态
        get_result = self.tool.execute_action("get_todo", id=todo_id)
        data = self._get_result_data(get_result)
        self.assertEqual(data.get("status"), "completed", "状态未变为completed")
        self.assertIsNotNone(data.get("completed_at"), "完成时间未记录")
        print(f"  ✓ 任务状态: {data.get('status')}")
        print(f"  ✓ 完成时间: {data.get('completed_at')}")
        print(f"  ✓ 完成备注: {data.get('completion_note')}")
        
        print("  ✅ complete_todo 测试通过")

    def test_06_cancel_todo(self):
        """测试 6: cancel_todo — 取消待办事项"""
        print("\n✅ 测试 6: cancel_todo")
        
        # 创建任务
        create_result = self.tool.execute_action(
            "create_todo",
            title="需要取消的任务",
            category="study",
        )
        data = self._get_result_data(create_result)
        todo_id = data.get("id")
        
        # 取消任务
        result = self.tool.execute_action(
            "cancel_todo",
            id=todo_id,
            reason="计划变更，不需要了",
        )
        
        self.assertTrue(result.success, f"取消失败: {result.message}")
        
        # 验证状态
        get_result = self.tool.execute_action("get_todo", id=todo_id)
        data = self._get_result_data(get_result)
        self.assertEqual(data.get("status"), "cancelled", "状态未变为cancelled")
        print(f"  ✓ 任务状态: {data.get('status')}")
        print(f"  ✓ 取消原因: {data.get('cancel_reason', '计划变更，不需要了')}")
        
        print("  ✅ cancel_todo 测试通过")

    def test_07_delete_todo(self):
        """测试 7: delete_todo — 删除待办事项"""
        print("\n✅ 测试 7: delete_todo")
        
        # 创建任务
        create_result = self.tool.execute_action(
            "create_todo",
            title="需要删除的任务",
            category="general",
        )
        data = self._get_result_data(create_result)
        todo_id = data.get("id")
        
        # 删除任务
        result = self.tool.execute_action("delete_todo", id=todo_id)
        
        self.assertTrue(result.success, f"删除失败: {result.message}")
        
        # 验证已删除
        get_result = self.tool.execute_action("get_todo", id=todo_id)
        data = self._get_result_data(get_result)
        self.assertIsNone(data.get("id"), "任务未正确删除")
        print(f"  ✓ 任务已删除")
        
        print("  ✅ delete_todo 测试通过")

    def test_08_decompose_todo(self):
        """测试 8: decompose_todo — 分解任务"""
        print("\n✅ 测试 8: decompose_todo")
        
        # 创建主任务
        create_result = self.tool.execute_action(
            "create_todo",
            title="项目A",
            category="work",
            time_frame="month",
            priority=1,
        )
        data = self._get_result_data(create_result)
        parent_id = data.get("id")
        
        # 定义子任务
        subtasks = [
            {"title": "子任务1-需求分析", "priority": 1},
            {"title": "子任务2-系统设计", "priority": 2},
            {"title": "子任务3-编码开发", "priority": 2},
            {"title": "子任务4-测试验收", "priority": 3},
        ]
        
        # 分解任务
        result = self.tool.execute_action(
            "decompose_todo",
            id=parent_id,
            subtasks=subtasks,
        )
        
        self.assertTrue(result.success, f"分解失败: {result.message}")
        
        # 获取主任务详情，验证子任务
        get_result = self.tool.execute_action("get_todo", id=parent_id)
        data = self._get_result_data(get_result)
        
        # 列出所有任务，查找该父任务的所有子任务
        list_result = self.tool.execute_action("list_todos")
        list_data = self._get_result_data(list_result)
        items = list_data.get("items", list_data.get("todos", []))
        
        children = [t for t in items if t.get("parent_id") == parent_id]
        self.assertEqual(len(children), 4, f"子任务数量不正确，期望4个，实际{len(children)}个")
        print(f"  ✓ 分解为 {len(children)} 个子任务")
        
        for child in children:
            print(f"    - {child.get('title')} (priority={child.get('priority')})")
        
        print("  ✅ decompose_todo 测试通过")

    def test_09_get_overdue_todos(self):
        """测试 9: get_overdue_todos — 获取过期任务"""
        print("\n✅ 测试 9: get_overdue_todos")
        
        # 创建已过期的任务
        overdue_deadline = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
        self.tool.execute_action(
            "create_todo",
            title="已过期任务1",
            category="work",
            deadline=overdue_deadline,
        )
        
        self.tool.execute_action(
            "create_todo",
            title="已过期任务2",
            category="study",
            deadline=overdue_deadline,
        )
        
        # 创建未过期的任务
        future_deadline = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
        self.tool.execute_action(
            "create_todo",
            title="未过期任务",
            category="health",
            deadline=future_deadline,
        )
        
        # 获取过期任务
        result = self.tool.execute_action("get_overdue_todos")
        
        self.assertTrue(result.success, f"获取失败: {result.message}")
        data = self._get_result_data(result)
        items = data.get("items", data.get("todos", []))
        
        # 过滤出未完成且已过期的
        overdue_count = len([t for t in items if t.get("status") != "completed"])
        self.assertGreaterEqual(overdue_count, 2, "过期任务数量不正确")
        print(f"  ✓ 过期任务数量: {overdue_count}")
        
        for task in items[:3]:
            print(f"    - {task.get('title')} (deadline: {task.get('deadline')})")
        
        print("  ✅ get_overdue_todos 测试通过")

    def test_10_get_upcoming_todos(self):
        """测试 10: get_upcoming_todos — 获取即将到期任务"""
        print("\n✅ 测试 10: get_upcoming_todos")
        
        # 创建即将到期的任务(3天内)
        near_deadline = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
        self.tool.execute_action(
            "create_todo",
            title="即将到期任务-紧急",
            category="work",
            priority=1,
            deadline=near_deadline,
        )
        
        # 创建较远到期的任务
        far_deadline = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M")
        self.tool.execute_action(
            "create_todo",
            title="较远到期任务",
            category="study",
            deadline=far_deadline,
        )
        
        # 获取3天内即将到期的任务
        result = self.tool.execute_action("get_upcoming_todos", days=3)
        
        self.assertTrue(result.success, f"获取失败: {result.message}")
        data = self._get_result_data(result)
        items = data.get("items", data.get("todos", []))
        
        # 过滤未完成的任务
        upcoming = [t for t in items if t.get("status") != "completed"]
        self.assertGreaterEqual(len(upcoming), 1, "即将到期任务数量不正确")
        print(f"  ✓ 即将到期(3天内)任务数量: {len(upcoming)}")
        
        for task in upcoming:
            print(f"    - {task.get('title')} (deadline: {task.get('deadline')})")
        
        # 测试7天
        result_7 = self.tool.execute_action("get_upcoming_todos", days=7)
        data_7 = self._get_result_data(result_7)
        items_7 = data_7.get("items", data_7.get("todos", []))
        upcoming_7 = [t for t in items_7 if t.get("status") != "completed"]
        print(f"  ✓ 即将到期(7天内)任务数量: {len(upcoming_7)}")
        
        print("  ✅ get_upcoming_todos 测试通过")


class TestTodoToolEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_edge.db"
        self.tool = TodoTool(str(self.db_path))

    def tearDown(self):
        """测试后清理"""
        try:
            self.tool.storage.close()
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_empty_params_create(self):
        """测试空参数创建"""
        print("\n✅ 边界测试: 空参数创建")
        
        # 最小参数
        result = self.tool.execute_action("create_todo", title="最小参数任务")
        self.assertTrue(result.success, "最小参数应成功创建")
        print("  ✓ 最小参数创建成功")
        
    def test_invalid_priority(self):
        """测试无效优先级"""
        print("\n✅ 边界测试: 无效优先级")
        
        result = self.tool.execute_action(
            "create_todo",
            title="测试优先级",
            priority=10,  # 无效优先级
        )
        # 应该使用默认值或处理边界值
        self.assertTrue(result.success, "应能处理无效优先级")
        print("  ✓ 无效优先级已处理")

    def test_nonexistent_id(self):
        """测试不存在的ID"""
        print("\n✅ 边界测试: 不存在的ID")
        
        result = self.tool.execute_action("get_todo", id=99999)
        self.assertFalse(result.success, "不存在的ID应返回失败")
        print("  ✓ 不存在的ID正确处理")

    def test_invalid_action(self):
        """测试无效动作"""
        print("\n✅ 边界测试: 无效动作")
        
        result = self.tool.execute_action("invalid_action")
        self.assertFalse(result.success, "无效动作应返回失败")
        print("  ✓ 无效动作正确处理")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 待办事项工具测试套件 (10 Actions)")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestTodoTool))
    suite.addTests(loader.loadTestsFromTestCase(TestTodoToolEdgeCases))
    
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
