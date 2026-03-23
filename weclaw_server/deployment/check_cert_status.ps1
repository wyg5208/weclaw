# WeClaw 证书状态检查脚本
# 用于验证 Let's Encrypt 证书安装和运行状态

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " WeClaw 证书状态检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$SSL_DIR = "D:\nginx\ssl\weclaw.cc"
$NGINX_PATH = "D:\nginx"
$WIN_ACME_DIR = "D:\tools\win-acme"

# ========== 1. 检查证书文件 ==========
Write-Host "[1/6] 检查证书文件..." -ForegroundColor Yellow
$certFiles = @(
    @{Path = "$SSL_DIR\fullchain.pem"; Name = "完整证书链"},
    @{Path = "$SSL_DIR\privkey.pem"; Name = "私钥"},
    @{Path = "$SSL_DIR\certificate.pfx"; Name = "PFX 证书 (可选)"}
)

foreach ($cert in $certFiles) {
    if (Test-Path $cert.Path) {
        $fileInfo = Get-Item $cert.Path
        Write-Host "  ✓ $($cert.Name): $($cert.Path)" -ForegroundColor Green
        Write-Host "    大小：$([math]::Round($fileInfo.Length / 1KB, 2)) KB | 修改时间：$($fileInfo.LastWriteTime)" -ForegroundColor Gray
    } else {
        if ($cert.Name -eq "PFX 证书 (可选)") {
            Write-Host "  ⚠ $($cert.Name): 不存在（可选）" -ForegroundColor Yellow
        } else {
            Write-Host "  ✗ $($cert.Name): 不存在" -ForegroundColor Red
        }
    }
}
Write-Host ""

# ========== 2. 检查证书有效期 ==========
Write-Host "[2/6] 检查证书有效期..." -ForegroundColor Yellow
if (Test-Path "$SSL_DIR\fullchain.pem") {
    try {
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
        $cert.Import("$SSL_DIR\fullchain.pem")
        
        Write-Host "  颁发给：$($cert.Subject)" -ForegroundColor Cyan
        Write-Host "  颁发者：$($cert.Issuer)" -ForegroundColor Cyan
        Write-Host "  有效期：$($cert.NotBefore) 至 $($cert.NotAfter)" -ForegroundColor Cyan
        
        $daysLeft = ($cert.NotAfter - (Get-Date)).Days
        if ($daysLeft -gt 30) {
            Write-Host "  ✓ 证书还有 $daysLeft 天过期" -ForegroundColor Green
        } elseif ($daysLeft -gt 7) {
            Write-Host "  ⚠ 证书还有 $daysLeft 天过期，建议尽快续期" -ForegroundColor Yellow
        } else {
            Write-Host "  ✗ 证书将在 $daysLeft 天内过期，请立即续期！" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ⚠ 无法读取证书详情：$_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ 证书文件不存在，无法检查" -ForegroundColor Red
}
Write-Host ""

# ========== 3. 检查 Nginx 配置 ==========
Write-Host "[3/6] 检查 Nginx 配置..." -ForegroundColor Yellow
try {
    $testResult = & $NGINX_PATH\nginx.exe -t 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Nginx 配置测试通过" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Nginx 配置测试失败：$testResult" -ForegroundColor Red
    }
} catch {
    Write-Host "  ✗ 执行 Nginx 测试时出错：$_" -ForegroundColor Red
}
Write-Host ""

# ========== 4. 检查 Nginx 运行状态 ==========
Write-Host "[4/6] 检查 Nginx 运行状态..." -ForegroundColor Yellow
$nginxProcess = Get-Process nginx -ErrorAction SilentlyContinue
if ($nginxProcess) {
    Write-Host "  ✓ Nginx 正在运行 (PID: $($nginxProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "  ✗ Nginx 未运行" -ForegroundColor Red
}
Write-Host ""

# ========== 5. 检查 win-acme 安装 ==========
Write-Host "[5/6] 检查 win-acme 安装..." -ForegroundColor Yellow
if (Test-Path "$WIN_ACME_DIR\wacs.exe") {
    Write-Host "  ✓ win-acme 已安装：$WIN_ACME_DIR" -ForegroundColor Green
    
    # 检查版本
    try {
        $version = & "$WIN_ACME_DIR\wacs.exe" --version 2>&1
        Write-Host "  版本：$version" -ForegroundColor Gray
    } catch {
        Write-Host "  ⚠ 无法获取版本信息" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ win-acme 未安装" -ForegroundColor Red
    Write-Host "  请运行：deployment/quick_install_cert.ps1" -ForegroundColor Yellow
}
Write-Host ""

# ========== 6. 检查自动续期任务 ==========
Write-Host "[6/6] 检查自动续期任务..." -ForegroundColor Yellow
try {
    $renewalTasks = Get-ScheduledTask | Where-Object {$_.TaskName -like "*win-acme*"}
    
    if ($renewalTasks) {
        foreach ($task in $renewalTasks) {
            $taskInfo = Get-ScheduledTaskInfo -TaskName $task.TaskName
            Write-Host "  ✓ 任务：$($task.TaskName)" -ForegroundColor Green
            Write-Host "    状态：$($task.State)" -ForegroundColor Gray
            Write-Host "    上次运行：$($taskInfo.LastRunTime)" -ForegroundColor Gray
            Write-Host "    下次运行：$($taskInfo.NextRunTime)" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ⚠ 未找到 win-acme 续期任务" -ForegroundColor Yellow
        Write-Host "  win-acme 通常会在首次申请证书时自动创建计划任务" -ForegroundColor Gray
    }
} catch {
    Write-Host "  ⚠ 无法检查计划任务：$_" -ForegroundColor Yellow
}
Write-Host ""

# ========== 总结 ==========
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  检查完成" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 快速操作提示
Write-Host "快速操作：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 手动续期证书:" -ForegroundColor White
Write-Host "   D:\tools\win-acme\wacs.exe --renew" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 重新申请证书:" -ForegroundColor White
Write-Host "   D:\tools\win-acme\wacs.exe --target manual --host `"weclaw.cc,*.weclaw.cc`" --webroot `"D:\www\weclaw`" --store pemfiles --pemfilespath `"D:\nginx\ssl\weclaw.cc`" --accepttos" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 重启 Nginx:" -ForegroundColor White
Write-Host "   D:\nginx\nginx.exe -s reload" -ForegroundColor Gray
Write-Host ""
Write-Host "4. 查看 Nginx 日志:" -ForegroundColor White
Write-Host "   Get-Content D:\nginx\logs\weclaw_https_error.log -Tail 50" -ForegroundColor Gray
Write-Host ""
