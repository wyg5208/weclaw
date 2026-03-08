"""测试赛博宇宙蓝主题效果。"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget
from src.ui.theme import Theme, apply_theme


def test_cyber_universe_blue():
    """测试赛博宇宙蓝主题。"""
    print("=" * 60)
    print("🌌 测试赛博宇宙蓝主题")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    # 应用赛博宇宙蓝主题
    apply_theme(app, Theme.CYBER_UNIVERSE_BLUE)
    print("✅ 主题已应用：赛博宇宙蓝")
    
    # 创建测试窗口
    window = QMainWindow()
    window.setWindowTitle("🌌 赛博宇宙蓝主题测试")
    window.setGeometry(100, 100, 600, 400)
    
    central = QWidget()
    window.setCentralWidget(central)
    layout = QVBoxLayout(central)
    
    # 标题
    title = QLabel("🌌 欢迎来到赛博宇宙蓝主题")
    title.setStyleSheet("font-size: 28px; font-weight: bold; color: #00bfff; padding: 20px;")
    title.setAlignment(Qt.AlignCenter)
    layout.addWidget(title)
    
    # 说明文字
    desc = QLabel("深邃宇宙蓝背景 + 电光蓝按钮 + 荧光青点缀")
    desc.setStyleSheet("font-size: 14px; color: #a8c8ff; padding: 10px;")
    desc.setAlignment(Qt.AlignCenter)
    layout.addWidget(desc)
    
    # 按钮
    btn1 = QPushButton("普通按钮")
    layout.addWidget(btn1)
    
    btn2 = QPushButton("✨ 主要按钮（默认）")
    btn2.setDefault(True)
    layout.addWidget(btn2)
    
    # 输入框
    from PySide6.QtWidgets import QLineEdit
    input_field = QLineEdit()
    input_field.setPlaceholderText("请输入内容... 查看发光边框效果")
    layout.addWidget(input_field)
    
    # 进度条
    from PySide6.QtWidgets import QProgressBar
    progress = QProgressBar()
    progress.setValue(75)
    progress.setFormat("%p% - 能量充能中...")
    layout.addWidget(progress)
    
    window.show()
    
    print("\n" + "=" * 60)
    print("📋 请查看以下效果:")
    print("  • 深邃的宇宙渐变背景")
    print("  • 蓝色霓虹发光按钮")
    print("  • 电光蓝进度条能量条")
    print("  • 荧光青输入框边框")
    print("  • 整体蓝色科技感风格")
    print("=" * 60)
    
    return app.exec()


if __name__ == "__main__":
    from PySide6.QtCore import Qt
    sys.exit(test_cyber_universe_blue())
