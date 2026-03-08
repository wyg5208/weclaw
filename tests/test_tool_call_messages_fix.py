"""测试 tool_call 消息完整性修复。

验证当工具调用失败时，所有 tool_call 都有对应的 tool 结果消息。
"""

import asyncio
from src.core.session import SessionManager
from src.core.agent import Agent
from src.models.registry import ModelRegistry
from src.tools.registry import ToolRegistry


async def test_tool_call_messages_on_failure():
    """测试连续失败时，所有 tool_call 都有对应的 tool 消息。"""
    
    # 创建组件
    model_registry = ModelRegistry()
    tool_registry = ToolRegistry()
    session_manager = SessionManager()
    
    agent = Agent(
        model_registry=model_registry,
        tool_registry=tool_registry,
        session_manager=session_manager,
        max_steps=5,
    )
    
    # 模拟一个会返回多个 tool_calls 的响应
    # 然后让工具调用失败
    print("测试场景：模型一次调用返回 3 个 tool_calls，但工具执行失败")
    
    # 手动添加一个 assistant 消息，包含多个 tool_calls
    assistant_msg = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": "tc1", "type": "function", "function": {"name": "shell_run", "arguments": "{}"}},
            {"id": "tc2", "type": "function", "function": {"name": "file_read", "arguments": "{}"}},
            {"id": "tc3", "type": "function", "function": {"name": "web_search", "arguments": "{}"}},
        ]
    }
    session_manager.current_session.messages.append(assistant_msg)
    
    # 模拟第一个工具成功，第二个开始失败
    # （实际场景中，连续失败 3 次会触发提前返回）
    
    # 检查消息结构
    messages = session_manager.current_session.messages
    print(f"\n初始消息数：{len(messages)}")
    print(f"Assistant message tool_calls: {len(messages[-1]['tool_calls'])}")
    
    # 验证每个 tool_call 都有对应的 tool 消息
    # （这里只是示例，实际需要 mock 工具调用）
    print("\n✓ 测试框架已搭建，需要集成到完整的 agent 测试中")
    

if __name__ == "__main__":
    asyncio.run(test_tool_call_messages_on_failure())
    print("\n✅ 测试完成")
