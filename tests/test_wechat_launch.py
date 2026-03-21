"""测试微信启动和窗口检测"""

import sys
sys.path.insert(0, '.')

from src.tools.wechat_core import WeChatBot
import time


def main():
    print("=" * 60)
    print("微信启动与窗口检测测试")
    print("=" * 60)
    
    bot = WeChatBot()
    
    # 测试 1: 查找窗口
    print("\n[测试 1] 查找微信窗口")
    hwnd = bot.find_wechat_window()
    if hwnd:
        print(f"✓ 找到微信窗口，句柄：{hwnd}")
    else:
        print("✗ 未找到微信窗口")
    
    # 测试 2: 启动微信
    print("\n[测试 2] 启动微信")
    if not hwnd:
        print("正在启动 weixin.exe...")
        success = bot.launch_wechat()
        if success:
            print("✓ 启动命令已发送")
            
            # 等待并检测
            print("\n等待微信启动（最多 10 秒）...")
            for i in range(10):
                time.sleep(1.0)
                hwnd = bot.find_wechat_window()
                if hwnd:
                    print(f"✓ 微信启动成功！耗时 {i+1} 秒")
                    print(f"  窗口句柄：{hwnd}")
                    
                    # 激活窗口
                    bot.activate_window()
                    print("✓ 窗口已激活")
                    break
                else:
                    print(f"  第 {i+1} 次检测：未找到窗口...")
            
            if not hwnd:
                print("✗ 超时未检测到窗口，请手动检查")
        else:
            print("✗ 启动失败")
    else:
        print("⚠ 微信已在运行，跳过启动测试")
    
    # 测试 3: 获取聊天列表
    print("\n[测试 3] 获取聊天列表")
    if hwnd:
        chat_list = bot.get_chat_list(limit=5)
        if chat_list:
            print(f"✓ 获取到 {len(chat_list)} 个聊天对象:")
            for chat in chat_list[:3]:
                print(f"  - {chat['name']}: {chat['last_message']} ({chat['timestamp']})")
        else:
            print("✗ 未获取到聊天对象")
    else:
        print("⚠ 跳过（微信未运行）")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
