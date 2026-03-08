"""
神经形态意识系统 - 快速启动脚本

一键启动 Dashboard 可视化
"""

import sys
import os
from pathlib import Path

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'consciousness' / 'neuroconscious'))

print("🧠 神经形态意识系统 Dashboard")
print("="*60)

try:
    from visualizer import NeuroDashboard
    
    # 静默初始化（visualizer.py 内部会打印简要信息）
    dashboard = NeuroDashboard(n_neurons=1000, n_modules=6)
    dashboard.run(debug=False, port=8050)
    
except ImportError as e:
    print(f"\n❌ 错误：缺少必要的依赖")
    print(f"详情：{e}")
    print("\n请运行以下命令安装依赖:")
    print("  pip install dash plotly numpy scipy rich")
    
except Exception as e:
    print(f"\n❌ 发生错误：{e}")
    import traceback
    traceback.print_exc()
