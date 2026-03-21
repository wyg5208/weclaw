"""测试微信窗口查找逻辑，确保不会选择错误的窗口。

此脚本用于验证 find_wechat_window 方法能够正确识别微信窗口，
而不会错误地选择 weclaw 或其他应用的窗口。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.wechat_core import WeChatBot


def test_window_finding():
    """测试窗口查找功能"""
    print("=" * 60)
    print("微信窗口查找测试")
    print("=" * 60)
    
    # 创建微信机器人实例
    bot = WeChatBot()
    
    # 测试 1: 查找微信窗口
    print("\n[测试 1] 查找微信窗口")
    hwnd = bot.find_wechat_window()
    
    if hwnd:
        import win32gui
        
        window_title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        
        print(f"✓ 找到窗口:")
        print(f"  - 句柄：{hwnd}")
        print(f"  - 标题：{window_title}")
        print(f"  - 类名：{class_name}")
        
        # 验证窗口类名
        if any(kw in class_name for kw in ["WeChat", "Weixin", "微信"]):
            print(f"  ✓ 窗口类名验证通过 (标准版)")
        elif "Qt" in class_name:
            print(f"  ✓ 窗口类名验证通过 (Qt 版微信)")
        else:
            print(f"  ✗ 窗口类名不匹配，可能选择了错误的窗口!")
            
        # 验证窗口标题不包含排除关键词
        title_lower = window_title.lower()
        if any(exclude in title_lower for exclude in ["weclaw", "winclaw", "助手"]):
            print(f"  ✗ 窗口标题包含排除关键词，可能选择了错误的窗口!")
        else:
            print(f"  ✓ 窗口标题验证通过")
    else:
        print("✗ 未找到微信窗口（微信可能未运行）")
    
    # 测试 2: 列出所有可见窗口（用于调试）
    print("\n[测试 2] 当前所有可见窗口:")
    try:
        import win32gui
        
        def enum_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:  # 只显示有标题的窗口
                    class_name = win32gui.GetClassName(hwnd)
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "class": class_name
                    })
            return True
        
        all_windows = []
        win32gui.EnumWindows(enum_callback, all_windows)
        
        print(f"共找到 {len(all_windows)} 个窗口:\n")
        
        # 显示前 20 个窗口
        for i, win in enumerate(all_windows[:20], 1):
            is_wechat = any(kw in win["title"] for kw in ["微信", "WeChat", "Weixin"])
            is_excluded = any(ex in win["title"].lower() for ex in ["weclaw", "winclaw", "助手"])
            
            marker = ""
            if is_wechat and not is_excluded:
                marker = " [微信✓]"
            elif is_excluded:
                marker = " [排除✗]"
            
            print(f"  {i}. [{win['hwnd']}] {win['title']}")
            print(f"     类名：{win['class']}{marker}")
        
        if len(all_windows) > 20:
            print(f"  ...(仅显示前 20 个，共 {len(all_windows)} 个)")
            
    except Exception as e:
        print(f"枚举窗口失败：{e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    test_window_finding()
