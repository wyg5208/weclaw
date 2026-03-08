"""测试后台循环是否正常启动"""

import asyncio
from pathlib import Path
import sys

project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.models.registry import ModelRegistry
from src.tools.registry import create_default_registry
from src.core.agent import Agent, CONSCIOUSNESS_ENABLED

print("=" * 60)
print("测试：意识系统后台循环")
print("=" * 60)

print(f"\n✓ 意识系统启用状态：{CONSCIOUSNESS_ENABLED}")

# 创建 Agent
print("\n创建 Agent（带主动思考功能）...")
agent = Agent(
    model_registry=ModelRegistry(),
    tool_registry=create_default_registry(),
    model_key="deepseek-chat",
    max_steps=3
)
print("✓ Agent 创建成功")

# 检查意识系统
if hasattr(agent, 'consciousness') and agent.consciousness:
    print("✓ 意识系统已初始化")
    
    # 检查后台循环
    if hasattr(agent.consciousness, 'background_loop'):
        print("✓ 后台循环对象已创建")
        
        # 懒启动意识系统
        print("\n启动意识系统...")
        agent._ensure_consciousness_started()
        
        # 等待 2 秒让后台线程启动
        import time
        time.sleep(2)
        
        # 检查后台循环状态
        if agent.consciousness.background_loop:
            stats = agent.consciousness.background_loop.get_stats()
            print(f"\n📊 后台循环统计:")
            print(f"  运行中：{stats['is_running']}")
            print(f"  运行时长：{stats['uptime_hours']} 小时")
            print(f"  健康检查次数：{stats['health_checks']}")
            print(f"  主动思考周期：{stats['thinking_cycles']}")
            print(f"  记忆巩固周期：{stats['consolidation_cycles']}")
            
            if stats['is_running']:
                print("\n✅ 后台循环已成功启动！意识系统现在具有自主思考能力！")
            else:
                print("\n⚠️ 后台循环未运行")
        else:
            print("⚠️ 后台循环对象不存在")
    else:
        print("⚠️ 意识系统缺少 background_loop 属性")
else:
    print("✗ 意识系统未初始化")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
