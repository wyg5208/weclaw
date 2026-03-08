"""
突触权重变化验证脚本
====================
验证学习模块的权重矩阵在刺激后是否确实发生了变化。
"""
import sys
import os
import numpy as np

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'consciousness', 'neuroconscious'))

from manager import NeuroConsciousnessManager


def main():
    print("=" * 60)
    print("突触权重变化验证测试")
    print("=" * 60)
    
    # 初始化系统
    manager = NeuroConsciousnessManager(n_neurons=1000, n_modules=6)
    manager.start()
    
    # 记录初始权重
    w0 = manager.learning.get_weight_matrix().copy()
    print(f"\n[初始状态]")
    print(f"  权重矩阵形状: {w0.shape}")
    print(f"  均值: {np.mean(w0):.6f}")
    print(f"  最大值: {np.max(w0):.6f}")
    print(f"  最小值(非零): {w0[w0 > 0].min():.6f}")
    print(f"  稀疏度: {np.mean(w0 < 0.01):.2%}")
    
    # 模拟多次刺激
    stimuli = [
        ("红色闪光", [1.0, 0.0, 0.0]),
        ("蓝色闪光", [0.0, 0.5, 1.0]),
        ("绿色闪光", [0.0, 1.0, 0.0]),
        ("红色闪光", [1.0, 0.0, 0.0]),
        ("蓝色闪光", [0.0, 0.5, 1.0]),
        ("随机图案", list(np.random.rand(3))),
        ("红色闪光", [1.0, 0.0, 0.0]),
        ("绿色闪光", [0.0, 1.0, 0.0]),
        ("蓝色闪光", [0.0, 0.5, 1.0]),
        ("随机图案", list(np.random.rand(3))),
    ]
    
    print(f"\n{'=' * 60}")
    print(f"开始模拟 {len(stimuli)} 次刺激...")
    print(f"{'=' * 60}")
    
    for i, (name, color) in enumerate(stimuli, 1):
        sensory_data = {'visual': np.array(color) * 10}
        result = manager.process_cycle(sensory_data)
        
        w_now = manager.learning.get_weight_matrix()
        delta = w_now - w0
        
        stats = manager.learning.get_stats()
        hebbian = stats['hebbian']
        
        print(f"\n[刺激 #{i}: {name}]")
        print(f"  权重均值: {np.mean(w_now):.6f} (Δ={np.mean(delta):+.6f})")
        print(f"  权重最大: {np.max(w_now):.6f} (Δ={np.max(delta):+.6f})")
        print(f"  |Δ| 均值: {np.mean(np.abs(delta)):.6f}")
        print(f"  |Δ| 最大: {np.max(np.abs(delta)):.6f}")
        print(f"  变化>0.001的元素数: {np.sum(np.abs(delta) > 0.001)}")
        print(f"  变化>0.01的元素数:  {np.sum(np.abs(delta) > 0.01)}")
        print(f"  LTP增强: {hebbian['ltp_count']}, LTD抑制: {hebbian['ltd_count']}")
    
    # 最终对比
    w_final = manager.learning.get_weight_matrix()
    delta_total = w_final - w0
    
    print(f"\n{'=' * 60}")
    print(f"最终对比（{len(stimuli)} 次刺激后 vs 初始）")
    print(f"{'=' * 60}")
    print(f"  总权重变化 |Δ| 均值: {np.mean(np.abs(delta_total)):.6f}")
    print(f"  总权重变化 |Δ| 最大: {np.max(np.abs(delta_total)):.6f}")
    print(f"  正变化 (LTP) 元素数: {np.sum(delta_total > 0)}")
    print(f"  负变化 (LTD) 元素数: {np.sum(delta_total < 0)}")
    print(f"  无变化元素数: {np.sum(delta_total == 0)}")
    print(f"  变化>0.001: {np.sum(np.abs(delta_total) > 0.001)}")
    print(f"  变化>0.01:  {np.sum(np.abs(delta_total) > 0.01)}")
    print(f"  变化>0.05:  {np.sum(np.abs(delta_total) > 0.05)}")
    print(f"  变化>0.1:   {np.sum(np.abs(delta_total) > 0.1)}")
    
    # 可视化用：打印 20x20 采样的 delta 矩阵片段
    step = w0.shape[0] // 20
    sample = delta_total[::step, ::step][:20, :20]
    print(f"\n  20x20 采样 delta 矩阵统计:")
    print(f"    均值: {np.mean(sample):.6f}")
    print(f"    最大: {np.max(sample):.6f}")
    print(f"    最小: {np.min(sample):.6f}")
    print(f"    标准差: {np.std(sample):.6f}")
    
    manager.stop()
    print(f"\n{'=' * 60}")
    print("测试完成！")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
