# WinClaw Let's Encrypt 证书自动安装脚本
# 适用于 Windows Server + Nginx
# 域名：weclaw.cc

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " WinClaw Let's Encrypt 证书自动安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 配置变量
$DOMAIN = "weclaw.cc"
$WILDCARD_DOMAIN = "*.weclaw.cc"
$WEBROOT_DIR = "D:\www\winclaw"
$SSL_DIR = "D:\nginx\ssl\weclaw.cc"
$NGINX_PATH = "D:\nginx"
$WIN_ACME_URL = "https://github.com/win-acme/win-acme/releases/download/v2.2.8.1635/win-acme.v2.2.8.1635.x64.pluggable.zip"
$WIN_ACME_DIR = "D:\tools\win-acme"
$TEMP_DIR = "D:\temp"

# 步骤 1: 创建必要目录
Write-Host "[1/7] 创建必要目录..." -ForegroundColor Yellow
try {
    New-Item -ItemType Directory -Path $WEBROOT_DIR -Force | Out-Null
    New-Item -ItemType Directory -Path "$WEBROOT_DIR\.well-known\acme-challenge" -Force | Out-Null
    New-Item -ItemType Directory -Path $SSL_DIR -Force | Out-Null
    New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null
    Write-Host "  ✓ 目录创建成功" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 目录创建失败：$_" -ForegroundColor Red
    exit 1
}

# 步骤 2: 测试 Nginx 配置
Write-Host "`n[2/7] 测试 Nginx 配置..." -ForegroundColor Yellow
try {
    $testResult = & "$NGINX_PATH\nginx.exe" -t 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Nginx 配置测试通过" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Nginx 配置测试失败：$testResult" -ForegroundColor Red
        Write-Host "  请检查 Nginx 配置文件" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "  ✗ 执行 Nginx 测试时出错：$_" -ForegroundColor Red
    exit 1
}

# 步骤 3: 重启 Nginx
Write-Host "`n[3/7] 重启 Nginx..." -ForegroundColor Yellow
try {
    & "$NGINX_PATH\nginx.exe" -s reload 2>&1
    Write-Host "  ✓ Nginx 重启成功" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Nginx 重启失败，可能未运行：$_" -ForegroundColor Yellow
    Write-Host "  尝试启动 Nginx..." -ForegroundColor Yellow
    Start-Process -FilePath "$NGINX_PATH\nginx.exe" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

# 步骤 4: 下载并安装 win-acme
Write-Host "`n[4/7] 下载 win-acme..." -ForegroundColor Yellow
$winAcmeZip = "$TEMP_DIR\win-acme.zip"
try {
    if (Test-Path "$WIN_ACME_DIR\wacs.exe") {
        Write-Host "  ✓ win-acme 已存在，跳过下载" -ForegroundColor Green
    } else {
        Write-Host "  正在下载 win-acme..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri $WIN_ACME_URL -OutFile $winAcmeZip -UseBasicParsing
        Write-Host "  ✓ 下载完成" -ForegroundColor Green
        
        Write-Host "  正在解压..." -ForegroundColor Cyan
        Expand-Archive -Path $winAcmeZip -DestinationPath $WIN_ACME_DIR -Force
        Write-Host "  ✓ 解压完成" -ForegroundColor Green
    }
} catch {
    Write-Host "  ⚠ win-acme 下载失败：$_" -ForegroundColor Red
    Write-Host "  请手动下载：$WIN_ACME_URL" -ForegroundColor Yellow
    Write-Host "  并解压到：$WIN_ACME_DIR" -ForegroundColor Yellow
    exit 1
}

# 步骤 5: 申请 Let's Encrypt 证书
Write-Host "`n[5/7] 申请 Let's Encrypt 证书..." -ForegroundColor Yellow
Write-Host "  域名：$DOMAIN, $WILDCARD_DOMAIN" -ForegroundColor Cyan

$certParams = @(
    "--target", "manual",
    "--host", "$DOMAIN,$WILDCARD_DOMAIN",
    "--webroot", $WEBROOT_DIR,
    "--store", "pemfiles",
    "--pemfilespath", $SSL_DIR,
    "--accepttos",
    "--verbose"
)

try {
    Write-Host "  正在运行 win-acme 申请证书..." -ForegroundColor Cyan
    $output = & "$WIN_ACME_DIR\wacs.exe" @certParams 2>&1
    
    # 检查是否成功
    if ($output -match "Successfully created certificate" -or $output -match "Renewal scheduled") {
        Write-Host "  ✓ 证书申请成功！" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ 证书申请可能遇到问题，请检查输出" -ForegroundColor Yellow
        Write-Host $output
    }
} catch {
    Write-Host "  ✗ 证书申请失败：$_" -ForegroundColor Red
    Write-Host "  请手动运行 win-acme:" -ForegroundColor Yellow
    Write-Host "  cd $WIN_ACME_DIR" -ForegroundColor Yellow
    Write-Host "  .\wacs.exe" -ForegroundColor Yellow
    exit 1
}

# 步骤 6: 验证证书文件
Write-Host "`n[6/7] 验证证书文件..." -ForegroundColor Yellow
$certFiles = @(
    "$SSL_DIR\fullchain.pem",
    "$SSL_DIR\privkey.pem"
)

$allExist = $true
foreach ($file in $certFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file 存在" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file 不存在" -ForegroundColor Red
        $allExist = $false
    }
}

if (-not $allExist) {
    Write-Host "`n  ✗ 证书文件不完整，请检查 win-acme 输出" -ForegroundColor Red
    exit 1
}

# 步骤 7: 更新 Nginx 配置启用 HTTPS
Write-Host "`n[7/7] 配置 HTTPS..." -ForegroundColor Yellow
Write-Host "  证书路径：" -ForegroundColor Cyan
Write-Host "    - fullchain.pem: $SSL_DIR\fullchain.pem" -ForegroundColor Gray
Write-Host "    - privkey.pem: $SSL_DIR\privkey.pem" -ForegroundColor Gray

# 提示用户确认
Write-Host "`n  ========================================" -ForegroundColor Cyan
Write-Host "  证书安装完成！" -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  下一步操作：" -ForegroundColor Yellow
Write-Host "  1. 检查 Nginx 配置中的证书路径是否正确" -ForegroundColor White
Write-Host "  2. 取消 HTTP 到 HTTPS 重定向的注释" -ForegroundColor White
Write-Host "  3. 重启 Nginx" -ForegroundColor White
Write-Host ""

$response = Read-Host "  是否现在启用 HTTPS 重定向？(y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host "`n  正在更新 Nginx 配置..." -ForegroundColor Cyan
    
    $nginxConfigPath = "D:\python_projects\weclaw_server\deployment\nginx\winclaw.conf"
    if (Test-Path $nginxConfigPath) {
        $config = Get-Content $nginxConfigPath -Raw
        
        # 取消 HTTPS 重定向注释
        $config = $config -replace '# if \(\$host = weclaw\.cc\) \{', 'if ($host = weclaw.cc) {'
        $config = $config -replace '#     return 301 https://\$host\$request_uri;', '    return 301 https://$host$request_uri;'
        $config = $config -replace '# \}', '}'
        $config = $config -replace '# if \(\$host ~ \^\(\.\+\)\\\.weclaw\\\.cc\$\) \{', 'if ($host ~ ^(.+)\.weclaw\.cc$) {'
        
        # 开启 HSTS
        $config = $config -replace '# add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;', 'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
        
        Save-Content -Path $nginxConfigPath -Value $config
        Write-Host "  ✓ Nginx 配置已更新" -ForegroundColor Green
        
        Write-Host "  正在重启 Nginx..." -ForegroundColor Cyan
        & "$NGINX_PATH\nginx.exe" -s reload
        Write-Host "  ✓ Nginx 已重启" -ForegroundColor Green
        
        Write-Host "`n  ========================================" -ForegroundColor Green
        Write-Host "  🎉 HTTPS 配置完成！" -ForegroundColor Green
        Write-Host "  ========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "  访问 https://$DOMAIN 测试" -ForegroundColor Cyan
    } else {
        Write-Host "  ✗ 未找到 Nginx 配置文件：$nginxConfigPath" -ForegroundColor Red
    }
}

Write-Host "`n  查看续期任务:" -ForegroundColor Yellow
Write-Host "  Get-ScheduledTask | Where-Object {`$_.TaskName -like '*win-acme*'}" -ForegroundColor Gray
Write-Host ""
Write-Host "  手动续期:" -ForegroundColor Yellow
Write-Host "  $WIN_ACME_DIR\wacs.exe --renew" -ForegroundColor Gray
Write-Host ""
