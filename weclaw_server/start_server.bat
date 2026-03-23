@echo off
chcp 65001 >nul
title WeClaw 服务端启动器

echo ========================================
echo   WeClaw 远程服务端启动器
echo ========================================
echo.

REM 检查虚拟环境是否存在
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 未找到虚拟环境！
    echo 请先创建虚拟环境并安装依赖：
    echo   python -m venv venv
    echo   venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo [信息] 正在激活虚拟环境...
call venv\Scripts\activate.bat

echo [信息] 正在启动 WeClaw 远程服务...
echo [信息] 服务地址：http://localhost:8188
echo.

REM 使用 uvicorn 启动服务
python -m uvicorn remote_server.main:app --host 0.0.0.0 --port 8188

REM 如果服务退出，显示提示
echo.
echo [提示] 服务已停止
pause
