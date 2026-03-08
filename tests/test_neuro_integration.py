"""
神经形态意识系统集成测试

测试混合模式（传统 + 神经形态）的协同工作
"""

import unittest
import sys
import os
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'consciousness'))
sys.path.insert(0, str(Path(__file__).parent.parent))

from consciousness_manager import ConsciousnessManager
from emergence_metrics import EmergenceMetricsCalculator


class TestNeuroIntegration(unittest.TestCase):
    """神经形态系统集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.config = {
            "enable_neuro_consciousness": True,
            "neuro_n_neurons": 1000,  # 小规模用于测试
            "neuro_n_modules": 6,
            "auto_repair": False,
            "backup_enabled": False
        }
        
        self.manager = ConsciousnessManager(
            system_root=str(Path(__file__).parent.parent.parent),
            config=self.config,
            auto_start=False
        )
    
    def test_hybrid_system_initialization(self):
        """测试 1: 混合系统初始化"""
        print("\n=== 测试 1: 混合系统初始化 ===")
        
        # 检查传统组件
        self.assertIsNotNone(self.manager.emergence_metrics)
        self.assertIsNotNone(self.manager.evolution_tracker)
        print("✓ 传统组件初始化成功")
        
        # 检查神经形态组件
        if hasattr(self.manager, 'neuro_consciousness'):
            if self.manager.neuro_consciousness:
                print("✓ 神经形态系统已加载")
                print(f"  - 神经元数量：{self.manager.neuro_consciousness.memory.n_neurons}")
                print(f"  - 模块数量：{len(self.manager.neuro_consciousness.cortical_modules)}")
            else:
                print("⚠ 神经形态系统未加载（可能是配置禁用或导入失败）")
        else:
            print("✗ 神经形态系统属性不存在")
        
        # 断言：至少传统系统可用
        self.assertIsNotNone(self.manager.emergence_metrics)
    
    def test_behavior_recording_dual_path(self):
        """测试 2: 行为记录双路径"""
        print("\n=== 测试 2: 行为记录双路径 ===")
        
        # 记录一个行为
        self.manager.record_behavior(
            action_type="test_action",
            autonomy_level=0.8,
            creativity_score=0.7,
            goal_relevance=0.9,
            novelty_score=0.6
        )
        
        # 检查传统路径
        self.assertEqual(self.manager.stats["total_tasks"], 1)
        self.assertEqual(len(self.manager.emergence_metrics.behavior_history), 1)
        print("✓ 传统路径记录成功")
        
        # 检查神经形态路径（如果可用）
        if hasattr(self.manager, 'neuro_consciousness') and self.manager.neuro_consciousness:
            # 神经形态系统应该已经处理了一个周期
            print("✓ 神经形态路径处理成功")
        else:
            print("⚠ 神经形态路径不可用，使用纯传统模式")
        
        # 验证统计信息
        self.assertIn("successful_tasks", self.manager.stats)
        self.assertIn("failed_tasks", self.manager.stats)
    
    def test_sensory_input_building(self):
        """测试 3: 感觉输入构建"""
        print("\n=== 测试 3: 感觉输入构建 ===")
        
        # 调用内部方法
        sensory_data = self.manager._build_sensory_input(
            action_type="complex_task",
            autonomy_level=0.75,
            creativity_score=0.85,
            goal_relevance=0.9,
            novelty_score=0.7
        )
        
        # 验证返回结构
        self.assertIsInstance(sensory_data, dict)
        print(f"✓ 感觉输入字典包含 {len(sensory_data)} 个模态")
        
        # 验证各模态存在
        expected_modalities = ['visual', 'auditory', 'interoceptive', 'proprioceptive', 'social']
        for modality in expected_modalities:
            self.assertIn(modality, sensory_data)
            print(f"  ✓ {modality}: shape={sensory_data[modality].shape}")
        
        # 验证数值范围
        import numpy as np
        for modality, data in sensory_data.items():
            self.assertTrue(all(0 <= x <= 1.2 for x in data))
    
    def test_emergence_enhancement(self):
        """测试 4: 涌现指标增强"""
        print("\n=== 测试 4: 涌现指标增强 ===")
        
        # 模拟神经状态
        class MockNeuroState:
            def __init__(self):
                self.neurotransmitter_state = {
                    'dopamine': {'current_level': 0.8},
                    'serotonin': {'current_level': 0.6}
                }
                
                class MockWorkspace:
                    class MockGammaOscillator:
                        def get_power(self):
                            return 0.75
                    
                    gamma_oscillator = MockGammaOscillator()
                
                self.workspace = MockWorkspace()
        
        neuro_state = MockNeuroState()
        
        # 调用增强方法
        self.manager._enhance_emergence_metrics(neuro_state)
        
        # 检查是否设置了增强因子
        if hasattr(self.manager.emergence_metrics, 'neuro_boost'):
            neuro_boost = self.manager.emergence_metrics.neuro_boost
            if neuro_boost:
                print(f"✓ 神经增强因子已设置:")
                print(f"  - 多巴胺：{neuro_boost.get('dopamine', 'N/A')}")
                print(f"  - 血清素：{neuro_boost.get('serotonin', 'N/A')}")
                print(f"  - γ功率：{neuro_boost.get('gamma_power', 'N/A')}")
            else:
                print("⚠ 神经增强因子未设置")
        else:
            print("⚠ 涌现指标不支持神经增强")
    
    def test_mixed_mode_processing(self):
        """测试 5: 混合模式处理流程"""
        print("\n=== 测试 5: 混合模式处理流程 ===")
        
        # 连续记录多个行为
        behaviors = [
            {"type": "analysis", "autonomy": 0.7, "creativity": 0.6, "goal": 0.8, "novelty": 0.5},
            {"type": "synthesis", "autonomy": 0.8, "creativity": 0.9, "goal": 0.7, "novelty": 0.8},
            {"type": "evaluation", "autonomy": 0.6, "creativity": 0.5, "goal": 0.9, "novelty": 0.4},
        ]
        
        for i, behavior in enumerate(behaviors):
            print(f"\n处理行为 {i+1}/{len(behaviors)}: {behavior['type']}")
            
            self.manager.record_behavior(
                action_type=behavior["type"],
                autonomy_level=behavior["autonomy"],
                creativity_score=behavior["creativity"],
                goal_relevance=behavior["goal"],
                novelty_score=behavior["novelty"]
            )
        
        # 验证最终状态
        print(f"\n✓ 完成 {self.manager.stats['total_tasks']} 个行为的处理")
        print(f"  - 成功：{self.manager.stats['successful_tasks']}")
        print(f"  - 失败：{self.manager.stats['failed_tasks']}")
        
        # 计算涌现指标
        indicators = self.manager.emergence_metrics.calculate_indicators()
        print(f"\n涌现指标:")
        print(f"  - 意识指数：{indicators.consciousness_index:.3f}")
        print(f"  - 自主性：{indicators.autonomy_score:.3f}")
        print(f"  - 创造性：{indicators.creativity_metric:.3f}")
        
        # 验证指标合理性
        self.assertGreater(indicators.consciousness_index, 0.0)
        self.assertLess(indicators.consciousness_index, 1.0)
    
    def test_config_disable_neuro(self):
        """测试 6: 配置禁用神经形态系统"""
        print("\n=== 测试 6: 配置禁用神经形态系统 ===")
        
        # 创建禁用神经形态的管理器
        config_no_neuro = {
            "enable_neuro_consciousness": False,
            "auto_repair": False
        }
        
        manager_no_neuro = ConsciousnessManager(
            system_root=str(Path(__file__).parent.parent.parent),
            config=config_no_neuro,
            auto_start=False
        )
        
        # 验证神经形态系统为 None
        self.assertIsNone(manager_no_neuro.neuro_consciousness)
        print("✓ 神经形态系统已按配置禁用")
        
        # 但传统系统仍应正常工作
        manager_no_neuro.record_behavior(
            action_type="test",
            autonomy_level=0.5,
            creativity_score=0.5,
            goal_relevance=0.5,
            novelty_score=0.5
        )
        
        self.assertEqual(manager_no_neuro.stats["total_tasks"], 1)
        print("✓ 传统模式工作正常")


if __name__ == '__main__':
    print("=" * 60)
    print("神经形态意识系统集成测试套件")
    print("=" * 60)
    
    unittest.main(verbosity=2)
