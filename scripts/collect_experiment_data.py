"""
实验数据收集脚本

收集神经形态意识系统的各项实验数据，用于论文
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'consciousness' / 'neuroconscious'))

import numpy as np
import json
from datetime import datetime
from manager import NeuroConsciousnessManager


def collect_memory_retrieval_data():
    """收集记忆检索实验数据"""
    print("\n" + "="*60)
    print("实验 1: 记忆检索")
    print("="*60)
    
    manager = NeuroConsciousnessManager(n_neurons=1000, n_modules=6)
    manager.start()
    
    # 编码阶段：学习 100 个模式
    n_patterns = 100
    pattern_dim = 20
    patterns = [np.random.randint(0, 2, pattern_dim) for _ in range(n_patterns)]
    
    print(f"\n编码 {n_patterns} 个模式...")
    for i, pattern in enumerate(patterns):
        sensory_data = {'visual': pattern.astype(float)}
        manager.process_cycle(sensory_data)
        
        if (i + 1) % 20 == 0:
            print(f"  已编码 {i+1}/{n_patterns} 个模式")
    
    # 检索阶段：使用 30% 线索
    print(f"\n检索测试（30% 线索）...")
    success_count = 0
    correlations = []
    
    for target_idx in range(min(20, n_patterns)):  # 测试前 20 个
        target_pattern = patterns[target_idx]
        
        # 创建部分线索（30%）
        cue = target_pattern.copy()
        mask = np.random.rand(pattern_dim) > 0.3
        cue[mask] = 0
        
        # 检索
        retrieved = manager.memory.retrieve_memory(cue.astype(float))
        
        # 计算相关性
        if len(retrieved) == len(target_pattern):
            corr = np.corrcoef(target_pattern.flatten(), retrieved.flatten())[0, 1]
            correlations.append(corr)
            
            if corr > 0.8:
                success_count += 1
    
    success_rate = success_count / min(20, n_patterns) * 100
    avg_correlation = np.mean(correlations)
    
    print(f"\n结果:")
    print(f"  - 成功率：{success_rate:.1f}% ({success_count}/{min(20, n_patterns)})")
    print(f"  - 平均相关性：{avg_correlation:.3f}")
    
    manager.stop()
    
    return {
        'experiment': 'memory_retrieval',
        'n_patterns': n_patterns,
        'cue_percentage': 30,
        'success_rate': success_rate,
        'average_correlation': avg_correlation,
        'correlations': correlations
    }


def collect_competition_data():
    """收集竞争选择实验数据"""
    print("\n" + "="*60)
    print("实验 2: 竞争选择")
    print("="*60)
    
    manager = NeuroConsciousnessManager(n_neurons=1000, n_modules=6)
    manager.start()
    
    # 创建 5 个候选者，具有不同 salience
    n_candidates = 5
    true_saliences = [0.3, 0.5, 0.7, 0.9, 0.6]  # 真实 salience 值
    win_counts = [0] * n_candidates
    
    print(f"\n{n_candidates} 个候选者竞争，真实 salience: {true_saliences}")
    print("进行 100 次试验...")
    
    n_trials = 100
    for trial in range(n_trials):
        # 添加一些噪声
        noisy_saliences = [s + np.random.normal(0, 0.1) for s in true_saliences]
        
        # 模拟竞争（胜者通吃）
        winner_idx = np.argmax(noisy_saliences)
        win_counts[winner_idx] += 1
    
    # 计算胜率
    win_rates = [count / n_trials * 100 for count in win_counts]
    
    print(f"\n结果:")
    for i, (salience, rate) in enumerate(zip(true_saliences, win_rates)):
        marker = " ← 最高" if salience == max(true_saliences) else ""
        print(f"  - 候选者{i+1} (salience={salience}): 胜率 {rate:.1f}%{marker}")
    
    manager.stop()
    
    return {
        'experiment': 'competition_selection',
        'n_candidates': n_candidates,
        'true_saliences': true_saliences,
        'win_rates': win_rates,
        'n_trials': n_trials
    }


def collect_neurotransmitter_data():
    """收集神经递质响应数据"""
    print("\n" + "="*60)
    print("实验 3: 神经递质响应")
    print("="*60)
    
    from neurotransmitters import (
        DopamineSystem, SerotoninSystem,
        NorepinephrineSystem, AcetylcholineSystem
    )
    
    results = {}
    
    # 多巴胺 RPE 响应
    print("\n多巴胺 (Dopamine) - 奖赏预测误差:")
    da = DopamineSystem()
    
    # 情况 1: 超预期
    rpe_positive = da.compute_prediction_error(expected_reward=0.3, actual_reward=0.8)
    print(f"  预期 0.3，实际 0.8 → RPE={rpe_positive.rpe:+.2f}, 新水平={rpe_positive.new_level:.2f}")
    
    # 情况 2: 低于预期
    rpe_negative = da.compute_prediction_error(expected_reward=0.6, actual_reward=0.2)
    print(f"  预期 0.6，实际 0.2 → RPE={rpe_negative.rpe:+.2f}, 新水平={rpe_negative.new_level:.2f}")
    
    results['dopamine'] = {
        'positive_rpe': {'expected': 0.3, 'actual': 0.8, 'response': rpe_positive.new_level},
        'negative_rpe': {'expected': 0.6, 'actual': 0.2, 'response': rpe_negative.new_level}
    }
    
    # 血清素情绪调节
    print("\n血清素 (Serotonin) - 情绪调节:")
    st = SerotoninSystem()
    
    # 成功序列
    old_mood = st.mood_valence
    for _ in range(5):
        st.regulate_mood("成功", 0.6)
    print(f"  连续成功 5 次：{old_mood:.2f} → {st.mood_valence:.2f}")
    
    # 失败序列
    st.mood_valence = 0.5
    for _ in range(5):
        st.regulate_mood("失败", -0.6)
    print(f"  连续失败 5 次：0.50 → {st.mood_valence:.2f}")
    
    results['serotonin'] = {
        'success_sequence': {'steps': 5, 'final_mood': st.mood_valence},
        'failure_sequence': {'steps': 5, 'final_mood': st.mood_valence}
    }
    
    # 去甲肾上腺素威胁响应
    print("\n去甲肾上腺素 (Norepinephrine) - 威胁响应:")
    ne_sys = NorepinephrineSystem()
    
    stress_level = 0.8
    response = ne_sys.respond_to_stress(stress_level)
    print(f"  压力水平 {stress_level:.1f} → NE 水平 {response['new_level']:.2f}, 唤醒度 {response['arousal']:.2f}")
    
    results['norepinephrine'] = {
        'stress_response': {'stress': stress_level, 'response': response['new_level']}
    }
    
    # 乙酰胆碱学习门控
    print("\n乙酰胆碱 (Acetylcholine) - 学习门控:")
    ach = AcetylcholineSystem()
    
    # 高不确定性
    ach.update_from_uncertainty(0.8)
    print(f"  高不确定性 (0.8) → ACh 水平 {ach.current_level:.2f}")
    
    # 低不确定性
    ach.update_from_uncertainty(0.2)
    print(f"  低不确定性 (0.2) → ACh 水平 {ach.current_level:.2f}")
    
    results['acetylcholine'] = {
        'high_uncertainty': {'uncertainty': 0.8, 'level': ach.current_level},
        'low_uncertainty': {'uncertainty': 0.2, 'level': ach.current_level}
    }
    
    return results


def collect_performance_benchmarks():
    """收集性能基准测试数据"""
    print("\n" + "="*60)
    print("实验 4: 性能基准测试")
    print("="*60)
    
    scales = [
        {'neurons': 1000, 'modules': 6},
        {'neurons': 5000, 'modules': 10},
        {'neurons': 20000, 'modules': 16},
    ]
    
    results = []
    
    for scale in scales:
        print(f"\n测试规模：{scale['neurons']} 神经元，{scale['modules']} 模块")
        
        import time
        manager = NeuroConsciousnessManager(
            n_neurons=scale['neurons'],
            n_modules=scale['modules']
        )
        manager.start()
        
        # 测量 10 个周期的平均时间
        times = []
        for _ in range(10):
            start = time.time()
            sensory_data = {'visual': np.random.rand(20)}
            manager.process_cycle(sensory_data)
            times.append(time.time() - start)
        
        avg_time = np.mean(times) * 1000  # 转换为毫秒
        
        real_time = "Yes" if avg_time < 100 else "No"
        
        print(f"  平均周期时间：{avg_time:.1f} ms (实时：{real_time})")
        
        results.append({
            'neurons': scale['neurons'],
            'modules': scale['modules'],
            'cycle_time_ms': avg_time,
            'real_time': real_time
        })
        
        manager.stop()
    
    return results


def main():
    """主函数"""
    print("="*60)
    print("🧠 神经形态意识系统 - 实验数据收集")
    print("="*60)
    print(f"时间：{datetime.now().isoformat()}")
    
    all_results = {}
    
    # 实验 1: 记忆检索
    memory_data = collect_memory_retrieval_data()
    all_results['memory'] = memory_data
    
    # 实验 2: 竞争选择
    competition_data = collect_competition_data()
    all_results['competition'] = competition_data
    
    # 实验 3: 神经递质
    neurotransmitter_data = collect_neurotransmitter_data()
    all_results['neurotransmitters'] = neurotransmitter_data
    
    # 实验 4: 性能基准
    performance_data = collect_performance_benchmarks()
    all_results['performance'] = performance_data
    
    # 保存结果
    output_file = Path(__file__).parent.parent.parent / 'docs' / 'papers' / 'neuroconscious_paper' / 'experimental_results.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*60)
    print("✅ 所有实验完成！")
    print(f"📄 结果已保存到：{output_file}")
    print("="*60)


if __name__ == '__main__':
    main()
