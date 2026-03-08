# -*- mode: python ; coding: utf-8 -*-
"""
WinClaw PyInstaller 打包配置

使用方法:
    pyinstaller winclaw.spec

输出:
    dist/WinClaw/
        winclaw.exe      - GUI 版本（默认，无控制台窗口）
        winclaw-cli.exe  - CLI 版本（带控制台窗口）

运行方式:
    winclaw.exe          # 启动 GUI
    winclaw.exe --cli    # 从 GUI 目录启动 CLI 模式
    winclaw-cli.exe      # 直接启动 CLI
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 项目根目录
ROOT_DIR = Path(SPECPATH)

# 收集数据文件
datas = [
    # 配置文件
    (str(ROOT_DIR / 'config'), 'config'),
    # 资源文件
    (str(ROOT_DIR / 'resources'), 'resources'),
]

# 收集 litellm 数据文件（包含模型价格配置等）
datas += collect_data_files('litellm')

# 收集 rich 数据文件（包含 unicode 数据）
datas += collect_data_files('rich')

# 收集 rich unicode 子模块（文件名含连字符，需要特殊处理）
rich_unicode_modules = collect_submodules('rich._unicode_data')

# 隐藏导入（动态导入的模块）
hiddenimports = [
    # PySide6 相关
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    # 工具类
    'src.tools.shell',
    'src.tools.file',
    'src.tools.screen',
    'src.tools.browser',
    'src.tools.app_control',
    'src.tools.clipboard',
    'src.tools.notify',
    'src.tools.search',
    'src.tools.cron',
    'src.tools.ocr',
    'src.tools.voice_input',
    'src.tools.voice_output',
    # 异步支持
    'asyncio',
    'aiohttp',
    # 调度器
    'apscheduler.schedulers.asyncio',
    'apscheduler.triggers.cron',
    'apscheduler.triggers.date',
    'apscheduler.triggers.interval',
    # 其他依赖
    'litellm',
    'yaml',
    'jinja2',
    'PIL',
    'mss',
    'pyautogui',
    'pyperclip',
    'keyring',
    'pynput',
    'rich',
] + rich_unicode_modules

# 排除的模块（减小体积）
excludes = [
    # 测试相关
    'pytest',
    'pytest_asyncio',
    # 开发工具
    'black',
    'ruff',
    'mypy',
    # 不需要的大型库
    'matplotlib',
    'scipy',
    'numpy.testing',
    # Playwright（可选依赖，单独安装）
    'playwright',
    # Whisper（可选依赖，单独安装）
    'whisper',
    'openai-whisper',
]

# 分析入口
a = Analysis(
    ['src/__main__.py'],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

# 去重
pyz = PYZ(a.pure)

# 可执行文件 - GUI 版本（无控制台窗口）
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='winclaw',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI 应用，无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT_DIR / 'resources' / 'icons' / 'app_icon.ico') if (ROOT_DIR / 'resources' / 'icons' / 'app_icon.ico').exists() else None,
    version='file_version_info.txt' if Path('file_version_info.txt').exists() else None,
)

# 可执行文件 - CLI 版本（带控制台窗口）
exe_cli = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='winclaw-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # CLI 应用，显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT_DIR / 'resources' / 'icons' / 'app_icon.ico') if (ROOT_DIR / 'resources' / 'icons' / 'app_icon.ico').exists() else None,
    version='file_version_info.txt' if Path('file_version_info.txt').exists() else None,
)

# 收集所有文件（包括 GUI 和 CLI 两个版本）
coll = COLLECT(
    exe,
    exe_cli,  # CLI 版本
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WinClaw',
)
