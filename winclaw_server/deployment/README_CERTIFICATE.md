# WinClaw Let's Encrypt 证书部署指南

本目录包含完整的 Let's Encrypt 证书申请、安装和部署工具。

---

## 📦 文件说明

| 文件名 | 说明 |
|--------|------|
| `quick_install_cert.ps1` | **推荐使用** - 快速安装脚本，一键完成证书申请 |
| `install_letsencrypt_cert.ps1` | 完整安装脚本，包含更多自动化选项 |
| `check_cert_status.ps1` | 证书状态检查工具，用于验证和维护 |
| `letsencrypt_deploy.md` | 详细部署文档 |

---

## 🚀 快速开始

### 方式一：自动安装（推荐）

以**管理员身份**运行 PowerShell，执行：

```powershell
cd D:\python_projects\winclaw_server\deployment
.\quick_install_cert.ps1
```

脚本会自动完成：
1. ✅ 创建必要的目录结构
2. ✅ 重启 Nginx
3. ✅ 下载并安装 win-acme
4. ✅ 申请 Let's Encrypt 证书（weclaw.cc, *.weclaw.cc）
5. ✅ 验证证书文件
6. ✅ 提供后续配置指引

### 方式二：手动安装

按照 `letsencrypt_deploy.md` 文档逐步操作。

---

## 📋 前置要求

1. **服务器要求**
   - Windows Server 2016 或更高版本
   - Nginx 已安装（路径：`D:\nginx`）
   - 域名已解析到服务器 IP（weclaw.cc, *.weclaw.cc）

2. **端口要求**
   - 80 端口开放（用于 HTTP 验证）
   - 443 端口开放（用于 HTTPS）

3. **权限要求**
   - 管理员权限运行 PowerShell
   - 对 Nginx 目录有写入权限

---

## 🔧 使用工具

### 1. 申请证书

```powershell
# 快速安装
.\quick_install_cert.ps1

# 或完整安装
.\install_letsencrypt_cert.ps1
```

### 2. 检查证书状态

```powershell
.\check_cert_status.ps1
```

此脚本会检查：
- ✓ 证书文件是否存在
- ✓ 证书有效期
- ✓ Nginx 配置状态
- ✓ Nginx 运行状态
- ✓ win-acme 安装状态
- ✓ 自动续期任务状态

### 3. 手动续期证书

Let's Encrypt 证书有效期为 90 天，win-acme 会自动续期。如需手动续期：

```powershell
D:\tools\win-acme\wacs.exe --renew
```

### 4. 重新申请证书

```powershell
D:\tools\win-acme\wacs.exe --target manual --host "weclaw.cc,*.weclaw.cc" --webroot "D:\www\winclaw" --store pemfiles --pemfilespath "D:\nginx\ssl\weclaw.cc" --accepttos
```

---

## ⚙️ 配置 HTTPS

证书申请成功后，需要启用 HTTPS 重定向：

### 步骤 1：编辑 Nginx 配置文件

打开 `deployment/nginx/winclaw.conf`

### 步骤 2：取消注释（在 HTTP server 块中）

找到以下代码段并取消注释：

```nginx
# 取消这两行的注释
if ($host = weclaw.cc) {
    return 301 https://$host$request_uri;
}
if ($host ~ ^(.+)\.weclaw\.cc$) {
    return 301 https://$host$request_uri;
}
```

### 步骤 3：开启 HSTS（建议）

在 HTTPS server 块中添加：

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 步骤 4：测试并重启 Nginx

```powershell
D:\nginx\nginx.exe -t
D:\nginx\nginx.exe -s reload
```

---

## 📁 目录结构

```
D:/
├── www/
│   └── winclaw/              # Web 根目录（HTTP 验证用）
│       └── .well-known/
│           └── acme-challenge/
│
├── nginx/
│   ├── ssl/
│   │   └── weclaw.cc/        # 证书目录
│   │       ├── fullchain.pem # 完整证书链
│   │       ├── privkey.pem   # 私钥
│   │       └── certificate.pfx # PFX 格式（可选）
│   └── nginx.exe             # Nginx 主程序
│
└── tools/
    └── win-acme/             # win-acme 工具
        ├── wacs.exe          # 主程序
        └── ...
```

---

## 🔍 故障排查

### 问题 1：证书申请失败

**可能原因：**
- 80 端口未开放
- 域名未正确解析
- 防火墙阻止 HTTP 访问

**解决方法：**
```powershell
# 检查 80 端口
netstat -ano | findstr :80

# 检查域名解析
nslookup weclaw.cc

# 临时关闭防火墙测试
Set-NetFirewallProfile -Enabled False
```

### 问题 2：Nginx 启动失败

**可能原因：**
- 证书路径错误
- 配置文件语法错误
- 端口被占用

**解决方法：**
```powershell
# 测试配置
D:\nginx\nginx.exe -t

# 查看错误日志
Get-Content D:\nginx\logs\error.log -Tail 50
```

### 问题 3：HTTPS 无法访问

**检查清单：**
- [ ] 证书文件存在且有效
- [ ] Nginx 配置中的证书路径正确
- [ ] 443 端口开放
- [ ] Nginx 正在运行

```powershell
# 检查 443 端口
netstat -ano | findstr :443

# 检查 Nginx 进程
Get-Process nginx
```

---

## 🔄 自动续期

win-acme 会自动创建 Windows 计划任务进行续期：

### 查看续期任务

```powershell
Get-ScheduledTask | Where-Object {$_.TaskName -like "*win-acme*"}
```

### 查看任务详情

```powershell
Get-ScheduledTaskInfo -TaskName "<任务名称>"
```

### 手动触发续期

```powershell
D:\tools\win-acme\wacs.exe --renew
```

---

## 📊 证书信息

- **颁发机构**: Let's Encrypt
- **有效期**: 90 天
- **续期**: 到期前 30 天自动续期
- **支持域名**: 
  - weclaw.cc
  - *.weclaw.cc (通配符)

---

## 🔗 相关资源

- [win-acme 官方文档](https://www.win-acme.com/)
- [Let's Encrypt 官网](https://letsencrypt.org/)
- [Nginx SSL 配置指南](https://nginx.org/en/docs/http/configuring_https_servers.html)

---

## 💡 最佳实践

1. **定期检查证书状态**
   ```powershell
   .\check_cert_status.ps1
   ```

2. **监控续期任务**
   确保 Windows 计划任务正常运行

3. **备份证书**
   定期备份 `D:\nginx\ssl\weclaw.cc\` 目录

4. **测试环境先验证**
   在正式部署前，先在测试环境验证配置

5. **开启 HSTS**
   确保证书稳定后开启 HSTS 增强安全性

---

## 🆘 获取帮助

如遇到问题：
1. 运行 `check_cert_status.ps1` 诊断问题
2. 查看 Nginx 错误日志
3. 查看 win-acme 日志（在 `D:\tools\win-acme\Log`）

---

**最后更新**: 2026-02-22  
**适用版本**: Windows Server 2016+
