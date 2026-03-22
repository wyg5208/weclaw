import pyautogui
import time

# 设置安全参数
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

print("窗口控制演示")
print("=" * 50)

# 1. 获取所有窗口信息
print("1. 当前所有包含'WeClaw'的窗口:")
windows = pyautogui.getWindowsWithTitle("WeClaw")
for i, win in enumerate(windows):
    print(f"  [{i}] {win.title}")
    print(f"     位置: ({win.left}, {win.top})")
    print(f"     大小: {win.width}x{win.height}")
    print(f"     是否最大化: {win.isMaximized}")
    print(f"     是否最小化: {win.isMinimized}")
    print(f"     是否激活: {win.isActive}")

if not windows:
    print("未找到WinClaw窗口")
    exit()

winclaw = windows[0]

# 2. 演示窗口状态切换
print("\n2. 窗口状态切换演示:")

if winclaw.isMaximized:
    print("当前窗口已最大化，先恢复窗口大小")
    winclaw.restore()
    time.sleep(1)
    print(f"恢复后位置: ({winclaw.left}, {winclaw.top})")
    print(f"恢复后大小: {winclaw.width}x{winclaw.height}")
    
    # 等待2秒
    time.sleep(2)
    
    # 现在演示如何最大化
    print("\n现在演示最大化窗口...")
    
    # 方法1: 使用窗口对象的maximize方法
    print("方法1: 使用maximize()方法")
    winclaw.maximize()
    time.sleep(1)
    print(f"最大化后位置: ({winclaw.left}, {winclaw.top})")
    print(f"最大化后大小: {winclaw.width}x{winclaw.height}")
    
    # 等待2秒
    time.sleep(2)
    
    # 方法2: 使用鼠标点击最大化按钮
    print("\n方法2: 使用鼠标点击最大化按钮")
    
    # 先恢复窗口
    winclaw.restore()
    time.sleep(1)
    
    # 计算最大化按钮位置
    window_right = winclaw.left + winclaw.width
    window_top = winclaw.top
    
    # 最大化按钮位置（从右往左第二个按钮）
    maximize_x = window_right - 46 * 2 - 5  # 减去两个按钮宽度和间距
    maximize_y = window_top + 15  # 标题栏中间
    
    print(f"最大化按钮位置: ({maximize_x}, {maximize_y})")
    
    # 移动鼠标并点击
    pyautogui.moveTo(maximize_x, maximize_y, duration=0.5)
    time.sleep(0.2)
    pyautogui.click()
    time.sleep(1)
    
    print(f"点击后位置: ({winclaw.left}, {winclaw.top})")
    print(f"点击后大小: {winclaw.width}x{winclaw.height}")
    
    # 方法3: 使用键盘快捷键
    print("\n方法3: 使用键盘快捷键")
    
    # 先恢复窗口
    winclaw.restore()
    time.sleep(1)
    
    # 激活窗口
    winclaw.activate()
    time.sleep(0.3)
    
    # Windows最大化快捷键：Win + 上箭头
    pyautogui.hotkey('win', 'up')
    time.sleep(1)
    
    print(f"快捷键后位置: ({winclaw.left}, {winclaw.top})")
    print(f"快捷键后大小: {winclaw.width}x{winclaw.height}")
    
    # 方法4: 双击标题栏
    print("\n方法4: 双击标题栏")
    
    # 先恢复窗口
    winclaw.restore()
    time.sleep(1)
    
    # 计算标题栏中间位置
    title_bar_x = winclaw.left + winclaw.width // 2
    title_bar_y = winclaw.top + 15
    
    # 双击标题栏
    pyautogui.moveTo(title_bar_x, title_bar_y, duration=0.5)
    pyautogui.doubleClick()
    time.sleep(1)
    
    print(f"双击后位置: ({winclaw.left}, {winclaw.top})")
    print(f"双击后大小: {winclaw.width}x{winclaw.height}")

else:
    print("当前窗口未最大化，直接演示最大化方法")
    
    # 演示所有最大化方法
    methods = [
        ("maximize()方法", lambda: winclaw.maximize()),
        ("鼠标点击最大化按钮", lambda: None),  # 这个需要单独处理
        ("键盘快捷键", lambda: pyautogui.hotkey('win', 'up')),
        ("双击标题栏", lambda: None)  # 这个需要单独处理
    ]
    
    for method_name, method_func in methods:
        print(f"\n尝试方法: {method_name}")
        
        # 先确保窗口不是最大化状态
        if winclaw.isMaximized:
            winclaw.restore()
            time.sleep(0.5)
        
        # 激活窗口
        winclaw.activate()
        time.sleep(0.3)
        
        if method_name == "maximize()方法":
            method_func()
        elif method_name == "鼠标点击最大化按钮":
            # 计算按钮位置并点击
            window_right = winclaw.left + winclaw.width
            window_top = winclaw.top
            maximize_x = window_right - 46 * 2 - 5
            maximize_y = window_top + 15
            
            pyautogui.moveTo(maximize_x, maximize_y, duration=0.3)
            pyautogui.click()
        elif method_name == "键盘快捷键":
            method_func()
        elif method_name == "双击标题栏":
            title_bar_x = winclaw.left + winclaw.width // 2
            title_bar_y = winclaw.top + 15
            pyautogui.moveTo(title_bar_x, title_bar_y, duration=0.3)
            pyautogui.doubleClick()
        
        time.sleep(1)
        print(f"  位置: ({winclaw.left}, {winclaw.top})")
        print(f"  大小: {winclaw.width}x{winclaw.height}")
        print(f"  是否最大化: {winclaw.isMaximized}")

print("\n" + "=" * 50)
print("演示完成！")
print("最终窗口状态:")
print(f"  位置: ({winclaw.left}, {winclaw.top})")
print(f"  大小: {winclaw.width}x{winclaw.height}")
print(f"  是否最大化: {winclaw.isMaximized}")
print(f"  是否最小化: {winclaw.isMinimized}")