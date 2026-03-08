@echo off
chcp 65001 >nul
REM ========================================
REM WinClaw Remote Server 启动脚本
REM ========================================

echo.
echo ========================================
echo     WinClaw 远程服务启动器
echo ========================================
echo.

REM 切换到 winclaw 目录
cd /d "%~dp0"

REM 检查虚拟环境
if exist ".venv\Scripts\activate.bat" (
    echo [1/3] 激活虚拟环境...
    call .venv\Scripts\activate.bat
) else (
    echo [警告] 未找到虚拟环境，使用系统 Python
)

REM 检查环境变量
if not defined OPENAI_API_KEY if not defined DEEPSEEK_API_KEY (
    echo [警告] 未检测到 API Key 环境变量
    echo 请在 .env 文件中设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY
    echo.
)

REM 创建必要的目录
if not exist "keys" mkdir keys
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs
if not exist "data" mkdir data

echo [2/3] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装远程服务依赖...
    pip install fastapi uvicorn python-multipart websockets python-jose bcrypt tomli httpx
)

echo [3/3] 启动远程服务...
echo ----------------------------------------
echo 服务地址: http://localhost:8080
echo API 文档: http://localhost:8080/docs
echo WebSocket: ws://localhost:8080/ws/chat
echo ----------------------------------------
echo.

python -m remote_server.main
