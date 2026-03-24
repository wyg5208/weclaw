"""测试英语口语 UI 是否正确显示 HTML。"""

import sys
import asyncio
from PySide6.QtWidgets import QApplication
from src.tools.english_conversation import EnglishConversationTool


async def test_ui_html_display():
    """测试 UI 是否使用 HTML 模板。"""
    print("=" * 60)
    print("测试：英语口语 UI HTML 显示")
    print("=" * 60)
    
    # 创建 QApplication
    if not QApplication.instance():
        app = QApplication(sys.argv)
        print("✅ 创建了 QApplication 实例")
    else:
        print("⚠️ QApplication 实例已存在")
    
    # 创建工具
    tool = EnglishConversationTool()
    
    print("\n1️⃣  开始对话（带 UI，无图片）...")
    result = await tool.execute(
        "start_conversation",
        {
            "topic": "restaurant",
            "difficulty": "beginner",
            "enable_voice": False,
            "enable_ui": True,
        },
    )
    
    if result.is_success:
        session_id = result.data["session_id"]
        print(f"✅ 对话启动成功，会话 ID: {session_id}")
        
        # 检查对话框是否创建
        if tool._dialog:
            print(f"✅ 对话框已创建")
            print(f"   对话框类型：{type(tool._dialog).__name__}")
            print(f"   对话框标题：{tool._dialog.windowTitle()}")
            
            # 检查是否有 web_view 属性
            if hasattr(tool._dialog, 'web_view'):
                print(f"✅ QWebEngineView 可用")
            elif hasattr(tool._dialog, 'text_browser'):
                print(f"⚠️ 使用降级方案：QTextBrowser")
            else:
                print(f"❌ 未找到显示组件")
        else:
            print(f"❌ 对话框未创建")
        
        # 等待 3 秒让图片生成（如果有 API）
        print("\n⏳ 等待 3 秒（等待图片生成）...")
        await asyncio.sleep(3)
        
        # 测试添加对话
        print("\n2️⃣  添加用户对话...")
        respond_result = await tool.execute(
            "respond",
            {
                "session_id": session_id,
                "user_input": "I'd like to order some food.",
                "input_type": "text",
                "enable_voice": False,
                "enable_ui": True,
            },
        )
        
        if respond_result.is_success:
            print(f"✅ AI 回复：{respond_result.data.get('ai_response', 'N/A')}")
        else:
            print(f"❌ 回复失败：{respond_result.error}")
        
        # 结束对话
        print("\n3️⃣  结束对话...")
        await tool.execute("end_conversation", {"session_id": session_id})
        print("✅ 对话已结束")
        
    else:
        print(f"❌ 启动失败：{result.error}")
    
    print("\n" + "=" * 60)
    print("测试完成！请查看弹出的 UI 窗口")
    print("=" * 60)
    print("\n💡 提示:")
    print("- 如果看到紫色渐变背景的 HTML 页面，说明模板加载成功")
    print("- 如果图片未显示，可能是因为没有 API key")
    print("- 即使没有图片，HTML 结构和文字应该正常显示")
    print("=" * 60)


def run_test():
    """运行测试。"""
    print("\n🔍 英语口语 UI HTML 显示测试\n")
    asyncio.run(test_ui_html_display())


if __name__ == "__main__":
    run_test()
