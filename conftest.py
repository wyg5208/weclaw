"""pytest 全局配置 - 设置测试路径"""
import sys
from pathlib import Path

# 将 weclaw_server 目录加入路径，确保 remote_server 模块可直接导入
WINCLAW_SERVER_DIR = str(Path(__file__).parent / "weclaw_server")
if WINCLAW_SERVER_DIR not in sys.path:
    sys.path.insert(0, WINCLAW_SERVER_DIR)
