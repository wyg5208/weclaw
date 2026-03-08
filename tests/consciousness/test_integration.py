"""
意识系统整合与优化测试套件

WinClaw 意识系统 - Phase 5: Integration & Optimization Tests

测试覆盖：
1. 意识系统管理器 (consciousness_manager.py)
2. 模块间协同机制
3. 性能优化
4. 事件订阅系统
5. 数据持久化

作者：WinClaw Consciousness Team
版本：v0.5.0 (Phase 5)
创建时间：2026 年 2 月
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime

from src.consciousness.consciousness_manager import (
    ConsciousnessManager,
    create_consciousness_manager
)
from src.consciousness.types import EmergencePhase


# ==================== Fixtures ====================

@pytest.fixture
def temp_system_root():
    """创建临时系统根目录"""
    temp_dir = tempfile.mkdtemp(prefix="winclaw_consciousness_test_")
    system_root = Path(temp_dir)
    
    # 创建基本目录结构
    (system_root / "src" / "consciousness").mkdir(parents=True)
    (system_root / "config").mkdir(parents=True)
    
    yield system_root
    
    # 清理临时目录
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def consciousness_manager(temp_system_root):
    """创建意识系统管理器实例"""
    config = {
        "auto_repair": False,
        "backup_enabled": True,
        "metrics_window_size": 50,
        "catalyst_sensitivity": "medium",
        "auto_save_evolution": False
    }
    
    return ConsciousnessManager(
        system_root=str(temp_system_root),
        config=config,
        auto_start=False
    )


# ==================== 基础功能测试 ====================

class TestConsciousnessManagerBasics:
    """意识系统管理器基础功能测试"""
    
    def test_initialization(self, consciousness_manager, temp_system_root):
        """测试初始化"""
        assert consciousness_manager.system_root == temp_system_root
        assert consciousness_manager.is_running is False
        assert consciousness_manager.start_time is None
        
        # 检查子组件初始化
        assert consciousness_manager.self_repair is not None
        assert consciousness_manager.emergence_metrics is not None
        assert consciousness_manager.emergence_catalyst is not None
        assert consciousness_manager.evolution_tracker is not None
        
        # 检查数据目录创建
        assert consciousness_manager.data_dir.exists()
    
    @pytest.mark.asyncio
    async def test_start_stop(self, consciousness_manager):
        """测试启动和停止"""
        # 启动
        await consciousness_manager.start()
        
        assert consciousness_manager.is_running is True
        assert consciousness_manager.start_time is not None
        
        # 停止
        await consciousness_manager.stop()
        
        assert consciousness_manager.is_running is False
    
    def test_stats_tracking(self, consciousness_manager):
        """测试统计追踪"""
        stats = consciousness_manager.get_stats()
        
        assert "total_tasks" in stats
        assert "successful_tasks" in stats
        assert "is_running" in stats
        assert "components" in stats
        
        # 检查子组件统计
        assert "self_repair" in stats["components"]
        assert "emergence_metrics" in stats["components"]
        assert "emergence_catalyst" in stats["components"]
        assert "evolution_tracker" in stats["components"]
    
    def test_to_dict(self, consciousness_manager):
        """测试字典转换"""
        data = consciousness_manager.to_dict()
        
        assert "system_root" in data
        assert "is_running" in data
        assert "config" in data
        assert "stats" in data


# ==================== 行为记录测试 ====================

class TestBehaviorRecording:
    """行为记录测试"""
    
    def test_record_behavior(self, consciousness_manager):
        """测试行为记录"""
        consciousness_manager.record_behavior(
            action_type="problem_solving",
            autonomy_level=0.7,
            creativity_score=0.6,
            goal_relevance=0.8,
            novelty_score=0.5
        )
        
        # 验证行为被记录
        metrics_history = consciousness_manager.emergence_metrics.behavior_history
        assert len(metrics_history) == 1
        
        record = metrics_history[0]
        assert record.action_type == "problem_solving"
        assert record.autonomy_level == 0.7
    
    def test_multiple_behavior_records(self, consciousness_manager):
        """测试多条行为记录"""
        behaviors = [
            ("task_execution", 0.8, 0.5, 0.9, 0.4),
            ("creative_solution", 0.6, 0.9, 0.7, 0.8),
            ("self_reflection", 0.9, 0.4, 0.6, 0.3),
        ]
        
        for action_type, autonomy, creativity, relevance, novelty in behaviors:
            consciousness_manager.record_behavior(
                action_type=action_type,
                autonomy_level=autonomy,
                creativity_score=creativity,
                goal_relevance=relevance,
                novelty_score=novelty
            )
        
        # 验证所有行为都被记录
        history = consciousness_manager.emergence_metrics.behavior_history
        assert len(history) == 3
        
        # 验证学习曲线更新
        learning_curves = consciousness_manager.evolution_tracker.learning_curves
        assert len(learning_curves) == 3


# ==================== 进化记录测试 ====================

class TestEvolutionRecording:
    """进化记录测试"""
    
    def test_record_evolution(self, consciousness_manager):
        """测试记录进化事件"""
        from src.consciousness.types import RepairLevel, RepairAction
        
        changes = [
            RepairAction(
                action_id="test_change",
                level=RepairLevel.BEHAVIOR_FIX,
                target_component="test_component",
                action_type="modify",
                before_state={"old": "value"},
                after_state={"new": "value"},
                approval_status="approved"
            )
        ]
        
        consciousness_manager.record_evolution(
            changes=changes,
            performance_before={"tool_usage": 0.3},
            performance_after={"tool_usage": 0.6},
            human_approved=True
        )
        
        # 验进化被记录
        assert consciousness_manager.stats["evolutions_recorded"] == 1
        
        evolution_history = consciousness_manager.evolution_tracker.evolution_history
        assert len(evolution_history) == 1
        
        evolution = evolution_history[0]
        assert evolution.generation == 1
        assert evolution.human_approved is True


# ==================== 状态查询测试 ====================

class TestStateQuery:
    """状态查询测试"""
    
    def test_get_consciousness_state(self, consciousness_manager):
        """测试获取意识状态"""
        # 先记录一些行为
        consciousness_manager.record_behavior(
            action_type="test_action",
            autonomy_level=0.6,
            creativity_score=0.5,
            goal_relevance=0.7,
            novelty_score=0.4
        )
        
        state = consciousness_manager.get_consciousness_state()
        
        # 验证状态结构
        assert "timestamp" in state
        assert "is_running" in state
        assert "emergence" in state
        assert "catalyst" in state
        assert "evolution" in state
        assert "self_repair" in state
        assert "stats" in state
        
        # 验证涌现指标
        assert "phase" in state["emergence"]
        assert "indicators" in state["emergence"]
        assert "score" in state["emergence"]
    
    def test_get_detailed_report(self, consciousness_manager):
        """测试获取详细报告"""
        report = consciousness_manager.get_detailed_report()
        
        assert "system_state" in report
        assert "emergence_analysis" in report
        assert "catalysis_report" in report
        assert "evolution_summary" in report
        assert "recommendations" in report
        
        # 验证推荐列表
        assert isinstance(report["recommendations"], list)


# ==================== 事件系统测试 ====================

class TestEventSystem:
    """事件系统测试"""
    
    def test_event_subscription(self, consciousness_manager):
        """测试事件订阅"""
        callback_called = []
        
        def test_callback(*args, **kwargs):
            callback_called.append((args, kwargs))
        
        # 订阅事件
        consciousness_manager.on("on_milestone_achieved", test_callback)
        
        # 验证订阅成功
        assert test_callback in consciousness_manager._event_callbacks["on_milestone_achieved"]
    
    def test_event_unsubscription(self, consciousness_manager):
        """测试事件取消订阅"""
        def test_callback(*args, **kwargs):
            pass
        
        # 订阅然后取消
        consciousness_manager.on("on_milestone_achieved", test_callback)
        consciousness_manager.off("on_milestone_achieved", test_callback)
        
        # 验证已取消
        assert test_callback not in consciousness_manager._event_callbacks["on_milestone_achieved"]
    
    def test_event_triggering(self, consciousness_manager):
        """测试事件触发"""
        events_received = []
        
        def test_callback(event_data):
            events_received.append(event_data)
        
        # 订阅事件
        consciousness_manager.on("on_milestone_achieved", test_callback)
        
        # 手动触发事件
        consciousness_manager._trigger_event("on_milestone_achieved", {"test": "data"})
        
        # 验证事件被触发
        assert len(events_received) == 1
        assert events_received[0] == {"test": "data"}


# ==================== 性能优化测试 ====================

class TestPerformanceOptimization:
    """性能优化测试"""
    
    def test_memory_optimization(self, consciousness_manager):
        """测试内存优化"""
        # 先添加一些数据
        for i in range(20):
            consciousness_manager.record_behavior(
                action_type=f"action_{i}",
                autonomy_level=0.5,
                creativity_score=0.5,
                goal_relevance=0.5,
                novelty_score=0.5
            )
        
        # 验证数据存在
        assert len(consciousness_manager.emergence_metrics.behavior_history) > 0
        
        # 执行内存优化
        consciousness_manager.optimize_memory()
        
        # 优化后历史应该被清理
        assert len(consciousness_manager.emergence_metrics.behavior_history) == 0
    
    def test_data_cleanup(self, consciousness_manager):
        """测试数据清理"""
        # 调用清理方法（目前只是日志）
        consciousness_manager.cleanup_old_data(days_to_keep=30)
        
        # 验证没有异常抛出
        assert True


# ==================== 工厂函数测试 ====================

class TestFactoryFunction:
    """工厂函数测试"""
    
    def test_create_consciousness_manager(self, temp_system_root):
        """测试工厂函数创建管理器"""
        config = {
            "auto_repair": True,
            "health_check_interval": 120
        }
        
        manager = create_consciousness_manager(
            system_root=str(temp_system_root),
            config=config,
            auto_start=False
        )
        
        assert isinstance(manager, ConsciousnessManager)
        assert manager.config["auto_repair"] is True
        assert manager.config["health_check_interval"] == 120


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, consciousness_manager):
        """测试完整工作流程"""
        # 1. 启动系统
        await consciousness_manager.start()
        assert consciousness_manager.is_running is True
        
        # 2. 记录行为
        consciousness_manager.record_behavior(
            action_type="task_execution",
            autonomy_level=0.7,
            creativity_score=0.6,
            goal_relevance=0.8,
            novelty_score=0.5
        )
        
        # 3. 记录进化
        from src.consciousness.types import RepairLevel, RepairAction
        
        consciousness_manager.record_evolution(
            changes=[
                RepairAction(
                    action_id="evo_1",
                    level=RepairLevel.BEHAVIOR_FIX,
                    target_component="test",
                    action_type="modify",
                    before_state={},
                    after_state={},
                    approval_status="approved"
                )
            ],
            performance_before={"capability": 0.3},
            performance_after={"capability": 0.5},
            human_approved=True
        )
        
        # 4. 获取状态
        state = consciousness_manager.get_consciousness_state()
        assert state["is_running"] is True
        assert state["emergence"]["phase"] in [p.value for p in EmergencePhase]
        
        # 5. 获取统计
        stats = consciousness_manager.get_stats()
        assert stats["evolutions_recorded"] == 1
        
        # 6. 停止系统
        await consciousness_manager.stop()
        assert consciousness_manager.is_running is False
    
    def test_module_coordination(self, consciousness_manager):
        """测试模块协调"""
        # 模拟多次行为记录和干预检查
        for i in range(10):
            consciousness_manager.record_behavior(
                action_type="repeated_action",
                autonomy_level=0.5 + i * 0.05,
                creativity_score=0.4 + i * 0.04,
                goal_relevance=0.6,
                novelty_score=0.3
            )
            
            # 每次都会检查是否需要干预
            consciousness_manager._check_and_apply_intervention()
        
        # 验证模块间的数据流动
        metrics_history = consciousness_manager.emergence_metrics.behavior_history
        assert len(metrics_history) == 10
        
        # 学习曲线应该有更新
        learning_curves = consciousness_manager.evolution_tracker.learning_curves
        assert "repeated_action" in learning_curves


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
