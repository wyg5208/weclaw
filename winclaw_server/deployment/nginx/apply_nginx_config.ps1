# WinClaw Nginx 配置修复脚本
# 功能：修复 https://weclaw.cc 自动定向问题

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "WinClaw Nginx 配置修复工具" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$sourceConf = "d:\python_projects\weclaw_server\deployment\nginx\nginx.conf"
$targetConf = "d:\nginx\conf\nginx.conf"

# 检查源文件是否存在
if (-not (Test-Path $sourceConf)) {
    Write-Host "错误：源配置文件不存在：$sourceConf" -ForegroundColor Red
    pause
    exit 1
}

# 备份当前配置
Write-Host "[1/4] 正在备份当前 Nginx 配置..." -ForegroundColor Yellow
$backupPath = $targetConf + ".backup." + (Get-Date -Format "yyyyMMdd_HHmmss")
Copy-Item $targetConf $backupPath -Force
Write-Host "✓ 已备份到：$backupPath" -ForegroundColor Green
Write-Host ""

# 复制新配置
Write-Host "[2/4] 正在复制修订后的配置文件..." -ForegroundColor Yellow
Copy-Item $sourceConf $targetConf -Force
Write-Host "✓ 配置文件已复制到：$targetConf" -ForegroundColor Green
Write-Host ""

# 测试 Nginx 配置
Write-Host "[3/4] 正在测试 Nginx 配置..." -ForegroundColor Yellow
$testOutput = & d:\nginx\nginx.exe -t -c $targetConf 2>&1
Write-Host $testOutput
Write-Host ""

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Nginx 配置测试通过！" -ForegroundColor Green
    Write-Host ""
    
    # 重新加载 Nginx
    Write-Host "[4/4] 正在重新加载 Nginx 配置..." -ForegroundColor Yellow
    & d:\nginx\nginx.exe -s reload
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Nginx 配置已成功重新加载！" -ForegroundColor Green
        Write-Host ""
        Write-Host "======================================" -ForegroundColor Green
        Write-Host "修复完成！" -ForegroundColor Green
        Write-Host "======================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "主要修改内容：" -ForegroundColor Cyan
        Write-Host "1. ✓ 已注释 D:\deploy1 下已暂停的 AI 换装和微信小程序项目" -ForegroundColor White
        Write-Host "2. ✓ 已启用 weclaw.cc 的 HTTPS 强制跳转" -ForegroundColor White
        Write-Host "3. ✓ 已移除 winclaw_http.conf 中的 default_server 标记" -ForegroundColor White
        Write-Host "4. ✓ 已正确导入 winclaw.conf（包含完整 HTTPS 配置）" -ForegroundColor White
        Write-Host ""
        Write-Host "现在可以访问 https://weclaw.cc 了" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "⚠ Nginx 重新加载失败，但配置文件已更新" -ForegroundColor Yellow
        Write-Host "请手动重启 Nginx 服务" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "错误信息：" -ForegroundColor Red
        Write-Host $testOutput -ForegroundColor Red
    }
} else {
    Write-Host "✗ Nginx 配置测试失败！" -ForegroundColor Red
    Write-Host "正在恢复备份..." -ForegroundColor Yellow
    Copy-Item $backupPath $targetConf -Force
    Write-Host "✓ 已恢复到备份配置" -ForegroundColor Green
    Write-Host ""
    Write-Host "错误信息：" -ForegroundColor Red
    Write-Host $testOutput -ForegroundColor Red
}

Write-Host ""
pause
