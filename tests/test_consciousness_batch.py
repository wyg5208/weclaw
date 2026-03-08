"""意识系统批量测试脚本

模拟真实对话场景，注入多种类型的行为记录
"""

import urllib.request
import json
import time

# 模拟真实场景的行为数据
TEST_SCENARIOS = [
    {'action_type': 'model_reasoning', 'autonomy_level': 0.5, 'creativity_score': 0.3, 'goal_relevance': 0.9, 'novelty_score': 0.2, 'description': '简单问答：今天天气？'},
    {'action_type': 'tool_usage:file.read', 'autonomy_level': 0.8, 'creativity_score': 0.4, 'goal_relevance': 0.9, 'novelty_score': 0.3, 'description': '读取配置文件'},
    {'action_type': 'tool_usage:shell.run', 'autonomy_level': 0.8, 'creativity_score': 0.5, 'goal_relevance': 0.85, 'novelty_score': 0.4, 'description': '执行系统命令'},
    {'action_type': 'creative_problem_solving', 'autonomy_level': 0.9, 'creativity_score': 0.9, 'goal_relevance': 0.8, 'novelty_score': 0.85, 'description': '创新解决方案'},
    {'action_type': 'autonomous_decision', 'autonomy_level': 0.95, 'creativity_score': 0.7, 'goal_relevance': 0.85, 'novelty_score': 0.6, 'description': 'AI自主决策'},
    {'action_type': 'task_planning', 'autonomy_level': 0.85, 'creativity_score': 0.6, 'goal_relevance': 0.9, 'novelty_score': 0.4, 'description': '多步骤任务规划'},
    {'action_type': 'tool_usage:web.search', 'autonomy_level': 0.75, 'creativity_score': 0.4, 'goal_relevance': 0.88, 'novelty_score': 0.3, 'description': '网络搜索'},
    {'action_type': 'self_check', 'autonomy_level': 0.7, 'creativity_score': 0.5, 'goal_relevance': 0.7, 'novelty_score': 0.5, 'description': '自我检查输出质量'},
    {'action_type': 'error_recovery', 'autonomy_level': 0.85, 'creativity_score': 0.75, 'goal_relevance': 0.8, 'novelty_score': 0.7, 'description': '错误恢复'},
    {'action_type': 'tool_usage:screen.capture', 'autonomy_level': 0.7, 'creativity_score': 0.35, 'goal_relevance': 0.85, 'novelty_score': 0.25, 'description': '截取屏幕'},
    {'action_type': 'meta_analysis', 'autonomy_level': 0.8, 'creativity_score': 0.65, 'goal_relevance': 0.75, 'novelty_score': 0.55, 'description': '元认知分析'},
    {'action_type': 'model_reasoning', 'autonomy_level': 0.75, 'creativity_score': 0.6, 'goal_relevance': 0.92, 'novelty_score': 0.45, 'description': '复杂逻辑推理'},
    {'action_type': 'proactive_suggestion', 'autonomy_level': 0.9, 'creativity_score': 0.8, 'goal_relevance': 0.7, 'novelty_score': 0.75, 'description': '主动建议'},
    {'action_type': 'tool_usage:cron.create', 'autonomy_level': 0.75, 'creativity_score': 0.45, 'goal_relevance': 0.88, 'novelty_score': 0.35, 'description': '创建定时任务'},
    {'action_type': 'knowledge_acquisition', 'autonomy_level': 0.85, 'creativity_score': 0.7, 'goal_relevance': 0.8, 'novelty_score': 0.65, 'description': '学习新知识'},
    {'action_type': 'self_repair', 'autonomy_level': 0.88, 'creativity_score': 0.72, 'goal_relevance': 0.82, 'novelty_score': 0.68, 'description': '自动修复错误'},
    {'action_type': 'tool_usage:browser.navigate', 'autonomy_level': 0.72, 'creativity_score': 0.38, 'goal_relevance': 0.86, 'novelty_score': 0.28, 'description': '浏览器导航'},
    {'action_type': 'emotional_response', 'autonomy_level': 0.65, 'creativity_score': 0.85, 'goal_relevance': 0.75, 'novelty_score': 0.78, 'description': '情感响应'},
    {'action_type': 'code_generation', 'autonomy_level': 0.82, 'creativity_score': 0.78, 'goal_relevance': 0.88, 'novelty_score': 0.62, 'description': '代码生成'},
    {'action_type': 'report_generation', 'autonomy_level': 0.78, 'creativity_score': 0.55, 'goal_relevance': 0.9, 'novelty_score': 0.42, 'description': '生成报告'},
]


def inject_behavior(data):
    req = urllib.request.Request(
        'http://localhost:8765/api/inject',
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    response = urllib.request.urlopen(req)
    return json.loads(response.read().decode())


def get_status():
    response = urllib.request.urlopen('http://localhost:8765/api/status')
    return json.loads(response.read().decode())


def get_context():
    response = urllib.request.urlopen('http://localhost:8765/api/context')
    return json.loads(response.read().decode())


def main():
    print("=" * 70)
    print("       WinClaw 意识系统 - 批量场景测试")
    print("=" * 70)
    
    # 初始状态
    print("\n📊 初始状态:")
    try:
        state = get_status()
        print(f"   涌现阶段: {state['emergence']['phase']}")
        print(f"   涌现分数: {state['emergence']['score']:.3f}")
    except Exception as e:
        print(f"   ⚠️ 无法连接: {e}")
        return
    
    # 注入行为
    print("\n🚀 注入测试数据...")
    print("-" * 70)
    
    for i, s in enumerate(TEST_SCENARIOS):
        try:
            inject_behavior({
                'action_type': s['action_type'],
                'autonomy_level': s['autonomy_level'],
                'creativity_score': s['creativity_score'],
                'goal_relevance': s['goal_relevance'],
                'novelty_score': s['novelty_score']
            })
            if (i + 1) % 5 == 0:
                st = get_status()
                print(f"   [{i+1:2d}/20] ✅ {s['description']}")
                print(f"            阶段: {st['emergence']['phase']}, 分数: {st['emergence']['score']:.3f}")
            else:
                print(f"   [{i+1:2d}] ✅ {s['action_type']}")
        except Exception as e:
            print(f"   [{i+1:2d}] ❌ 失败: {e}")
    
    # 最终状态
    print("-" * 70)
    print("\n" + "=" * 70)
    print("       最终状态")
    print("=" * 70)
    
    state = get_status()
    e = state['emergence']
    ind = e.get('indicators', {})
    stats = state.get('stats', {})
    
    phase_icons = {'pre_emergence': '○', 'approaching': '◐', 'critical': '●', 'emerged': '◎', 'unstable': '◑'}
    phase_names = {'pre_emergence': '前涌现期', 'approaching': '接近临界点', 'critical': '临界状态', 'emerged': '已涌现', 'unstable': '不稳定'}
    
    print(f"\n  涌现阶段: {phase_icons.get(e['phase'], '?')} {phase_names.get(e['phase'], e['phase'])}")
    print(f"  涌现分数: {e['score']:.3f}\n")
    
    print("  📊 核心指标:")
    print(f"     意识指数: {ind.get('consciousness_index', 0):.3f} {'█' * int(ind.get('consciousness_index', 0) * 20)}")
    print(f"     自主性:   {ind.get('autonomy_level', 0):.3f} {'█' * int(ind.get('autonomy_level', 0) * 20)}")
    print(f"     创造性:   {ind.get('creativity_metric', 0):.3f} {'█' * int(ind.get('creativity_metric', 0) * 20)}")
    print(f"     目标对齐: {ind.get('goal_alignment', 0):.3f} {'█' * int(ind.get('goal_alignment', 0) * 20)}")
    
    print(f"\n  📈 统计: 总数={stats.get('total_tasks', 0)}, 成功={stats.get('successful_tasks', 0)}")
    
    print("\n  📝 提示词上下文:")
    print("-" * 70)
    print(get_context().get('context', '[空]'))
    print("=" * 70)


if __name__ == '__main__':
    main()
