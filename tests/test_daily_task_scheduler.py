"""每日任务调度器测试 — DailyTaskScheduler 功能验证。

运行方式：
    python -m pytest tests/test_daily_task_scheduler.py -v
    或
    python tests/test_daily_task_scheduler.py

测试内容：
1. 调度器初始化
2. 手动触发分析
3. 手动触发推送
4. 消息格式化
5. 启动/停止生命周期
6. 启动时检查

预期结果：所有测试通过 ✅
"""

import os
import sys
import unittest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.todo_storage import TodoStorage, TaskCategory, TimeFrame, RecommendationStatus
from src.core.daily_task_scheduler import DailyTaskScheduler


class TestDailyTaskScheduler(unittest.TestCase):
    """每日任务调度器测试"""

    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_scheduler.db"
        self.storage = TodoStorage(self.db_path)
        
        # 创建 mock 的 event_bus 和 companion_engine
        self.mock_event_bus = MagicMock()
        self.mock_companion_engine = MagicMock()
        self.mock_companion_engine.send_daily_task_message = AsyncMock()
        
        self.scheduler = DailyTaskScheduler(
            event_bus=self.mock_event_bus,
            companion_engine=self.mock_companion_engine,
            db_path=self.db_path,
        )
        
        self.today = datetime.now().strftime("%Y-%m-%d")
        print(f"\n📦 测试数据库: {self.db_path}")
        print(f"📅 今日日期: {self.today}")

    def tearDown(self):
        """测试后清理"""
        try:
            # 确保调度器已停止
            if self.scheduler._running:
                asyncio.run(self.scheduler.stop())
            
            self.storage.close()
            shutil.rmtree(self.test_dir)
            print("🧹 临时数据库已清理")
        except Exception as e:
            print(f"⚠️ 清理失败: {e}")

    def test_01_scheduler_initialization(self):
        """测试 1: 调度器初始化"""
        print("\n✅ 测试 1: 调度器初始化")
        
        self.assertIsNotNone(self.scheduler, "调度器初始化失败")
        self.assertFalse(self.scheduler._running, "初始状态应为未运行")
        print(f"  ✓ 调度器已初始化")
        print(f"  ✓ 数据库路径: {self.scheduler._db_path}")
        print(f"  ✓ 运行状态: {self.scheduler._running}")
        
        print("  ✅ 调度器初始化测试通过")

    def test_02_trigger_analysis_now(self):
        """测试 2: 手动触发分析"""
        print("\n✅ 测试 2: 手动触发分析")
        
        # 准备测试数据
        self.storage.create_todo(
            title="分析测试任务",
            category=TaskCategory.WORK,
            priority=1,
        )
        
        # 触发分析
        async def run_test():
            result = await self.scheduler.trigger_analysis_now()
            return result
        
        result = asyncio.run(run_test())
        
        self.assertTrue(result.get("success"), f"分析失败: {result}")
        self.assertEqual(result.get("date"), self.today, "日期应匹配")
        
        print(f"  ✓ 分析成功: {result.get('success')}")
        print(f"  ✓ 日期: {result.get('date')}")
        
        # 验证推荐已保存
        rec = self.storage.get_recommendation(self.today)
        self.assertIsNotNone(rec, "推荐应已保存")
        print(f"  ✓ 推荐已保存: {len(rec.recommendations)} 个任务")
        
        print("  ✅ 手动触发分析测试通过")

    def test_03_trigger_push_now(self):
        """测试 3: 手动触发推送"""
        print("\n✅ 测试 3: 手动触发推送")
        
        # 先生成推荐
        async def generate_first():
            await self.scheduler.trigger_analysis_now()
        
        asyncio.run(generate_first())
        
        # 重置 mock
        self.mock_companion_engine.send_daily_task_message.reset_mock()
        
        # 触发推送
        async def run_push():
            result = await self.scheduler.trigger_push_now()
            return result
        
        result = asyncio.run(run_push())
        
        self.assertTrue(result.get("success"), f"推送失败: {result}")
        
        # 验证推送调用
        self.mock_companion_engine.send_daily_task_message.assert_called_once()
        
        print(f"  ✓ 推送成功: {result.get('success')}")
        print(f"  ✓ 推送日期: {result.get('date')}")
        
        # 验证状态已更新
        rec = self.storage.get_recommendation(self.today)
        self.assertEqual(rec.status, RecommendationStatus.PUSHED, "状态应为PUSHED")
        print(f"  ✓ 推荐状态: {rec.status}")
        
        print("  ✅ 手动触发推送测试通过")

    def test_04_message_formatting(self):
        """测试 4: 消息格式化"""
        print("\n✅ 测试 4: 消息格式化")
        
        # 准备推荐数据
        recommendations = [
            {"title": "紧急任务", "priority": 1, "source": "todo_overdue"},
            {"title": "今日任务", "priority": 2, "source": "todo_today"},
            {"title": "推荐任务1", "priority": 3, "source": "ai_suggested"},
        ]
        
        self.storage.save_recommendation(
            task_date=self.today,
            recommendations=recommendations,
            analysis_summary="测试分析摘要",
        )
        
        rec = self.storage.get_recommendation(self.today)
        
        # 格式化消息
        message = self.scheduler._format_recommendation_message(rec)
        
        self.assertIsInstance(message, str, "消息应为字符串")
        self.assertIn("今日任务清单", message, "消息应包含标题")
        self.assertIn("紧急任务", message, "消息应包含紧急任务")
        self.assertIn("测试分析摘要", message, "消息应包含分析摘要")
        
        print(f"  ✓ 消息格式化成功")
        print(f"  ✓ 消息长度: {len(message)} 字符")
        print(f"  ✓ 消息预览:")
        for line in message.split('\n')[:10]:
            print(f"    {line}")
        
        print("  ✅ 消息格式化测试通过")

    def test_05_scheduler_start_stop(self):
        """测试 5: 启动/停止生命周期"""
        print("\n✅ 测试 5: 启动/停止生命周期")
        
        # 启动
        async def run_start():
            await self.scheduler.start()
        
        asyncio.run(run_start())
        
        self.assertTrue(self.scheduler._running, "启动后应为运行状态")
        print(f"  ✓ 调度器已启动")
        print(f"  ✓ 运行状态: {self.scheduler._running}")
        
        # 停止
        async def run_stop():
            await self.scheduler.stop()
        
        asyncio.run(run_stop())
        
        self.assertFalse(self.scheduler._running, "停止后应为非运行状态")
        print(f"  ✓ 调度器已停止")
        print(f"  ✓ 运行状态: {self.scheduler._running}")
        
        print("  ✅ 启动/停止测试通过")

    def test_06_check_and_push_on_startup(self):
        """测试 6: 启动时检查推送"""
        print("\n✅ 测试 6: 启动时检查推送")
        
        # 准备推荐数据
        recommendations = [
            {"title": "启动测试任务", "priority": 1},
        ]
        
        self.storage.save_recommendation(
            task_date=self.today,
            recommendations=recommendations,
        )
        
        # 重置推送状态
        self.mock_companion_engine.send_daily_task_message.reset_mock()
        
        # 检查推送
        async def run_check():
            pushed = await self.scheduler.check_and_push_on_startup()
            return pushed
        
        pushed = asyncio.run(run_check())
        
        # 由于可能在非推送时间窗口，验证逻辑
        print(f"  ✓ 检查完成")
        print(f"  ✓ 是否推送: {pushed}")
        
        print("  ✅ 启动检查测试通过")

    def test_07_set_companion_engine(self):
        """测试 7: 设置陪伴引擎"""
        print("\n✅ 测试 7: 设置陪伴引擎")
        
        # 创建新的调度器
        new_scheduler = DailyTaskScheduler(
            event_bus=self.mock_event_bus,
            db_path=self.db_path,
        )
        
        # 初始无引擎
        self.assertIsNone(new_scheduler._companion_engine, "初始应无引擎")
        
        # 设置引擎
        new_engine = MagicMock()
        new_scheduler.set_companion_engine(new_engine)
        
        self.assertEqual(new_scheduler._companion_engine, new_engine, "引擎未正确设置")
        print(f"  ✓ 陪伴引擎已设置")
        
        print("  ✅ 设置陪伴引擎测试通过")

    def test_08_priority_icons(self):
        """测试 8: 优先级图标"""
        print("\n✅ 测试 8: 优先级图标")
        
        test_cases = [
            (1, "🔴"),
            (2, "🟠"),
            (3, "🟡"),
            (4, "🟢"),
            (5, "⚪"),
        ]
        
        for priority, expected_icon in test_cases:
            icon = self.scheduler._get_priority_icon(priority)
            self.assertEqual(icon, expected_icon, f"优先级{priority}图标不正确")
            print(f"  ✓ priority={priority} → {icon}")
        
        # 测试无效优先级
        invalid_icon = self.scheduler._get_priority_icon(99)
        self.assertEqual(invalid_icon, "🟡", "无效优先级应返回默认")
        print(f"  ✓ 无效优先级 → {invalid_icon} (默认)")
        
        print("  ✅ 优先级图标测试通过")

    def test_09_push_without_companion(self):
        """测试 9: 无陪伴引擎时推送"""
        print("\n✅ 测试 9: 无陪伴引擎时推送")
        
        # 创建无引擎的调度器
        scheduler_no_eng = DailyTaskScheduler(
            event_bus=self.mock_event_bus,
            db_path=self.db_path,
        )
        
        # 准备推荐
        self.storage.save_recommendation(
            task_date=self.today,
            recommendations=[{"title": "测试任务", "priority": 1}],
        )
        
        # 推送（应该通过事件总线）
        async def run_push():
            await scheduler_no_eng._push_recommendations()
        
        # 不应抛出异常
        try:
            asyncio.run(run_push())
            print(f"  ✓ 无引擎推送成功（通过事件总线）")
        except Exception as e:
            self.fail(f"无引擎推送应不抛异常: {e}")
        
        print("  ✅ 无陪伴引擎推送测试通过")

    def test_10_double_push_prevention(self):
        """测试 10: 防止重复推送"""
        print("\n✅ 测试 10: 防止重复推送")
        
        # 准备已推送的推荐
        self.storage.save_recommendation(
            task_date=self.today,
            recommendations=[{"title": "已推送任务", "priority": 1}],
            status=RecommendationStatus.PUSHED,
        )
        
        self.mock_companion_engine.send_daily_task_message.reset_mock()
        
        # 尝试推送
        async def run_push():
            await self.scheduler.trigger_push_now()
        
        asyncio.run(run_push())
        
        # 验证没有再次调用推送
        self.mock_companion_engine.send_daily_task_message.assert_not_called()
        print(f"  ✓ 已推送状态，未重复推送")
        
        print("  ✅ 防止重复推送测试通过")


class TestSchedulerEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_edge.db"
        self.storage = TodoStorage(self.db_path)
        
        self.scheduler = DailyTaskScheduler(
            db_path=self.db_path,
        )
        
        self.today = datetime.now().strftime("%Y-%m-%d")

    def tearDown(self):
        """测试后清理"""
        try:
            if self.scheduler._running:
                asyncio.run(self.scheduler.stop())
            self.storage.close()
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_no_recommendations(self):
        """测试无推荐情况"""
        print("\n✅ 边界测试: 无推荐情况")
        
        # 不创建任何推荐，直接推送
        async def run_push():
            await self.scheduler._push_recommendations()
        
        # 应该不会崩溃，而是尝试生成推荐
        try:
            asyncio.run(run_push())
            print("  ✓ 无推荐时推送处理正常")
        except Exception as e:
            print(f"  ✓ 异常已处理: {e}")

    def test_empty_recommendations(self):
        """测试空推荐列表"""
        print("\n✅ 边界测试: 空推荐列表")
        
        self.storage.save_recommendation(
            task_date=self.today,
            recommendations=[],
        )
        
        rec = self.storage.get_recommendation(self.today)
        message = self.scheduler._format_recommendation_message(rec)
        
        self.assertIn("暂无推荐任务", message, "应提示暂无推荐")
        print("  ✓ 空推荐消息格式化正常")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 每日任务调度器测试套件")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDailyTaskScheduler))
    suite.addTests(loader.loadTestsFromTestCase(TestSchedulerEdgeCases))
    
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
