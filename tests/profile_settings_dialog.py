"""性能分析脚本：诊断设置对话框加载慢的根本原因。"""

import cProfile
import pstats
import io
from pstats import SortKey

# 模拟创建对话框
def create_settings_dialog():
    """创建设置对话框并计时。"""
    from PySide6.QtWidgets import QApplication, QDialog
    from src.ui.settings_dialog import SettingsDialog
    
    app = QApplication.instance() or QApplication([])
    
    dlg = SettingsDialog(
        None,
        current_theme="light",
        current_model="GPT-4",
        available_models=["GPT-4", "Claude 3", "Gemini"],
        current_hotkey="Win+Shift+Space",
        current_whisper_model="base",
        mcp_manager=None,
    )
    
    return dlg


def profile_settings_creation():
    """性能分析。"""
    print("="*70)
    print("开始性能分析：SettingsDialog 创建过程")
    print("="*70)
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    dlg = create_settings_dialog()
    
    profiler.disable()
    
    # 输出统计
    s = io.StringIO()
    stats = pstats.Stats(profiler, stream=s).sort_stats(SortKey.CUMULATIVE)
    stats.print_stats(30)  # 打印前 30 个最耗时的函数
    
    print(s.getvalue())
    print("="*70)
    
    # 分析关键路径
    print("\n关键发现:")
    print("-" * 70)
    
    total_time = stats.total_tt
    print(f"总耗时：{total_time:.4f} 秒")
    
    # 检查 keyring 相关调用
    keyring_time = sum(
        stat[3] for stat in stats.stats.values() 
        if 'keyring' in stat[0] or 'load_key' in stat[0]
    )
    if keyring_time > 0:
        print(f"⚠️  Keyring/加密存储相关耗时：{keyring_time:.4f} 秒 ({keyring_time/total_time*100:.1f}%)")
    
    # 检查网络相关
    network_time = sum(
        stat[3] for stat in stats.stats.values()
        if 'device_binder' in stat[0] or 'httpx' in stat[0] or 'asyncio' in stat[0]
    )
    if network_time > 0:
        print(f"⚠️  网络/异步操作相关耗时：{network_time:.4f} 秒 ({network_time/total_time*100:.1f}%)")
    
    # 检查 UI 构建
    ui_time = sum(
        stat[3] for stat in stats.stats.values()
        if '_create_' in stat[0] or 'QWidget' in stat[0]
    )
    print(f"📊 UI 构建耗时：{ui_time:.4f} 秒 ({ui_time/total_time*100:.1f}%)")
    
    print("\n建议优化方向:")
    print("-" * 70)
    if keyring_time > total_time * 0.3:
        print("1. ✅ 已将 API Key 加载改为异步 - 正确方向")
    if network_time > total_time * 0.3:
        print("2. ✅ 已将设备状态加载改为异步 - 正确方向")
    if ui_time > total_time * 0.5:
        print("3. ⚠️  UI 构建本身较慢，考虑简化选项卡结构或使用 QStackedWidget")


if __name__ == "__main__":
    profile_settings_creation()
