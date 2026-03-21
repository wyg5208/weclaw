"""快速测试微信工具"""

import sys
sys.path.insert(0, '.')

import asyncio
from src.tools.wechat import WeChatTool
from src.tools.base import ToolResultStatus


async def main():
    print("=" * 60)
    print("微信工具功能测试")
    print("=" * 60)
    
    tool = WeChatTool()
    
    # 测试 1: 获取聊天列表
    print("\n[测试 1] 获取聊天列表")
    result = await tool.execute("get_chat_list", {"limit": 5})
    print(f"状态：{result.status}")
    print(f"输出：{result.output}")
    print(f"数据：{result.data.get('chat_list', [])}")
    
    # 测试 2: 切换聊天（空参数返回聊天列表）
    print("\n[测试 2] 切换聊天（获取列表）")
    result = await tool.execute("switch_chat", {})
    print(f"状态：{result.status}")
    print(f"输出：{result.output}")
    print(f"数据：{result.data.get('chat_list', [])}")
    
    # 测试 3: 查看消息
    print("\n[测试 3] 查看当前聊天消息")
    result = await tool.execute("view_messages", {"limit": 5})
    print(f"状态：{result.status}")
    print(f"输出：{result.output}")
    print(f"数据：{result.data.get('messages', [])}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
