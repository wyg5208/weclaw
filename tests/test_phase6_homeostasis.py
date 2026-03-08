"""
Phase 6 稳态调节器测试
Test Homeostatic Synaptic Scaling
"""
import sys
sys.path.insert(0, 'src')

import pytest
import numpy as np
from neuroconscious.homeostasis import SynapticScaling, HomeostaticState


class TestSynapticScaling:
    """测试稳态突触缩放功能"""
    
    def test_initialization(self):
        """测试初始化参数"""
        scaler = SynapticScaling(
            target_activity=0.5,
            hyper_threshold=0.8,
            silence_threshold=0.1,
            scaling_rate=0.1
        )
        
        assert scaler.target_activity == 0.5
        assert scaler.hyper_threshold == 0.8
        assert scaler.silence_threshold == 0.1
        assert scaler.scaling_rate == 0.1
    
    def test_detect_imbalance_hyperactive(self):
        """检测过度活跃"""
        scaler = SynapticScaling()
        
        # 活动率 > 0.8
        activities = np.array([0.85, 0.90, 0.95, 0.88])
        is_hyper, is_silent = scaler.detect_imbalance(activities)
        
        assert is_hyper == True
        assert is_silent == False
    
    def test_detect_imbalance_silent(self):
        """检测沉寂"""
        scaler = SynapticScaling()
        
        # 活动率 < 0.1
        activities = np.array([0.05, 0.08, 0.03, 0.07])
        is_hyper, is_silent = scaler.detect_imbalance(activities)
        
        assert is_hyper == False
        assert is_silent == True
    
    def test_detect_imbalance_normal(self):
        """检测正常范围"""
        scaler = SynapticScaling()
        
        # 活动率在正常范围 (0.1~0.8)
        activities = np.array([0.4, 0.5, 0.6, 0.55])
        is_hyper, is_silent = scaler.detect_imbalance(activities)
        
        assert is_hyper == False
        assert is_silent == False
    
    def test_compute_scaling_factor_hyperactive(self):
        """计算缩放因子 - 过度活跃情况"""
        scaler = SynapticScaling(scaling_rate=0.1)
        
        # 平均活动 0.9 (>0.8 阈值)
        activities = np.array([0.85, 0.95])
        factor = scaler.compute_scaling_factor(activities)
        
        assert factor < 1.0, "过度活跃应下调（factor < 1）"
        assert factor >= 0.5, "最多减半（不低于 0.5）"
    
    def test_compute_scaling_factor_silent(self):
        """计算缩放因子 - 沉寂情况"""
        scaler = SynapticScaling(scaling_rate=0.1)
        
        # 平均活动 0.05 (<0.1 阈值)
        activities = np.array([0.03, 0.07])
        factor = scaler.compute_scaling_factor(activities)
        
        assert factor > 1.0, "沉寂应上调（factor > 1）"
        assert factor <= 2.0, "最多翻倍（不超过 2.0）"
    
    def test_compute_scaling_factor_normal(self):
        """计算缩放因子 - 正常情况"""
        scaler = SynapticScaling()
        
        # 平均活动 0.5（接近目标）
        activities = np.array([0.45, 0.55])
        factor = scaler.compute_scaling_factor(activities)
        
        assert np.isclose(factor, 1.0, rtol=0.01), "正常范围应保持 1.0"
    
    def test_scale_to_target_downregulation(self):
        """测试向下调节完整流程"""
        scaler = SynapticScaling()
        
        # 模拟过度活跃的权重和活动
        weights = np.ones((5, 5)) * 0.8  # 高权重
        activities = np.array([0.85, 0.90, 0.88, 0.92, 0.87])
        
        scaled_weights, state = scaler.scale_to_target(weights, activities)
        
        # 验证状态
        assert state.is_hyperactive == True
        assert state.is_silent == False
        assert state.scaling_factor < 1.0
        
        # 验证权重被下调
        assert np.mean(scaled_weights) < np.mean(weights)
        # 所有权重仍应在 [0, 1] 范围内
        assert np.all(scaled_weights >= 0) and np.all(scaled_weights <= 1)
    
    def test_scale_to_target_upregulation(self):
        """测试向上调节完整流程"""
        scaler = SynapticScaling()
        
        # 模拟沉寂的权重和活动
        weights = np.ones((5, 5)) * 0.3  # 低权重
        activities = np.array([0.05, 0.08, 0.06, 0.07, 0.04])
        
        scaled_weights, state = scaler.scale_to_target(weights, activities)
        
        # 验证状态
        assert state.is_hyperactive == False
        assert state.is_silent == True
        assert state.scaling_factor > 1.0
        
        # 验证权重被上调
        assert np.mean(scaled_weights) > np.mean(weights)
        # 所有权重仍应在 [0, 1] 范围内
        assert np.all(scaled_weights >= 0) and np.all(scaled_weights <= 1)
    
    def test_scale_preserves_relative_weights(self):
        """测试缩放保持相对权重关系"""
        scaler = SynapticScaling()
        
        # 创建有不同权重的突触
        weights = np.array([
            [0.2, 0.5, 0.8],
            [0.3, 0.6, 0.9],
            [0.1, 0.4, 0.7]
        ])
        
        # 模拟过度活跃
        activities = np.array([0.9, 0.95, 0.88])
        
        scaled_weights, state = scaler.scale_to_target(weights, activities)
        
        # 验证相对关系保持不变（乘法缩放不改变大小顺序）
        # 如果 a > b，则 a*factor > b*factor（当 factor > 0）
        for i in range(3):
            for j in range(3):
                if weights[i, j] > weights[0, 0]:
                    assert scaled_weights[i, j] > scaled_weights[0, 0]
                elif weights[i, j] < weights[0, 0]:
                    assert scaled_weights[i, j] < scaled_weights[0, 0]
    
    def test_get_stats(self):
        """获取统计信息"""
        scaler = SynapticScaling()
        
        # 初始无调节
        stats = scaler.get_stats()
        assert stats['total_adjustments'] == 0
        assert stats['current_state'] is None
        
        # 执行一次调节
        weights = np.ones((5, 5))
        activities = np.array([0.9, 0.9, 0.9, 0.9, 0.9])
        scaler.scale_to_target(weights, activities)
        
        # 检查统计
        stats = scaler.get_stats()
        assert stats['total_adjustments'] == 1
        assert stats['down_regulations'] == 1
        assert stats['up_regulations'] == 0
        assert stats['average_scaling_factor'] < 1.0
        assert 'current_state' in stats
        assert stats['current_state'] is not None
    
    def test_scaling_history_limit(self):
        """测试历史记录限制"""
        scaler = SynapticScaling()
        
        # 执行多次调节
        for _ in range(15):
            weights = np.random.rand(5, 5)
            activities = np.random.rand(5) * 0.3 + 0.8  # 总是过度活跃
            scaler.scale_to_target(weights, activities)
        
        stats = scaler.get_stats()
        # recent_events 应该只保留最近 10 条
        assert len(stats['recent_events']) <= 10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
