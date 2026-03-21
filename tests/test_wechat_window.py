"""测试微信窗口检测功能"""

import sys
sys.path.insert(0, '.')

from src.tools.wechat_core import WeChatBot


def main():
    print("=" * 60)
    print("微信窗口检测测试")
    print("=" * 60)
    
    bot = WeChatBot()
    
    # 测试 1: 查找微信窗口
    print("\n[测试 1] 查找微信窗口")
    hwnd = bot.find_wechat_window()
    if hwnd:
        print(f"✓ 找到微信窗口，句柄：{hwnd}")
    else:
        print("✗ 未找到微信窗口")
        print("\n提示：请先打开微信客户端并登录")
    
    # 测试 2: 激活窗口
    print("\n[测试 2] 激活微信窗口")
    if hwnd:
        success = bot.activate_window()
        if success:
            print("✓ 窗口激活成功")
        else:
            print("✗ 窗口激活失败")
    else:
        print("⚠ 跳过（未找到窗口）")
    
    # 测试 3: 获取聊天列表
    print("\n[测试 3] 获取聊天列表")
    chat_list = bot.get_chat_list(limit=5)
    if chat_list:
        print(f"✓ 获取到 {len(chat_list)} 个聊天对象:")
        for chat in chat_list[:3]:
            print(f"  - {chat['name']}: {chat['last_message']} ({chat['timestamp']})")
    else:
        print("✗ 未获取到聊天对象")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
