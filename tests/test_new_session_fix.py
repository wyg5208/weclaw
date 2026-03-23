"""测试新建会话功能修复。

验证点击"新建会话"按钮后是否创建了新的会话实例。
"""

import pytest
from src.core.session import SessionManager
from src.core.agent import Agent
from src.core.model_registry import ModelRegistry
from src.core.tool_registry import ToolRegistry


def test_session_manager_create_session():
    """测试会话管理器创建新会话。"""
    mgr = SessionManager(system_prompt="你是一个助手")
    
    # 初始有一个默认会话
    assert len(mgr.list_sessions()) == 1
    initial_session_id = mgr.current_session_id
    
    # 创建新会话
    new_session = mgr.create_session(title="测试对话")
    
    # 验证新会话已创建
    assert new_session.id != initial_session_id
    assert new_session.title == "测试对话"
    assert len(mgr.list_sessions()) == 2
    assert mgr.current_session_id == new_session.id
    
    # 验证 system prompt 已添加
    assert new_session.has_system_prompt
    assert new_session.messages[0]["role"] == "system"


def test_session_manager_clear_vs_create():
    """测试清空消息与创建新会话的区别。"""
    mgr = SessionManager(system_prompt="你是助手")
    
    # 添加一些消息
    mgr.add_message(role="user", content="你好")
    mgr.add_message(role="assistant", content="你好！有什么可以帮助你的？")
    
    initial_session_id = mgr.current_session_id
    initial_msg_count = len(mgr.current_session.messages)
    
    # 场景 1: 只清空消息（旧实现）
    mgr.clear_messages()
    assert len(mgr.current_session.messages) < initial_msg_count
    assert mgr.current_session_id == initial_session_id  # 会话 ID 不变
    
    # 添加消息
    mgr.add_message(role="user", content="第一条消息")
    
    # 场景 2: 创建新会话（新实现）
    new_session = mgr.create_session(title="新对话")
    assert new_session.id != initial_session_id  # 会话 ID 改变
    assert len(new_session.messages) == 1  # 只有 system prompt
    assert mgr.current_session_id == new_session.id


async def test_agent_reset():
    """测试 Agent reset 方法。"""
    model_reg = ModelRegistry()
    tool_reg = ToolRegistry()
    
    agent = Agent(
        model_registry=model_reg,
        tool_registry=tool_reg,
        system_prompt="你是助手",
    )
    
    # 添加一些消息
    agent.session_manager.add_message(role="user", content="你好")
    agent.session_manager.add_message(role="assistant", content="你好！")
    
    initial_session_id = agent.session_manager.current_session_id
    initial_msg_count = len(agent.session_manager.current_session.messages)
    
    # 重置 Agent（只会清空消息，不会创建新会话）
    agent.reset()
    
    # 验证消息被清空
    assert len(agent.session_manager.current_session.messages) < initial_msg_count
    # 会话 ID 不变
    assert agent.session_manager.current_session_id == initial_session_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
