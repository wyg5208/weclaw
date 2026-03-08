"""赛博朋克紫色主题测试工具。

用于预览和测试 Cyberpunk Purple 主题的视觉效果。
"""

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QProgressBar,
    QGroupBox,
    QCheckBox,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QStatusBar,
    QToolBar,
    QMenuBar,
    QMenu,
    QScrollArea,
    QFrame,
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt
from src.ui.theme import Theme, apply_theme, get_stylesheet
from src.ui.cyberpunk_effects import GlowEffect


def create_test_window() -> QMainWindow:
    """创建测试窗口。"""
    window = QMainWindow()
    window.setWindowTitle("🌃 赛博朋克紫色主题测试 - Cyberpunk Purple Theme")
    window.setMinimumSize(1000, 800)
    
    # 中央容器
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    layout.setSpacing(20)
    layout.setContentsMargins(20, 20, 20, 20)
    
    # 标题
    title_label = QLabel("🚀 赛博朋克紫色主题展示中心")
    title_label.setStyleSheet("""
        font-size: 32px; 
        font-weight: bold;
        color: #d7bde2;
        padding: 20px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 transparent, 
            stop:0.5 rgba(155, 89, 182, 0.3), 
            stop:1 transparent);
        border-radius: 10px;
    """)
    title_label.setAlignment(Qt.AlignCenter)
    layout.addWidget(title_label)
    
    # 标签页容器
    tabs = QTabWidget()
    tabs.setObjectName("testTabs")
    layout.addWidget(tabs)
    
    # ===== 标签页 1: 基础组件 =====
    tab1 = QWidget()
    tab1_layout = QVBoxLayout(tab1)
    tab1_layout.setSpacing(15)
    
    # 按钮组
    btn_group = QGroupBox("🔘 按钮组件 Buttons")
    btn_layout = QHBoxLayout()
    
    normal_btn = QPushButton("普通按钮")
    normal_btn.setObjectName("normalBtn")
    
    primary_btn = QPushButton("主要按钮")
    primary_btn.setObjectName("primaryBtn")
    primary_btn.setDefault(True)
    
    glow_btn = QPushButton("✨ 发光按钮")
    glow_btn.setObjectName("glowBtn")
    # 应用发光效果
    GlowEffect.apply_glow(glow_btn, color="#be90d4", blur_radius=25, animated=True)
    
    btn_layout.addWidget(normal_btn)
    btn_layout.addWidget(primary_btn)
    btn_layout.addWidget(glow_btn)
    btn_group.setLayout(btn_layout)
    tab1_layout.addWidget(btn_group)
    
    # 输入框组
    input_group = QGroupBox("📝 输入框 Input Fields")
    input_layout = QVBoxLayout()
    
    line_edit = QLineEdit("这是单行输入框")
    line_edit.setPlaceholderText("请输入内容...")
    
    text_edit = QTextEdit("这是多行文本框\n支持多行输入")
    text_edit.setMaximumHeight(100)
    
    input_layout.addWidget(line_edit)
    input_layout.addWidget(text_edit)
    input_group.setLayout(input_layout)
    tab1_layout.addWidget(input_group)
    
    # 选择器组
    selector_group = QGroupBox("🔽 选择器 Selectors")
    selector_layout = QHBoxLayout()
    
    combo = QComboBox()
    combo.addItems(["选项 1", "选项 2", "选项 3", "选项 4"])
    combo.setCurrentIndex(0)
    
    spin = QSpinBox()
    spin.setRange(0, 100)
    spin.setValue(50)
    
    checkbox = QCheckBox("复选框 Check")
    radio = QRadioButton("单选框 Radio")
    
    selector_layout.addWidget(combo)
    selector_layout.addWidget(spin)
    selector_layout.addWidget(checkbox)
    selector_layout.addWidget(radio)
    selector_group.setLayout(selector_layout)
    tab1_layout.addWidget(selector_group)
    
    # 进度条
    progress_group = QGroupBox("📊 进度条 Progress")
    progress_layout = QVBoxLayout()
    
    progress = QProgressBar()
    progress.setValue(75)
    progress.setFormat("%p% - 能量充能中...")
    
    slider = QSlider(Qt.Horizontal)
    slider.setValue(70)
    slider.setMinimumWidth(300)
    
    progress_layout.addWidget(progress)
    progress_layout.addWidget(slider)
    progress_group.setLayout(progress_layout)
    tab1_layout.addWidget(progress_group)
    
    tabs.addTab(tab1, "🏠 基础组件")
    
    # ===== 标签页 2: 聊天气泡 =====
    tab2 = QWidget()
    tab2_layout = QVBoxLayout(tab2)
    tab2_layout.setSpacing(15)
    
    chat_container = QFrame()
    chat_container.setObjectName("chatContainer")
    chat_layout = QVBoxLayout(chat_container)
    
    # 用户消息
    user_msg = QLabel("这是用户发送的消息气泡 💬\n测试多行显示效果")
    user_msg.setObjectName("userMessageBubble")
    user_msg.setWordWrap(True)
    user_msg.setStyleSheet("""
        #userMessageBubble {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #9b59b6, stop:1 #be90d4);
            color: white;
            border-radius: 12px;
            padding: 15px;
            margin: 5px;
        }
    """)
    
    # AI 消息
    ai_msg = QLabel("这是 AI 助手的回复消息 🤖\n赛博朋克风格是不是很酷？")
    ai_msg.setObjectName("assistantMessageBubble")
    ai_msg.setWordWrap(True)
    ai_msg.setStyleSheet("""
        #assistantMessageBubble {
            background-color: rgba(30, 25, 70, 0.5);
            color: #e0e0ff;
            border: 2px solid #6c3483;
            border-radius: 12px;
            padding: 15px;
            margin: 5px;
        }
    """)
    
    chat_layout.addWidget(user_msg)
    chat_layout.addWidget(ai_msg)
    
    tab2_layout.addWidget(chat_container)
    tabs.addTab(tab2, "💬 聊天样式")
    
    # ===== 标签页 3: 特殊效果 =====
    tab3 = QWidget()
    tab3_layout = QVBoxLayout(tab3)
    tab3_layout.setSpacing(20)
    
    # 发光效果展示
    glow_group = QGroupBox("✨ 发光特效展示 Glow Effects")
    glow_layout = QHBoxLayout()
    
    glow_btn1 = QPushButton("脉冲发光 1")
    glow_btn1.setObjectName("pulseGlow1")
    GlowEffect.apply_glow(glow_btn1, color="#9b59b6", blur_radius=20, animated=True)
    
    glow_btn2 = QPushButton("脉冲发光 2")
    glow_btn2.setObjectName("pulseGlow2")
    GlowEffect.apply_glow(glow_btn2, color="#00ffff", blur_radius=20, animated=True)
    
    glow_btn3 = QPushButton("静态发光")
    glow_btn3.setObjectName("staticGlow")
    GlowEffect.apply_glow(glow_btn3, color="#be90d4", blur_radius=30, animated=False)
    
    glow_layout.addWidget(glow_btn1)
    glow_layout.addWidget(glow_btn2)
    glow_layout.addWidget(glow_btn3)
    glow_group.setLayout(glow_layout)
    tab3_layout.addWidget(glow_group)
    
    # 渐变背景展示
    gradient_group = QGroupBox("🎨 渐变背景 Gradients")
    gradient_layout = QHBoxLayout()
    
    gradient1 = QLabel("渐变背景 1")
    gradient1.setAlignment(Qt.AlignCenter)
    gradient1.setStyleSheet("""
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0f0c29, stop:0.5 #302b63, stop:1 #24243e);
        color: white;
        padding: 30px;
        border-radius: 10px;
        font-size: 16px;
        font-weight: bold;
    """)
    
    gradient2 = QLabel("渐变背景 2")
    gradient2.setAlignment(Qt.AlignCenter)
    gradient2.setStyleSheet("""
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #8e44ad, stop:1 #9b59b6);
        color: white;
        padding: 30px;
        border-radius: 10px;
        font-size: 16px;
        font-weight: bold;
    """)
    
    gradient_layout.addWidget(gradient1)
    gradient_layout.addWidget(gradient2)
    gradient_group.setLayout(gradient_layout)
    tab3_layout.addWidget(gradient_group)
    
    tabs.addTab(tab3, "✨ 特效展示")
    
    # 状态栏
    status_bar = QStatusBar()
    status_bar.showMessage("🎨 赛博朋克紫色主题已激活 | Cyberpunk Purple Theme Active")
    window.setStatusBar(status_bar)
    
    # 工具栏
    toolbar = QToolBar("主工具栏")
    toolbar.setMovable(False)
    tool_action = QAction("🛠️ 工具", window)
    help_action = QAction("❓ 帮助", window)
    toolbar.addAction(tool_action)
    toolbar.addAction(help_action)
    window.addToolBar(toolbar)
    
    # 菜单栏
    menubar = window.menuBar()
    file_menu = menubar.addMenu("📁 文件")
    edit_menu = menubar.addMenu("✏️ 编辑")
    view_menu = menubar.addMenu("👁️ 视图")
    help_menu = menubar.addMenu("❓ 帮助")
    
    return window


def main():
    """主函数。"""
    app = QApplication(sys.argv)
    
    # 应用赛博朋克紫色主题
    print("=" * 60)
    print("🌃 正在应用赛博朋克紫色主题...")
    print("=" * 60)
    apply_theme(app, Theme.CYBERPUNK_PURPLE)
    print("✅ 主题应用成功！")
    print("=" * 60)
    print("\n📋 测试窗口功能:")
    print("  • 查看各种 UI 组件的赛博朋克风格效果")
    print("  • 测试按钮、输入框、下拉框等交互组件")
    print("  • 体验霓虹发光特效和渐变背景")
    print("  • 查看聊天气泡样式")
    print("=" * 60)
    print("\n按 Ctrl+C 或关闭窗口退出测试\n")
    
    # 创建并显示窗口
    window = create_test_window()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
