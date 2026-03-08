"""
神经形态意识系统 - 交互式 Dashboard 快速启动
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src' / 'consciousness' / 'neuroconscious'))

print("🧠 神经形态意识系统 - 交互式 Dashboard")
print("="*60)

try:
    from interactive_dashboard import InteractiveNeuroDashboard
    
    # 启动 Dashboard（关闭 debug 模式避免双重初始化）
    dashboard = InteractiveNeuroDashboard(n_neurons=1000, n_modules=6)
    dashboard.run(debug=False, port=8067)  # 修改端口强制刷新浏览器缓存
    
except Exception as e:
    print(f"\n❌ 发生错误：{e}")
    import traceback
    traceback.print_exc()
