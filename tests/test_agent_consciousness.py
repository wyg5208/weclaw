"""测试Agent意识系统"""
from src.core.agent import Agent

# 创建 Agent
agent = Agent()

# 检查意识系统
print(f"Agent has consciousness: {hasattr(agent, 'consciousness')}")
if hasattr(agent, 'consciousness'):
    print(f"consciousness value: {agent.consciousness}")
    print(f"consciousness type: {type(agent.consciousness)}")
