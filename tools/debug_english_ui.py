"""调试英语口语 UI 显示问题。"""

import sys
import logging
import asyncio
from PySide6.QtWidgets import QApplication
from src.tools.english_conversation import EnglishConversationTool

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def debug_ui_display():
    """调试 UI 显示。"""
    print("=" * 60)
    print("调试：英语口语 UI 显示问题")
    print("=" * 60)
    
    # 创建 QApplication
    if not QApplication.instance():
        app = QApplication(sys.argv)
        print("✅ 创建了 QApplication 实例")
    else:
        print("⚠️ QApplication 实例已存在")
    
    # 创建工具
    tool = EnglishConversationTool()
    
    print("\n1️⃣  开始对话（带 UI）...")
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
        
        # 检查对话框状态
        if tool._dialog:
            print(f"\n📊 对话框状态:")
            print(f"   - 类型：{type(tool._dialog).__name__}")
            print(f"   - 标题：{tool._dialog.windowTitle()}")
            print(f"   - 可见：{tool._dialog.isVisible()}")
            print(f"   - 尺寸：{tool._dialog.size().width()}x{tool._dialog.size().height()}")
            
            # 检查组件
            if hasattr(tool._dialog, 'web_view'):
                print(f"   - QWebEngineView: ✅")
                print(f"   - web_view 可见：{tool._dialog.web_view.isVisible()}")
            elif hasattr(tool._dialog, 'text_browser'):
                print(f"   - QTextBrowser: ⚠️ (降级方案)")
                print(f"   - text_browser 可见：{tool._dialog.text_browser.isVisible()}")
            else:
                print(f"   - ❌ 未找到显示组件")
        else:
            print(f"❌ 对话框未创建")
            return
        
        # 等待图片生成
        print("\n⏳ 等待 5 秒（等待图片生成和 UI 更新）...")
        await asyncio.sleep(5)
        
        # 再次检查
        if tool._dialog:
            print(f"\n📊 5 秒后的状态:")
            print(f"   - 对话框可见：{tool._dialog.isVisible()}")
            print(f"   - 对话框激活：{tool._dialog.isActiveWindow()}")
            
            # 尝试手动更新一次
            print("\n2️⃣  手动触发一次 UI 更新...")
            from src.tools.english_conversation import TOPIC_LIBRARY
            
            topic_config = TOPIC_LIBRARY.get("restaurant")
            if topic_config:
                tool._update_ui_scene(
                    topic_config=topic_config,
                    ai_role="Waiter",
                    scene_path=None,
                    char_path=None
                )
                print("✅ 手动更新 UI 场景完成")
        
        # 测试添加对话
        print("\n3️⃣  添加对话...")
        respond_result = await tool.execute(
            "respond",
            {
                "session_id": session_id,
                "user_input": "Hello!",
                "input_type": "text",
                "enable_voice": False,
                "enable_ui": True,
            },
        )
        
        if respond_result.is_success:
            print(f"✅ AI 回复：{respond_result.data.get('ai_response', 'N/A')}")
        else:
            print(f"❌ 回复失败：{respond_result.error}")
        
        # 结束
        print("\n4️⃣  结束对话...")
        await tool.execute("end_conversation", {"session_id": session_id})
        print("✅ 对话已结束")
        
    else:
        print(f"❌ 启动失败：{result.error}")
    
    print("\n" + "=" * 60)
    print("调试完成!")
    print("=" * 60)
    print("\n💡 请查看:")
    print("1. 窗口是否弹出？")
    print("2. 窗口是否有内容？")
    print("3. 控制台有什么日志？")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(debug_ui_display())
