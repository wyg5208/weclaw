"""智能分析引擎测试 — TaskAnalyzer 功能验证。

运行方式：
    python -m pytest tests/test_task_analyzer.py -v
    或
    python tests/test_task_analyzer.py

测试内容：
1. 初始化与数据库连接
2. 待办事项分析
3. 过期任务识别
4. 即将到期任务分析
5. 优先级排序
6. 推荐算法验证
7. 综合分析生成

预期结果：所有测试通过 ✅
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

from src.tools.todo_storage import TodoStorage, TaskCategory, TimeFrame, TodoStatus
from src.core.task_analyzer import TaskAnalyzer


class TestTaskAnalyzer(unittest.TestCase):
    """智能分析引擎测试"""

    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test_analyzer.db"
        self.storage = TodoStorage(self.db_path)
        self.analyzer = TaskAnalyzer(self.db_path)
        
        self.today = datetime.now().strftime("%Y-%m-%d")
        print(f"\n📦 测试数据库: {self.db_path}")
        print(f"📅 今日日期: {self.today}")

    def tearDown(self):
        """测试后清理"""
        try:
            self.storage.close()
            shutil.rmtree(self.test_dir)
            print("🧹 临时数据库已清理")
        except Exception as e:
            print(f"⚠️ 清理失败: {e}")

    def test_01_analyzer_initialization(self):
        """测试 1: 分析器初始化"""
        print("\n✅ 测试 1: 分析器初始化")
        
        self.assertIsNotNone(self.analyzer, "分析器初始化失败")
        self.assertIsNotNone(self.analyzer._db_path, "数据库路径未设置")
        print(f"  ✓ 分析器已初始化")
        print(f"  ✓ 数据库路径: {self.analyzer._db_path}")
        
        print("  ✅ 分析器初始化测试通过")

    def test_02_analyze_overdue_todos(self):
        """测试 2: 分析过期待办事项"""
        print("\n✅ 测试 2: 分析过期待办事项")
        
        # 创建过期任务
        overdue_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
        self.storage.create_todo(
            title="已过期任务-紧急",
            category=TaskCategory.WORK,
            priority=1,
            deadline=overdue_date,
            status=TodoStatus.PENDING,
        )
        
        self.storage.create_todo(
            title="已过期任务-普通",
            category=TaskCategory.STUDY,
            priority=3,
            deadline=overdue_date,
            status=TodoStatus.PENDING,
        )
        
        # 分析
        overdue = self.analyzer._analyze_overdue_todos()
        
        self.assertIsInstance(overdue, list, "过期任务应为列表")
        self.assertGreaterEqual(len(overdue), 2, "应识别至少2个过期任务")
        print(f"  ✓ 识别过期任务: {len(overdue)} 个")
        
        for task in overdue:
            print(f"    - {task.get('title')} (priority={task.get('priority')})")
        
        print("  ✅ 过期任务分析测试通过")

    def test_03_analyze_upcoming_todos(self):
        """测试 3: 分析即将到期任务"""
        print("\n✅ 测试 3: 分析即将到期任务")
        
        # 创建3天内到期的任务
        near_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
        self.storage.create_todo(
            title="即将到期-高优先",
            category=TaskCategory.WORK,
            priority=1,
            deadline=near_date,
        )
        
        self.storage.create_todo(
            title="即将到期-中优先",
            category=TaskCategory.HEALTH,
            priority=2,
            deadline=near_date,
        )
        
        # 创建较远到期的任务
        far_date = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d %H:%M")
        self.storage.create_todo(
            title="较远到期",
            category=TaskCategory.STUDY,
            deadline=far_date,
        )
        
        # 分析
        upcoming = self.analyzer._analyze_upcoming_todos(days=3)
        
        self.assertIsInstance(upcoming, list, "即将到期任务应为列表")
        print(f"  ✓ 即将到期(3天内): {len(upcoming)} 个")
        
        for task in upcoming:
            print(f"    - {task.get('title')} (deadline: {task.get('deadline')})")
        
        print("  ✅ 即将到期分析测试通过")

    def test_04_analyze_today_todos(self):
        """测试 4: 分析今日任务"""
        print("\n✅ 测试 4: 分析今日任务")
        
        # 创建今日任务
        self.storage.create_todo(
            title="今日任务-工作",
            category=TaskCategory.WORK,
            time_frame=TimeFrame.TODAY,
            priority=1,
        )
        
        self.storage.create_todo(
            title="今日任务-学习",
            category=TaskCategory.STUDY,
            time_frame=TimeFrame.TODAY,
            priority=2,
        )
        
        # 分析
        today_tasks = self.analyzer._analyze_today_todos()
        
        self.assertIsInstance(today_tasks, list, "今日任务应为列表")
        self.assertGreaterEqual(len(today_tasks), 2, "应识别至少2个今日任务")
        print(f"  ✓ 今日任务: {len(today_tasks)} 个")
        
        for task in today_tasks:
            print(f"    - {task.get('title')} ({task.get('category')})")
        
        print("  ✅ 今日任务分析测试通过")

    def test_05_priority_scoring(self):
        """测试 5: 优先级评分"""
        print("\n✅ 测试 5: 优先级评分")
        
        # 创建不同优先级的任务
        tasks = [
            {"title": "最高优先", "priority": 1},
            {"title": "高优先", "priority": 2},
            {"title": "中优先", "priority": 3},
            {"title": "低优先", "priority": 4},
            {"title": "最低优先", "priority": 5},
        ]
        
        for task in tasks:
            self.storage.create_todo(
                title=task["title"],
                priority=task["priority"],
                category=TaskCategory.GENERAL,
            )
        
        # 排序
        todos = self.storage.list_todos()
        scored = self.analyzer._score_tasks(todos)
        
        self.assertEqual(len(scored), 5, "评分任务数量不正确")
        
        # 最高分应该是优先级1的任务
        top_task = scored[0]
        self.assertEqual(top_task.get("title"), "最高优先", "最高分应该是最高优先级任务")
        self.assertGreater(top_task.get("score", 0), 0, "应有正分数")
        
        print(f"  ✓ 评分任务数: {len(scored)}")
        print(f"  ✓ 最高分任务: {top_task.get('title')} (score={top_task.get('score', 0):.1f})")
        
        for i, task in enumerate(scored):
            print(f"    {i+1}. {task.get('title')} - score={task.get('score', 0):.1f}, priority={task.get('priority')}")
        
        print("  ✅ 优先级评分测试通过")

    def test_06_urgency_scoring(self):
        """测试 6: 时效性评分"""
        print("\n✅ 测试 6: 时效性评分")
        
        # 创建不同截止时间的任务
        tasks_data = [
            ("紧急-今天", 1, datetime.now()),
            ("紧急-明天", 1, datetime.now() + timedelta(days=1)),
            ("不急-一周后", 3, datetime.now() + timedelta(days=7)),
        ]
        
        for title, priority, deadline in tasks_data:
            self.storage.create_todo(
                title=title,
                priority=priority,
                deadline=deadline.strftime("%Y-%m-%d %H:%M"),
            )
        
        # 获取任务并评分
        todos = self.storage.list_todos()
        scored = self.analyzer._score_tasks(todos)
        
        # 找到紧急任务
        urgent = [t for t in scored if "紧急" in t.get("title", "")]
        self.assertGreater(len(urgent), 0, "应找到紧急任务")
        
        print(f"  ✓ 时效性评分完成")
        for task in urgent:
            deadline = task.get("deadline", "无")
            print(f"    - {task.get('title')}: deadline={deadline}, score={task.get('score', 0):.1f}")
        
        print("  ✅ 时效性评分测试通过")

    def test_07_recommendation_generation(self):
        """测试 7: 推荐生成"""
        print("\n✅ 测试 7: 推荐生成")
        
        # 准备测试数据
        self.storage.create_todo(
            title="推荐测试-紧急",
            category=TaskCategory.WORK,
            priority=1,
            deadline=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M"),
        )
        
        self.storage.create_todo(
            title="推荐测试-今日",
            category=TaskCategory.STUDY,
            time_frame=TimeFrame.TODAY,
            priority=2,
        )
        
        self.storage.create_todo(
            title="推荐测试-常规",
            category=TaskCategory.HEALTH,
            priority=3,
        )
        
        # 生成推荐
        recommendations = self.analyzer._generate_recommendations()
        
        self.assertIsInstance(recommendations, list, "推荐应为列表")
        self.assertGreaterEqual(len(recommendations), 3, "应生成至少3个推荐")
        print(f"  ✓ 生成推荐: {len(recommendations)} 个")
        
        # 验证推荐格式
        for rec in recommendations[:5]:
            self.assertIn("title", rec, "推荐应包含title")
            self.assertIn("priority", rec, "推荐应包含priority")
            self.assertIn("score", rec, "推荐应包含score")
        
        for rec in recommendations[:5]:
            print(f"    - {rec.get('title')} (score={rec.get('score', 0):.1f})")
        
        print("  ✅ 推荐生成测试通过")

    def test_08_full_analysis_pipeline(self):
        """测试 8: 完整分析流程"""
        print("\n✅ 测试 8: 完整分析流程")
        
        # 准备完整的测试数据
        test_data = [
            {"title": "过期紧急", "priority": 1, "deadline": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")},
            {"title": "今日工作", "category": TaskCategory.WORK, "time_frame": TimeFrame.TODAY, "priority": 2},
            {"title": "本周学习", "category": TaskCategory.STUDY, "time_frame": TimeFrame.WEEK, "priority": 2},
            {"title": "家庭事务", "category": TaskCategory.FAMILY, "priority": 3},
            {"title": "未来计划", "category": TaskCategory.GENERAL, "time_frame": TimeFrame.FUTURE, "priority": 4},
        ]
        
        for data in test_data:
            self.storage.create_todo(**data)
        
        # 运行完整分析
        async def run_analysis():
            result = await self.analyzer.analyze_and_recommend(self.today)
            return result
        
        result = asyncio.run(run_analysis())
        
        # 验证结果结构
        self.assertIn("date", result, "结果应包含date")
        self.assertIn("recommendations", result, "结果应包含recommendations")
        self.assertIn("analysis_summary", result, "结果应包含analysis_summary")
        
        self.assertEqual(result["date"], self.today, "日期应匹配")
        self.assertIsInstance(result["recommendations"], list, "推荐应为列表")
        
        recommendations = result["recommendations"]
        print(f"  ✓ 分析日期: {result['date']}")
        print(f"  ✓ 推荐数量: {len(recommendations)}")
        print(f"  ✓ 分析摘要: {result['analysis_summary'][:100] if result['analysis_summary'] else 'N/A'}...")
        
        if recommendations:
            print(f"  ✓ Top 5 推荐:")
            for i, rec in enumerate(recommendations[:5]):
                print(f"    {i+1}. {rec.get('title')} (score={rec.get('score', 0):.1f})")
        
        print("  ✅ 完整分析流程测试通过")

    def test_09_ranking_and_filtering(self):
        """测试 9: 排序与筛选"""
        print("\n✅ 测试 9: 排序与筛选")
        
        # 创建多个任务
        for i in range(15):
            self.storage.create_todo(
                title=f"排序测试-{i}",
                priority=(i % 5) + 1,
                category=TaskCategory.WORK,
            )
        
        # 获取并排序
        todos = self.storage.list_todos()
        scored = self.analyzer._score_tasks(todos)
        ranked = self.analyzer._rank_and_filter(scored, limit=10)
        
        # 验证排序
        self.assertLessEqual(len(ranked), 10, "应限制在10个以内")
        
        # 验证降序排列
        for i in range(len(ranked) - 1):
            self.assertGreaterEqual(
                ranked[i].get("score", 0),
                ranked[i+1].get("score", 0),
                "分数应降序排列"
            )
        
        print(f"  ✓ 排序后数量: {len(ranked)} (限制10)")
        print(f"  ✓ Top 3:")
        for i, task in enumerate(ranked[:3]):
            print(f"    {i+1}. {task.get('title')} (score={task.get('score', 0):.1f})")
        
        print("  ✅ 排序与筛选测试通过")

    def test_10_confidence_calculation(self):
        """测试 10: AI置信度计算"""
        print("\n✅ 测试 10: AI置信度计算")
        
        # 创建不同来源的任务
        self.storage.create_todo(
            title="AI建议任务",
            priority=1,
        )
        
        self.storage.create_todo(
            title="手动创建任务",
            priority=3,
        )
        
        todos = self.storage.list_todos()
        scored = self.analyzer._score_tasks(todos)
        
        # 所有任务应该有置信度
        for task in scored:
            self.assertIn("ai_confidence", task, "任务应包含ai_confidence")
            confidence = task.get("ai_confidence", 0)
            self.assertGreaterEqual(confidence, 0, "置信度应>=0")
            self.assertLessEqual(confidence, 1, "置信度应<=1")
        
        print(f"  ✓ 置信度计算完成")
        for task in scored:
            print(f"    - {task.get('title')}: confidence={task.get('ai_confidence', 0):.2f}")
        
        print("  ✅ 置信度计算测试通过")


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 智能分析引擎测试套件")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestTaskAnalyzer))
    
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
