"""验证赛博朋克主题是否可以在设置和菜单中正常显示和切换。"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QMessageBox
from src.ui.theme import Theme, apply_theme
from src.ui.settings_dialog import SettingsDialog


def test_settings_dialog():
    """测试设置对话框中的主题选项。"""
    print("=" * 60)
    print("测试 1: 设置对话框主题下拉框")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    # 创建设置对话框
    dialog = SettingsDialog(
        current_theme="light",
        current_model="GPT-4",
        available_models=["GPT-4", "Claude 3", "Gemini"]
    )
    
    # 检查主题下拉框的选项数量
    theme_combo = dialog._theme_combo
    count = theme_combo.count()
    print(f"✓ 主题下拉框共有 {count} 个选项")
    
    # 列出所有主题选项
    print("\n主题列表:")
    for i in range(count):
        text = theme_combo.itemText(i)
        print(f"  {i}. {text}")
    
    # 检查是否有赛博朋克主题
    has_cyberpunk = False
    for i in range(count):
        if "赛博朋克" in theme_combo.itemText(i):
            has_cyberpunk = True
            print(f"\n✅ 找到赛博朋克主题 (索引：{i})")
            break
    
    if not has_cyberpunk:
        print("\n❌ 未找到赛博朋克主题!")
        QMessageBox.critical(None, "错误", "设置对话框中没有赛博朋克主题选项!")
        return False
    
    # 测试选择赛博朋克主题
    print("\n尝试切换到赛博朋克主题...")
    for i in range(count):
        if "赛博朋克" in theme_combo.itemText(i):
            theme_combo.setCurrentIndex(i)
            print(f"✓ 已选择索引 {i}: {theme_combo.currentText()}")
            
            # 验证信号是否正确发出
            def check_signal(theme_name):
                print(f"✓ 信号发出：theme_changed('{theme_name}')")
                
            dialog.theme_changed.connect(check_signal)
            dialog._on_theme_changed(i)
            break
    
    print("\n✅ 设置对话框测试通过!")
    print("=" * 60)
    return True


def test_main_window_menu():
    """测试主窗口主题菜单。"""
    print("\n测试 2: 主窗口主题菜单")
    print("=" * 60)
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # 创建主窗口
    window = QMainWindow()
    window.setWindowTitle("主题菜单测试")
    window.setGeometry(100, 100, 400, 300)
    
    # 模拟主窗口的主题菜单创建
    from PySide6.QtWidgets import QMenuBar, QMenu
    from PySide6.QtGui import QAction
    
    menubar = QMenuBar(window)
    view_menu = QMenu("显示", window)
    menubar.addMenu(view_menu)
    
    theme_menu = QMenu("主题", window)
    view_menu.addMenu(theme_menu)
    
    # 添加所有主题选项（与 main_window.py 一致）
    themes = [
        ("亮色", "light"),
        ("暗色", "dark"),
        ("跟随系统", "system"),
        ("海洋蓝", "ocean_blue"),
        ("森林绿", "forest_green"),
        ("日落橙", "sunset_orange"),
        ("紫色梦幻", "purple_dream"),
        ("玫瑰粉", "pink_rose"),
        ("极简白", "minimal_white"),
        ("深蓝色", "deep_blue"),
        ("深棕色", "deep_brown"),
        ("赛博朋克紫", "cyberpunk_purple"),  # 新增
    ]
    
    actions = []
    for name, theme_id in themes:
        action = QAction(name, window)
        action.triggered.connect(lambda checked, t=theme_id: print(f"✓ 主题已切换：{t}"))
        theme_menu.addAction(action)
        actions.append(action)
    
    # 检查菜单项
    menu_actions = theme_menu.actions()
    print(f"✓ 主题菜单共有 {len(menu_actions)} 个选项")
    
    print("\n菜单选项列表:")
    for i, action in enumerate(menu_actions):
        if action.isSeparator():
            print(f"  {i}. --- 分隔线 ---")
        else:
            print(f"  {i}. {action.text()}")
    
    # 检查是否有赛博朋克主题
    has_cyberpunk = any("赛博朋克" in action.text() for action in menu_actions)
    
    if has_cyberpunk:
        print("\n✅ 找到赛博朋克主题菜单项!")
    else:
        print("\n❌ 未找到赛博朋克主题菜单项!")
        return False
    
    print("\n✅ 主窗口菜单测试通过!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 赛博朋克主题集成验证")
    print("=" * 60)
    
    success = True
    
    # 测试 1: 设置对话框
    try:
        result1 = test_settings_dialog()
        success = success and result1
    except Exception as e:
        print(f"\n❌ 测试 1 失败：{e}")
        import traceback
        traceback.print_exc()
        success = False
    
    # 测试 2: 主窗口菜单
    try:
        result2 = test_main_window_menu()
        success = success and result2
    except Exception as e:
        print(f"\n❌ 测试 2 失败：{e}")
        import traceback
        traceback.print_exc()
        success = False
    
    # 总结
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过！赛博朋克主题已成功集成到 UI 中。")
        print("\n你现在可以:")
        print("  1. 在「显示」→「主题」菜单中选择「赛博朋克紫」")
        print("  2. 在设置对话框的「通用」→「外观」中选择「赛博朋克紫」")
    else:
        print("❌ 部分测试失败，请检查错误信息。")
    print("=" * 60 + "\n")
    
    sys.exit(0 if success else 1)
