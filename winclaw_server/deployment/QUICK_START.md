# 🚀 Let's Encrypt 证书部署 - 快速开始

## ✅ 已创建的文件

| 文件 | 用途 | 推荐度 |
|------|------|--------|
| `one_click_deploy.ps1` | **一键部署** - 自动完成所有步骤 | ⭐⭐⭐⭐⭐ |
| `quick_install_cert.ps1` | 快速安装 - 分步执行更清晰 | ⭐⭐⭐⭐ |
| `check_cert_status.ps1` | 状态检查 - 验证证书和配置 | ⭐⭐⭐⭐⭐ |
| `install_letsencrypt_cert.ps1` | 完整安装 - 包含更多选项 | ⭐⭐⭐ |
| `README_CERTIFICATE.md` | 详细文档 - 完整使用说明 | ⭐⭐⭐⭐ |

---

## 🎯 最简单的部署方式（3 分钟完成）

### 步骤 1：以管理员身份打开 PowerShell

右键点击"Windows PowerShell"，选择"**以管理员身份运行**"

### 步骤 2：执行一键部署脚本

```powershell
cd D:\python_projects\winclaw_server\deployment
.\one_click_deploy.ps1
```

### 步骤 3：等待完成

脚本会自动完成：
- ✅ 创建目录结构
- ✅ 下载 win-acme 工具
- ✅ 申请 Let's Encrypt 证书
- ✅ 配置 Nginx HTTPS
- ✅ 启用 HTTP→HTTPS 重定向
- ✅ 开启 HSTS 安全策略

### 步骤 4：访问测试

打开浏览器访问：
- https://weclaw.cc
- https://www.weclaw.cc

看到锁标志表示成功！🎉

---

## 📋 详细部署方式（如需更多控制）

### 方式 A：使用快速安装脚本

```powershell
.\quick_install_cert.ps1
```

这个脚本会逐步显示进度，并在完成后给出详细的后续操作指引。

### 方式 B：完全手动操作

按照 `letsencrypt_deploy.md` 文档的详细说明逐步执行。

---

## 🔍 验证部署

### 检查证书状态

```powershell
.\check_cert_status.ps1
```

这个脚本会检查：
- ✓ 证书文件是否存在
- ✓ 证书有效期（剩余天数）
- ✓ Nginx 配置是否正确
- ✓ Nginx 是否正在运行
- ✓ win-acme 是否安装
- ✓ 自动续期任务是否正常

### 在线验证

访问以下网站验证 SSL 配置：
- https://www.ssllabs.com/ssltest/
- https://cryptographur.com/ssl-checker

---

## 🔄 证书管理

### 查看证书信息

```powershell
# 查看证书详情
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
$cert.Import("D:\nginx\ssl\weclaw.cc\fullchain.pem")
Write-Host "颁发给：$($cert.Subject)"
Write-Host "有效期至：$($cert.NotAfter)"
Write-Host "剩余天数：$(($cert.NotAfter - (Get-Date)).Days)"
```

### 手动续期证书

```powershell
D:\tools\win-acme\wacs.exe --renew
```

### 查看自动续期任务

```powershell
Get-ScheduledTask | Where-Object {$_.TaskName -like "*win-acme*"}
```

### 重新申请证书

```powershell
D:\tools\win-acme\wacs.exe --target manual --host "weclaw.cc,*.weclaw.cc" --webroot "D:\www\winclaw" --store pemfiles --pemfilespath "D:\nginx\ssl\weclaw.cc" --accepttos
```

---

## 🛠️ 故障排查

### 问题 1：80 端口无法访问

**症状：** 证书申请失败，提示 HTTP 验证失败

**解决：**
```powershell
# 检查防火墙
netsh advfirewall firewall show rule name=all | findstr "80"

# 临时关闭防火墙测试
Set-NetFirewallProfile -Enabled False

# 检查端口占用
netstat -ano | findstr :80
```

### 问题 2：域名解析不正确

**症状：** 证书申请超时

**解决：**
```powershell
# 检查 DNS 解析
nslookup weclaw.cc
nslookup www.weclaw.cc

# 应该返回你的服务器 IP
```

### 问题 3：Nginx 启动失败

**症状：** 配置修改后 Nginx 无法重启

**解决：**
```powershell
# 测试配置
D:\nginx\nginx.exe -t

# 查看错误日志
Get-Content D:\nginx\logs\error.log -Tail 50

# 回滚配置（如果有备份）
# 或检查证书路径是否正确
```

### 问题 4：HTTPS 无法访问但 HTTP 正常

**症状：** http://weclaw.cc 可以访问，https://weclaw.cc 无法访问

**检查清单：**
- [ ] 证书文件存在
- [ ] Nginx 配置的证书路径正确
- [ ] 443 端口开放
- [ ] Nginx 正在运行

```powershell
# 检查 443 端口
netstat -ano | findstr :443

# 检查 Nginx 进程
Get-Process nginx

# 检查证书路径
Test-Path "D:\nginx\ssl\weclaw.cc\fullchain.pem"
Test-Path "D:\nginx\ssl\weclaw.cc\privkey.pem"
```

---

## 📊 证书信息摘要

| 项目 | 值 |
|------|-----|
| 颁发机构 | Let's Encrypt |
| 证书类型 | DV SSL/TLS |
| 支持域名 | weclaw.cc, *.weclaw.cc |
| 有效期 | 90 天 |
| 自动续期 | 到期前 30 天 |
| 加密算法 | RSA 2048 位 |
| 签名算法 | SHA-256 |

---

## 🔐 安全建议

### 1. 开启 HSTS（已自动开启）

已在 Nginx 配置中启用：
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 2. 定期检查更新

```powershell
# 检查 win-acme 版本
D:\tools\win-acme\wacs.exe --version

# 检查 Nginx 版本
D:\nginx\nginx.exe -v
```

### 3. 监控证书到期时间

设置提醒在证书到期前 15 天检查：
```powershell
# 添加到每日任务
$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2
$cert.Import("D:\nginx\ssl\weclaw.cc\fullchain.pem")
$daysLeft = ($cert.NotAfter - (Get-Date)).Days
if ($daysLeft -lt 15) {
    Write-Warning "证书将在 $daysLeft 天后过期！"
}
```

### 4. 备份证书

```powershell
# 定期备份证书
$backupDir = "D:\backup\ssl\$(Get-Date -Format 'yyyyMMdd')"
New-Item -ItemType Directory -Path $backupDir -Force
Copy-Item "D:\nginx\ssl\weclaw.cc\*" $backupDir
```

---

## 📞 获取帮助

### 日志位置

- **win-acme 日志**: `D:\tools\win-acme\Log\`
- **Nginx 访问日志**: `D:\nginx\logs\winclaw_*_access.log`
- **Nginx 错误日志**: `D:\nginx\logs\winclaw_*_error.log`

### 有用的命令

```powershell
# 查看 win-acme 日志
Get-ChildItem "D:\tools\win-acme\Log\" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content

# 查看最近的 Nginx 错误
Get-Content "D:\nginx\logs\winclaw_https_error.log" -Tail 50

# 查看计划任务历史
Get-ScheduledTaskInfo -TaskName "<win-acme 任务名>"
```

---

## ✨ 成功标志

部署成功后，你应该能看到：

✅ 浏览器地址栏有锁标志  
✅ HTTPS 协议显示  
✅ 证书信息显示 weclaw.cc  
✅ 无安全警告  
✅ HTTP 自动跳转到 HTTPS  

---

**祝你部署顺利！** 🎉

如有问题，请查看 `README_CERTIFICATE.md` 获取详细文档。
