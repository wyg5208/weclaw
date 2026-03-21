"""测试 WeChatTool 的 ToolResult 修复"""

import asyncio
from pathlib import Path
from src.tools.wechat import WeChatTool
from src.tools.base import ToolResultStatus


async def test_wechat_tool_result():
    """测试微信工具返回正确的 ToolResult 格式"""
    
    # 创建工具实例（使用默认配置路径）
    tool = WeChatTool()
    
    print("=" * 60)
    print("测试 WeChatTool 的 ToolResult 修复")
    print("=" * 60)
    
    # 测试 1: switch_chat - 空参数（应返回聊天列表）
    print("\n[测试 1] switch_chat (空参数)")
    try:
        result = await tool.execute("switch_chat", {})
        assert result.status == ToolResultStatus.SUCCESS, f"期望成功，但得到：{result.status}"
        # 注意：如果没有运行微信，会返回空列表，这也是正常的
        print(f"✓ 通过：output='{result.output}', data keys={list(result.data.keys()) if result.data else 'empty'}")
    except Exception as e:
        print(f"✗ 失败：{e}")
        return False
    
    # 测试 2: send_message - 发送消息
    print("\n[测试 2] send_message")
    try:
        result = await tool.execute("send_message", {"message": "你好"})
        # 注意：由于微信可能未运行，这里只验证返回格式正确
        if result.status == ToolResultStatus.SUCCESS:
            assert "sent" in result.data or "message" in result.data
            print(f"✓ 通过：output='{result.output}', data={result.data}")
        else:
            # 失败也是正常的（微信可能未运行）
            print(f"⚠ 预期可能的失败：error='{result.error}'")
    except Exception as e:
        print(f"✗ 失败：{e}")
        return False
    
    # 测试 3: get_chat_list
    print("\n[测试 3] get_chat_list")
    try:
        result = await tool.execute("get_chat_list", {"limit": 10})
        assert result.status == ToolResultStatus.SUCCESS
        assert "chat_list" in result.data
        print(f"✓ 通过：output='{result.output}', count={result.data.get('count', 0)}")
    except Exception as e:
        print(f"✗ 失败：{e}")
        return False
    
    # 测试 4: enable_auto_reply - 启用
    print("\n[测试 4] enable_auto_reply (启用)")
    try:
        result = await tool.execute("enable_auto_reply", {"enabled": True})
        assert result.status == ToolResultStatus.SUCCESS
        assert result.data.get("enabled") is True
        print(f"✓ 通过：output='{result.output}', enabled={result.data.get('enabled')}")
    except Exception as e:
        print(f"✗ 失败：{e}")
        return False
    
    # 测试 5: enable_auto_reply - 禁用
    print("\n[测试 5] enable_auto_reply (禁用)")
    try:
        result = await tool.execute("enable_auto_reply", {"enabled": False})
        assert result.status == ToolResultStatus.SUCCESS
        assert result.data.get("enabled") is False
        print(f"✓ 通过：output='{result.output}', enabled={result.data.get('enabled')}")
    except Exception as e:
        print(f"✗ 失败：{e}")
        return False
    
    # 测试 6: customer_service - 启用
    print("\n[测试 6] customer_service (启用)")
    try:
        result = await tool.execute("customer_service", {"enabled": True})
        assert result.status == ToolResultStatus.SUCCESS
        assert result.data.get("enabled") is True
        print(f"✓ 通过：output='{result.output}', enabled={result.data.get('enabled')}")
    except Exception as e:
        print(f"✗ 失败：{e}")
        return False
    
    # 测试 7: customer_service - 禁用
    print("\n[测试 7] customer_service (禁用)")
    try:
        result = await tool.execute("customer_service", {"enabled": False})
        assert result.status == ToolResultStatus.SUCCESS
        assert result.data.get("enabled") is False
        print(f"✓ 通过：output='{result.output}', enabled={result.data.get('enabled')}")
    except Exception as e:
        print(f"✗ 失败：{e}")
        return False
    
    print("\n" + "=" * 60)
    print("所有测试通过！✅")
    print("=" * 60)
    print("\n关键验证点：")
    print("1. ✓ ToolResult 使用 output 和 data 参数（而非 result）")
    print("2. ✓ 所有动作都返回正确的 ToolResult 格式")
    print("3. ✓ output 字段提供人类可读的状态描述")
    print("4. ✓ data 字段包含结构化的返回数据")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_wechat_tool_result())
    exit(0 if success else 1)
