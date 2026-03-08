# 清除 WinClaw PWA 浏览器缓存脚本

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "WinClaw PWA 缓存清除工具" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "请按以下步骤操作：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 打开浏览器开发者工具 (F12)" -ForegroundColor White
Write-Host "2. 右键点击刷新按钮" -ForegroundColor White
Write-Host "3. 选择 '清空缓存并硬性重新加载'" -ForegroundColor White
Write-Host ""
Write-Host "或者：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 按 Ctrl+Shift+Delete 打开清除浏览历史记录" -ForegroundColor White
Write-Host "2. 选择 '缓存的图片和文件'" -ForegroundColor White
Write-Host "3. 时间范围选择 '全部时间'" -ForegroundColor White
Write-Host "4. 点击 '清除数据'" -ForegroundColor White
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "重要提示：" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "PWA 应用已更新为使用 weclaw.cc 域名" -ForegroundColor Green
Write-Host "旧版本可能缓存了 ws.madechango.com 的配置" -ForegroundColor Red
Write-Host ""
Write-Host "如果清除缓存后仍有问题，请检查：" -ForegroundColor Yellow
Write-Host "1. Service Worker 是否已注销" -ForegroundColor White
Write-Host "2. Application > Storage > Clear storage data" -ForegroundColor White
Write-Host ""

pause
