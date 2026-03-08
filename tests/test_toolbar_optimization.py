"""测试工具栏按钮优化效果。"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QToolBar, QPushButton, QLabel, QComboBox, QHBoxLayout
from src.ui.theme import Theme, apply_theme


def test_toolbar_optimization():
    """测试工具栏按钮优化。"""
    print("=" * 60)
    print("🔧 测试工具栏按钮优化")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    # 应用赛博宇宙蓝主题（可选）
    apply_theme(app, Theme.CYBER_UNIVERSE_BLUE)
    print("✅ 主题已应用")
    
    # 创建测试窗口
    window = QMainWindow()
    window.setWindowTitle("🔧 工具栏按钮优化测试")
    window.setGeometry(100, 100, 900, 200)
    
    # 创建工具栏
    toolbar = QToolBar("测试工具栏")
    toolbar.setMovable(False)
    window.addToolBar(toolbar)
    
    # 模型标签和下拉框
    model_label = QLabel("模型:")
    model_label.setStyleSheet("font-size: 11px;")
    toolbar.addWidget(model_label)
    
    model_combo = QComboBox()
    model_combo.addItems(["GPT-4", "Claude 3", "Gemini Pro"])
    model_combo.setMinimumWidth(150)
    model_combo.setStyleSheet("font-size: 11px; padding: 3px 6px;")
    toolbar.addWidget(model_combo)
    
    toolbar.addSeparator()
    
    # 优化工具栏按钮 - 缩小版本
    btn1 = QPushButton("新建会话")
    btn1.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 60px; max-width: 70px;")
    toolbar.addWidget(btn1)
    
    btn2 = QPushButton("📋 复制对话")
    btn2.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 80px; max-width: 90px;")
    toolbar.addWidget(btn2)
    
    btn3 = QPushButton("📋 历史对话")
    btn3.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 80px; max-width: 90px;")
    toolbar.addWidget(btn3)
    
    toolbar.addSeparator()
    
    btn4 = QPushButton("清空")
    btn4.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 50px; max-width: 60px;")
    toolbar.addWidget(btn4)
    
    toolbar.addSeparator()
    
    btn5 = QPushButton("🎤 录音")
    btn5.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 70px; max-width: 80px;")
    toolbar.addWidget(btn5)
    
    btn6 = QPushButton("🔇 TTS")
    btn6.setStyleSheet("font-size: 11px; padding: 4px 8px; min-width: 60px; max-width: 70px;")
    toolbar.addWidget(btn6)
    
    # 对话模式下拉框
    mode_combo = QComboBox()
    mode_combo.setMinimumWidth(120)
    mode_combo.setStyleSheet("font-size: 11px; padding: 3px 6px;")
    mode_combo.addItems(["💬 对话模式", "⚡ 持续对话", "🔔 唤醒词模式"])
    toolbar.addWidget(mode_combo)
    
    window.show()
    
    print("\n" + "=" * 60)
    print("📋 优化效果对比:")
    print("  • 字体大小：从默认 (~13px) 缩小到 11px")
    print("  • 按钮宽度：缩小约 40% (设置最小/最大宽度)")
    print("  • 内边距：从默认缩小到 4px 8px")
    print("  • 下拉框：宽度从 140px 缩小到 120px")
    print("\n请查看工具栏按钮是否更紧凑、更精致！")
    print("=" * 60)
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(test_toolbar_optimization())
