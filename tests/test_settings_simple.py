"""简单测试设置对话框打开速度。"""

import sys
import time
from PySide6.QtWidgets import QApplication
from src.ui.settings_dialog import SettingsDialog

app = QApplication(sys.argv)

print("\n" + "="*60)
print("简单性能测试：设置对话框创建时间")
print("="*60)

start = time.time()

# 创建对话框
dlg = SettingsDialog(
    None,
    current_theme="light",
    current_model="GPT-4",
    available_models=["GPT-4", "Claude 3"],
    current_hotkey="Win+Shift+Space",
    current_whisper_model="base",
    mcp_manager=None,
)

created_time = time.time() - start
print(f"\n✅ 对话框创建完成：{created_time:.3f} 秒")

# 显示对话框（不等待关闭）
dlg.show()

show_time = time.time() - start
print(f"✅ 对话框显示完成：{show_time:.3f} 秒")

print("\n请手动关闭对话框...")
print("="*60 + "\n")

result = dlg.exec()

total_time = time.time() - start
print(f"\n总耗时：{total_time:.3f} 秒")
print("="*60 + "\n")
