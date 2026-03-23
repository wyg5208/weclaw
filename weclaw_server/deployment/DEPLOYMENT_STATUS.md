# Let's Encrypt Certificate Deployment Status

## Current Status: Ready for Application

### Completed Steps

1. **Directory Structure Created** ✓
   - `D:\www\winclaw` - Web root for HTTP validation
   - `D:\www\winclaw\.well-known\acme-challenge` - Challenge directory
   - `D:\nginx\ssl\weclaw.cc` - Certificate storage

2. **win-acme Installed** ✓
   - Location: `D:\tools\win-acme`
   - Version: 2.2.8.1635
   - Status: Ready to use

3. **Nginx Configuration Updated** ✓
   - HTTP validation path configured
   - SSL certificate paths set
   - HSTS enabled

4. **Scripts Created** ✓
   - `one_click_deploy.ps1` - Automated deployment (needs DNS validation)
   - `apply_dns_cert.ps1` - DNS validation application
   - `check_cert_status.ps1` - Status verification

---

## Next Step: Apply for Certificate

### Option A: DNS Validation (Recommended)

Since Nginx is running on port 80, DNS validation is the easiest method.

**Steps:**

1. Run the DNS application script:
   ```powershell
   cd D:\python_projects\weclaw_server\deployment
   .\apply_dns_cert.ps1
   ```

2. win-acme will display a TXT record value like:
   ```
   Host: _acme-challenge.weclaw.cc
   Type: TXT
   Value: "abc123xyz..."
   ```

3. Add this TXT record to your DNS provider (e.g., Cloudflare, GoDaddy, etc.)

4. After adding the record, press Enter in the PowerShell window

5. win-acme will verify and issue the certificate

### Option B: Stop Nginx Temporarily

If you prefer HTTP validation:

1. Stop Nginx:
   ```powershell
   D:\nginx\nginx.exe -s stop
   ```

2. Run win-acme:
   ```powershell
   cd D:\tools\win-acme
   .\wacs.exe --target manual --host "weclaw.cc" --webroot "D:\www\winclaw" --accepttos
   ```

3. Start Nginx again:
   ```powershell
   D:\nginx\nginx.exe
   ```

---

## Verification After Application

Once the certificate is applied, run:

```powershell
.\check_cert_status.ps1
```

This will verify:
- Certificate files exist
- Certificate validity period
- Nginx configuration
- Auto-renewal task

---

## Expected Output

After successful application, you should see:

```
✓ fullchain.pem - X.XX KB
✓ privkey.pem - X.XX KB
✓ Certificate valid until: MM/DD/YYYY (XX days remaining)
✓ Nginx configuration test passed
✓ Renewal task scheduled
```

---

## Access Test

After deployment:
- HTTP: http://weclaw.cc (should redirect to HTTPS)
- HTTPS: https://weclaw.cc (should show secure connection)

---

## Troubleshooting

### Issue: DNS validation fails

**Solution:**
- Wait 1-2 minutes after adding DNS record (DNS propagation)
- Verify DNS record is correct using: `nslookup -type=TXT _acme-challenge.weclaw.cc`

### Issue: Certificate files not found

**Solution:**
- Check win-acme output for errors
- Verify folder permissions on `D:\nginx\ssl\weclaw.cc`

### Issue: Nginx won't reload

**Solution:**
- Test config: `D:\nginx\nginx.exe -t`
- Check error log: `Get-Content D:\nginx\logs\error.log -Tail 50`

---

## Manual Commands Reference

### Apply certificate (DNS validation):
```powershell
cd D:\tools\win-acme
.\wacs.exe --target manual --host "weclaw.cc" --validation dns-01 --emailaddress admin@weclaw.cc --accepttos
```

### Renew certificate manually:
```powershell
.\wacs.exe --renew
```

### View renewal tasks:
```powershell
Get-ScheduledTask | Where-Object {$_.TaskName -like "*win-acme*"}
```

### Check certificate details:
```powershell
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
$cert.Import("D:\nginx\ssl\weclaw.cc\fullchain.pem")
Write-Host "Subject: $($cert.Subject)"
Write-Host "Valid Until: $($cert.NotAfter)"
Write-Host "Days Remaining: $(($cert.NotAfter - (Get-Date)).Days)"
```

---

**Ready to proceed? Run:** `.\apply_dns_cert.ps1`
