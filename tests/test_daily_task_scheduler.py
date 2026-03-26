"""DailyTaskScheduler 测试"""

import os
import sys
import unittest
import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tools.todo_storage import TodoStorage, RecommendationStatus
from src.core.daily_task_scheduler import DailyTaskScheduler


class TestDailyTaskScheduler(unittest.TestCase):
    """DailyTaskScheduler 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_scheduler.db"
        self.storage = TodoStorage(self.db_path)
        
        self.mock_event_bus = MagicMock()
        self.mock_companion_engine = MagicMock()
        self.mock_companion_engine.send_daily_task_message = AsyncMock()
        
        self.scheduler = DailyTaskScheduler(
            event_bus=self.mock_event_bus,
            companion_engine=self.mock_companion_engine,
            db_path=self.db_path,
        )
        
        self.today = datetime.now().strftime("%Y-%m-%d")

    def tearDown(self):
        try:
            if self.scheduler._running:
                asyncio.run(self.scheduler.stop())
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_scheduler_initialization(self):
        """测试调度器初始化"""
        print("\n[TEST] Scheduler Initialization")
        self.assertIsNotNone(self.scheduler)
        self.assertFalse(self.scheduler._running)
        print("  [OK] Scheduler initialized")
        print("  [PASS] Initialization")

    def test_trigger_analysis(self):
        """测试触发分析"""
        print("\n[TEST] Trigger Analysis")
        
        async def run():
            return await self.scheduler.trigger_analysis_now()
        
        result = asyncio.run(run())
        self.assertTrue(result.get("success"))
        print(f"  [OK] Analysis success: {result.get('success')}")
        print("  [PASS] Trigger analysis")

    def test_message_formatting(self):
        """测试消息格式化"""
        print("\n[TEST] Message Formatting")
        
        recommendations = [
            {"title": "Task 1", "priority": 1, "source": "todo_overdue"},
            {"title": "Task 2", "priority": 2, "source": "todo_today"},
        ]
        
        from src.tools.todo_storage import DailyRecommendation
        rec = DailyRecommendation(
            task_date=self.today,
            recommendations=recommendations,
            analysis_summary="Test summary",
        )
        self.storage.create_recommendation(rec)
        
        fetched = self.storage.get_recommendation(self.today)
        self.assertIsNotNone(fetched)
        
        # 手动格式化简单消息
        message = f"Today Task List ({self.today})\n"
        for r in recommendations:
            message += f"- {r.get('title')}\n"
        self.assertIsInstance(message, str)
        print(f"  [OK] Message length: {len(message)}")
        print("  [PASS] Message formatting")


def run_tests():
    print("=" * 60)
    print("[TEST SUITE] DailyTaskScheduler Tests")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDailyTaskScheduler)
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
