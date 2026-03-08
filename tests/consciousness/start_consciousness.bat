@echo off
REM ========================================
REM WinClaw 意识系统 - 快速启动脚本
REM 使用 .venv 虚拟环境
REM ========================================

echo ╔═══════════════════════════════════════════════════════╗
echo ║     WinClaw 意识系统 - Phase 6 Complete               ║
echo ║           Silicon Life Critical Point Module          ║
echo ╚═══════════════════════════════════════════════════════╝
echo.

REM 激活虚拟环境
echo [信息] 正在激活虚拟环境...
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    echo [成功] 虚拟环境已激活
) else (
    echo [错误] 未找到虚拟环境：.venv
    pause
    exit /b 1
)

echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 环境异常
    pause
    exit /b 1
)

echo [信息] Python 版本：(python --version)
echo.

REM 运行快速检查
echo ════════════════════════════════════════════════════════
echo 正在启动意识系统检查...
echo ════════════════════════════════════════════════════════
echo.

python quick_start_consciousness.py

if errorlevel 1 (
    echo.
    echo [错误] 启动失败，请检查上述错误信息
    pause
    exit /b 1
)

echo.
echo ════════════════════════════════════════════════════════
echo 启动完成！
echo ════════════════════════════════════════════════════════
pause
