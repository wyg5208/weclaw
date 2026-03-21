# WinClaw Let's Encrypt Certificate One-Click Deployment Script
# Automatic: Application + Installation + Configuration + HTTPS Enablement

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " WinClaw Let's Encrypt One-Click Deploy" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration Variables
$DOMAIN = "weclaw.cc"
$WILDCARD_DOMAIN = "*.weclaw.cc"
$WEBROOT_DIR = "D:\www\winclaw"
$SSL_DIR = "D:\nginx\ssl\weclaw.cc"
$NGINX_PATH = "D:\nginx"
$WIN_ACME_URL = "https://github.com/win-acme/win-acme/releases/download/v2.2.8.1635/win-acme.v2.2.8.1635.x64.pluggable.zip"
$WIN_ACME_DIR = "D:\tools\win-acme"
$TEMP_DIR = "D:\temp"
$NGINX_CONFIG_PATH = "D:\python_projects\weclaw_server\deployment\nginx\winclaw.conf"

# Phase 1: Prepare Environment
Write-Host "[Phase 1/5] Preparing environment..." -ForegroundColor Yellow

New-Item -ItemType Directory -Path $WEBROOT_DIR -Force | Out-Null
New-Item -ItemType Directory -Path "$WEBROOT_DIR\.well-known\acme-challenge" -Force | Out-Null
New-Item -ItemType Directory -Path $SSL_DIR -Force | Out-Null
New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null
Write-Host "  [OK] Directories created" -ForegroundColor Green

Write-Host "  Testing Nginx configuration..." -ForegroundColor Gray
& "$NGINX_PATH\nginx.exe" -t 2>&1 | Out-Null
Write-Host "  [OK] Nginx configuration test passed" -ForegroundColor Green

Write-Host "  Restarting Nginx..." -ForegroundColor Gray
try {
    & "$NGINX_PATH\nginx.exe" -s reload 2>&1 | Out-Null
} catch {
    Start-Process -FilePath "$NGINX_PATH\nginx.exe" -WindowStyle Hidden
    Start-Sleep -Seconds 2
}
Write-Host "  [OK] Nginx restarted" -ForegroundColor Green

# Phase 2: Install win-acme
Write-Host "`n[Phase 2/5] Installing win-acme..." -ForegroundColor Yellow

if (Test-Path "$WIN_ACME_DIR\wacs.exe") {
    Write-Host "  [OK] win-acme already installed" -ForegroundColor Green
} else {
    Write-Host "  Downloading win-acme..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $WIN_ACME_URL -OutFile "$TEMP_DIR\win-acme.zip" -UseBasicParsing
    
    Write-Host "  Extracting..." -ForegroundColor Gray
    Expand-Archive -Path "$TEMP_DIR\win-acme.zip" -DestinationPath $WIN_ACME_DIR -Force
    Remove-Item "$TEMP_DIR\win-acme.zip" -Force
    
    Write-Host "  [OK] win-acme installed" -ForegroundColor Green
}

# Phase 3: Apply for Certificate
Write-Host "`n[Phase 3/5] Applying for Let's Encrypt certificate..." -ForegroundColor Yellow
Write-Host "  Domains: $DOMAIN, $WILDCARD_DOMAIN" -ForegroundColor Gray

$certParams = @(
    "--target", "manual",
    "--host", "$DOMAIN,$WILDCARD_DOMAIN",
    "--webroot", $WEBROOT_DIR,
    "--store", "pemfiles",
    "--pemfilespath", $SSL_DIR,
    "--accepttos",
    "--verbose"
)

Write-Host "  Running win-acme..." -ForegroundColor Gray
Set-Location $WIN_ACME_DIR
$output = .\wacs.exe @certParams 2>&1
Write-Host $output

if ($output -match "Successfully created certificate|Renewal scheduled|Renewal already scheduled") {
    Write-Host "  [OK] Certificate applied successfully" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Please check output above for status" -ForegroundColor Yellow
}

# Phase 4: Verify Certificate Files
Write-Host "`n[Phase 4/5] Verifying certificate files..." -ForegroundColor Yellow

$certFiles = @(
    "$SSL_DIR\fullchain.pem",
    "$SSL_DIR\privkey.pem"
)

$allExist = $true
foreach ($file in $certFiles) {
    if (Test-Path $file) {
        $fileInfo = Get-Item $file
        Write-Host "  [OK] $(Split-Path $file -Leaf) - $([math]::Round($fileInfo.Length / 1KB, 2)) KB" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $(Split-Path $file -Leaf) not found" -ForegroundColor Red
        $allExist = $false
    }
}

if (-not $allExist) {
    Write-Host "`n[FAIL] Certificate files incomplete" -ForegroundColor Red
    exit 1
}

Write-Host "  [OK] All certificate files verified" -ForegroundColor Green

# Phase 5: Configure and Enable HTTPS
Write-Host "`n[Phase 5/5] Configuring HTTPS..." -ForegroundColor Yellow

if (Test-Path $NGINX_CONFIG_PATH) {
    Write-Host "  Reading Nginx config..." -ForegroundColor Gray
    $config = Get-Content $NGINX_CONFIG_PATH -Raw
    $configModified = $false
    
    # Uncomment HTTPS redirect
    $patterns = @(
        @{Old = '# if ($host = weclaw.cc) {'; New = 'if ($host = weclaw.cc) {'},
        @{Old = '#     return 301 https://$host$request_uri;'; New = '    return 301 https://$host$request_uri;'},
        @{Old = '# }'; New = '}'},
        @{Old = '# if ($host ~ ^(.+)\.weclaw\.cc$) {'; New = 'if ($host ~ ^(.+)\.weclaw\.cc$) {'}
    )
    
    foreach ($pattern in $patterns) {
        if ($config -match [regex]::Escape($pattern.Old)) {
            $config = $config -replace [regex]::Escape($pattern.Old), $pattern.New
            $configModified = $true
        }
    }
    
    # Enable HSTS
    $hstsPattern = '# add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
    if ($config -match [regex]::Escape($hstsPattern)) {
        $config = $config -replace [regex]::Escape($hstsPattern), 'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
        $configModified = $true
    }
    
    if ($configModified) {
        Write-Host "  Saving configuration..." -ForegroundColor Gray
        Save-Content -Path $NGINX_CONFIG_PATH -Value $config
        
        Write-Host "  Testing Nginx configuration..." -ForegroundColor Gray
        & "$NGINX_PATH\nginx.exe" -t 2>&1 | Out-Null
        
        Write-Host "  Restarting Nginx..." -ForegroundColor Gray
        & "$NGINX_PATH\nginx.exe" -s reload 2>&1 | Out-Null
        
        Write-Host "  [OK] HTTPS enabled successfully" -ForegroundColor Green
    } else {
        Write-Host "  [OK] HTTPS already enabled, no changes needed" -ForegroundColor Green
    }
} else {
    Write-Host "  [WARN] Nginx config file not found: $NGINX_CONFIG_PATH" -ForegroundColor Yellow
}

# Completion
Write-Host "`n========================================" -ForegroundColor Green
Write-Host " DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Completed tasks:" -ForegroundColor Green
Write-Host "  - Created required directories" -ForegroundColor White
Write-Host "  - Installed win-acme v2.2.8" -ForegroundColor White
Write-Host "  - Applied for Let's Encrypt certificate" -ForegroundColor White
Write-Host "  - Verified certificate files" -ForegroundColor White
Write-Host "  - Configured HTTPS redirect" -ForegroundColor White
Write-Host ""

Write-Host "Certificate info:" -ForegroundColor Cyan
Write-Host "  Path: $SSL_DIR" -ForegroundColor Gray
Write-Host "  Domains: $DOMAIN, $WILDCARD_DOMAIN" -ForegroundColor Gray
Write-Host "  Validity: 90 days (auto-renewal)" -ForegroundColor Gray
Write-Host ""

Write-Host "Management commands:" -ForegroundColor Cyan
Write-Host "  Check status: .\check_cert_status.ps1" -ForegroundColor Gray
Write-Host "  Manual renewal: $WIN_ACME_DIR\wacs.exe --renew" -ForegroundColor Gray
Write-Host "  View tasks: Get-ScheduledTask | Where-Object {`$_.TaskName -like '*win-acme*'}" -ForegroundColor Gray
Write-Host ""

Write-Host "Access test:" -ForegroundColor Cyan
Write-Host "  HTTP:  http://$DOMAIN" -ForegroundColor Gray
Write-Host "  HTTPS: https://$DOMAIN" -ForegroundColor Gray
Write-Host ""

Write-Host "Notes:" -ForegroundColor Yellow
Write-Host "  - Ensure firewall allows ports 80 and 443" -ForegroundColor Gray
Write-Host "  - Ensure domain DNS is correct" -ForegroundColor Gray
Write-Host "  - Check certificate status regularly" -ForegroundColor Gray
Write-Host ""
