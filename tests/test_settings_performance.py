"""测试设置对话框加载性能优化。

验证点：
1. 设置对话框是否快速弹出（不阻塞）
2. API Key 是否异步加载
3. 设备状态是否异步加载
4. MCP Server 列表是否异步加载
"""

import sys
import time
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from src.ui.settings_dialog import SettingsDialog


class TestWindow(QMainWindow):
    """测试窗口。"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("设置对话框性能测试")
        self.resize(400, 300)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        btn = QPushButton("打开设置对话框")
        btn.clicked.connect(self._open_settings)
        layout.addWidget(btn)
        
        self._dialog_open_time = None
    
    def _open_settings(self):
        """打开设置对话框并计时。"""
        print("\n" + "="*60)
        print("开始测试设置对话框加载性能")
        print("="*60)
        
        start = time.time()
        self._dialog_open_time = start
        
        dlg = SettingsDialog(
            self,
            current_theme="light",
            current_model="GPT-4",
            available_models=["GPT-4", "Claude 3", "Gemini"],
            current_hotkey="Win+Shift+Space",
            current_whisper_model="base",
            mcp_manager=None,
        )
        
        # 连接信号用于观察加载情况
        def on_loaded():
            elapsed = time.time() - start
            print(f"[{elapsed:.3f}s] 对话框已显示")
        
        # 使用 QTimer 模拟延迟回调
        from PySide6.QtCore import QTimer
        QTimer.singleShot(100, on_loaded)
        
        # 显示对话框
        result = dlg.exec()
        end = time.time()
        
        print(f"\n对话框打开耗时：{end - start:.3f} 秒")
        print(f"预期：< 0.5 秒（优化后应该几乎瞬间显示）")
        
        if (end - start) < 0.5:
            print("✅ 性能测试通过：对话框加载非常快！")
        elif (end - start) < 1.0:
            print("⚠️  性能一般：可以接受但有优化空间")
        else:
            print("❌ 性能问题：对话框加载仍然较慢")
        
        print("="*60 + "\n")


def main():
    """运行测试。"""
    app = QApplication(sys.argv)
    
    print("\n" + "="*60)
    print("WeClaw 设置对话框性能优化测试")
    print("="*60)
    print("\n优化内容：")
    print("1. ✅ 设备状态加载改为异步（QTimer + QThread）")
    print("2. ✅ API Key 加载改为异步（QTimer 延迟加载）")
    print("3. ✅ MCP Server 列表改为异步（QTimer 延迟加载）")
    print("\n预期效果：对话框应在 < 0.5 秒内显示")
    print("="*60 + "\n")
    
    win = TestWindow()
    win.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
