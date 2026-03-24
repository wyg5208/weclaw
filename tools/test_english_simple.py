"""快速测试英语口语工具（无 UI 版本）。"""

import asyncio
from src.tools.english_conversation import EnglishConversationTool


async def test_basic():
    """测试基本功能。"""
    print("=" * 60)
    print("英语口语对话工具 - 快速测试")
    print("=" * 60)
    
    tool = EnglishConversationTool()
    
    # 测试 1: 列出主题
    print("\n1️⃣  列出所有主题")
    result = await tool.execute("list_topics", {})
    if result.is_success:
        topics = result.data.get("topics", [])
        print(f"   ✅ 找到 {len(topics)} 个主题")
        for t in topics[:3]:
            print(f"      - {t['id']}: {t['title_zh']}")
    else:
        print(f"   ❌ 失败：{result.error}")
    
    # 测试 2: 开始对话（无 UI）
    print("\n2️⃣  开始一个餐厅点餐对话（无 UI）")
    result = await tool.execute(
        "start_conversation",
        {
            "topic": "restaurant",
            "difficulty": "beginner",
            "enable_voice": False,
            "enable_ui": False,  # 禁用 UI
        },
    )
    
    if result.is_success:
        session_id = result.data["session_id"]
        print(f"   ✅ 会话 ID: {session_id}")
        print(f"   📖 场景：{result.data.get('scenario_title', 'N/A')}")
        
        # 测试 3: 对话交互
        print("\n3️⃣  进行对话")
        user_input = "I'd like to order some food, please."
        print(f"   👤 用户：{user_input}")
        
        respond_result = await tool.execute(
            "respond",
            {
                "session_id": session_id,
                "user_input": user_input,
                "input_type": "text",
                "enable_voice": False,
                "enable_ui": False,  # 禁用 UI
            },
        )
        
        if respond_result.is_success:
            ai_response = respond_result.data.get("ai_response", "N/A")
            chinese_tip = respond_result.data.get("chinese_tip")
            print(f"   🤖 AI: {ai_response}")
            if chinese_tip:
                print(f"   💡 提示：{chinese_tip}")
        else:
            print(f"   ❌ 回复失败：{respond_result.error}")
        
        # 结束对话
        print("\n4️⃣  结束对话")
        end_result = await tool.execute(
            "end_conversation",
            {"session_id": session_id},
        )
        
        if end_result.is_success:
            print(f"   ✅ 对话已结束")
        else:
            print(f"   ❌ 结束失败：{end_result.error}")
            
    else:
        print(f"   ❌ 启动失败：{result.error}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_basic())
