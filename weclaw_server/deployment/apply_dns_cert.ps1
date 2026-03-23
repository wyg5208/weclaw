# Apply Certificate Using DNS Validation
# This works even with Nginx running on port 80

$ErrorActionPreference = "Stop"
$DOMAIN = "weclaw.cc"
$SSL_DIR = "D:\nginx\ssl\weclaw.cc"
$WIN_ACME = "D:\tools\win-acme"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Certificate Application via DNS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Domain: $DOMAIN" -ForegroundColor White
Write-Host "Method: DNS-01 Validation" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: You need to add a TXT record to your DNS" -ForegroundColor Yellow
Write-Host ""

# Run win-acme with DNS validation
Set-Location $WIN_ACME
Write-Host "Starting win-acme..." -ForegroundColor Gray
Write-Host "(It will pause and ask you to create DNS record)" -ForegroundColor Yellow
Write-Host ""

.\wacs.exe --target manual --host $DOMAIN --validation dns-01 --emailaddress admin@weclaw.cc --accepttos --verbose

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Application Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
