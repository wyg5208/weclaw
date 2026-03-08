@echo off
REM WinClaw Remote Server Windows 服务卸载脚本
REM 适用于 Windows Server 2022

setlocal enabledelayedexpansion

echo ========================================
echo  WinClaw Remote Server 服务卸载脚本
echo ========================================
echo.

set "PROJECT_ROOT=%~dp0.."
set "NSSM_PATH=%PROJECT_ROOT%\deployment\nssm.exe"
set "SERVICE_NAME=WinClawRemoteServer"

REM 检查服务是否存在
sc query "%SERVICE_NAME%" >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 服务不存在，无需卸载
    pause
    exit /b 0
)

echo [警告] 即将卸载服务: %SERVICE_NAME%
echo.
set /p CONFIRM="确认卸载? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo [信息] 操作已取消
    pause
    exit /b 0
)

echo.
echo [步骤 1/3] 停止服务...
"%NSSM_PATH%" stop "%SERVICE_NAME%" 2>nul
timeout /t 3 >nul

echo [步骤 2/3] 移除服务...
"%NSSM_PATH%" remove "%SERVICE_NAME%" confirm
if %errorlevel% neq 0 (
    echo [错误] 移除服务失败，尝试使用 sc 命令...
    sc delete "%SERVICE_NAME%"
)

echo [步骤 3/3] 清理...
echo 服务已成功卸载

echo.
echo ========================================
echo  服务卸载完成!
echo ========================================
echo.
pause
