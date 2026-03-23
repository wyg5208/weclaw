@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ================================================================
echo WeClaw 后台管理系统 - 集成启动模式
echo ================================================================
echo.
echo 访问地址：http://localhost:8188/admin
echo 默认管理员账号：admin / admin123456
echo.
echo [提示] Admin模块已集成到 WeClaw 主服务，通过 8188/admin 访问
echo.

REM 检查端口占用情况
echo 正在检查端口 8188...
REM 只检测 LISTENING 状态的进程（真正占用端口的进程）
netstat -ano | findstr ":8188.*LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo [警告] 端口 8188 已被占用！
    echo.
    echo 占用情况：
    netstat -ano | findstr ":8188.*LISTENING"
    echo.
    
    REM 获取占用端口的 PID 并杀死进程
    for /f "tokens=5 delims= " %%a in ('netstat -ano ^| findstr ":8188.*LISTENING"') do (
        set "PID=%%a"
        goto :kill_process
    )
    goto :port_still_occupied
)
REM 检查是否有 TIME_WAIT 等连接状态（PID 为 0，无需处理）
netstat -ano | findstr ":8188" | findstr /V "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo [提示] 检测到 TCP 连接状态（TIME_WAIT/FIN_WAIT/CLOSE_WAIT）
    echo 这些是正常的连接关闭状态，会在几秒内自动清理
    echo 继续启动服务...
    echo.
)
goto :port_free

:kill_process
echo.
echo [信息] 占用进程的 PID: !PID!
echo.
choice /C YN /M "是否强制结束该进程"
if errorlevel 2 (
    echo.
    echo [提示] 已取消操作，请手动关闭占用的程序
    pause
    exit /b 1
)
if errorlevel 1 (
    echo.
    echo [操作] 正在强制结束进程 !PID! ...
    taskkill /F /PID !PID! >nul 2>&1
    if %errorlevel% equ 0 (
        echo [成功] 进程已结束
        timeout /t 2 >nul
        goto :port_free
    ) else (
        echo [失败] 无法结束进程，可能需要管理员权限
        echo.
        echo 请尝试以管理员身份运行此脚本
        pause
        exit /b 1
    )
)

:port_still_occupied
echo.
echo [错误] 端口仍然被占用
pause
exit /b 1

:port_free

echo.
echo 正在启动 WeClaw 服务（包含 Admin模块）...
echo.

cd /d "%~dp0"

REM 设置环境变量
set PYTHONIOENCODING=utf-8

REM 激活虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [信息] 正在激活虚拟环境...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [信息] 正在激活虚拟环境...
    call .venv\Scripts\activate.bat
) else (
    echo [警告] 未找到虚拟环境，请确认是否已安装依赖
    pause
)

REM 启动服务（集成 Admin模块，使用 8188 端口）
python -m uvicorn remote_server.main:app --host 0.0.0.0 --port 8188

pause
