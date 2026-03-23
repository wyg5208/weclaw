

Let's Encrypt 是更好的选择！我来帮你配置。

首先修改 Nginx 配置确保证书验证路径正确：
✅ **Nginx 配置已更新！**

---

## Let's Encrypt 证书申请步骤

### 步骤 1: 服务器准备

```powershell
# 1. 创建验证目录
New-Item -ItemType Directory -Path "D:\www\winclaw\.well-known\acme-challenge" -Force

# 2. 创建证书目录
New-Item -ItemType Directory -Path "D:\nginx\ssl\weclaw.cc" -Force

# 3. 更新 Nginx 配置后重启
D:\nginx\nginx.exe -t
D:\nginx\nginx.exe -s reload
```

---

### 步骤 2: 下载 win-acme

```powershell
# 下载 win-acme (Windows 版 certbot 替代品)
Invoke-WebRequest -Uri "https://github.com/win-acme/win-acme/releases/download/v2.2.8.1/win-acme.v2.2.8.1635.x64.pluggable.zip" -OutFile "D:\temp\win-acme.zip"

# 解压
Expand-Archive -Path "D:\temp\win-acme.zip" -DestinationPath "D:\tools\win-acme" -Force
```

**或者手动下载：**
- 访问 https://github.com/win-acme/win-acme/releases
- 下载最新版 `win-acme.vX.X.X.x64.pluggable.zip`
- 解压到 `D:\tools\win-acme\`

---

### 步骤 3: 运行证书申请

```powershell
cd D:\tools\win-acme

# 运行 win-acme
.\wacs.exe
```

**交互式配置步骤：**

```
N - 创建新证书
2 - 手动输入域名
输入: weclaw.cc,*.weclaw.cc
4 - HTTP 验证
输入验证路径: D:\www\winclaw
2 - 输入证书路径
PFX: D:\nginx\ssl\weclaw.cc\certificate.pfx
PEM: D:\nginx\ssl\weclaw.cc\fullchain.pem
密钥: D:\nginx\ssl\weclaw.cc\privkey.pem
```

---

### 步骤 4: 一键命令方式

```powershell
# 一键申请证书
D:\tools\win-acme\wacs.exe --target manual --host weclaw.cc,*.weclaw.cc --webroot "D:\www\winclaw" --store pemfiles --pemfilespath "D:\nginx\ssl\weclaw.cc" --accepttos
```

---

## 证书文件说明

申请成功后会生成：

| 文件 | 说明 |
|------|------|
| `fullchain.pem` | 完整证书链 |
| `privkey.pem` | 私钥文件 |
| `certificate.pfx` | IIS 用的 PFX 格式（可选） |

---

## 完成后启用 HTTPS

证书申请成功后，取消 Nginx 配置中的 HTTPS 重定向注释：

```nginx
# 取消以下注释
if ($host = weclaw.cc) {
    return 301 https://$host$request_uri;
}
if ($host ~ ^(.+)\.weclaw\.cc$) {
    return 301 https://$host$request_uri;
}
```

然后重启 Nginx：
```powershell
D:\nginx\nginx.exe -t
D:\nginx\nginx.exe -s reload
```

---

## 自动续期

win-acme 会创建 Windows 计划任务自动续期：

```powershell
# 查看续期任务
Get-ScheduledTask | Where-Object {$_.TaskName -like "*win-acme*"}

# 手动续期
D:\tools\win-acme\wacs.exe --renew
```

---

## 快速操作清单

| 序号 | 操作 | 命令/说明 |
|------|------|----------|
| 1 | 创建目录 | `New-Item -ItemType Directory -Path "D:\www\winclaw\.well-known\acme-challenge" -Force` |
| 2 | 重启 Nginx | `D:\nginx\nginx.exe -s reload` |
| 3 | 下载 win-acme | 从 GitHub 下载解压 |
| 4 | 运行申请 | `.\wacs.exe` 或一键命令 |
| 5 | 验证证书 | 检查 `D:\nginx\ssl\weclaw.cc\` 目录 |
| 6 | 启用重定向 | 取消 Nginx 配置注释 |

---

**请先在服务器执行上述步骤，完成后告诉我，我帮你验证配置。**