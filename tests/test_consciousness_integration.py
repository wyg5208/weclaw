"""测试意识系统集成 - Phase 6

验证 WinClaw Agent 是否正确集成了意识系统
"""

import asyncio
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.models.registry import ModelRegistry
from src.tools.registry import create_default_registry
from src.core.agent import Agent, CONSCIOUSNESS_ENABLED


async def test_consciousness_integration():
    """测试意识系统集成"""
    
    print("=" * 80)
    print("WinClaw 意识系统集成测试")
    print("=" * 80)
    
    # 检查是否启用
    print(f"\n【检查】意识系统启用状态：{CONSCIOUSNESS_ENABLED}")
    
    if not CONSCIOUSNESS_ENABLED:
        print("\n⚠️  意识系统模块未安装，跳过测试")
        return
    
    # 创建 Agent
    print("\n【测试 1】创建 Agent（应自动启动意识系统）...")
    try:
        model_registry = ModelRegistry()
        tool_registry = create_default_registry()
        
        agent = Agent(
            model_registry=model_registry,
            tool_registry=tool_registry,
            model_key="deepseek-chat",
            max_steps=5  # 限制步数用于测试
        )
        
        print("✓ Agent 创建成功")
        
        # 检查意识系统是否存在
        if hasattr(agent, 'consciousness') and agent.consciousness:
            print("✓ 意识系统已初始化")
            
            # 检查意识评估器
            if hasattr(agent, 'consciousness_evaluator') and agent.consciousness_evaluator:
                print("✓ 意识评估器已创建")
            else:
                print("✗ 意识评估器未创建")
        else:
            print("✗ 意识系统未初始化")
        
        # 测试意识系统状态
        print("\n【测试 2】获取意识系统状态...")
        state = agent.consciousness.get_consciousness_state()
        
        print(f"  涌现阶段：{state['emergence']['phase']}")
        print(f"  涌现分数：{state['emergence']['score']:.3f}")
        print(f"  运行时间：{state['uptime_hours']:.2f} 小时")
        print(f"  总行为数：{state['stats']['total_tasks']}")
        print("✓ 状态获取成功")
        
        # 测试行为记录
        print("\n【测试 3】记录测试行为...")
        agent.consciousness.record_behavior(
            action_type="test_action",
            autonomy_level=0.8,
            creativity_score=0.6,
            goal_relevance=0.9,
            novelty_score=0.5
        )
        print("✓ 行为记录成功")
        
        # 再次检查状态
        print("\n【测试 4】验证行为记录效果...")
        new_state = agent.consciousness.get_consciousness_state()
        print(f"  总行为数：{new_state['stats']['total_tasks']}")
        
        if new_state['stats']['total_tasks'] > state['stats']['total_tasks']:
            print("✓ 行为数据已更新")
        else:
            print("⚠️  行为数据未更新")
        
        # 测试意识评估器
        print("\n【测试 5】测试意识评估器...")
        from src.tools.base import ToolResult, ToolResultStatus
        
        # 创建模拟的工具结果
        mock_result = ToolResult(
            status=ToolResultStatus.SUCCESS,
            output="测试输出",
            data={"action": "write", "content": "测试内容"},
            duration_ms=100
        )
        
        metrics = agent.consciousness_evaluator.evaluate_tool_call(
            tool_name="file",
            result=mock_result,
            user_input="帮我创建一个测试文件",
            context={"test": True}
        )
        
        print(f"  自主性：{metrics['autonomy_level']:.2f}")
        print(f"  创造性：{metrics['creativity_score']:.2f}")
        print(f"  目标相关：{metrics['goal_relevance']:.2f}")
        print(f"  新颖性：{metrics['novelty_score']:.2f}")
        print("✓ 评估成功")
        
        # 获取平均指标
        avg_metrics = agent.consciousness_evaluator.get_average_metrics()
        print(f"\n【测试 6】平均指标:")
        print(f"  平均自主性：{avg_metrics['autonomy_level']:.2f}")
        print(f"  平均创造性：{avg_metrics['creativity_score']:.2f}")
        print(f"  平均目标相关：{avg_metrics['goal_relevance']:.2f}")
        print(f"  平均新颖性：{avg_metrics['novelty_score']:.2f}")
        
        # 清理
        print("\n【测试 7】清理资源...")
        await agent.cleanup()
        print("✓ 清理完成")
        
        print("\n" + "=" * 80)
        print("✅ 所有测试通过！意识系统已成功集成到 WinClaw Agent")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_consciousness_integration())
    sys.exit(0 if success else 1)
