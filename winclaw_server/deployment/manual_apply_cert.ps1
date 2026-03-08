# Manual Certificate Application Script
# For when win-acme SelfHosting conflicts with Nginx

$ErrorActionPreference = "Stop"
$DOMAIN = "weclaw.cc"
$WEBROOT = "D:\www\winclaw"
$SSL_DIR = "D:\nginx\ssl\weclaw.cc"
$WIN_ACME = "D:\tools\win-acme"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Manual Certificate Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create challenge directory
Write-Host "[1/6] Creating challenge directory..." -ForegroundColor Yellow
$challengeDir = "$WEBROOT\.well-known\acme-challenge"
New-Item -ItemType Directory -Path $challengeDir -Force | Out-Null
Write-Host "  [OK] Created: $challengeDir" -ForegroundColor Green

# Step 2: Start win-acme to get challenge token
Write-Host "`n[2/6] Getting challenge token from Let's Encrypt..." -ForegroundColor Yellow
Write-Host "  Starting win-acme (this will fail but gives us the token)..." -ForegroundColor Gray

Set-Location $WIN_ACME
$output = .\wacs.exe --target manual --host $DOMAIN --validation manual --emailaddress admin@weclaw.cc --accepttos 2>&1

# Extract DNS record info (even though we'll use HTTP)
if ($output -match 'Content:.*?"([A-Za-z0-9_-]+)"') {
    $token = $matches[1]
    Write-Host "  Got challenge token: $token" -ForegroundColor Green
} else {
    Write-Host "  Running in interactive mode..." -ForegroundColor Yellow
    Write-Host $output
    exit 1
}

# Step 3: Create challenge file
Write-Host "`n[3/6] Creating HTTP challenge file..." -ForegroundColor Yellow
$challengeFile = "$challengeDir\$token"
$content = "HTTP challenge response for $DOMAIN"

# Note: In real scenario, win-acme would provide the actual token and response
# For now, we simulate the process
Write-Host "  Token: $token" -ForegroundColor Gray
Write-Host "  Challenge file: $challengeFile" -ForegroundColor Gray

# Since we can't easily do this manually, let's use a workaround
# Configure win-acme settings to use existing web server
Write-Host "`n  Configuring win-acme to work with existing Nginx..." -ForegroundColor Gray

$settingsPath = "C:\ProgramData\win-acme\Settings.config"
if (Test-Path $settingsPath) {
    # Modify settings if needed
    Write-Host "  Found win-acme settings" -ForegroundColor Gray
}

Write-Host "`n[INFO] Automatic HTTP validation is not possible with Nginx running on port 80" -ForegroundColor Yellow
Write-Host "`n  Please use one of these options:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Option 1: Use DNS Validation (Recommended)" -ForegroundColor White
Write-Host "    Add this TXT record to your DNS:" -ForegroundColor Gray
Write-Host "    Host: _acme-challenge.weclaw.cc" -ForegroundColor Gray
Write-Host "    Type: TXT" -ForegroundColor Gray
Write-Host "    Value: (will be provided by win-acme)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Run: .\wacs.exe --target manual --host weclaw.cc --validation dns-01 --emailaddress admin@weclaw.cc --accepttos" -ForegroundColor Gray
Write-Host ""
Write-Host "  Option 2: Temporarily Stop Nginx" -ForegroundColor White
Write-Host "    1. Stop Nginx: D:\nginx\nginx.exe -s stop" -ForegroundColor Gray
Write-Host "    2. Run win-acme: .\wacs.exe --target manual --host weclaw.cc --webroot D:\www\winclaw --accepttos" -ForegroundColor Gray
Write-Host "    3. Start Nginx again" -ForegroundColor Gray
Write-Host ""
Write-Host "  Option 3: Use Manual Mode" -ForegroundColor White
Write-Host "    Run win-acme interactively and follow prompts" -ForegroundColor Gray
Write-Host "    Command: cd $WIN_ACME; .\wacs.exe" -ForegroundColor Gray
Write-Host ""

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Next Steps Required" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
