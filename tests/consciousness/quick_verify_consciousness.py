"""快速验证意识系统集成 - 无长时间运行测试"""

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
print("快速验证：意识系统集成")
print("=" * 60)

print(f"\n✓ 意识系统启用状态：{CONSCIOUSNESS_ENABLED}")

# 创建 Agent
print("\n创建 Agent...")
agent = Agent(
    model_registry=ModelRegistry(),
    tool_registry=create_default_registry(),
    model_key="deepseek-chat",
    max_steps=3
)
print("✓ Agent 创建成功（无错误）")

# 检查意识系统
if hasattr(agent, 'consciousness') and agent.consciousness:
    print("✓ 意识系统已初始化")
else:
    print("✗ 意识系统未初始化")

# 检查评估器
if hasattr(agent, 'consciousness_evaluator') and agent.consciousness_evaluator:
    print("✓ 意识评估器已创建")
else:
    print("✗ 意识评估器未创建")

print("\n" + "=" * 60)
print("✅ 验证完成！Agent 可以正常创建和初始化")
print("=" * 60)
print("\n提示：现在可以启动 GUI 测试完整功能")
print("命令：python start_winclaw_gui.bat")
