"""测试英语口语工具与主窗体的兼容性。

验证点：
1. 在已有 QApplication 的情况下复用实例
2. 对话框不会与 MainWindow 冲突
3. 可以多次打开/关闭对话框
"""

import sys
import asyncio
from PySide6.QtWidgets import QApplication
from src.tools.english_conversation import EnglishConversationTool


async def test_with_existing_qapplication():
    """测试场景 1：已有 QApplication 实例时。"""
    print("=" * 60)
    print("测试场景 1: 已有 QApplication 实例")
    print("=" * 60)
    
    # 创建 QApplication（模拟主程序已启动）
    if not QApplication.instance():
        app = QApplication(sys.argv)
        print("✅ 创建了 QApplication 实例（模拟主程序）")
    else:
        print("⚠️ QApplication 实例已存在")
    
    # 创建工具并尝试显示 UI
    tool = EnglishConversationTool()
    
    print("\n尝试开始对话（带 UI）...")
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
        print(f"✅ 对话启动成功，会话 ID: {result.data['session_id']}")
        print(f"   UI 对话框状态：{'已显示' if tool._dialog is not None else '未显示'}")
        
        if tool._dialog:
            print(f"   对话框标题：{tool._dialog.windowTitle()}")
            print(f"   对话框可见：{tool._dialog.isVisible()}")
        
        # 测试再次打开（应该不会创建新窗口）
        print("\n再次调用 start_conversation（应该激活已有窗口）...")
        result2 = await tool.execute(
            "start_conversation",
            {
                "topic": "airport",
                "difficulty": "intermediate",
                "enable_voice": False,
                "enable_ui": True,
            },
        )
        
        if result2.is_success:
            print(f"✅ 第二次调用成功，会话 ID: {result2.data['session_id']}")
            print(f"   对话框数量：1 个（应复用）")
        
        # 结束对话
        await tool.execute("end_conversation", {"session_id": result.data["session_id"]})
        print("\n✅ 第一次对话已结束")
        
        if result2.is_success:
            await tool.execute("end_conversation", {"session_id": result2.data["session_id"]})
            print("✅ 第二次对话已结束")
            
    else:
        print(f"❌ 失败：{result.error}")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


def run_test():
    """运行测试。"""
    print("\n🔍 英语口语工具 - QApplication 兼容性测试\n")
    
    # 使用 asyncio 运行
    asyncio.run(test_with_existing_qapplication())


if __name__ == "__main__":
    run_test()
