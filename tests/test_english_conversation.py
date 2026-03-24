"""英语口语对话练习工具测试。

测试 EnglishConversationTool 的各项功能：
1. 列出主题
2. 开始对话
3. 对话交互
4. 结束对话
"""
import asyncio
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.english_conversation import EnglishConversationTool


async def test_list_topics(tool: EnglishConversationTool):
    """测试列出所有主题。"""
    print("\n" + "=" * 60)
    print("测试 1: 列出所有可用的对话主题")
    print("=" * 60)
    
    result = await tool.execute("list_topics", {})
    
    if result.is_success:
        print(f"\n✅ 成功列出 {len(result.data.get('topics', []))} 个主题")
        print("\n可用主题:")
        for topic in result.data.get("topics", []):
            print(f"  - {topic['id']}: {topic['title_zh']} ({topic['title_en']})")
    else:
        print(f"\n❌ 失败：{result.error}")
    
    return result.is_success


async def test_start_conversation(tool: EnglishConversationTool):
    """测试开始对话。"""
    print("\n" + "=" * 60)
    print("测试 2: 开始一个餐厅点餐对话")
    print("=" * 60)
    
    result = await tool.execute(
        "start_conversation",
        {
            "topic": "restaurant",
            "difficulty": "beginner",
            "enable_voice": False,  # 测试时不播放语音
        },
    )
    
    if result.is_success:
        print(f"\n✅ 对话启动成功")
        print(f"会话 ID: {result.data.get('session_id')}")
        print(f"主题：{result.data.get('title_zh')}")
        print(f"难度：{result.data.get('difficulty')}")
        print(f"\n输出:\n{result.output}")
    else:
        print(f"\n❌ 失败：{result.error}")
    
    return result.is_success, result.data.get("session_id") if result.is_success else None


async def test_respond(tool: EnglishConversationTool, session_id: str):
    """测试对话交互。"""
    print("\n" + "=" * 60)
    print("测试 3: 与 AI 进行对话交互")
    print("=" * 60)
    
    if not session_id:
        print("\n❌ 跳过测试：没有有效的会话 ID")
        return False
    
    # 模拟用户输入
    user_inputs = [
        "Yes, I'd like to order some food.",
        "Can I have a beef steak, please?",
        "Medium, please.",
        "Thank you!",
    ]
    
    for i, user_input in enumerate(user_inputs, 1):
        print(f"\n--- 第 {i} 轮对话 ---")
        print(f"用户：{user_input}")
        
        result = await tool.execute(
            "respond",
            {
                "session_id": session_id,
                "user_input": user_input,
                "input_type": "text",  # 测试时使用文字输入
                "enable_voice": False,
            },
        )
        
        if result.is_success:
            print(f"AI: {result.data.get('ai_response', 'N/A')}")
            if result.data.get("chinese_tip"):
                print(f"💡 提示：{result.data.get('chinese_tip')}")
        else:
            print(f"❌ 回复失败：{result.error}")
            return False
        
        await asyncio.sleep(0.5)  # 模拟思考时间
    
    return True


async def test_end_conversation(tool: EnglishConversationTool, session_id: str):
    """测试结束对话。"""
    print("\n" + "=" * 60)
    print("测试 4: 结束对话并获取总结")
    print("=" * 60)
    
    if not session_id:
        print("\n❌ 跳过测试：没有有效的会话 ID")
        return False
    
    tool = EnglishConversationTool()
    result = await tool.execute(
        "end_conversation",
        {
            "session_id": session_id,
            "save_recording": False,
        },
    )
    
    if result.is_success:
        print(f"\n✅ 对话已结束")
        print(f"总结:\n{result.output}")
    else:
        print(f"\n❌ 失败：{result.error}")
    
    return result.is_success


async def test_custom_scenario(tool: EnglishConversationTool):
    """测试自定义场景。"""
    print("\n" + "=" * 60)
    print("测试 5: 自定义场景对话")
    print("=" * 60)
    
    tool = EnglishConversationTool()
    result = await tool.execute(
        "start_conversation",
        {
            "topic": "custom",
            "custom_scenario": "You are at a coffee shop ordering a cup of coffee.",
            "difficulty": "beginner",
            "enable_voice": False,
        },
    )
    
    if result.is_success:
        print(f"\n✅ 自定义场景启动成功")
        print(f"会话 ID: {result.data.get('session_id')}")
        print(f"\n输出:\n{result.output}")
        
        # 测试一轮对话
        respond_result = await tool.execute(
            "respond",
            {
                "session_id": result.data["session_id"],
                "user_input": "I'd like a latte, please.",
                "input_type": "text",
                "enable_voice": False,
            },
        )
        
        if respond_result.is_success:
            print(f"\nAI 回复：{respond_result.data.get('ai_response', 'N/A')}")
        
        # 结束对话
        await tool.execute(
            "end_conversation",
            {"session_id": result.data["session_id"]},
        )
    else:
        print(f"\n❌ 失败：{result.error}")
    
    return result.is_success


async def main():
    """运行所有测试。"""
    print("\n" + "=" * 60)
    print("  英语口语对话练习工具 - 集成测试")
    print("=" * 60)
    
    # 创建共享工具实例
    tool = EnglishConversationTool()
    
    results = []
    
    # 测试 1: 列出主题
    results.append(await test_list_topics(tool))
    
    # 测试 2: 开始对话
    success, session_id = await test_start_conversation(tool)
    results.append(success)
    
    # 测试 3: 对话交互
    if session_id:
        results.append(await test_respond(tool, session_id))
    else:
        results.append(False)
    
    # 测试 4: 结束对话
    if session_id:
        results.append(await test_end_conversation(tool, session_id))
    else:
        results.append(False)
    
    # 测试 5: 自定义场景
    results.append(await test_custom_scenario(tool))
    
    # 总结
    print("\n" + "=" * 60)
    print(f"测试结果：{sum(results)}/{len(results)} 通过")
    print("=" * 60)
    
    if all(results):
        print("\n✅ 所有测试通过！")
        return 0
    else:
        print("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
