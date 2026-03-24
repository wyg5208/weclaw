"""英语口语对话练习工具 - UI 功能测试。

测试可视化 UI 对话框功能，包括：
1. 场景图片显示
2. 角色形象显示
3. 词汇卡片展示
4. 对话内容实时更新
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.english_conversation import EnglishConversationTool


async def test_ui_with_images():
    """测试带 UI 的对话（生成真实图片）。"""
    print("\n" + "=" * 70)
    print("测试：英语口语对话 UI 展示（带图片生成）")
    print("=" * 70)
    
    tool = EnglishConversationTool()
    
    # 1. 开始对话（启用 UI）
    print("\n[1] 开始餐厅点餐对话...")
    result = await tool.execute("start_conversation", {
        "topic": "restaurant",
        "difficulty": "beginner",
        "enable_voice": False,
        "enable_ui": True,  # 启用 UI
    })
    
    if not result.is_success:
        print(f"启动失败：{result.error}")
        return
    
    session_id = result.data["session_id"]
    print(f"会话 ID: {session_id}")
    print(result.output)
    print("\n💡 UI 窗口已打开，正在加载场景图片...")
    
    # 等待图片生成（可能需要 10-20 秒）
    await asyncio.sleep(15)
    
    # 2. 进行对话
    conversation_flow = [
        ("Yes, I'd like to order some food.", "是的，我想点些食物。"),
        ("Can I have a beef steak, please?", "请给我一份牛排。"),
        ("Medium, please.", "五分熟，谢谢。"),
        ("What drinks do you recommend?", "你推荐什么饮料？"),
        ("Thank you! This is great.", "谢谢！太棒了。"),
    ]
    
    for i, (user_input, cn_translation) in enumerate(conversation_flow, 1):
        print(f"\n[对话 {i}/{len(conversation_flow)}]")
        print(f"👤 用户：{user_input}")
        
        result = await tool.execute("respond", {
            "session_id": session_id,
            "user_input": user_input,
            "input_type": "text",
            "enable_voice": False,
            "enable_ui": True,  # 更新 UI
        })
        
        if result.is_success:
            ai_response = result.data.get("ai_response", "N/A")
            print(f"🤖 AI: {ai_response}")
        else:
            print(f"❌ 回复失败：{result.error}")
        
        # 每轮对话间隔，让用户有时间查看 UI
        await asyncio.sleep(3)
    
    # 3. 结束对话
    print("\n[结束对话]")
    result = await tool.execute("end_conversation", {
        "session_id": session_id
    })
    
    if result.is_success:
        print(result.output)
    else:
        print(f"结束失败：{result.error}")
    
    # 保持 UI 窗口显示一段时间
    print("\n💡 对话结束，UI 窗口将在 5 秒后关闭...")
    await asyncio.sleep(5)


async def test_ui_without_images():
    """测试不带图片的 UI（快速模式）。"""
    print("\n" + "=" * 70)
    print("测试：英语口语对话 UI 展示（无图片快速模式）")
    print("=" * 70)
    
    tool = EnglishConversationTool()
    
    # 开始对话（不启用 UI，或 UI 但不生成图片）
    result = await tool.execute("start_conversation", {
        "topic": "hotel",
        "difficulty": "intermediate",
        "enable_voice": False,
        "enable_ui": True,
    })
    
    session_id = result.data["session_id"]
    print(f"会话 ID: {session_id}")
    print(result.output)
    
    # 简单对话
    dialogues = [
        "I have a reservation under the name Smith.",
        "What time is breakfast served?",
        "Could I have a late checkout?"
    ]
    
    for user_input in dialogues:
        print(f"\n👤 用户：{user_input}")
        
        result = await tool.execute("respond", {
            "session_id": session_id,
            "user_input": user_input,
            "input_type": "text",
            "enable_voice": False,
            "enable_ui": True,
        })
        
        if result.is_success:
            print(f"🤖 AI: {result.data.get('ai_response', 'N/A')}")
        
        await asyncio.sleep(2)
    
    # 结束
    await tool.execute("end_conversation", {"session_id": session_id})
    print("\n对话结束")


async def main():
    """主测试函数。"""
    print("\n" + "=" * 70)
    print("  英语口语对话练习工具 - UI 功能测试")
    print("=" * 70)
    
    print("\n请选择测试模式:")
    print("1. 完整模式（带图片生成，需要 API Key 和较长时间）")
    print("2. 快速模式（仅 UI 框架，无图片）")
    print("3. 跳过测试")
    
    choice = input("\n请输入选项 (1/2/3): ").strip()
    
    if choice == "1":
        await test_ui_with_images()
    elif choice == "2":
        await test_ui_without_images()
    elif choice == "3":
        print("已跳过测试")
    else:
        print("无效选项")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n测试出错：{e}")
        import traceback
        traceback.print_exc()
