@echo off
REM WeClaw Remote Server Windows 服务安装脚本
REM 适用于 Windows Server 2022
REM 需要 NSSM (Non-Sucking Service Manager)

setlocal enabledelayedexpansion

echo ========================================
echo  WeClaw Remote Server 服务安装脚本
echo ========================================
echo.

REM 设置路径
set "PROJECT_ROOT=%~dp0.."
set "PYTHON_EXE=%PROJECT_ROOT%\..\.venv\Scripts\python.exe"
set "SERVER_SCRIPT=%PROJECT_ROOT%\remote_server\main.py"
set "NSSM_PATH=%PROJECT_ROOT%\deployment\nssm.exe"

REM 检查 Python
if not exist "%PYTHON_EXE%" (
    echo [错误] Python 解释器不存在: %PYTHON_EXE%
    echo 请修改脚本中的 PYTHON_EXE 路径
    pause
    exit /b 1
)

REM 检查服务脚本
if not exist "%SERVER_SCRIPT%" (
    echo [错误] 服务脚本不存在: %SERVER_SCRIPT%
    pause
    exit /b 1
)

REM 检查 NSSM
if not exist "%NSSM_PATH%" (
    echo [提示] NSSM 不存在，尝试下载...
    
    REM 创建临时目录
    set "TEMP_DIR=%PROJECT_ROOT%\temp\nssm"
    mkdir "%TEMP_DIR%" 2>nul
    
    echo 请手动下载 NSSM 并放置到: %NSSM_PATH%
    echo 下载地址: https://nssm.cc/download
    echo.
    echo 或者使用以下 PowerShell 命令安装:
    echo   choco install nssm
    echo.
    pause
    exit /b 1
)

echo [信息] 项目路径: %PROJECT_ROOT%
echo [信息] Python: %PYTHON_EXE%
echo [信息] 服务脚本: %SERVER_SCRIPT%
echo.

REM 服务名称
set "SERVICE_NAME=WeClawRemoteServer"
set "SERVICE_DISPLAY_NAME=WeClaw Remote Server"
set "SERVICE_DESCRIPTION=WeClaw 远程控制服务器 - 提供 API 和 WebSocket 服务"

REM 检查服务是否已存在
sc query "%SERVICE_NAME%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [警告] 服务已存在，将先卸载...
    "%NSSM_PATH%" stop "%SERVICE_NAME%" >nul 2>&1
    "%NSSM_PATH%" remove "%SERVICE_NAME%" confirm >nul 2>&1
    timeout /t 2 >nul
)

echo [步骤 1/5] 创建服务...
"%NSSM_PATH%" install "%SERVICE_NAME%" "%PYTHON_EXE%" "%SERVER_SCRIPT%"
if %errorlevel% neq 0 (
    echo [错误] 创建服务失败
    pause
    exit /b 1
)

echo [步骤 2/5] 配置服务参数...
"%NSSM_PATH%" set "%SERVICE_NAME%" DisplayName "%SERVICE_DISPLAY_NAME%"
"%NSSM_PATH%" set "%SERVICE_NAME%" Description "%SERVICE_DESCRIPTION%"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppDirectory "%PROJECT_ROOT%"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStdout "%PROJECT_ROOT%\logs\service_stdout.log"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStderr "%PROJECT_ROOT%\logs\service_stderr.log"

REM 日志轮转
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStdoutCreationDisposition 4
"%NSSM_PATH%" set "%SERVICE_NAME%" AppStderrCreationDisposition 4
"%NSSM_PATH%" set "%SERVICE_NAME%" AppRotateFiles 1
"%NSSM_PATH%" set "%SERVICE_NAME%" AppRotateBytes 10485760

echo [步骤 3/5] 配置环境变量...
"%NSSM_PATH%" set "%SERVICE_NAME%" AppEnvironmentExtra "PYTHONUNBUFFERED=1"
"%NSSM_PATH%" set "%SERVICE_NAME%" AppEnvironmentExtra "WECLAW_CONFIG=%PROJECT_ROOT%\config\remote_server.toml"

echo [步骤 4/5] 配置服务恢复选项...
"%NSSM_PATH%" set "%SERVICE_NAME%" AppExit Default Restart
"%NSSM_PATH%" set "%SERVICE_NAME%" AppRestartDelay 5000
"%NSSM_PATH%" set "%SERVICE_NAME%" AppThrottle 15000

echo [步骤 5/5] 设置服务启动类型...
"%NSSM_PATH%" set "%SERVICE_NAME%" Start SERVICE_AUTO_START

REM 创建日志目录
mkdir "%PROJECT_ROOT%\logs" 2>nul

echo.
echo ========================================
echo  服务安装完成!
echo ========================================
echo.
echo 服务名称: %SERVICE_NAME%
echo 服务状态: 已安装 (未启动)
echo.
echo 管理命令:
echo   启动服务: nssm start %SERVICE_NAME%
echo   停止服务: nssm stop %SERVICE_NAME%
echo   重启服务: nssm restart %SERVICE_NAME%
echo   查看状态: sc query %SERVICE_NAME%
echo   卸载服务: %~dp0uninstall_service.bat
echo.
echo 或者使用 Windows 服务管理器 (services.msc)
echo.

REM 询问是否启动服务
set /p START_SERVICE="是否立即启动服务? (Y/N): "
if /i "%START_SERVICE%"=="Y" (
    echo.
    echo [信息] 启动服务...
    "%NSSM_PATH%" start "%SERVICE_NAME%"
    timeout /t 3 >nul
    sc query "%SERVICE_NAME%"
)

echo.
pause
