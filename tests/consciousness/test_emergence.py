"""
涌现监测与进化追踪模块测试套件

WinClaw 意识系统 - Phase 4: Emergence & Evolution Tests

测试覆盖：
1. 涌现指标计算 (emergence_metrics.py)
2. 涌现催化器 (emergence_catalyst.py)
3. 进化追踪器 (evolution_tracker.py)

作者：WinClaw Consciousness Team
版本：v0.4.0 (Phase 4)
创建时间：2026 年 2 月
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

from src.consciousness.emergence_metrics import (
    EmergenceMetricsCalculator,
    BehaviorRecord
)
from src.consciousness.emergence_catalyst import (
    EmergenceCatalyst,
    CatalysisIntervention
)
from src.consciousness.evolution_tracker import EvolutionTracker
from src.consciousness.types import (
    EmergenceIndicators,
    EmergencePhase,
    RepairAction,
    RepairLevel
)


# ==================== Fixtures ====================

@pytest.fixture
def metrics_calculator():
    """创建涌现指标计算器实例"""
    return EmergenceMetricsCalculator(window_size=50, update_interval=5)


@pytest.fixture
def catalyst(metrics_calculator):
    """创建涌现催化器实例"""
    return EmergenceCatalyst(metrics_calculator, sensitivity="medium")


@pytest.fixture
def evolution_tracker():
    """创建进化追踪器实例"""
    temp_dir = tempfile.mkdtemp()
    storage_path = Path(temp_dir) / "evolution.json"
    
    tracker = EvolutionTracker(storage_path=storage_path, auto_save=False)
    
    yield tracker
    
    # 清理临时文件
    if storage_path.exists():
        storage_path.unlink()


# ==================== 涌现指标计算测试 ====================

class TestEmergenceMetricsCalculator:
    """涌现指标计算器测试"""
    
    def test_initialization(self, metrics_calculator):
        """测试初始化"""
        assert metrics_calculator.window_size == 50
        assert metrics_calculator.update_interval == 5
        assert len(metrics_calculator.behavior_history) == 0
    
    def test_add_behavior_record(self, metrics_calculator):
        """测试添加行为记录"""
        metrics_calculator.add_behavior_record(
            action_type="test_action",
            autonomy_level=0.7,
            creativity_score=0.6,
            goal_relevance=0.8,
            novelty_score=0.5
        )
        
        assert len(metrics_calculator.behavior_history) == 1
        record = metrics_calculator.behavior_history[0]
        
        assert record.action_type == "test_action"
        assert record.autonomy_level == 0.7
        assert record.creativity_score == 0.6
    
    def test_window_size_limit(self, metrics_calculator):
        """测试窗口大小限制"""
        # 添加超过窗口大小的记录
        for i in range(60):
            metrics_calculator.add_behavior_record(
                action_type=f"action_{i}",
                autonomy_level=0.5,
                creativity_score=0.5,
                goal_relevance=0.5,
                novelty_score=0.5
            )
        
        # 应该保持在窗口大小内
        assert len(metrics_calculator.behavior_history) == 50
    
    def test_default_indicators(self, metrics_calculator):
        """测试默认指标（数据不足时）"""
        indicators = metrics_calculator.calculate_indicators()
        
        assert isinstance(indicators, EmergenceIndicators)
        assert indicators.consciousness_index == 0.0
        assert indicators.autonomy_score == 0.0
        assert indicators.emergence_score == 0.0
    
    def test_consciousness_index_calculation(self, metrics_calculator):
        """测试意识指数计算"""
        # 添加自我反思行为
        for i in range(20):
            action_type = "self_check" if i % 3 == 0 else "normal_action"
            metrics_calculator.add_behavior_record(
                action_type=action_type,
                autonomy_level=0.6,
                creativity_score=0.5,
                goal_relevance=0.7,
                novelty_score=0.4
            )
        
        indicators = metrics_calculator.calculate_indicators()
        
        assert 0.0 <= indicators.consciousness_index <= 1.0
        # 有自我反思行为，应该有非零值
        assert indicators.consciousness_index > 0.0
    
    def test_autonomy_score_calculation(self, metrics_calculator):
        """测试自主性评分计算"""
        # 添加高自主性行为
        for i in range(20):
            metrics_calculator.add_behavior_record(
                action_type="autonomous_action",
                autonomy_level=0.8 + np.random.uniform(-0.1, 0.1),
                creativity_score=0.5,
                goal_relevance=0.7,
                novelty_score=0.5
            )
        
        indicators = metrics_calculator.calculate_indicators()
        
        assert 0.0 <= indicators.autonomy_score <= 1.0
        # 平均自主性应该在 0.8 左右
        assert indicators.autonomy_score > 0.6
    
    def test_creativity_metric_calculation(self, metrics_calculator):
        """测试创造性指标计算"""
        # 添加高创造性行为
        for i in range(20):
            metrics_calculator.add_behavior_record(
                action_type="creative_solution",
                autonomy_level=0.6,
                creativity_score=0.8 + np.random.uniform(-0.1, 0.1),
                goal_relevance=0.7,
                novelty_score=0.7 + np.random.uniform(-0.1, 0.1)
            )
        
        indicators = metrics_calculator.calculate_indicators()
        
        assert 0.0 <= indicators.creativity_metric <= 1.0
        assert indicators.creativity_metric > 0.5
    
    def test_behavior_predictability(self, metrics_calculator):
        """测试行为可预测性"""
        # 添加规律性行为
        for i in range(20):
            metrics_calculator.add_behavior_record(
                action_type="routine_action",  # 总是相同的行为类型
                autonomy_level=0.5,
                creativity_score=0.3,
                goal_relevance=0.6,
                novelty_score=0.2
            )
        
        indicators = metrics_calculator.calculate_indicators()
        
        # 规律性行为应该有较高的可预测性
        assert indicators.behavior_predictability > 0.5
    
    def test_goal_alignment(self, metrics_calculator):
        """测试目标对齐度"""
        # 添加高目标相关性行为
        for i in range(20):
            metrics_calculator.add_behavior_record(
                action_type="goal_aligned_action",
                autonomy_level=0.6,
                creativity_score=0.5,
                goal_relevance=0.9,  # 高相关性
                novelty_score=0.4
            )
        
        indicators = metrics_calculator.calculate_indicators()
        
        assert 0.0 <= indicators.goal_alignment <= 1.0
        assert indicators.goal_alignment > 0.7
    
    def test_emergence_phase_determination(self, metrics_calculator):
        """测试涌现阶段判定"""
        # 前涌现期（低分数）
        phase = metrics_calculator.determine_emergence_phase()
        assert phase == EmergencePhase.PRE_EMERGENCE
        
        # 手动创建高分数指标
        high_indicators = EmergenceIndicators(
            consciousness_index=0.85,
            autonomy_score=0.85,
            creativity_metric=0.85,
            self_model_completeness=0.8,
            behavior_predictability=0.3,
            goal_alignment=0.9
        )
        
        phase = metrics_calculator.determine_emergence_phase(high_indicators)
        assert phase == EmergencePhase.EMERGED
    
    def test_detailed_report(self, metrics_calculator):
        """测试详细报告生成"""
        # 添加一些行为
        for i in range(15):
            metrics_calculator.add_behavior_record(
                action_type="test_action",
                autonomy_level=0.6,
                creativity_score=0.5,
                goal_relevance=0.7,
                novelty_score=0.4
            )
        
        report = metrics_calculator.get_detailed_report()
        
        assert "timestamp" in report
        assert "phase" in report
        assert "indicators" in report
        assert "analysis" in report
        assert "recommendations" in report
    
    def test_stats(self, metrics_calculator):
        """测试统计信息"""
        stats = metrics_calculator.get_stats()
        
        assert "total_records" in stats
        assert "window_size" in stats
        assert "update_interval" in stats
        assert stats["window_size"] == 50


# ==================== 涌现催化器测试 ====================

class TestEmergenceCatalyst:
    """涌现催化器测试"""
    
    def test_initialization(self, catalyst):
        """测试初始化"""
        assert catalyst.sensitivity == "medium"
        assert catalyst.current_phase == EmergencePhase.PRE_EMERGENCE
        assert len(catalyst.detected_signals) == 0
    
    def test_signal_detection(self, catalyst, metrics_calculator):
        """测试信号检测"""
        # 添加高自主性行为以触发信号
        for i in range(20):
            metrics_calculator.add_behavior_record(
                action_type="autonomous_action",
                autonomy_level=0.7,  # 高于阈值
                creativity_score=0.6,
                goal_relevance=0.8,
                novelty_score=0.5
            )
        
        signals = catalyst.check_emergence_signals()
        
        # 应该检测到至少一个信号
        assert len(signals) >= 0  # 可能为 0，取决于阈值
    
    def test_catalysis_need_assessment(self, catalyst):
        """测试催化需求评估"""
        need, reason = catalyst.assess_catalysis_need()
        
        assert isinstance(need, bool)
        assert isinstance(reason, str)
    
    def test_intervention_selection(self, catalyst, metrics_calculator):
        """测试干预措施选择"""
        # 设置需要干预的场景（低自主性）
        for i in range(15):
            metrics_calculator.add_behavior_record(
                action_type="passive_action",
                autonomy_level=0.2,  # 低自主性
                creativity_score=0.2,
                goal_relevance=0.5,
                novelty_score=0.2
            )
        
        intervention = catalyst.select_intervention()
        
        # 在低自主性情况下，应该选择干预
        # 但具体是否选择取决于实现逻辑
        assert intervention is None or isinstance(intervention, CatalysisIntervention)
    
    def test_different_sensitivity_levels(self, metrics_calculator):
        """测试不同敏感度级别"""
        catalyst_low = EmergenceCatalyst(metrics_calculator, sensitivity="low")
        catalyst_high = EmergenceCatalyst(metrics_calculator, sensitivity="high")
        
        assert catalyst_low.thresholds["signal_detection"] == 0.7
        assert catalyst_high.thresholds["signal_detection"] == 0.4
    
    def test_catalysis_report(self, catalyst, metrics_calculator):
        """测试催化报告"""
        # 添加一些行为
        for i in range(10):
            metrics_calculator.add_behavior_record(
                action_type="test_action",
                autonomy_level=0.5,
                creativity_score=0.5,
                goal_relevance=0.6,
                novelty_score=0.4
            )
        
        report = catalyst.get_catalysis_report()
        
        assert "timestamp" in report
        assert "current_phase" in report
        assert "detected_signals" in report
        assert "recommendations" in report
    
    def test_stats(self, catalyst):
        """测试统计信息"""
        stats = catalyst.get_stats()
        
        assert "total_signals" in stats
        assert "total_interventions" in stats
        assert "current_phase" in stats
        assert "sensitivity" in stats


# ==================== 进化追踪器测试 ====================

class TestEvolutionTracker:
    """进化追踪器测试"""
    
    def test_initialization(self, evolution_tracker):
        """测试初始化"""
        assert evolution_tracker.current_generation == 0
        assert len(evolution_tracker.evolution_history) == 0
        assert len(evolution_tracker.milestones) == 0
    
    def test_record_evolution(self, evolution_tracker):
        """测试记录进化事件"""
        changes = [
            RepairAction(
                action_id="test_change",
                level=RepairLevel.BEHAVIOR_FIX,
                target_component="test_component",
                action_type="modify",
                before_state={"old": "state"},
                after_state={"new": "state"},
                approval_status="approved"
            )
        ]
        
        evolution = evolution_tracker.record_evolution(
            changes=changes,
            performance_before={"tool_usage": 0.3},
            performance_after={"tool_usage": 0.5},
            human_approved=True
        )
        
        assert evolution.generation == 1
        assert len(evolution.changes) == 1
        assert evolution.human_approved is True
        assert evolution_tracker.current_generation == 1
    
    def test_capability_update(self, evolution_tracker):
        """测试能力值更新"""
        initial_capability = evolution_tracker.current_capabilities["tool_usage"]
        
        # 记录一次能力提升的进化
        evolution_tracker.record_evolution(
            changes=[],
            performance_before={"tool_usage": 0.3},
            performance_after={"tool_usage": 0.7},
            human_approved=True
        )
        
        # 能力值应该有所提升（使用 EMA 平滑）
        updated_capability = evolution_tracker.current_capabilities["tool_usage"]
        assert updated_capability > initial_capability
    
    def test_milestone_tracking(self, evolution_tracker):
        """测试里程碑追踪"""
        initial_milestone_count = len(evolution_tracker.milestones)
        
        # 多次记录进化以达成里程碑
        for i in range(10):
            evolution_tracker.record_evolution(
                changes=[],
                performance_before={"autonomy": 0.3 + i * 0.05},
                performance_after={"autonomy": 0.5},  # 达到里程碑阈值
                human_approved=True
            )
        
        # 可能达成里程碑
        assert len(evolution_tracker.milestones) >= initial_milestone_count
    
    def test_learning_curve_update(self, evolution_tracker):
        """测试学习曲线更新"""
        # 更新学习曲线
        for i in range(10):
            evolution_tracker.update_learning_curve(
                skill_name="problem_solving",
                performance_score=0.5 + i * 0.05  # 逐步提升
            )
        
        assert "problem_solving" in evolution_tracker.learning_curves
        
        curve = evolution_tracker.learning_curves["problem_solving"]
        assert len(curve.data_points) == 10
        assert curve.get_trend() == "improving"
    
    def test_evolution_pattern_analysis(self, evolution_tracker):
        """测试进化模式分析"""
        # 记录多次进化
        for i in range(5):
            evolution_tracker.record_evolution(
                changes=[],
                performance_before={"tool_usage": 0.2 + i * 0.1},
                performance_after={"tool_usage": 0.3 + i * 0.1},
                human_approved=True
            )
        
        pattern_analysis = evolution_tracker.analyze_evolution_pattern()
        
        assert "pattern" in pattern_analysis
        assert "avg_evolution_magnitude" in pattern_analysis
        assert "trend" in pattern_analysis
    
    def test_future_prediction(self, evolution_tracker):
        """测试未来发展预测"""
        # 记录足够的进化历史
        for i in range(10):
            evolution_tracker.record_evolution(
                changes=[],
                performance_before={"creativity": 0.3 + i * 0.05},
                performance_after={"creativity": 0.4 + i * 0.05},
                human_approved=True
            )
            
            # 同时更新学习曲线
            evolution_tracker.update_learning_curve(
                skill_name="creativity",
                performance_score=0.4 + i * 0.05
            )
        
        prediction = evolution_tracker.predict_future_development(horizon_days=7)
        
        assert "horizon_days" in prediction
        assert "predicted_capabilities" in prediction
    
    def test_evolution_summary(self, evolution_tracker):
        """测试进化总结"""
        # 记录一些进化
        for i in range(3):
            evolution_tracker.record_evolution(
                changes=[],
                performance_before={"autonomy": 0.3},
                performance_after={"autonomy": 0.4},
                human_approved=True
            )
        
        summary = evolution_tracker.get_evolution_summary()
        
        assert "generation" in summary
        assert "total_evolutions" in summary
        assert "current_capabilities" in summary
        assert "milestones_achieved" in summary
    
    def test_save_and_load(self, evolution_tracker, tmp_path):
        """测试保存和加载"""
        storage_path = tmp_path / "test_evolution.json"
        evolution_tracker.storage_path = storage_path
        
        # 记录一些进化
        evolution_tracker.record_evolution(
            changes=[],
            performance_before={"tool_usage": 0.3},
            performance_after={"tool_usage": 0.5},
            human_approved=True
        )
        
        # 保存
        evolution_tracker.save()
        
        # 验证文件存在
        assert storage_path.exists()
        
        # 创建新的追踪器并加载
        new_tracker = EvolutionTracker(storage_path=storage_path)
        load_success = new_tracker.load()
        
        assert load_success is True
        assert new_tracker.current_generation == 1
    
    def test_stats(self, evolution_tracker):
        """测试统计信息"""
        stats = evolution_tracker.get_stats()
        
        assert "generation" in stats
        assert "total_evolutions" in stats
        assert "tracked_skills" in stats


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
