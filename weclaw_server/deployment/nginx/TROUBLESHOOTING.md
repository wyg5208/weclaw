# WinClaw 缓存问题完整排查指南

## 🔍 可能存在的缓存层级

### 1️⃣ Nginx 服务器端缓存
- ✗ **已解决**：注释了 ws.madechango.com 的整个 server 块
- ✅ 当前配置：weclaw.cc 使用独立的 HTTPS server 块

### 2️⃣ PWA Service Worker 缓存
- ⚠️ **需要注意**：Service Worker 会缓存静态资源
- 📋 缓存策略：
  - JS/CSS 文件：版本化文件名（自动更新）
  - 图片资源：CacheFirst（7 天）
  - API 请求：NetworkFirst（5 分钟）

### 3️⃣ 浏览器 HTTP 缓存
- ⚠️ **需要注意**：浏览器会缓存 HTML、CSS、JS
- 📋 缓存控制：
  - HTML: no-cache, no-store
  - Assets: 长期缓存（带 hash 的文件名）

### 4️⃣ DNS 缓存
- ⚠️ **可能影响**：如果域名解析记录改变
- ⏱️ 缓存时间：通常 5-30 分钟

### 5️⃣ CDN 缓存（如果使用）
- ⚠️ **可能影响**：CDN 节点缓存
- 🔧 解决：刷新 CDN 缓存或等待过期

---

## 🛠️ 完整清理步骤（按顺序执行）

### 第一步：运行自动化脚本
```powershell
d:\python_projects\weclaw_server\deployment\nginx\full_cache_clean.ps1
```

这个脚本会：
1. ✅ 重新编译 PWA（生成新的 Service Worker）
2. ✅ 部署最新的静态文件
3. ✅ 测试并重新加载 Nginx 配置
4. ✅ 输出浏览器清理指南

---

### 第二步：清理浏览器缓存（必须！）

#### 方法 A：强制刷新（最简单）
1. 打开 https://weclaw.cc
2. 按 **F12** 打开开发者工具
3. **右键点击**浏览器刷新按钮
4. 选择 **"清空缓存并硬性重新加载"**

#### 方法 B：清除浏览数据（推荐）
1. 按 **Ctrl+Shift+Delete**
2. 时间范围：**全部时间**
3. 勾选：
   - ✓ 缓存的图片和文件
   - ✓ Cookie 及其他网站数据（可选）
4. 点击 **"清除数据"**

#### 方法 C：注销 Service Worker（终极方案）
1. 打开 https://weclaw.cc
2. 按 **F12** 打开开发者工具
3. 切换到 **Application** 标签页
4. 左侧选择 **Service Workers**
5. 点击 **"Unregister"** 按钮
6. 切换到 **Storage**
7. 点击 **"Clear storage data"**
8. **关闭所有** weclaw.cc 标签页
9. 重新打开浏览器访问网站

---

### 第三步：验证是否成功

#### 检查点 1：域名是否正确
```javascript
// 在浏览器控制台执行
console.log(window.location.href)
// 应该显示：https://weclaw.cc/
```

#### 检查点 2：API 请求路径
```javascript
// 在浏览器控制台执行 Network 标签页查看
// API 请求应该是：https://weclaw.cc/api/xxx
// 而不是：https://ws.madechango.com/api/xxx
```

#### 检查点 3：Service Worker 状态
```javascript
// 在浏览器控制台执行
navigator.serviceWorker.getRegistrations().then(registrations => {
    console.log('Service Workers:', registrations)
})
// 应该只有一个注册项
```

---

## 🔴 如果仍然看到旧网站

### 可能性 1：Service Worker 未清除
**症状**：清除缓存后短暂正常，刷新后又变回旧版

**解决**：
1. F12 > Application > Service Workers
2. 点击 "Unregister"
3. 关闭所有标签页
4. 重新访问

### 可能性 2：浏览器缓存顽固
**症状**：强制刷新无效

**解决**：
1. 使用无痕模式访问：`Ctrl+Shift+N`
2. 如果无痕模式正常，说明需要彻底清除缓存
3. 清除所有浏览数据（包括历史记录）

### 可能性 3：DNS 缓存
**症状**：提示证书错误或连接到错误的 IP

**解决**：
```cmd
# Windows 命令提示符（管理员）
ipconfig /flushdns
```

### 可能性 4：Nginx 配置未生效
**症状**：访问 weclaw.cc 跳转到其他网站

**检查**：
```powershell
# 测试 Nginx 配置
d:
ginx
ginx.exe -t -c d:
ginx\conf
ginx.conf

# 查看 Nginx 进程
Get-Process nginx
```

**解决**：
```powershell
# 停止 Nginx
d:\nginx\nginx.exe -s stop

# 等待 3 秒
Start-Sleep -Seconds 3

# 启动 Nginx
d:\nginx\nginx.exe
```

---

## ✅ 成功的标志

- [x] 浏览器地址栏显示：`https://weclaw.cc/`
- [x] 没有 ERR_CERT_DATE_INVALID 错误
- [x] Network 面板中所有请求都指向 weclaw.cc
- [x] 能看到 WinClaw 登录界面
- [x] 没有 ws.madechango.com 相关的请求

---

## 📞 需要帮助？

如果完成以上所有步骤仍有问题，请提供：
1. 浏览器控制台的完整错误信息
2. Network 面板中失败请求的截图
3. Application > Service Workers 的截图
4. 使用 `curl -I https://weclaw.cc` 的输出
