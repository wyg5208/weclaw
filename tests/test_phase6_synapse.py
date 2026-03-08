"""
Phase 6 微观进化测试 - 突触可塑性增强
Test Phase 6 Synaptic Plasticity Enhancements
"""
import sys
sys.path.insert(0, 'src')  # 添加模块路径

import pytest
import numpy as np
from neuroconscious.core import Synapse


class TestSynapsePhase6:
    """测试 Phase 6 增强的突触功能"""
    
    def test_synapse_initialization(self):
        """测试突触初始化时新增字段存在"""
        syn = Synapse(pre_neuron_id=1, post_neuron_id=2)
        
        # 检查原有字段
        assert syn.pre_neuron_id == 1
        assert syn.post_neuron_id == 2
        assert 0 <= syn.weight <= 1
        
        # 检查 Phase 6 新增字段
        assert hasattr(syn, 'learning_rate')
        assert hasattr(syn, 'eligibility_trace')
        assert hasattr(syn, 'age_ms')
        assert hasattr(syn, 'meta_plasticity')
        assert hasattr(syn, 'bcm_threshold')
        assert hasattr(syn, 'creation_time')
        
        # 检查默认值
        assert syn.learning_rate == 0.01
        assert syn.eligibility_trace == 0.0
        assert syn.meta_plasticity == 1.0
        assert syn.bcm_threshold == 0.5
    
    def test_stdp_basic_ltp(self):
        """测试基础 STDP - LTP（长时程增强）"""
        syn = Synapse(pre_neuron_id=1, post_neuron_id=2, weight=0.5)
        
        # 突触前神经元先发放（pre < post）→ LTP
        pre_spike = 10.0   # ms
        post_spike = 20.0  # ms
        
        delta = syn.apply_stdp_with_modulation(pre_spike, post_spike)
        
        assert delta > 0, "LTP 应该增加权重"
        assert syn.weight > 0.5
    
    def test_stdp_basic_ltd(self):
        """测试基础 STDP - LTD（长时程抑制）"""
        syn = Synapse(pre_neuron_id=1, post_neuron_id=2, weight=0.5)
        
        # 突触后神经元先发放（post < pre）→ LTD
        pre_spike = 20.0   # ms
        post_spike = 10.0  # ms
        
        delta = syn.apply_stdp_with_modulation(pre_spike, post_spike)
        
        assert delta < 0, "LTD 应该减少权重"
        assert syn.weight < 0.5
    
    def test_dopamine_gating_positive_rpe(self):
        """测试多巴胺门控 - 正 RPE 增强 LTP"""
        syn = Synapse(pre_neuron_id=1, post_neuron_id=2, weight=0.5)
        
        pre_spike = 10.0
        post_spike = 20.0
        
        # 无多巴胺基准
        delta_baseline = syn.apply_stdp_with_modulation(pre_spike, post_spike, dopamine=0.0)
        
        # 重置权重
        syn.weight = 0.5
        
        # 正 RPE（奖励预测误差）
        delta_reward = syn.apply_stdp_with_modulation(pre_spike, post_spike, dopamine=0.8)
        
        assert delta_reward > delta_baseline, "正 RPE 应增强 LTP"
        # 理论上最多增强 3 倍：1 + 0.8*2 = 2.6
        assert delta_reward <= delta_baseline * 3.0
    
    def test_dopamine_gating_negative_rpe(self):
        """测试多巴胺门控 - 负 RPE 抑制 LTP"""
        syn = Synapse(pre_neuron_id=1, post_neuron_id=2, weight=0.5)
        
        pre_spike = 10.0
        post_spike = 20.0
        
        # 无多巴胺基准
        delta_baseline = syn.apply_stdp_with_modulation(pre_spike, post_spike, dopamine=0.0)
        
        # 重置权重
        syn.weight = 0.5
        
        # 负 RPE（惩罚）
        delta_punish = syn.apply_stdp_with_modulation(pre_spike, post_spike, dopamine=-0.5)
        
        assert delta_punish < delta_baseline, "负 RPE 应抑制 LTP"
    
    def test_ach_modulation_uncertainty(self):
        """测试乙酰胆碱调节 - 高不确定性加速学习"""
        syn = Synapse(pre_neuron_id=1, post_neuron_id=2, weight=0.5)
        
        pre_spike = 10.0
        post_spike = 20.0
        
        # 低 ACh（确定性环境）
        delta_low = syn.apply_stdp_with_modulation(pre_spike, post_spike, acetylcholine=0.5)
        
        # 重置权重
        syn.weight = 0.5
        
        # 高 ACh（高不确定性，需要快速学习）
        delta_high = syn.apply_stdp_with_modulation(pre_spike, post_spike, acetylcholine=2.0)
        
        assert abs(delta_high) > abs(delta_low), "高 ACh 应加速学习"
    
    def test_bcm_sliding_threshold_high_weight(self):
        """测试 BCM 滑动阈值 - 高权重时抑制进一步增加"""
        syn = Synapse(pre_neuron_id=1, post_neuron_id=2, weight=0.8)  # 已很高
        syn.bcm_threshold = 0.5
        
        pre_spike = 10.0
        post_spike = 20.0
        
        delta = syn.apply_stdp_with_modulation(pre_spike, post_spike)
        
        # 由于 weight > bcm_threshold，LTP 应被抑制
        # 对比低权重的情况
        syn_low = Synapse(pre_neuron_id=1, post_neuron_id=2, weight=0.2)
        syn_low.bcm_threshold = 0.5
        delta_low = syn_low.apply_stdp_with_modulation(pre_spike, post_spike)
        
        # 高权重时的增量应小于低权重时
        assert delta < delta_low, "高权重时应抑制进一步增加"
    
    def test_meta_plasticity_modulation(self):
        """测试 Meta-plasticity - 老练突触更难改变"""
        # 年轻突触（meta_plasticity = 1.0）
        syn_young = Synapse(pre_neuron_id=1, post_neuron_id=2, meta_plasticity=1.0)
        
        # 老练突触（meta_plasticity = 0.3）
        syn_old = Synapse(pre_neuron_id=1, post_neuron_id=2, meta_plasticity=0.3)
        
        pre_spike = 10.0
        post_spike = 20.0
        
        delta_young = syn_young.apply_stdp_with_modulation(pre_spike, post_spike)
        delta_old = syn_old.apply_stdp_with_modulation(pre_spike, post_spike)
        
        assert abs(delta_old) < abs(delta_young), "老练突触变化应更小"
        # 理论上 delta_old ≈ delta_young * 0.3
        assert np.isclose(abs(delta_old), abs(delta_young) * 0.3, rtol=0.1)
    
    def test_age_update(self):
        """测试突触年龄更新"""
        syn = Synapse(pre_neuron_id=1, post_neuron_id=2, creation_time=100.0)
        
        # 调用时传入当前时间
        syn.apply_stdp_with_modulation(10.0, 20.0, current_time=200.0)
        
        assert syn.age_ms == 100.0, "突触年龄应为 100ms"
    
    def test_weight_bounds(self):
        """测试权重边界保护"""
        syn = Synapse(pre_neuron_id=1, post_neuron_id=2, weight=0.99)
        
        # 多次 LTP 刺激
        for _ in range(100):
            syn.apply_stdp_with_modulation(10.0, 20.0)
        
        assert syn.weight <= 1.0, "权重不应超过 1.0"
        
        # 重置为低权重
        syn.weight = 0.01
        
        # 多次 LTD 刺激
        for _ in range(100):
            syn.apply_stdp_with_modulation(20.0, 10.0)
        
        assert syn.weight >= 0.0, "权重不应低于 0.0"
    
    def test_eligibility_trace_field(self):
        """测试资格迹字段存在和衰减"""
        syn = Synapse(pre_neuron_id=1, post_neuron_id=2)
        
        # 初始为 0
        assert syn.eligibility_trace == 0.0
        
        # 模拟标记（实际使用由 neuromodulators.py 管理）
        syn.eligibility_trace = 1.0
        
        # 模拟衰减（手动）
        syn.eligibility_trace *= syn.trace_decay
        assert np.isclose(syn.eligibility_trace, 0.9), "资格迹应衰减"


class TestBCMThresholdUpdate:
    """测试 BCM 阈值更新机制"""
    
    def test_bcm_threshold_update_method_exists(self):
        """测试 memory 类有 update_bcm_threshold 方法"""
        from neuroconscious.core import SynapticPlasticityMemory
        
        memory = SynapticPlasticityMemory(n_neurons=100)
        
        assert hasattr(memory, 'update_bcm_threshold')
    
    def test_bcm_threshold_adaptation(self):
        """测试 BCM 阈值根据活动自适应调整"""
        from neuroconscious.core import SynapticPlasticityMemory
        
        memory = SynapticPlasticityMemory(n_neurons=50, sparsity=0.1)
        
        # 获取第一个神经元相关的突触
        neuron_id = 0
        related_before = [
            syn for (pre, post), syn in memory.synapses.items()
            if pre == neuron_id or post == neuron_id
        ]
        
        if not related_before:
            pytest.skip("No synapses found for this neuron")
        
        initial_thresholds = [syn.bcm_threshold for syn in related_before]
        
        # 模拟高频刺激（添加 spike）
        for i in range(10):
            memory._record_spike(neuron_id, i * 10.0)  # 每 10ms 一个 spike
        
        # 更新 BCM 阈值（目标活动 0.5，当前活动很高）
        memory.update_bcm_threshold(neuron_id, target_activity=0.5, learning_rate=0.1)
        
        # 获取更新后的阈值
        related_after = [
            syn for (pre, post), syn in memory.synapses.items()
            if pre == neuron_id or post == neuron_id
        ]
        new_thresholds = [syn.bcm_threshold for syn in related_after]
        
        # 由于活动过高（10 个 spike），阈值应该提高
        avg_increase = np.mean(new_thresholds) - np.mean(initial_thresholds)
        assert avg_increase > 0, "高活动应提高 BCM 阈值"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
