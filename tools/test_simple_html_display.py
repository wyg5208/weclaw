"""最简单的 HTML 显示测试。"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView


class SimpleTestWindow(QMainWindow):
    """简单测试窗口。"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HTML 测试窗口")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建 Web 视图
        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)
        
        # 设置简单 HTML
        html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        h1 { font-size: 48px; margin-bottom: 20px; }
        p { font-size: 24px; }
        .box {
            background: rgba(255,255,255,0.2);
            padding: 20px;
            border-radius: 15px;
            margin: 20px auto;
            max-width: 600px;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>🎉 测试成功！</h1>
        <p>如果您看到这段文字，说明 HTML 渲染正常。</p>
        <p>背景应该是紫色渐变的。</p>
    </div>
</body>
</html>'''
        
        print("✅ 准备设置 HTML...")
        print(f"   HTML 长度：{len(html)}")
        self.web_view.setHtml(html)
        print("✅ HTML 已设置")
        
        # 强制刷新
        self.web_view.reload()
        print("✅ 已调用 reload()")


def main():
    print("=" * 60)
    print("最简单的 HTML 显示测试")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    window = SimpleTestWindow()
    window.show()
    
    print("\n✅ 窗口已显示")
    print("💡 请查看窗口内容:")
    print("   - 能看到紫色渐变背景吗？")
    print("   - 能看到 '🎉 测试成功！' 文字吗？")
    print("   - 窗口是空白还是有内容？")
    print("=" * 60)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
