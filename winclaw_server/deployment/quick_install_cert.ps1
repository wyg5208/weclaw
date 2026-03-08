# WinClaw Let's Encrypt 证书快速安装指南
# 按照步骤执行即可完成证书申请和部署

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " WinClaw Let's Encrypt 证书快速安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ========== 第 1 步：创建目录 ==========
Write-Host "[第 1 步] 创建必要目录..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "D:\www\winclaw" -Force | Out-Null
New-Item -ItemType Directory -Path "D:\www\winclaw\.well-known\acme-challenge" -Force | Out-Null
New-Item -ItemType Directory -Path "D:\nginx\ssl\weclaw.cc" -Force | Out-Null
Write-Host "  ✓ 目录创建完成" -ForegroundColor Green
Write-Host ""

# ========== 第 2 步：重启 Nginx ==========
Write-Host "[第 2 步] 重启 Nginx..." -ForegroundColor Yellow
try {
    D:\nginx\nginx.exe -s reload
    Write-Host "  ✓ Nginx 已重启" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Nginx 可能未运行，尝试启动..." -ForegroundColor Yellow
    Start-Process -FilePath "D:\nginx\nginx.exe" -WindowStyle Hidden
}
Write-Host ""

# ========== 第 3 步：下载 win-acme ==========
Write-Host "[第 3 步] 准备 win-acme..." -ForegroundColor Yellow
if (Test-Path "D:\tools\win-acme\wacs.exe") {
    Write-Host "  ✓ win-acme 已存在" -ForegroundColor Green
} else {
    Write-Host "  正在下载 win-acme..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path "D:\temp" -Force | Out-Null
    New-Item -ItemType Directory -Path "D:\tools\win-acme" -Force | Out-Null
    
    $url = "https://github.com/win-acme/win-acme/releases/download/v2.2.8.1635/win-acme.v2.2.8.1635.x64.pluggable.zip"
    Invoke-WebRequest -Uri $url -OutFile "D:\temp\win-acme.zip" -UseBasicParsing
    Expand-Archive -Path "D:\temp\win-acme.zip" -DestinationPath "D:\tools\win-acme" -Force
    Remove-Item "D:\temp\win-acme.zip" -Force
    
    Write-Host "  ✓ win-acme 已安装" -ForegroundColor Green
}
Write-Host ""

# ========== 第 4 步：申请证书 ==========
Write-Host "[第 4 步] 申请 Let's Encrypt 证书..." -ForegroundColor Yellow
Write-Host "  域名：weclaw.cc, *.weclaw.cc" -ForegroundColor Cyan
Write-Host ""
Write-Host "  正在运行 win-acme..." -ForegroundColor Cyan
Write-Host "  （首次运行可能需要确认条款）" -ForegroundColor Gray
Write-Host ""

Set-Location "D:\tools\win-acme"
.\wacs.exe --target manual --host "weclaw.cc,*.weclaw.cc" --webroot "D:\www\winclaw" --store pemfiles --pemfilespath "D:\nginx\ssl\weclaw.cc" --accepttos --verbose

Write-Host ""

# ========== 第 5 步：验证证书 ==========
Write-Host "[第 5 步] 验证证书文件..." -ForegroundColor Yellow
$certFiles = @(
    "D:\nginx\ssl\weclaw.cc\fullchain.pem",
    "D:\nginx\ssl\weclaw.cc\privkey.pem"
)

$allExist = $true
foreach ($file in $certFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file (缺失)" -ForegroundColor Red
        $allExist = $false
    }
}

if (-not $allExist) {
    Write-Host "`n  ✗ 证书文件不完整，请检查上方错误信息" -ForegroundColor Red
    exit 1
}

Write-Host "`n  ✓ 证书文件验证通过！" -ForegroundColor Green
Write-Host ""

# ========== 第 6 步：提示后续操作 ==========
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  证书申请成功！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步操作：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 更新 Nginx 配置启用 HTTPS（编辑 deployment/nginx/winclaw.conf）" -ForegroundColor White
Write-Host "   取消以下行的注释（在 HTTP server 块中）：" -ForegroundColor Gray
Write-Host "   - if (`$host = weclaw.cc) { return 301 https://`$host`$request_uri; }" -ForegroundColor Gray
Write-Host "   - if (`$host ~ ^(.+)\.weclaw\.cc$) { return 301 https://`$host`$request_uri; }" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 开启 HSTS（可选，建议先测试）" -ForegroundColor Gray
Write-Host "   add_header Strict-Transport-Security `"max-age=31536000; includeSubDomains`" always;" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 重启 Nginx" -ForegroundColor White
Write-Host "   D:\nginx\nginx.exe -t" -ForegroundColor Gray
Write-Host "   D:\nginx\nginx.exe -s reload" -ForegroundColor Gray
Write-Host ""
Write-Host "4. 访问 https://weclaw.cc 测试" -ForegroundColor White
Write-Host ""
Write-Host "查看自动续期任务：" -ForegroundColor Yellow
Write-Host "Get-ScheduledTask | Where-Object {`$_.TaskName -like '*win-acme*'}" -ForegroundColor Gray
Write-Host ""
Write-Host "手动续期命令：" -ForegroundColor Yellow
Write-Host "D:\tools\win-acme\wacs.exe --renew" -ForegroundColor Gray
Write-Host ""
