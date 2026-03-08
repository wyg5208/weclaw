@echo off
chcp 65001 >nul
title WinClaw PWA 前端预览服务器

echo ========================================
echo   WinClaw PWA 前端预览服务器
echo ========================================
echo.

REM 检查 Node.js 是否安装
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Node.js！
    echo 请先安装 Node.js: https://nodejs.org/
    echo.
    pause
    exit /b 1
)

REM 检查 pwa 目录是否存在
if not exist "pwa" (
    echo [错误] 未找到 pwa 目录！
    echo 请确保在正确的目录下运行此脚本
    echo.
    pause
    exit /b 1
)

REM 检查 dist 目录是否存在，不存在则构建
if not exist "pwa\dist" (
    echo [警告] 未找到 dist 目录，需要先构建项目...
    echo.
    
    REM 检查 node_modules 是否存在
    if not exist "pwa\node_modules" (
        echo [信息] 正在安装依赖...
        cd pwa
        call npm install
        cd ..
    )
    
    echo [信息] 正在构建项目...
    cd pwa
    call npm run build
    cd ..
    
    if not exist "pwa\dist" (
        echo [错误] 构建失败！
        pause
        exit /b 1
    )
    
    echo [成功] 构建完成！
    echo.
)

echo [信息] 正在启动 PWA 预览服务器...
echo [信息] 访问地址：http://localhost:4173
echo.

cd pwa
call npm run preview

REM 如果服务退出，显示提示
echo.
echo [提示] 预览服务器已停止
pause
