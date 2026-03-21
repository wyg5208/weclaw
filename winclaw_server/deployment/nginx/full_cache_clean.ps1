# WinClaw 完整缓存清理脚本
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "WinClaw 完整缓存清理工具" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# 1. 重新编译 PWA（强制清除旧 Service Worker）
Write-Host "[1/4] 正在重新编译 PWA 应用..." -ForegroundColor Yellow
Set-Location d:\python_projects\weclaw_server\pwa
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ PWA 编译失败！" -ForegroundColor Red
    pause
    exit 1
}
Write-Host "✓ PWA 编译完成" -ForegroundColor Green
Write-Host ""

# 2. 复制更新后的文件到部署目录
Write-Host "[2/4] 正在部署 PWA 文件..." -ForegroundColor Yellow
Copy-Item ".\dist\*" "d:\python_projects\weclaw_server\pwa\dist\" -Recurse -Force
Write-Host "✓ PWA 文件已部署" -ForegroundColor Green
Write-Host ""

# 3. 测试并重新加载 Nginx
Write-Host "[3/4] 正在测试 Nginx 配置..." -ForegroundColor Yellow
Set-Location d:\nginx
.\nginx.exe -t -c conf\nginx.conf
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Nginx 配置测试通过" -ForegroundColor Green
    Write-Host "`n[4/4] 正在重新加载 Nginx..." -ForegroundColor Yellow
    .\nginx.exe -s reload
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Nginx 已重新加载" -ForegroundColor Green
    } else {
        Write-Host "⚠ Nginx 重新加载失败，请手动重启" -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ Nginx 配置测试失败！" -ForegroundColor Red
}
Write-Host ""

# 4. 输出浏览器缓存清理指南
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "服务器端更新已完成！" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "现在请在浏览器中执行以下操作：" -ForegroundColor Yellow
Write-Host ""
Write-Host "【方法一】强制刷新（推荐）" -ForegroundColor White
Write-Host "1. 打开 https://weclaw.cc" -ForegroundColor Gray
Write-Host "2. 按 F12 打开开发者工具" -ForegroundColor Gray
Write-Host "3. 右键点击刷新按钮" -ForegroundColor Gray
Write-Host "4. 选择'清空缓存并硬性重新加载'" -ForegroundColor Gray
Write-Host ""
Write-Host "【方法二】清除浏览数据" -ForegroundColor White
Write-Host "1. 按 Ctrl+Shift+Delete" -ForegroundColor Gray
Write-Host "2. 时间范围：全部时间" -ForegroundColor Gray
Write-Host "3. 勾选：缓存的图片和文件" -ForegroundColor Gray
Write-Host "4. 点击'清除数据'" -ForegroundColor Gray
Write-Host ""
Write-Host "【方法三】注销 Service Worker（如果上述方法无效）" -ForegroundColor White
Write-Host "1. F12 > Application > Service Workers" -ForegroundColor Gray
Write-Host "2. 点击 'Unregister' 注销所有 Service Worker" -ForegroundColor Gray
Write-Host "3. F12 > Application > Storage" -ForegroundColor Gray
Write-Host "4. 点击 'Clear storage data'" -ForegroundColor Gray
Write-Host "5. 关闭所有标签页，重新访问网站" -ForegroundColor Gray
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "注意事项：" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "• Service Worker 可能会缓存旧版本资源" -ForegroundColor Red
Write-Host "• 建议先清除缓存再访问" -ForegroundColor Red
Write-Host "• 如果仍看到旧网站，尝试使用无痕模式" -ForegroundColor Red
Write-Host ""

pause
