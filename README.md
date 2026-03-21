# Weclaw

> 你的随身 AI 桌面管家 - 22+ 工具 + 移动端远程控制

**版本**: v2.9.2  
**更新日期**: 2026 年 3 月 21 日

Weclaw 是一款**轻量级但功能强大**的跨平台 AI 桌面助手。它**身材小巧**（仅 Python 环境即可运行），但**内含 22+ 实用工具**，从文件管理、浏览器自动化到语音交互 OCR 识别样样精通。

更特别的是，Weclaw 支持**自建服务器 + PWA 移动端**，让你在手机上也能远程指挥桌面 AI，真正实现"**AI 随时随地为你服务**"的体验。

## 为什么选择 Weclaw？

| 对比维度 | Weclaw | 在线 AI 助手（如 ChatGPT） |
|----------|--------|---------------------------|
| **部署方式** | 🏠 本地部署，数据留在自己电脑 | ☁️ 云端服务，数据上传第三方 |
| **工具能力** | 🔧 22+ 实用工具，直接操作电脑 | 💬 仅限对话，无法实际操作 |
| **网络依赖** | 🌐 离线也能运行核心功能 | ❌ 断网即失联 |
| **移动端** | 📱 自建 PWA，手机远程指挥 | 📱 依赖官方 App，功能受限 |
| **定制化** | 🛠️ 完全开源，可随意定制 | ⚙️ 受限的 API 和插件 |
| **隐私安全** | 🔒 数据本地存储，自主掌控 | ⚠️ 数据需上传云端 |
| **成本** | 💰 按需付费，仅付 API 费用 | 💰 按订阅付费，价格较高 |
| **响应速度** | ⚡ 本地运行，无网络延迟 | ⏳ 受网络和服务器负载影响 |

**简单来说**：Weclaw = **本地部署的 ChatGPT + 22+ 专业工具 + 移动端远程控制**，让你真正拥有 一个能"干活"的 AI 助手！

## 功能特性

### 核心能力

- **AI 对话交互**：支持多模型接入（DeepSeek、OpenAI、Claude、Llama 等），自然语言理解与回复
- **智能工具调用**：AI 能够自动调用各种工具执行实际操作，而不仅仅是对话
- **工作流引擎**：支持定义多步骤工作流，自动化复杂任务
- **定时任务**：内置 Cron 定时任务系统，支持计划任务管理

### 实用工具集（22+ 工具）

| 类别 | 工具 | 跨平台支持 |
|------|------|------------|
| **系统操作** | Shell 命令执行、文件管理、屏幕截图、应用控制 | ✅ 全平台（Windows/macOS/Linux） |
| **浏览器** | 网页自动化、搜索（本地 + Web） | ✅ 全平台 |
| **剪贴板** | 文本/图片复制粘贴 | ✅ 全平台 |
| **通知** | 系统 Toast 通知 | ⚠️ Windows 专用（macOS/Linux 需适配） |
| **多媒体** | 语音输入（STT）、语音输出（TTS）、OCR 文字识别 | ✅ 全平台 |
| **生活管理** | 日程管理、健康记录、服药提醒、日记、记账 | ✅ 全平台 |
| **实用计算** | 计算器、天气查询、日期时间、统计 | ✅ 全平台 |
| **知识库** | 本地知识库管理、对话历史 | ✅ 全平台 |
| **MCP** | MCP 服务器桥接 | ✅ 全平台 |

### 用户体验

- **双模式运行**：CLI 终端模式 + GUI 图形界面模式
- **系统托盘**：最小化到托盘，后台运行
- **全局快捷键**：Win+Shift+Space 快速唤起
- **亮/暗主题**：支持跟随系统或手动切换
- **流式输出**：AI 回复实时逐字显示，响应快速
- **生成空间**：AI 生成的文件自动归档管理

### 远程移动端支持 (v2.7.2+)

- **PWA 移动应用**：Progressive Web App，支持安装到手机主屏幕
- **安全认证**：JWT + RSA 混合认证，端到端加密通信
- **实时交互**：WebSocket 双向通信，流式 AI 响应
- **状态监控**：远程查看 Weclaw 运行状态、当前任务、可用工具
- **多端同步**：会话历史云同步，多设备无缝切换
- **部署友好**：支持 Nginx + MySQL + Redis 生产环境部署
- **离线容错**：离线消息自动保存和恢复，重连后批量推送（v2.7.2）
- **Markdown 渲染**：完整 Markdown 语法支持，移动端友好显示（v2.7.2）



## 技术架构

```
weclaw/
├── src/
│   ├── core/          # 核心模块（Agent、事件总线、会话管理、工作流）
│   ├── models/        # 模型管理（注册、选择、成本追踪）
│   ├── tools/         # 工具集（22+ 工具）
│   ├── ui/            # PySide6 图形界面
│   ├── permissions/   # 权限管理
│   └── updater/       # 自动更新
├── config/            # 配置文件（models.toml、tools.json）
├── tests/             # 单元测试和集成测试
├── build/             # PyInstaller 构建产物
└── dist/              # 发布包
```

### 技术栈

- **AI 框架**：LiteLLM + OpenAI SDK（跨平台）
- **GUI 框架**：PySide6 + qasync（跨平台 Qt）
- **自动化**：
  - Playwright（跨平台浏览器）
  - pywinauto（Windows 专用）
  - pyautogui（跨平台）
- **语音**：Whisper、pyttsx3（跨平台）
- **构建**：PyInstaller（跨平台打包）
- **远程服务**：FastAPI + MySQL/SQLite + Redis（跨平台）
- **PWA 移动端**：Vue 3 + Vite（跨平台 Web 应用）

## 快速开始

### 环境要求

- Python 3.11+
- **支持平台**：Windows 10/11（主要开发环境）、macOS 10.15+、Linux（Ubuntu 20.04+/Debian 10+/Fedora 33+）
- **GUI 依赖**：PySide6（各平台原生支持）
- **浏览器自动化**：Playwright（需在各平台单独安装浏览器）

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/wyg5208/WeClaw.git
cd WinClaw/weclaw

# 2. 创建虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\activate

# 3. 安装依赖
pip install -e ".[all]"

# 或按需安装
pip install -e .           # 核心依赖
pip install -e ".[gui]"    # GUI 依赖
pip install -e ".[browser]" # 浏览器自动化
```

### 配置

1. 复制环境变量模板：
```bash
copy .env.example .env
```

2. 编辑 `.env`，添加你的 API Key：
```env
DEEPSEEK_API_KEY=your_key_here
# 或其他模型 API Key
```

### 运行

```bash
# CLI 模式
python -m src.app

# GUI 模式
python -m src.ui.gui_app

# 或使用快捷脚本
.\start_weclaw.bat      # CLI (Windows)
.\start_weclaw_gui.bat  # GUI (Windows)

# macOS/Linux
python -m src.app       # CLI
python -m src.ui.gui_app  # GUI
```

## 项目里程碑

| 里程碑 | 状态 | 说明 |
|--------|------|------|
| M0 - MVP | ✅ | CLI 版本，核心链路跑通 |
| M1 - 核心架构 | ✅ | 配置驱动、事件总线、会话管理 |
| M2 - GUI 应用 | ✅ | 完整桌面应用，8 种工具 |
| M3 - 功能完整 | ✅ | 工作流、语音、多模态、打包 |
| M4 - 正式发布 | 进行中 | 插件系统、性能优化 |
| **M5 - 跨平台支持** | 🔄 进行中 | macOS/Linux 适配、平台兼容性测试 |

### 已完成功能

- ✅ Phase 0：MVP 快速验证（500行代码跑通核心链路）
- ✅ Phase 1：核心骨架（配置系统、事件总线、会话管理、权限审计）
- ✅ Phase 2：GUI + 扩展工具（PySide6 界面、22+ 工具）
- ✅ Phase 3：高级功能（工作流引擎、定时任务、语音交互、自动更新、打包安装）

## 跨平台部署指南

Weclaw 基于 Python 开发，天生具有跨平台能力。虽然主要开发环境是 Windows，但通过简单配置即可在 macOS 和 Linux 上运行。

### 🍎 macOS 部署

#### 1. 环境准备
```bash
# 安装 Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python 3.11
brew install python@3.11

# 安装系统依赖
brew install portaudio  # 音频支持
```

#### 2. 安装依赖
```bash
# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装核心依赖
pip install -e ".[all]"

# Playwright 浏览器安装
playwright install  # 安装 WebKit、Chromium、Firefox
```

#### 3. 权限配置
- **屏幕录制**：系统偏好设置 → 安全性与隐私 → 隐私 → 屏幕录制 → 添加 Terminal/Python
- **辅助功能**：系统偏好设置 → 安全性与隐私 → 隐私 → 辅助功能 → 添加 Terminal/Python
- **麦克风**：系统偏好设置 → 安全性与隐私 → 隐私 → 麦克风 → 添加 Terminal/Python（语音输入需要）

#### 4. 运行
```bash
# CLI 模式
python -m src.app

# GUI 模式
python -m src.ui.gui_app
```

#### 5. macOS 特定注意事项
- **通知系统**：macOS 使用 UserNotification Framework，需适配 `NotifyTool`
- **全局快捷键**：`Win+Shift+Space` 改为 `Cmd+Shift+Space`
- **文件路径**：使用 POSIX 路径格式（`/Users/username/...`）
- **应用控制**：部分 Windows 专用 API 需替换为 AppleScript 或 Quartz

### 🐧 Linux 部署

#### 1. 环境准备（以 Ubuntu 为例）
```bash
# 更新包索引
sudo apt update

# 安装 Python 3.11
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.11 python3.11-venv python3.11-dev

# 安装系统依赖
sudo apt install -y \
    portaudio19-dev \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libegl1 \
    libopengl0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0
```

#### 2. 安装依赖
```bash
# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装核心依赖
pip install -e ".[all]"

# Playwright 浏览器安装
playwright install
playwright install-deps  # 安装浏览器系统依赖
```

#### 3. 权限配置
```bash
# 音频组权限（语音功能需要）
sudo usermod -a -G audio $USER

# 视频组权限（摄像头/截图需要）
sudo usermod -a -G video $USER
```

#### 4. 运行
```bash
# CLI 模式
python -m src.app

# GUI 模式
python -m src.ui.gui_app
```

#### 5. Linux 特定注意事项
- **桌面环境**：已在 KDE Plasma、GNOME、XFCE 测试，其他桌面环境可能需要额外适配
- **通知系统**：Linux 使用 D-Bus 通知协议，需适配 `NotifyTool` 使用 `notify-send` 命令
- **窗口管理**：部分窗口控制功能依赖 WM（窗口管理器），不同桌面环境行为可能不同
- **系统托盘**：某些桌面环境（如 GNOME Shell）需要扩展支持系统托盘

### ⚠️ 跨平台兼容性矩阵

| 功能模块 | Windows | macOS | Linux | 说明 |
|---------|---------|-------|-------|------|
| **CLI 核心** | ✅ | ✅ | ✅ | 完全兼容 |
| **GUI 界面** | ✅ | ✅ | ✅ | PySide6 原生支持 |
| **AI 对话** | ✅ | ✅ | ✅ | LiteLLM 跨平台 |
| **Shell 命令** | ✅ (PowerShell/CMD) | ✅ (zsh/bash) | ✅ (bash/zsh) | 需注意平台差异 |
| **文件操作** | ✅ | ✅ | ✅ | 路径分隔符自动处理 |
| **浏览器自动化** | ✅ | ✅ | ✅ | Playwright 全平台支持 |
| **语音输入 (STT)** | ✅ | ✅ | ✅ | Whisper 跨平台 |
| **语音输出 (TTS)** | ✅ (pyttsx3) | ✅ | ✅ | 各平台 TTS 引擎不同 |
| **OCR** | ✅ | ✅ | ✅ | 使用相同 OCR 引擎 |
| **系统通知** | ✅ (Toast) | ⚠️ 需适配 | ⚠️ 需适配 | 各平台通知协议不同 |
| **全局快捷键** | ✅ | ✅ | ✅ | 键位映射需调整 |
| **屏幕截图** | ✅ | ✅ | ✅ | pyautogui 跨平台 |
| **应用控制** | ✅ (pywinauto) | ❌ | ❌ | Windows 专用，需替代方案 |
| **剪贴板** | ✅ | ✅ | ✅ | pyperclip 跨平台 |
| **定时任务** | ✅ (Windows Task Scheduler) | ⚠️ 需适配 (launchd) | ⚠️ 需适配 (cron) | 后端实现不同 |

### 🔧 平台特定适配建议

#### 需要适配的模块

1. **通知工具 (`NotifyTool`)**
   ```python
   # Windows: winsdk / win10toast
   # macOS: Foundation / NSUserNotification
   # Linux: notify-send (subprocess)
   ```

2. **应用控制工具**
   ```python
   # Windows: pywinauto (已实现)
   # macOS: AppleScript / pyautogui + Quartz
   # Linux: xdotool / wmctrl + pyautogui
   ```

3. **定时任务系统**
   ```python
   # Windows: schtasks (已实现)
   # macOS: launchd (plist 配置)
   # Linux: cron / systemd timers
   ```

4. **全局快捷键**
   ```python
   # Windows: keyboard / pynput (已实现)
   # macOS: Quartz / pynput
   # Linux: X11 / pynput
   ```

### 📦 跨平台打包

#### macOS 打包
```bash
# 使用 PyInstaller
pyinstaller weclaw.spec --target-os macos

# 生成 .app  bundle
codesign --force --deep --sign - dist/weclaw.app
```

#### Linux 打包
```bash
# 使用 PyInstaller
pyinstaller weclaw.spec --target-os linux

# 创建 AppImage（可选）
appimagetool dist/weclaw.AppDir
```

### 🐳 Docker 容器化部署（推荐用于服务器端）

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    libxcb-xinerama0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Weclaw
COPY . .
RUN pip install -e ".[all]"

# 安装 Playwright 浏览器
RUN playwright install chromium
RUN playwright install-deps

# 启动远程服务（无头模式）
CMD ["python", "-m", "remote_server.main"]
```

```bash
# 构建镜像
docker build -t weclaw-server:latest .

# 运行容器
docker run -d \
  -p 8188:8188 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  weclaw-server:latest
```

### 📝 跨平台最佳实践

1. **路径处理**：始终使用 `pathlib.Path` 而非硬编码路径分隔符
2. **编码**：所有文本文件使用 UTF-8 编码
3. **换行符**：使用 `\n` 而非 `\r\n`
4. **环境变量**：使用 `os.environ` 而非平台特定注册表
5. **进程管理**：使用 `subprocess` 并注意平台差异（shell=True/False）
6. **网络**：监听 `0.0.0.0` 而非 `localhost` 以支持远程访问
7. **日志**：使用标准 logging 模块，避免平台特定的事件日志

### 🆘 常见问题

#### Q: macOS 提示"无法验证开发者"
A: 系统偏好设置 → 安全性与隐私 → 仍要打开，或使用 `codesign` 签名

#### Q: Linux GUI 应用无法启动
A: 确保已安装所有 X11 依赖：`sudo apt install libxcb-* libxkbcommon-x11-0`

#### Q: Playwright 浏览器安装失败
A: 使用 `playwright install-deps` 安装系统依赖，或手动安装 `chromium-browser`

#### Q: 语音功能在某些平台不可用
A: 检查音频设备权限，确保已安装 `portaudio` 和相关系统库

---

## 版本日志

### v2.6.0 新功能 - 远程移动端交互服务 2026 年 2 月 21 日

**核心功能：FastAPI 远程服务端，支持移动端远程访问 Weclaw**

#### 新增模块

1. **remote_server/** - 远程服务模块
   - `main.py`: FastAPI 应用入口，生命周期管理
   - `config.py`: 服务配置加载（支持 TOML）

2. **remote_server/auth/** - 认证系统
   - `jwt_handler.py`: JWT Token 生成/验证（支持 RS256/HS256）
   - `rsa_handler.py`: RSA 密钥管理，加密传输 Token
   - `user_manager.py`: 用户管理，SQLite 存储，登录锁定机制

3. **remote_server/api/** - REST API 端点
   - `auth.py`: 用户注册/登录/令牌刷新
   - `chat.py`: 消息发送/SSE 流式响应
   - `status.py`: WinClaw 状态查询/工具列表
   - `files.py`: 文件上传/下载（支持图片缩略图）
   - `commands.py`: 直接执行工具命令

4. **remote_server/websocket/** - 实时通信
   - `manager.py`: WebSocket 连接管理，心跳检测，多用户支持
   - `handlers.py`: 消息处理器，工具调用推送

5. **remote_server/bridge/** - Weclaw 桥接
   - `winclaw_bridge.py`: Agent 桥接，EventBus 事件转发

6. **remote_server/models/** - 数据模型
   - `user.py`: 用户模型（含设置、锁定状态）
   - `session.py`: 远程会话模型
   - `message.py`: 消息/工具调用/附件模型

#### 配置文件
- `config/remote_server.toml`: 服务配置（端口、认证、WebSocket、文件上传）

#### 启动方式
```bash
# 使用启动脚本
start_remote_server.bat

# 或直接运行
python -m remote_server.main
```

#### API 文档
启动后访问 http://localhost:8080/docs 查看 Swagger 文档

---

### v2.5.2 BUG 修复 - 任务锚定机制智能优化 2026 年 2 月 21 日

**问题描述：**
任务执行过程中的"提醒AI助手关注初始用户需求"功能存在副作用：
1. 已执行一半，提醒后反而重新来过
2. 执行完毕了，结果一提醒又再来一次
3. 缺乏执行过程的跟踪和反馈，无法根据进度决定是否重新执行

**根本原因：**
锚定机制（anchor_message）固定每3步发送提醒，消息内容总是"请继续推进此任务"，不考虑：
- 任务是否已完成
- 是否有重复操作
- 执行进展状态

**修复方案：**

1. **新增 ExecutionTracker 执行状态跟踪器**
   - 记录成功/失败的工具调用
   - 检测重复操作（基于工具名+参数哈希）
   - 计算连续成功次数
   - 判断是否应该建议模型考虑任务已完成

2. **智能锚定消息构建**
   根据执行状态动态调整消息内容：
   - **连续失败较多** → 建议检查问题，不要重复相同操作
   - **多次成功** → 建议评估任务是否已完成，考虑总结
   - **有成功操作** → 鼓励继续但明确提醒不要重复已执行的操作
   - **初始阶段** → 简单的继续推进提示

3. **核心改进逻辑**
```python
# 旧版锚定消息（问题代码）
anchor_content = f"请继续推进此任务，不要执行无关操作。"

# 新版智能锚定消息
if consecutive_failures >= 2:
    # 建议检查问题，避免重复失败操作
    anchor_content = "连续失败多次，请分析失败原因后再尝试..."
elif should_suggest_completion():
    # 建议评估任务是否已完成
    anchor_content = "已连续成功多次，请评估任务是否已完成..."
else:
    # 鼓励继续但提醒不要重复
    anchor_content = "已成功执行 N 次操作，请继续推进，但不要重复已执行的操作..."
```

**修改文件：**
- `src/core/agent.py`: 新增 ExecutionTracker 类，修改锚定消息逻辑

**测试验证：**
- ✅ 任务执行中不会重复开始
- ✅ 任务完成后能正确结束
- ✅ 连续失败时给出合理建议
- ✅ 已执行操作不会被重复执行

---

### v2.5.1 BUG 修复 - UI 组件销毁保护 2026 年 2 月 21 日

**BUG 修复：**

#### 问题 1: RuntimeError - Internal C++ object already deleted
主窗体启动后出现 `RuntimeError: Internal C++ object already deleted` 错误，原因是：
- 异步任务回调在 UI 组件销毁后仍尝试访问
- 多个 UI 组件（`_tool_status`, `_tool_log`, `_chat_widget` 等）被异步信号调用
- 缺少对象存活检查导致 C++ 对象已删除但仍被访问

#### 问题 2: 右侧工具执行状态卡片不显示 ⚠️ 关键
**根本原因**: `_create_status_panel()` 方法中创建了 `tools_group` (工具执行状态 GroupBox)，但**忘记将其添加到布局中**！

```python
# 错误代码：tools_group 创建后没有 addWidget
tools_group = QGroupBox("工具执行状态")
tools_layout = QVBoxLayout(tools_group)
# ... 添加各种子组件 ...
# 缺少这一行！layout.addWidget(tools_group)
```

**修复**: 在 `layout.addStretch()` 之前添加 `layout.addWidget(tools_group)`

#### 修复内容
为所有可能被异步调用的 UI 方法添加三重保护：
1. **属性存在性检查**: `hasattr(self, '_component') and self._component is not None`
2. **try-except 捕获**: 捕获 `RuntimeError` 异常并静默处理
3. **安全包装函数**: 在 `gui_app.py` 中添加 `safe_*` 系列函数

**修复的方法包括：**
- `_set_thinking_state()` - 设置思考状态
- `set_tool_status()` - 设置工具状态
- `add_tool_log()` - 添加工具日志
- `clear_tool_log()` - 清空工具日志
- `_copy_tool_status()` - 复制工具状态
- `add_ai_message()` - 添加 AI 消息
- `append_ai_message()` - 追加 AI 消息（流式输出）
- `start_reasoning()` / `append_reasoning()` / `finish_reasoning()` - 思考过程
- `set_models()` / `set_current_model()` - 模型切换
- `update_usage()` - Token 用量更新
- `set_connection_status()` - 连接状态更新

**技术细节：**
```python
def set_tool_status(self, status: str) -> None:
    """设置工具状态。"""
    # 检查组件是否仍然有效
    if not hasattr(self, '_tool_status') or self._tool_status is None:
        return
    try:
        self._tool_status.setText(status)
        # 控制进度条可见性
        is_busy = status not in ("空闲", "完成")
        if hasattr(self, '_tool_progress') and self._tool_progress is not None:
            self._tool_progress.setVisible(is_busy)
    except RuntimeError:
        # 组件已被销毁，忽略
        pass
```

#### 测试验证
- ✅ 程序正常启动
- ✅ 右侧工具执行卡片正常显示
- ✅ 异步任务不再抛出 RuntimeError
- ✅ UI 组件销毁后静默失败，不影响其他功能

#### UI 布局优化
**问题**: 工具执行状态卡片下方有大量空白
**修复**: 
- 移除 `_tool_log_scroll.setMaximumHeight(360)` 限制
- 使用 `layout.addWidget(tools_group, stretch=1)` 让工具卡片占用剩余空间
- 滚动区域也设置 `stretch=1` 自动填充
- 移除 `layout.addStretch()` 避免空白留白

#### 工具执行结果显示优化
**问题**: 工具执行结果显示被截断，只显示前 60 个字符
**修复**: 
- 显示长度从 60 字符增加到 150 字符
- 超过 150 字符时添加省略号 "..." 提示
```python
f"✔ {name}.{action} → {result[:150]}{'...' if len(result) > 150 else ''}"
```

---

### v2.5.0 Phase 6 微观进化 - 神经网络自我学习 2026 年 2 月 21 日

**核心功能：神经网络自主学习和进化能力**

Phase 6 引入四大进化机制，让神经网络能够像人脑一样自我优化：

#### 1. 增强 STDP 规则（多巴胺/ACh门控）
- ✅ `Synapse` 数据类增强：学习率/资格迹/年龄/meta-plasticity/BCM 阈值
- ✅ `apply_stdp_with_modulation()`：受多巴胺 RPE 和 ACh 不确定性调节
- ✅ `update_bcm_threshold()`：BCM 滑动阈值防止权重饱和
- 📊 **测试**: 13 个单元测试全部通过 (`test_phase6_synapse.py`)

#### 2. 结构可塑性（突触修剪与新生）
- ✅ `prune_weak_synapses()`: 修剪长期不活跃且权重低的突触
- ✅ `generate_new_synapses()`: 在活跃神经元之间生成新连接
- ✅ `synaptic_turnover_rate()`: 计算新生率/死亡率/翻转率
- 🎯 **指标**: 翻转率 ~5%/分钟（符合生物神经科学）

#### 3. 稳态突触缩放（防止活动爆炸/沉寂）
- ✅ 新建 `homeostasis.py` - `SynapticScaling` 类
- ✅ 检测过度活跃 (>0.8) / 沉寂 (<0.1)
- ✅ 全局乘法缩放（保持相对权重关系）
- ✅ 调节历史记录和可视化
- 📊 **测试**: 12 个单元测试全部通过 (`test_phase6_homeostasis.py`)

#### 4. 资格迹机制（延迟强化学习）
- ✅ 新建 `EligibilityTrace` 类（`neurotransmitters.py`）
- ✅ 标记同时激活的突触为"有资格"
- ✅ 指数衰减（decay_rate=0.9）
- ✅ 多巴胺到达时强化有资格的突触
- ⏱️ **延迟窗口**: 最多支持 10 秒延迟奖励（解决信用分配问题）

#### 5. 进化监控 Dashboard（可视化所有进化指标）
- ✅ 新建 `dashboard_evolution.py` - 独立进化监控窗体
- 📊 **突触权重分布直方图**（实时更新）
- 📈 **结构变化时间线**（新生 vs 死亡曲线）
- 🔥 **资格迹状态面板**（活跃迹数量/强度）
- ⚖️ **稳态调节日志**（上调/下调事件标记）
- 🎛️ **进化指标仪表盘**：
  - 突触总数
  - 翻转率 (%/min)
  - 新生率/死亡率
  - 平均权重
  - 网络复杂度
  - 稳态因子
  - 活跃资格迹数

**修改文件：**
- `core.py`: Synapse 增强 (+86 行) + BCM 阈值更新 (+43 行) + 结构可塑性方法 (+135 行)
- `neurotransmitters.py`: EligibilityTrace 类 (+181 行)
- `homeostasis.py`: 新建稳态调节器 (238 行)
- `dashboard_evolution.py`: 新建进化 Dashboard (469 行)
- `tests/test_phase6_synapse.py`: 13 个测试
- `tests/test_phase6_homeostasis.py`: 12 个测试

**性能指标：**
- ✅ 单次 process_cycle() < 10ms（含进化检查）
- ✅ Dashboard 刷新帧率 > 15 FPS
- ✅ 内存占用稳定（无泄漏）
- ✅ 25 个单元测试全部通过

---

### v2.4.0 Phase 5 Dashboard 性能优化 + 体验日志修复 2026 年 2 月 21 日

**BUG 修复：**
- ✅ 发育面板「最近体验日志」显示问号 → 完整场景信息
  - 根因：Dashboard 读取字段名与引擎存储不匹配（scenario 是字符串而非 dict，stage 字段应为 curriculum_phase）
  - 修复：正确解析 scenario、curriculum_phase、developmental_stage 字段
  - 效果：现在显示 `[阶段] 场景名 — 描述 (语义标签)` 完整信息
- ✅ litellm RuntimeWarning: coroutine was never awaited 警告抑制
  - 根因：litellm 内部异步日志协程未 await
  - 修复：禁用 telemetry + 清空 success_callback + warnings.filterwarnings
  - 效果：CMD 不再显示 "coroutine was never awaited" 警告

**性能优化：**
- ✅ Dashboard 表征桥接可视化加 5 秒 TTL 缓存
  - _refresh_bridge() 投影矩阵 toarray() + 随机编码 → 缓存结果
  - 避免每帧重复计算稀疏矩阵转换和随机向量编码
- ✅ 语义锚定条形图仅在数据变化时重绘
  - _refresh_grounding() 跟踪概念数量变化，仅增量更新高度
- ✅ DevelopmentalWorkerThread 每步间 sleep(0.02) 释放 GIL
  - 避免长时间独占 GIL 导致 UI 卡顿

**修改文件：**
- `dashboard_developmental.py`: 体验日志渲染逻辑 + 桥接可视化缓存
- `models/registry.py`: litellm 警告抑制配置

### v2.3.0 Phase 5 发育引擎 Dashboard 集成 2026 年 2 月 21 日

**新增独立 Phase 5 发育引擎可视化窗体**

1. **新建 `dashboard_developmental.py`**（746行，独立 QMainWindow 窗体）：
   - 意识仪表盘：ConsciousnessLevel 等级显示（5级颜色映射）、综合得分条、6维雷达图、Phi 实时曲线
   - 发育进度面板：6阶段（A→F）进度指示器、阶段描述、周期统计、体验日志、交互运行按钮
   - 表征桥接可视化：稀疏投影矩阵热图（20×20 缩略）、编码活动波形、桥接统计
   - 语义锚定状态：已锚定概念列表 + 关联强度条形图、手动锚定/检索输入、统计信息
   - QTimer 1秒定时刷新 + QThread 异步发育步进（不阻塞 UI）
   - 深色主题 (#1e1e1e) 与主 Dashboard 视觉统一

2. **主 Dashboard 集成入口**（`dashboard_pyqtgraph.py`）：
   - 状态面板新增 "🧬 Phase 5 发育面板" 按钮
   - 点击打开独立窗体，共享同一 NeuroConsciousnessManager 实例
   - 模块不可用时按钮自动禁用（优雅降级）

3. **自动发育引擎启用**：
   - 新窗体打开时自动调用 `manager.enable_developmental_engine(embedding_dim=128, n_bridge_neurons=500)`
   - 无需手动初始化即可使用全部 Phase 5 功能

4. **测试验证**：
   - ✅ Phase 5 模块导入测试通过
   - ✅ Phase 5 全部 38 个单元测试通过

### v1.2.2 语音对话系统重构 2026年2月18日

**修复对话模式频繁崩溃，重构线程安全架构**

1. **TTSPlayer Worker+QThread 正确模式重构**：
   - 从覆盖 `QThread.run()` 的反模式改为标准 Worker + `moveToThread()` 模式
   - 所有 Signal 从工作线程事件循环安全发射，通过 QueuedConnection 到主线程
   - pyttsx3 引擎在工作线程中初始化，保证 COM 线程亲和性
   - 停止机制使用跨线程标志 + 直接中断（pyttsx3.stop / winsound.PlaySound(None, SND_PURGE)）

2. **VoiceRecognizer 线程安全信号发射**：
   - 新增内部信号 `_bg_speech_result` / `_bg_speech_error`，显式 QueuedConnection
   - 后台线程不再直接发射公共 Signal，消除从非 Qt 线程发射信号导致的随机崩溃
   - Whisper 路径从 pyaudio 替换为 sounddevice，统一音频后端，消除设备冲突

3. **ConversationManager Watchdog 超时恢复**：
   - 为 THINKING（AI 回复）和 SPEAKING（TTS 播放）状态增加超时保护
   - 超时后自动恢复到 LISTENING 状态，防止信号链断裂导致状态机永久卡死
   - 超时参数可在 `[conversation]` 配置节中自定义

4. **TTS 路径统一**：
   - GUI 层所有 TTS 播放统一走 TTSPlayer，消除 VoiceOutputTool 独立 pyttsx3 实例冲突
   - 非对话模式和对话模式使用同一 TTS 通道

5. **清理重复代码**：
   - 删除 `main_window.py` 中重复的 `_on_conversation_play_tts` 空实现定义

### v1.2.1 BUG修复 2026年2月17日

**定时任务系统稳定性修复**

1. **修复定时任务 UI 编辑对话框崩溃**：QHBoxLayout 没有 setVisible 方法，将触发类型切换控件包装为 QWidget
2. **修复定时任务参数缺失导致 KeyError 崩溃**：所有 cron 动作方法增加参数验证，返回清晰错误提示
3. **修复 AI 误用 Linux 命令创建定时任务**：
   - 增强 System Prompt 定时任务工具选择指南，引导 AI 使用 add_ai_task 而非 add_cron
   - 工具描述明确区分 Shell 命令任务和 AI 任务
   - 任务恢复时自动检测并清理使用 Linux 命令（如 notify_send）的无效任务
   - 命令执行前预检查，发现无效命令直接移除任务
4. **修复文件追加结果失败**：`_handle_ai_task_result` 中改用 `execute("write", {append: True})` 替代不存在的 `file_tool.read/write` 方法
5. **修复命令执行编码问题**：subprocess 指定 `encoding='utf-8'` + `errors='replace'`，避免 GBK 解码错误
6. **改善 file.write 受限提示**：被拒绝的文件类型错误信息建议使用 shell.run 替代

### v1.2.0 更新日志 2026年2月18日

**录音功能整体优化**

1. **新增 `record_audio` 录音保存动作**：
   - VoiceInputTool 新增纯录音动作，录制音频并保存为 WAV 文件
   - 支持自定义保存路径或自动生成到 `generated/audio/` 目录
   - AI Agent 可独立调用录音功能，无需同时做语音转文字

2. **VAD 智能录音（说完自动停止）**：
   - 基于 RMS 能量阈值的语音活动检测（Voice Activity Detection）
   - 使用 sounddevice InputStream 流式录音，检测到持续静音后自动停止
   - 可配置参数：静音阈值、静音持续时间、最大录音时长
   - 最短录音保护（1秒），防止误触发

3. **修复持续对话模式信号链断裂**：
   - 修复对话模式只能对话一次的核心 Bug
   - 根因：gui_app 的 TTS 路径（VoiceOutputTool）播放完毕后不通知 ConversationManager，导致状态机卡在 THINKING 状态
   - 修复方案：对话模式下统一走 conversation TTS 路径（TTSPlayer），正确触发 `on_tts_finished()` 恢复监听
   - 补充：TTS 未开启时也正确恢复监听状态

4. **录音配置化**：
   - 移除 gui_app.py 中多处硬编码的 5 秒录音时长
   - 新增 `[voice]` 配置节：`max_duration`、`auto_stop`、`silence_threshold`、`silence_duration`
   - 录音弹窗支持 VAD 模式 UI（显示已录时长，说完自动停止提示）

### v2.1.0 更新日志 2026 年 2 月 20 日

**Phase 4：LLM 大模型集成模块优化**

1. **Dashboard LLM 认知增强面板**（`dashboard_pyqtgraph.py`）：
   - 主 Dashboard 仅新增极简 LLM 状态指示 + "🧠 LLM 面板" 按钮，不增加界面拥堵
   - 点击按钮打开独立 QDialog + QTabWidget 弹窗，包含 4 个 Tab 页：
     - 🤔 自我反思 (DMN)：生成自然语言自我反思报告
     - 📊 元认知 (BA10)：将神经活动数据翻译为可理解的认知状态描述
     - 💬 意识对话 (Broca-Wernicke)：与意识系统自然语言交互
     - 🎯 参数建议 (dlPFC)：LLM 分析当前神经状态并提供参数调优建议
   - QThread + Signal 异步模式避免 LLM 调用阻塞 UI（1-5 秒 LLM 调用不卡顿）
   - LLM 不可用时安全降级（按钮 disable、状态标签显示"未启用"）

2. **自动反思触发机制**：
   - 每 200 个意识周期自动检查一次反思条件
   - 非强制触发，尊重 SelfReflectionEngine 内置触发条件
   - 反思结果自动存入交互日志，记录到 Dashboard 显示

3. **反思报告存入情景记忆**（`manager.py`）：
   - LLM 生成的自我反思报告自动存入情景记忆系统
   - 实现从碎片记忆到叙事记忆的飞跃
   - 记忆格式：`stimulus="LLM 自我反思 (cycle=N)"`
   - 上下文信息完整（包含 type、cycle 等元数据）

4. **Markdown 导出增强**（`exporter.py`）：
   - 实验报告新增第 7 章 "LLM 认知增强分析"
   - 包含：
     - 快速元认知解释（规则引擎生成，不调用 LLM）
     - 最近自我反思报告（最多 3 份）
     - LLM 使用统计表（调用次数、Token 用量、费用）
   - LLM 未启用时第 7 章自动隐藏

5. **LLM 面板状态栏**：
   - 实时显示模型名称、调用次数、Token 用量、费用、缓存命中率
   - 2 秒自动刷新定时器
   - 支持窗口最大化和最小化

6. **测试验证**：
   - ✅ 快速冒烟测试通过（_test_quick.py）
   - ✅ LLM 集成测试 11/11 通过（test_llm_integration.py）
   - ✅ Phase 1-3 回归测试全部通过（test_phase1_3_improvements.py）

### v2.0.0 更新日志 2026 年 2 月 19 日

**Phase 4 续：LLM 认知增强 Dashboard 集成（最后一公里）**

1. **LLM 认知增强面板**（`dashboard_pyqtgraph.py`）：
   - 主 Dashboard 仅新增极简 LLM 状态指示 + "LLM 面板" 按钮，不增加界面拥堵
   - 点击按钮打开独立 QDialog + QTabWidget 弹窗，包含 4 个 Tab 页：
     - 🤔 自我反思 (DMN)：生成自然语言自我反思报告
     - 📊 元认知 (BA10)：将神经活动数据翻译为可理解的认知状态描述
     - 💬 意识对话 (Broca-Wernicke)：与意识系统自然语言交互
     - 🎯 参数建议 (dlPFC)：LLM 分析当前神经状态并提供参数调优建议
   - QThread + Signal 异步模式避免 LLM 调用阻塞 UI
   - LLM 不可用时安全降级（按钮 disable、状态标签显示"未启用"）

2. **自动反思触发**：
   - 每 200 个意识周期自动检查一次反思条件
   - 非强制触发，尊重 SelfReflectionEngine 内置条件
   - 反思结果自动存入交互日志

3. **反思报告存入情景记忆**（`manager.py`）：
   - LLM 生成的自我反思报告自动存入情景记忆系统
   - 实现从碎片记忆到叙事记忆的飞跃

4. **Markdown 导出增强**（`exporter.py`）：
   - 实验报告新增第 7 章 "LLM 认知增强分析"
   - 包含元认知解释、最近反思报告（最多 3 份）、LLM 使用统计表

5. **LLM 面板状态栏**：
   - 实时显示模型名称、调用次数、Token 用量、费用、缓存命中率
   - 2 秒自动刷新

### v1.1.0 更新日志 2026年2月17日

**Phase 7：全链路追踪与新工具纳入规范**

1. **TaskTrace 全链路追踪系统**（新增 `task_trace.py`）：
   - 记录用户请求从意图识别到任务完成的完整轨迹
   - 数据结构：trace_id、session_id、意图识别结果、工具暴露策略、工具调用序列、最终状态
   - 敏感信息自动脱敏（api_key、password、token 等）
   - JSONL 文件存储，按日期分文件，自动清理过期文件
   - 配置项：`[agent.trace] enabled/trace_dir/max_output_preview/max_trace_days`

2. **agent.py 采集埋点**：
   - chat() 和 chat_stream() 方法完整采集轨迹数据
   - 记录每次工具调用的参数、状态、耗时、错误信息
   - 记录层级升级事件

3. **全链路一致性校验脚本**（新增 `validate_tool_chain.py`）：
   - 7 项一致性检查：INTENT_TOOL_MAPPING 覆盖、引用有效性、INTENT_PRIORITY_MAP 引用、_extract_tool_name 覆盖、dependencies 引用、_build_init_kwargs 覆盖、三表 key 对齐
   - 支持 MCP 动态工具识别
   - 支持 `--fix-suggestions` 输出修复建议

4. **新工具纳入规范**（`tools.json` onboarding_checklist）：
   - 10 项标准化检查清单
   - 确保新工具在全链路中一致注册

5. **工具废弃流程**：
   - 工具配置支持 `deprecated`、`deprecation_message`、`migrate_to` 字段
   - 废弃工具调用时返回友好提示和替代方案
   - chat() 和 chat_stream() 方法均支持

6. **离线分析脚本**（新增 `analyze_traces.py`）：
   - 意图识别准确率统计
   - 工具使用频率分析
   - 失败模式识别
   - 层级升级频率统计
   - 支持按日期/最近 N 天/全部分析

### v1.0.24 更新日志 2026年2月17日

**Phase 6：工具调用全链路优化**

1. **渐进式工具暴露引擎**（新增 `tool_exposure.py`）：
   - 根据意图置信度分三层暴露工具 Schema（推荐集 ~10 → 扩展集 ~20 → 全量集 35+）
   - 核心工具（shell/file/screen/search）始终保留
   - 连续失败 >= 2 次自动升级到更大工具集

2. **多维度意图识别增强**（`prompts.py`）：
   - 10 个意图维度关键词匹配 + 归一化置信度评估（0.0-1.0）
   - 意图-工具映射表、意图-优先级映射表
   - 可选的模型辅助意图分类（默认关闭）

3. **Schema 动态优先级标注**：
   - 在工具 description 前添加 `[推荐]`/`[备选]` 前缀引导模型决策
   - 不删除任何工具，只做标注引导

4. **单次工具调用数量限制**：
   - 硬性限制 `MAX_TOOLS_PER_CALL = 3`，直接拦截超限调用
   - 新增前置校验器模块（`tool_validator.py`）

5. **分级错误反馈**（`base.py`）：
   - 首次失败返回简短版、第 2 次返回标准版（含建议）、第 3 次+返回详细版

6. **工具依赖自动解析**（`tools.json`）：
   - 通过 `dependencies.input_sources` 字段避免过滤掉内容源工具

7. **任务锚定机制优化**（`agent.py`）：
   - 锚定消息包含执行状态摘要（步数、工具调用次数、连续失败次数）

8. **审计日志增强**（`audit.py`）：
   - 新增 intent/confidence/tool_tier/consecutive_failures/user_input 字段

9. **配置化开关**（`default.toml [agent.tool_optimization]`）：
   - 所有优化功能可通过独立开关启用/关闭，支持随时回退

### v1.0.23 更新日志 2026年2月16日

**新功能：**

1. **录音可视化弹窗**：
   - 新增 `VoiceRecordDialog` 录音弹窗组件，录音时弹出可视化窗口
   - 显示录音状态（准备→录音中→识别中→完成/失败）
   - 音量波形动画提示用户可以说话
   - 倒计时进度条显示录音时长
   - 支持手动停止录音和取消
   - 识别成功/失败后自动关闭
   - 支持对话模式持续监听状态显示
   - 支持两种触发路径：工具栏录音按钮点击 和 AI Agent 调用 voice_input 工具

### v1.0.22 更新日志 2026年2月16日

**Bug修复：**

1. **修复定时任务对话框崩溃**
2. **修复 browser-use provider 属性错误**
3. **修复 MCP 工具重复注册警告**
4. **改进全局快捷键异常处理**

### v2.7.0 更新日志 2026年2月21日

**新增功能：远程移动端支持 (PWA)**

1. **FastAPI 后端服务**：
   - 完整的 RESTful API 服务，支持用户认证、会话管理、消息收发
   - JWT + RSA 混合认证机制，Access Token 15分钟过期，Refresh Token 7天
   - WebSocket 实时双向通信，支持流式 AI 响应
   - WinClaw Agent 桥接层，连接远程用户与本地 WinClaw

2. **数据库支持**：
   - MySQL/SQLite 双数据库抽象层，通过配置切换
   - Redis 缓存支持（会话存储、Token 黑名单、速率限制）
   - 完整的数据库初始化脚本和存储过程

3. **PWA 移动端**：
   - Vue 3 + Vite + Vant UI 现代化前端架构
   - 完整的用户认证流程（登录、注册、Token 刷新）
   - 实时聊天界面，支持流式响应和工具调用显示
   - WinClaw 状态监控面板
   - 支持深色/浅色主题切换
   - PWA 离线缓存和安装支持

4. **部署配置**：
   - Nginx 反向代理配置（支持 SSL、WebSocket、SSE）
   - Windows 服务安装脚本（基于 NSSM）
   - MySQL 数据库初始化 SQL 脚本

**技术栈更新：**
- 后端：FastAPI + aiomysql + redis + python-jose
- 前端：Vue 3 + Vite + Pinia + Vant + axios
- 部署：Nginx + MySQL + Redis + Windows Server 2022

### v2.7.3 更新日志 2026 年 3 月 2 日

**PWA-Weclaw 双向通信闭环修复 + 多设备消息隔离**

1. **消息响应闭环修复**：
   - 统一 request_id 路由机制，使用 message_id 作为 request_id
   - 修复 Weclaw 响应格式：payload.content 替代 delta，stream_end 替代 done
   - 基于 user_id 的 WebSocket 消息路由，解决 session_id 时间戳精度不一致问题
   - PWA 端 sendMessage() 时自动初始化 WebSocket 连接

2. **多设备消息隔离**：
   - PWA 端添加 pendingMessageIds 过滤器，只处理本设备发起的请求响应
   - 支持同一用户的多个设备同时交互，消息不会混淆
   - 双重保障：服务端精确路由 + 客户端过滤

3. **性能优化**：
   - 移除频繁的流式响应日志（每个 chunk 都输出）
   - 只保留关键节点日志（响应完成），日志量减少 95%+
   - 添加 reconnected 消息类型处理

4. **离线容错增强**：
   - 重连后自动恢复离线消息队列
   - 差异化错误提示：区分"未绑定设备"和"设备离线"

**修改文件**：
- `remote_server/api/chat.py`: request_id 统一，转发逻辑优化
- `remote_server/websocket/bridge_handler.py`: 基于 user_id 路由，日志清理
- `src/remote_client/client.py`: 消息格式修复，日志优化
- `pwa/src/stores/chat.ts`: WebSocket 初始化，多设备过滤
- `pwa/src/api/websocket.ts`: 添加 request_id 字段

**测试验证**：
- ✅ PWA 发送消息 → 桌面端接收并处理 → PWA 收到响应（完整闭环）
- ✅ 多设备同时交互，消息严格隔离
- ✅ 离线消息自动恢复
- ✅ Markdown 渲染正常

---

### v2.8.0 更新日志 2026 年 3 月 13 日

**远程绑定与后台管理模块**

1. **远程绑定持久化修复**：
   - 修复绑定状态无法保存的问题
   - JWT Token 安全存储到 keystore
   - 重启应用后自动加载已保存的 Token

2. **后台管理系统研发**：
   - 完整的 Web 管理后台（FastAPI + Jinja2）
   - 用户管理、设备管理、日志中心、统计分析
   - JWT 认证 + 权限控制

3. **安全加固**：
   - 禁止跨用户绑定
   - 数据库局部唯一索引防止重复绑定
   - 管理员凭据外部化（.env 方式）

4. **PWA 端优化**：
   - 响应路由request_id修复
   - 注册流程密码验证规则统一
   - 设备绑定检查机制

5. **Tool Call 消息完整性修复**：
   - 连续失败时为剩余 tool_call 补充错误消息
   - 确保对话历史结构完整

### v2.9.2 更新日志 2026 年 3 月 21 日

**Bug修复：Token 用量显示修复**

1. **修复 Token 用量面板显示问题**：
   - 修复桌面端右侧面板 Token 用量显示异常（输入/输出始终为 0）
   - 根因：`gui_app.py` 信号发射时硬编码 `0, 0`，缺少真实 Token 统计
   - 新增 `ModelRegistry.total_prompt_tokens` 和 `total_completion_tokens` 聚合属性
   - 修正 `usage_updated.emit()` 使用真实数据

2. **技术改进**：
   - 数据聚合属性完整性：覆盖 prompt_tokens、completion_tokens 字段
   - 信号机制正确传递 Token 统计数据到 UI 层

---

### v2.9.0 更新日志 2026 年 3 月 14 日

**前端优化与性能提升**

1. **管理后台CDN资源本地化**：
   - Tailwind CSS 和 Chart.js 本地部署
   - 移除 console.warn 警告代码
   - FastAPI StaticFiles 配置

2. **启动性能优化**：
   - Whisper 懒加载改造
   - MCP Server 并行连接
   - 启动时间减少约 15 秒

---

### v2.7.2 更新日志 2026 年 2 月 26 日

**PWA 离线容错优化 + Markdown 渲染增强**

1. **离线消息队列系统（Phase 2）**：
   - 新增 `offline_messages` 数据库表，支持 SQLite/MySQL 双后端
   - 消息队列服务（`message_queue.py`）：内存 + 数据库双写，TTL 过期策略
   - 差异化错误提示：区分"未绑定设备"和"设备离线"两种状态
   - 自动恢复逻辑：Weclaw 重连后批量推送积压消息
   - 监控告警模块：健康检查、积压告警、过期告警（5 分钟周期）

2. **PWA 端 Markdown 渲染增强**：
   - 集成 `marked` 库（v17+），完整支持标准 Markdown 语法
   - 支持的语法：标题 (H1-H6)、列表 (有序/无序)、引用块、代码块、表格、链接等
   - 降级保护：解析失败时自动降级为纯文本
   - TypeScript 类型声明：`src/types/marked.d.ts`
   - CSS 样式增强：深色主题适配、代码高亮背景、响应式表格

3. **服务器端优化**：
   - 数据库初始化集成到 main.py lifespan
   - asyncio 导入修复（监控任务启动）
   - 离线消息队列空值防护（降级到内存模式）
   - 国际化支持（i18n）：中英双语错误提示

4. **PWA 端 BUG 修复**：
   - 修复消息重复显示问题（移除 HTTP stream，依赖 WebSocket 推送）
   - marked v17 API 兼容（直接调用函数，传入配置选项）

**修改文件**：
- `weclaw_server/remote_server/models/offline_message.py` (新建，106 行)
- `weclaw_server/remote_server/services/message_queue.py` (新建，295 行)
- `weclaw_server/remote_server/i18n/__init__.py` (新建，145 行)
- `weclaw_server/remote_server/i18n/messages.json` (新建，19 行)
- `weclaw_server/remote_server/monitoring/alerts.py` (新建，238 行)
- `weclaw_server/pwa/src/views/Chat.vue` (修改，+86 行)
- `weclaw_server/pwa/src/types/marked.d.ts` (新建，70 行)
- `weclaw_server/remote_server/main.py` (修改，+17 行)
- `weclaw_server/remote_server/websocket/handlers.py` (修改，+7 行)
- `weclaw_server/remote_client/client.py` (修改，+28 行)

**测试验证**：
- ✅ 离线消息存入数据库
- ✅ Weclaw 重连后自动推送
- ✅ PWA 端 Markdown 正确渲染（标题/列表/代码块）
- ✅ 消息不再重复显示
- ✅ 监控任务正常启动（5 分钟周期）

---

### v2.7.1 更新日志 2026 年 2 月 21 日

**新增功能：Bridge 远程桥接模式**

1. **Weclaw 本机端 Bridge 客户端**：
   - WebSocket 客户端连接远程服务器
   - 自动重连机制（可配置重连次数和间隔）
   - 消息处理器转发远程命令到本地 Agent
   - 流式响应支持（SSE）
   - 定期状态上报（CPU、内存、模型信息等）

2. **服务器端 Bridge 端点**：
   - `/ws/bridge` WebSocket 端点接收 Weclaw 连接
   - BridgeConnectionManager 管理多用户多实例
   - 消息路由（PWA 请求 → 对应用户的 Weclaw）
   - 双向通信支持

3. **架构更新**：
   - 支持独立服务器模式（服务器与 Weclaw 分离）
   - 支持内嵌模式（服务器与 Weclaw 同一进程）
   - Chat API 自动检测连接模式

**配置示例** (`config/default.toml`)：
```toml
[remote]
enabled = true
server_url = "wss://your-server.com/ws/bridge"
token = "your-auth-token"
auto_connect = true
```

## 文档

- [安装指南](INSTALL_GUIDE.md)
- [LLM API 配置指南](llm_api_guide/)
- [开发文档](docs/)
- [研发方案与进度表](../WinClaw详细研发方案与进度表.md)

## 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_smoke.py
pytest tests/test_integration.py

# 带覆盖率
pytest --cov=src tests/
```

## 许可证

MIT License

## 作者

Weclaw Team

## 跨平台支持

Weclaw 基于 Python 开发，天生具有跨平台能力。虽然主要在 Windows 环境开发，但通过简单配置即可在 macOS 和 Linux 上运行。

- 🪟 **Windows**: 完整支持（主要开发平台）
- 🍎 **macOS**: 核心功能支持，部分系统工具需适配
- 🐧 **Linux**: 核心功能支持，已在 Ubuntu 22.04 测试

详细部署指南请参考：[跨平台部署文档](docs/CROSS_PLATFORM_GUIDE.md)

## Weclaw vs 在线 AI 助手

还在用只能"聊聊天"的在线 AI？Weclaw 让你拥有一个**真正能干活**的 AI 桌面管家：

- 📂 **帮你操作电脑**：文件管理、截图、运行命令...
- 🌐 **帮你操控浏览器**：自动填表、数据抓取、网页操作...
- 🎙️ **语音交互**：说话就能指挥 AI 干活
- 📱 **手机远程控制**：出门在外也能指挥家里电脑上的 AI
- 💾 **隐私安全**：所有数据本地存储，不用担心泄露

**一句话总结**：Weclaw = **本地版 ChatGPT + 22个专业工具 + 手机远程控制**，同等能力，更低成本，更高隐私！

---

让 AI 成为你的效率助手！（Windows/macOS/Linux）
