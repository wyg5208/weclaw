"""
测试刺激输入响应

验证点击刺激按钮后，系统状态是否有变化
"""

import sys
from pathlib import Path

# 添加模块路径
neuroconscious_path = Path(__file__).parent / 'src' / 'consciousness' / 'neuroconscious'
sys.path.insert(0, str(neuroconscious_path))

from manager import NeuroConsciousnessManager
import numpy as np
import time

print("="*60)
print("🧪 神经形态意识系统 - 刺激输入响应测试")
print("="*60)

# 创建系统
print("\n1️⃣ 初始化神经形态系统...")
manager = NeuroConsciousnessManager(n_neurons=1000, n_modules=6)
manager.start()
print("✅ 系统启动成功")

# 获取基线状态
print("\n2️⃣ 获取基线状态...")
baseline_stats = manager.get_stats()
print(f"   基础γ功率：{baseline_stats['workspace']['gamma_power']:.3f}")
print(f"   基础γ相位：{baseline_stats['workspace']['gamma_phase']:.3f}")
print(f"   多巴胺水平：{baseline_stats['neuromodulators']['dopamine']['current_level']:.3f}")

# 施加视觉刺激（红色闪光）
print("\n3️⃣ 施加视觉刺激：红色闪光")
sensory_data = {
    'visual': np.array([1.0, 0.0, 0.0]) * 10  # 高强度红色
}
print(f"   输入模式：{sensory_data['visual']}")

# 处理一个周期
start_time = time.time()
state = manager.process_cycle(sensory_data)
elapsed = (time.time() - start_time) * 1000  # 转为毫秒

print(f"   ⏱️ 处理耗时：{elapsed:.2f}ms")

# 获取刺激后状态
print("\n4️⃣ 获取刺激后状态...")
post_stimulus_stats = manager.get_stats()
print(f"   γ功率：{post_stimulus_stats['workspace']['gamma_power']:.3f}")
print(f"   γ相位：{post_stimulus_stats['workspace']['gamma_phase']:.3f}")
print(f"   多巴胺水平：{post_stimulus_stats['neuromodulators']['dopamine']['current_level']:.3f}")

# 计算变化
print("\n5️⃣ 分析变化:")
gamma_power_change = post_stimulus_stats['workspace']['gamma_power'] - baseline_stats['workspace']['gamma_power']
gamma_phase_change = post_stimulus_stats['workspace']['gamma_phase'] - baseline_stats['workspace']['gamma_phase']
da_change = post_stimulus_stats['neuromodulators']['dopamine']['current_level'] - baseline_stats['neuromodulators']['dopamine']['current_level']

print(f"   Δγ功率：{gamma_power_change:+.3f} ({'↑' if gamma_power_change > 0 else '↓' if gamma_power_change < 0 else '='})")
print(f"   Δγ相位：{gamma_phase_change:+.3f} rad")
print(f"   Δ多巴胺：{da_change:+.3f}")

# 检查是否有显著变化
print("\n6️⃣ 显著性检测:")
if abs(gamma_power_change) > 0.05:
    print("   ✅ γ功率有显著变化")
else:
    print("   ⚠️  γ功率变化不明显 (< 0.05)")

if abs(gamma_phase_change) > 0.1:
    print("   ✅ γ相位有显著变化")
else:
    print("   ⚠️  γ相位变化不明显 (< 0.1 rad)")

# 连续施加多次刺激
print("\n7️⃣ 连续刺激测试（5 次）:")
for i in range(5):
    sensory_data = {
        'visual': np.random.rand(3) * 10
    }
    state = manager.process_cycle(sensory_data)
    stats = manager.get_stats()
    print(f"   第{i+1}次：γ功率={stats['workspace']['gamma_power']:.3f}, "
          f"γ相位={stats['workspace']['gamma_phase']:.3f}")

# 停止系统
print("\n8️⃣ 停止系统...")
manager.stop()

print("\n" + "="*60)
print("✨ 测试完成！")
print("="*60)
