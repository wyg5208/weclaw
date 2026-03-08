"""
PyQtGraph Dashboard 启动脚本
高性能神经形态意识系统可视化
"""

import sys
import os

# 直接添加 neuroconscious 目录
neuro_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                          'src', 'consciousness', 'neuroconscious')
sys.path.insert(0, neuro_path)

from dashboard_pyqtgraph import main

if __name__ == '__main__':
    main()
