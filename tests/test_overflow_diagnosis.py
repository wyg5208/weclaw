"""
溢出诊断脚本 - 逐函数检测溢出位置
"""

import sys
import warnings
import numpy as np
from pathlib import Path

# 捕获所有溢出警告
warnings.filterwarnings('error', category=RuntimeWarning)

neuroconscious_path = Path(__file__).parent / 'src' / 'consciousness' / 'neuroconscious'
sys.path.insert(0, str(neuroconscious_path))

print("="*60)
print("🔍 神经形态意识系统 - 溢出诊断")
print("="*60)

# 测试 1: 记忆系统
print("\n1️⃣ 测试记忆系统...")
try:
    from core import SynapticPlasticityMemory
    memory = SynapticPlasticityMemory(n_neurons=500, sparsity=0.02)
    
    # 编码测试
    pattern = np.random.randn(500) * 0.5
    pattern[pattern > 0.3] = 1.0
    pattern[pattern <= 0.3] = 0.0
    memory.encode_memory(pattern, 0.0)
    
    # 检索测试
    cue = pattern[:100]
    retrieved = memory.retrieve_memory(cue, n_iterations=5)
    print("   ✅ 记忆系统正常")
except RuntimeWarning as e:
    print(f"   ❌ 记忆系统溢出：{e}")
except Exception as e:
    print(f"   ⚠️  记忆系统其他错误：{e}")

# 测试 2: 预测编码系统
print("\n2️⃣ 测试预测编码系统...")
try:
    from predictive_coding import PredictiveHierarchy, SensoryInput, HierarchyLevel
    
    hierarchy = PredictiveHierarchy()
    
    # 预测生成
    context = np.random.randn(10)
    prediction = hierarchy.generate_prediction(HierarchyLevel.INTEROCEPTION, context)
    print("   ✅ 预测生成正常")
    
    # 预测误差计算
    actual = np.random.randn(10)
    error = hierarchy.compute_prediction_error(HierarchyLevel.INTEROCEPTION, actual)
    print(f"   ✅ 预测误差计算正常，误差范围：[{np.min(error):.3f}, {np.max(error):.3f}]")
    
    # 自我推断
    sensory_input = SensoryInput(
        interoceptive=np.random.randn(10),
        proprioceptive=np.random.randn(6),
        exteroceptive=np.random.randn(20),
        social=np.random.randn(5)
    )
    self_rep = hierarchy.infer_self(sensory_input)
    print("   ✅ 自我推断正常")
    
    # 统计信息获取
    stats = hierarchy.get_stats()
    print(f"   ✅ 统计信息正常，自由能：{stats['current_free_energy']:.3f}")
    
except RuntimeWarning as e:
    print(f"   ❌ 预测编码系统溢出：{e}")
except Exception as e:
    print(f"   ⚠️  预测编码系统其他错误：{e}")

# 测试 3: 全局工作空间
print("\n3️⃣ 测试全局工作空间...")
try:
    from core import GlobalNeuralWorkspace, ConsciousContent
    
    workspace = GlobalNeuralWorkspace(n_modules=4)
    
    # 创建候选内容
    candidates = [
        ConsciousContent(
            content_id=f"test_{i}",
            representation=np.random.randn(100),
            salience=0.8
        )
        for i in range(3)
    ]
    
    # 竞争选择
    winner = workspace.select_winner(candidates, 0.0)
    print("   ✅ 竞争选择正常")
    
    # γ绑定
    if winner:
        workspace.bind_with_gamma(winner, 0.0)
        print("   ✅ γ绑定正常")
    
    # 获取统计
    stats = workspace.get_stats()
    print(f"   ✅ 工作空间统计正常，γ功率：{stats['gamma_power']:.3f}")
    
except RuntimeWarning as e:
    print(f"   ❌ 工作空间溢出：{e}")
except Exception as e:
    print(f"   ⚠️  工作空间其他错误：{e}")

# 测试 4: 完整处理周期
print("\n4️⃣ 测试完整处理周期...")
try:
    from manager import NeuroConsciousnessManager
    
    manager = NeuroConsciousnessManager(n_neurons=500, n_modules=4)
    manager.start()
    
    # 处理多个周期
    for i in range(5):
        sensory_data = {
            'visual': np.random.randn(50) * 0.5,
            'auditory': np.random.randn(30) * 0.4,
        }
        state = manager.process_cycle(sensory_data)
    
    print("   ✅ 完整处理周期正常")
    
    # 获取统计
    stats = manager.get_stats()
    print(f"   ✅ 统计信息：γ功率={stats['workspace']['gamma_power']:.3f}")
    
    manager.stop()
    
except RuntimeWarning as e:
    print(f"   ❌ 处理周期溢出：{e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"   ⚠️  处理周期其他错误：{e}")
    import traceback
    traceback.print_exc()

# 测试 5: 边界情况测试
print("\n5️⃣ 测试边界情况...")
try:
    from manager import NeuroConsciousnessManager
    
    manager = NeuroConsciousnessManager(n_neurons=500, n_modules=4)
    manager.start()
    
    # 大数值刺激
    large_stimulus = {'visual': np.ones(50) * 100}
    state = manager.process_cycle(large_stimulus)
    print("   ✅ 大数值刺激正常处理")
    
    # 负数值刺激
    negative_stimulus = {'visual': np.ones(50) * -100}
    state = manager.process_cycle(negative_stimulus)
    print("   ✅ 负数值刺激正常处理")
    
    # 随机刺激
    random_stimulus = {'visual': np.random.randn(50) * 50}
    state = manager.process_cycle(random_stimulus)
    print("   ✅ 随机刺激正常处理")
    
    manager.stop()
    
except RuntimeWarning as e:
    print(f"   ❌ 边界情况溢出：{e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"   ⚠️  边界情况其他错误：{e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("✨ 诊断完成")
print("="*60)
