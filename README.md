# Weclaw

> 你的随身 AI 桌面管家 - 51+ 工具 + 移动端远程控制

**版本**: v2.19.0
**更新日期**: 2026 年 3 月 23 日

Weclaw 是一款**轻量级但功能强大**的跨平台 AI 桌面助手。它**身材小巧**（仅 Python 环境即可运行），但**内含 51+ 实用工具**，从文件管理、浏览器自动化到语音交互 OCR 识别样样精通。

更特别的是，Weclaw 支持**自建服务器 + PWA 移动端**，让你在手机上也能远程指挥桌面 AI，真正实现"**AI 随时随地为你服务**"的体验。

## 为什么选择 Weclaw？

| 对比维度 | Weclaw | 在线 AI 助手（如 ChatGPT） |
|----------|--------|---------------------------|
| **部署方式** | 🏠 本地部署，数据留在自己电脑 | ☁️ 云端服务，数据上传第三方 |
| **工具能力** | 🔧 51+ 实用工具，直接操作电脑 | 💬 仅限对话，无法实际操作 |
| **网络依赖** | 🌐 离线也能运行核心功能 | ❌ 断网即失联 |
| **移动端** | 📱 自建 PWA，手机远程指挥 | 📱 依赖官方 App，功能受限 |
| **定制化** | 🛠️ 完全开源，可随意定制 | ⚙️ 受限的 API 和插件 |
| **隐私安全** | 🔒 数据本地存储，自主掌控 | ⚠️ 数据需上传云端 |
| **成本** | 💰 按需付费，仅付 API 费用 | 💰 按订阅付费，价格较高 |
| **响应速度** | ⚡ 本地运行，无网络延迟 | ⏳ 受网络和服务器负载影响 |

**简单来说**：Weclaw = **本地部署的 ChatGPT + 38+ 专业工具 + 移动端远程控制**，让你真正拥有 一个能"干活"的 AI 助手！

## 功能特性

### 核心能力

- **AI 对话交互**：支持多模型接入（DeepSeek、OpenAI、Claude、Llama 等），自然语言理解与回复
- **智能工具调用**：AI 能够自动调用各种工具执行实际操作，而不仅仅是对话
- **工作流引擎**：支持定义多步骤工作流，自动化复杂任务
- **定时任务**：内置 Cron 定时任务系统，支持计划任务管理

### 实用工具集（51+ 工具）

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
| **文档处理** | PDF 处理、格式转换、PPT 生成、合同/简历生成 | ✅ 全平台 |
| **数据分析** | 数据处理、数据可视化、财务报表 | ✅ 全平台 |
| **AI 创作** | AI 写作、思维导图、教育学习 | ✅ 全平台 |
| **多媒体扩展** | 证件照处理、GIF 制作、语音转文字 | ✅ 全平台 |
| **开发工具** | 编程辅助、文献检索 | ✅ 全平台 |
| **高拍仪** | 文档扫描、试卷解析、作业批改 | ✅ 全平台 |

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
│   ├── tools/         # 工具集（51+ 工具）
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

- ✅ Phase 0：MVP 快速验证（500 行代码跑通核心链路）
- ✅ Phase 1：核心骨架（配置系统、事件总线、会话管理、权限审计）
- ✅ Phase 2：GUI + 扩展工具（PySide6 界面、51+ 工具）
- ✅ Phase 3：高级功能（工作流引擎、定时任务、语音交互、自动更新、打包安装）
- ✅ Phase 6：工具扩展方案（16 个新工具、77 个 Actions、8 大领域覆盖）

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

### 最新版本 (v2.19.0)

**发布日期**: 2026-03-23

### 功能增强 🚀

#### 持续对话 CFTA 异步优化 🎙️
- ✅ 实现 CFTA (Chat-First, Tools-Async) 架构，语音模式先快速聊天后异步工具
- ✅ 三级分流设计：根据意图置信度路由到纯聊天 / 聊天+异步工具 / 口语确认+标准工具
- ✅ 新增 `chat_stream_voice_fast()` 快速聊天流（无工具 Schema，减少 2000+ tokens）
- ✅ 新增 `process_deferred_tools()` 后台异步工具检测与执行
- ✅ 双锁并发机制（chat_lock + deferred_lock），异步工具不阻塞新聊天
- ✅ 新增 `voice_message_sent` 信号，语音模式独立信号链
- ✅ 新增 DEFERRED_TOOL_STARTED / DEFERRED_TOOL_RESULT 事件类型
- ✅ fire-and-forget + cancel 策略，新请求自动取消上一次后台任务

### 性能提升 📊
- 📝 纯聊天场景（80%+）TTFT 从 3-5秒降至 1-2秒，改善 50-60%
- 📝 需要工具的场景首次出声从 5-15秒降至 ~1秒（口语确认）
- 📝 文本输入和 PWA 远程控制零影响

---

### v2.18.0

**发布日期**: 2026-03-24

### 新增功能 🎉

#### 高拍仪文档扫描工具 📷
- ✅ 新增 `document_scanner` 工具，专门处理高拍仪扫描的试卷、作业等文档
- ✅ 4 个核心 Actions：scan_file（单文件）、scan_folder（批量）、query_history（查询）、clear_cache（清理）
- ✅ GLM-4.6V 视觉模型智能题目识别和详细解答生成
- ✅ SQLite 数据库持久化存储所有解析结果
- ✅ 基于 SHA256 文件指纹的智能缓存机制，避免重复解析
- ✅ 支持批量处理和增量更新，自动跳过已处理文件
- ✅ 输出 Markdown 格式解答和 JSON 结构化数据
- ✅ 默认扫描目录：`D:/python_projects/weclaw/docs/deli_scan_image`

### 技术改进 🔧
- 📝 意图识别新增 16 个高拍仪相关关键词：高拍仪、扫描仪、扫描文档、扫一下、扫试卷等
- 📝 添加完整的 Prompt 使用指南和选择决策树
- 📝 工具总数：51 个启用工具
- 📝 全链路验证通过（6/7）
- 📝 性能优化：缓存命中<1 秒，首次解析 30-60 秒，重复扫描提升 30-60 倍

---

### 最新版本 (v2.17.0)

**发布日期**: 2026-03-24

### 新增功能 🎉

#### 家庭成员课程表管理 📅
- ✅ 新增 `course_schedule` 工具，支持家庭成员周课程表管理
- ✅ 5 个核心 Actions：create_schedule、query_schedule、add_course、edit_course、delete_course
- ✅ 支持 4 种课程类型（课程/课间/活动/休息）
- ✅ 双轨机制设计（Skill + Tool）
- ✅ 时间冲突自动检测
- ✅ 配套命令行工具脚本

### 技术改进 🔧
- 📝 意图识别新增 4 个关键词：课程表、课表、上课安排、学习计划
- 📝 工具总数：51 个启用工具
- 📝 全链路验证通过

---

### 最新版本 (v2.16.0)

**发布日期**: 2026-03-24

### 新增功能 🎉

#### 家庭成员营养食谱管理 🍽️
- ✅ 新增 `meal_menu` 工具，支持学校食谱和家庭食谱管理
- ✅ 7 个核心 Actions：create_menu、query_menu、add_dish、edit_dish、delete_dish、parse_image、list_menus
- ✅ 支持图片解析创建食谱（GLM-4.6V 视觉模型）
- ✅ 创新的双轨机制设计（Skill + Tool）
- ✅ 简洁的菜品数据结构（菜名必填，数量和描述可选）
- ✅ 周标识格式（YYYY-Www）便于管理

### 技术改进 🔧
- 📝 意图识别新增 6 个关键词：食谱、菜单、学校食谱、家庭食谱、今天吃什么、营养食谱
- 📝 工具总数：50 个启用工具
- 📝 全链路验证通过（6/7）

---

### 最新版本 (v2.15.0)

**发布日期**: 2026-03-24

### 新增功能 🎉

#### 家庭成员管理工具 👨‍👩‍👧‍👦
- ✅ 创建家庭成员档案（支持 12 种关系类型）
- ✅ 查询家庭成员列表和详情（按 ID/姓名/关系筛选）
- ✅ 更新家庭成员信息（支持部分字段更新）
- ✅ 删除家庭成员记录（二次确认 + 监护人依赖检查）
- ✅ 获取家庭关系图谱（结构化展示）
- ✅ 智能生日提醒（自动计算距离生日天数）

### 技术改进
- 📝 新增专业工具模块 `src/tools/family_member.py` (853 行)
- 📝 扩展意图识别维度（添加 `communication` 意图）
- 📝 完善工具注册表和配置管理
- 📝 添加工具链全链路验证
- 📝 修复 `meal_menu` 工具集成问题

### 测试与文档
- ✅ 单元测试全部通过 (9/9)
- ✅ 全链路一致性验证通过 (6/7)
- 📚 详细使用指南 `docs/FAMILY_MEMBER_TOOL_GUIDE.md`
- 📚 快速参考手册 `FAMILY_MEMBER_QUICKREF.md`
- 📚 开发报告 `FAMILY_MEMBER_DEVELOPMENT_REPORT.md`

---

### 最新版本 (v2.14.1)

**发布日期**: 2026-03-22

### Bug修复 🐛

#### 消息卡片TTS连续播放修复 🏗️
- ✅ 修复 emoji 正则表达式覆盖 CJK 汉字范围导致中文被清空的问题
- ✅ 同步 v2.9.4 经验到 tts_player.py（清理 _activeEngines 缓存）
- ✅ 添加同步停止机制避免连续播放冲突
- ✅ Windows COM 初始化/反初始化确保线程安全

### 技术改进
- 📝 添加 `_stop_event = threading.Event()` 用于同步等待旧任务完成
- 📝 每次播放前清理 pyttsx3._activeEngines 缓存
- 📝 显式指定 `driverName='sapi5'` 驱动

---

### 最新版本 (v2.14.0)

**发布日期**: 2026-03-22

### UI 重构 + 功能增强 🏗️

#### 历史对话 TAB页面集成与按钮样式优化 📋
- ✅ 将顶部"历史对话"按钮迁移到右侧 TAB面板（第 4 个 TAB）
- ✅ 完整功能：搜索框、排序器（时间↓/↑、消息数↓/↑）、会话卡片
- ✅ 会话卡片：标题、更新时间、消息数、打开/删除按钮
- ✅ 支持按关键词搜索会话标题
- ✅ 支持按时间和消息数量升序/降序排列
- ✅ 最多显示 50 条历史记录
- ✅ 空状态提示友好
- ✅ 移除顶部工具栏历史对话按钮，简化界面

### 技术改进
- 📝 新增 3 个信号：`history_refresh_requested`、`history_session_selected`、`history_session_delete_requested`
- 📝 实现懒加载模式（TAB 切换时才加载数据）
- 📝 使用 padding + min-width/max-width 替代 setFixedSize（避免文字截断）
- 📝 使用中文文字替代 emoji 图标（确保所有主题下可见）
- 📝 继承主题颜色而非硬编码（自动适配明暗主题）
- 📝 清空列表时保留空状态标签（避免误删）
- 📝 同时删除数据库和内存中的会话数据

---

## 最新版本 (v2.13.1)

**发布日期**: 2026-03-22

### 性能优化 ⚡

#### 设置对话框性能优化 🏗️
- ✅ 对话框加载速度从 4-15 秒优化到 0.35 秒（提升 10-40 倍）
- ✅ 设备状态异步加载（QThread + Signal/Slot）
- ✅ API Key 延迟加载（QTimer 分阶段初始化）
- ✅ 版本号获取延迟（避免重型模块导入阻塞 UI）
- ✅ MCP Server 列表异步加载
- ✅ 新增 DeviceStatusLoader 类支持取消机制

### 技术改进
- 📝 使用 QTimer.singleShot() 延迟非关键初始化
- 📝 QThread 处理网络请求和文件 IO
- 📝 Signal/Slot 线程间安全通信
- 📝 闭包变量正确捕获（lambda 默认参数）
- 📝 新增 3 个性能测试脚本验证优化效果

---

### 最新版本 (v2.13.0)

**发布日期**: 2026-03-22

### Bug修复 + 功能增强 🛠️

#### 远程绑定TAB页面优化与QThread崩溃修复 🏗️
- ✅ 修复设置窗体打开时 QThread 崩溃问题（线程生命周期管理优化）
- ✅ "绑定设备"改为"绑定用户"，准确反映绑定的是账号而非设备
- ✅ 绑定后显示用户名和Token（脱敏显示）
- ✅ 已绑定时按钮显示"重新绑定"并需确认
- ✅ "解绑用户"按钮未绑定时禁用
- ✅ 服务器端 DeviceInfoResponse 添加 username 字段

### 技术改进
- 📝 QThread 类移到模块级别，设置正确的 parent
- 📝 使用 showEvent 延迟启动后台任务
- 📝 使用 QueuedConnection 确保跨线程信号安全
- 📝 closeEvent 中正确等待线程结束

---

### v2.15.0 (2026-03-24)
- ✅ 家庭成员管理工具上线：专业的家庭成员档案管理系统
- ✅ 支持 5 个核心 Actions（创建/查询/更新/删除/关系图谱）
- ✅ 12 种家庭关系类型，18 个数据字段
- ✅ 智能生日提醒和监护人机制
- ✅ 全链路验证通过，单元测试 100% 覆盖
- ✅ 修复 meal_menu 工具集成问题

---

### v2.14.0 (2026-03-22)
- ✅ 历史对话 TAB页面集成：将顶部按钮迁移到右侧面板（第 4 个 TAB）
- ✅ 完整功能：搜索、排序（时间↓/↑、消息数↓/↑）、会话卡片（打开/删除）
- ✅ 按钮样式优化：使用 padding + min-width/max-width，中文文字替代 emoji
- ✅ 懒加载模式：TAB 切换时才加载数据
- ✅ 清空列表逻辑优化：保留空状态标签，避免误删

### v2.13.1 (2026-03-22)
- ✅ 设置对话框性能优化：加载速度从 4-15 秒优化到 0.35 秒（提升 10-40 倍）
- ✅ 设备状态异步加载（QThread + Signal/Slot，支持取消机制）
- ✅ API Key 延迟加载（QTimer 分阶段初始化，避免集中阻塞）
- ✅ 版本号获取延迟（避免 aiohttp 重型模块导入）
- ✅ MCP Server 列表异步加载
- ✅ 新增性能测试脚本验证优化效果

### v2.13.0 (2026-03-22)
- ✅ 修复设置窗体 QThread 崩溃问题（线程生命周期管理）
- ✅ 远程绑定TAB页面优化：文案改为"绑定用户"、显示用户名和Token
- ✅ 按钮逻辑优化：已绑定时显示"重新绑定"需确认

### v2.12.0 (2026-03-22)

#### 主动陪伴智能系统 (Life Companion Intelligence) 💝
- ✅ **CompanionEngine 陪伴引擎** — 核心调度器，评分算法(0-100)、定时/上下文/用户主动三种触发模式
- ✅ **UserProfile 用户档案工具** — 3张数据库表 + 8个Actions，完整用户画像管理
- ✅ **CareTopicRegistry 关怀主题注册表** — 15个预定义关怀主题 + 5步渐进建档 + 5条行为推断规则
- ✅ **CooldownManager 防骚扰机制** — 每日预算5次、连续限制2次、拒绝惩罚、asyncio.Lock 交互锁
- ✅ **MoodDetector 情绪感知** — 关键词匹配检测 5 种情绪状态（positive/negative/neutral/stressed/tired）
- ✅ **用户主动触发关怀** — 关键词匹配绕过冷却直接触发关怀回应
- ✅ **GUI 集成** — 💝前缀关怀消息显示 + TTS 语音播报 + EventBus 事件解耦
- ✅ **30分钟间隔调度器** — 自动检查关怀时机，懒加载随应用启动

### 系统集成
- 📝 events.py 新增 4 个 companion 事件类型 + 2 个数据类
- 📝 prompts.py 新增 COMPANION_PROMPT_MODULE + DEFAULT_SYSTEM_PROMPT
- 📝 agent.py 默认系统提示注入陪伴模块
- 📝 tools.json / registry.py / tool_exposure.py 完成 user_profile 工具注册
- 📝 conversation/manager.py 新增 WAITING_COMPANION_RESPONSE 会话状态
- 🎨 新增约 2,681 行核心代码，修改 8 个文件

---

### v2.11.1 (2026-03-22)
- ✅ prompts.py 意图识别体系优化：新增 7 个意图维度，补全 16 个新工具映射
- ✅ CORE_SYSTEM_PROMPT 扩展至 6,029 字符，新增 6 个工具场景决策树
- ✅ 关键词冲突解决 + 遗留配置清理
- ✅ 15/15 意图识别测试通过

### v2.11.0 (2026-03-22)
- ✅ Phase 6 工具扩展方案：新增 16 个工具、77 个 Actions
- ✅ 覆盖文档处理、数据分析、AI 创作、多媒体、教育、编程等 8 大领域
- ✅ 7 批次交付，135 个测试用例 100% 通过
- ✅ 条件导入 + 降级策略，最大化兼容性

### v2.10.0 (2026-03-22)
- ✅ 桌面端 UI 布局全面优化：窗体位置、底栏整合、消息气泡、输入栏、面板宽度

### v2.9.4 (2026-03-21)
- ✅ 修复语音输出工具连续播放静音问题（pyttsx3 `_activeEngines` 全局缓存清理）
- ✅ qasync 环境 COM 初始化/反初始化保障

### v2.9.3 (2026-03-21)

### Bug修复 + 功能增强 🛠️

#### 远程 PWA 请求状态显示与并发控制优化 🏗️
- ✅ 修复远程 PWA 请求时桌面端工具卡片状态不显示的问题
- ✅ 新增 EventBus 事件订阅机制统一本地和远程请求 UI 反馈
- ✅ 引入 asyncio.Lock 并发序列化锁防止多客户端 Session 污染
- ✅ 增加排队通知机制提升用户体验（⏳ 请求已排队）
- ✅ 工具日志带 📱[PWA:用户名] 前缀标识来源
- ✅ TypeScript 接口扩展支持 queued 消息类型

### 技术改进
- 📝 新增 `_get_username_for_user()` 方法查找用户名
- 📝 新增 `_setup_remote_events()` 方法订阅 4 个远程事件
- 🎨 懒加载 property 实现 `chat_lock`
- 🎨 finally 块确保锁一定释放，避免死锁

---

### v2.9.2 (2026-03-21)
- ✅ 修复 Token 用量面板显示问题（输入/输出始终为 0）
- ✅ 新增 ModelRegistry 聚合属性统计 Token 用量

### v2.9.0 (2026-03-14)
- ✅ 管理后台 CDN 资源本地化（Tailwind CSS、Chart.js）
- ✅ 启动性能优化（Whisper 懒加载、MCP Server 并行连接）
- ✅ 启动时间减少约 15 秒

### v2.8.0 (2026-03-13)
- ✅ 远程绑定持久化修复（JWT Token 安全存储）
- ✅ 后台管理系统研发（用户管理、设备管理、日志中心）
- ✅ 安全加固（禁止跨用户绑定、数据库唯一索引）
- ✅ Tool Call 消息完整性修复

### v2.7.3 (2026-03-02)
- ✅ PWA-Weclaw 双向通信闭环修复
- ✅ 多设备消息隔离（pendingMessageIds 过滤器）
- ✅ 性能优化（移除频繁日志，日志量减少 95%+）
- ✅ 离线容错增强（重连后自动恢复队列）

### v2.7.2 (2026-02-26)
- ✅ PWA 离线消息队列系统（数据库 + 内存双写）
- ✅ PWA 端 Markdown 渲染增强（marked 库集成）
- ✅ 监控告警模块（健康检查、积压告警）
- ✅ 国际化支持（中英双语错误提示）

### v2.7.1 (2026-02-21)
- ✅ Bridge 远程桥接模式（WebSocket 客户端）
- ✅ 服务器端 Bridge 端点（/ws/bridge）
- ✅ 支持独立服务器模式和内嵌模式

### v2.7.0 (2026-02-21)
- ✅ 远程移动端支持（PWA）
- ✅ FastAPI 后端服务（RESTful API + WebSocket）
- ✅ JWT + RSA 混合认证机制
- ✅ Vue 3 + Vite + Vant UI 移动端

### v2.6.0 (2026-02-21)
- ✅ 远程服务端模块（remote_server）
- ✅ 认证系统（JWT/RS256、RSA、用户管理）
- ✅ REST API 端点（auth/chat/status/files/commands）
- ✅ WebSocket 实时通信

### v2.5.2 (2026-02-21)
- ✅ 任务锚定机制智能优化（ExecutionTracker）
- ✅ 智能锚定消息构建（根据执行状态动态调整）
- ✅ 避免重复操作和无限循环

### v2.5.1 (2026-02-21)
- ✅ UI 组件销毁保护（RuntimeError 修复）
- ✅ 右侧工具执行状态卡片显示修复
- ✅ 三重保护机制（属性检查、try-except、安全包装）
- ✅ UI 布局优化（移除空白留白）

### v2.5.0 (2026-02-21)
- ✅ Phase 6 微观进化（神经网络自主学习）
- ✅ 增强 STDP 规则（多巴胺/ACh 门控）
- ✅ 结构可塑性（突触修剪与新生）
- ✅ 稳态突触缩放（防止活动爆炸/沉寂）
- ✅ 资格迹机制（延迟强化学习）
- ✅ 进化监控 Dashboard

### v2.4.0 (2026-02-21)
- ✅ Dashboard 性能优化（表征桥接可视化缓存）
- ✅ 发育面板体验日志修复
- ✅ litellm RuntimeWarning 警告抑制

### v2.3.0 (2026-02-21)
- ✅ Phase 5 发育引擎 Dashboard 集成
- ✅ 独立发育面板窗体（746 行）
- ✅ 意识仪表盘 + 发育进度 + 表征桥接 + 语义锚定

### v1.2.2 (2026-02-18)
- ✅ 语音对话系统重构（线程安全）
- ✅ TTSPlayer Worker+QThread 正确模式
- ✅ VoiceRecognizer 信号安全发射
- ✅ ConversationManager Watchdog 超时恢复

### v1.2.1 (2026-02-17)
- ✅ 定时任务系统稳定性修复
- ✅ UI 编辑对话框崩溃修复
- ✅ AI 误用 Linux 命令修复
- ✅ 编码问题修复（UTF-8）

### v1.2.0 (2026-02-18)
- ✅ 录音功能整体优化
- ✅ VAD 智能录音（说完自动停止）
- ✅ 持续对话模式信号链修复
- ✅ 录音配置化（default.toml）

### v2.1.0 (2026-02-20)
- ✅ Phase 4 LLM 集成模块优化
- ✅ Dashboard LLM 认知增强面板（4 Tab 页）
- ✅ 自动反思触发机制（每 200 周期）
- ✅ 反思报告存入情景记忆
- ✅ Markdown 导出增强（第 7 章）

### v2.0.0 (2026-02-19)
- ✅ Phase 4 LLM 认知增强 Dashboard 集成
- ✅ 自我反思/元认知/意识对话/参数建议
- ✅ QThread 异步模式避免 UI 卡顿

### v1.1.0 (2026-02-17)
- ✅ Phase 7 全链路追踪系统（TaskTrace）
- ✅ 新工具纳入规范（onboarding_checklist）
- ✅ 工具废弃流程（deprecated 字段）
- ✅ 离线分析脚本（analyze_traces.py）

### v1.0.24 (2026-02-17)
- ✅ Phase 6 工具调用全链路优化
- ✅ 渐进式工具暴露引擎（三层 Schema）
- ✅ 多维度意图识别增强
- ✅ 单次工具调用数量限制（MAX_TOOLS_PER_CALL=3）
- ✅ 分级错误反馈

### v1.0.23 (2026-02-16)
- ✅ 录音可视化弹窗（VoiceRecordDialog）
- ✅ 音量波形动画 + 倒计时进度条
- ✅ 支持两种触发路径（工具栏按钮/AI Agent 调用）

### v1.0.22 (2026-02-16)
- ✅ 定时任务对话框崩溃修复
- ✅ browser-use provider 属性错误修复
- ✅ MCP 工具重复注册警告修复
- ✅ 全局快捷键异常处理改进

### v2.18.0 (2026-03-24)
- ✅ 高拍仪文档扫描工具开发
- ✅ GLM-4.6V 视觉模型集成
- ✅ SQLite 缓存机制
- ✅ 全链路意图识别集成

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

**一句话总结**：Weclaw = **本地版 ChatGPT + 38 个专业工具 + 手机远程控制**，同等能力，更低成本，更高隐私！

---

让 AI 成为你的效率助手！（Windows/macOS/Linux）


**当前版本**: v2.19.0 (2026-03-23)
