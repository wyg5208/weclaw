# WinClaw 日志系统完善方案

## 现状分析

### 当前问题
1. **GUI 应用日志配置不完整** (`src/ui/gui_app.py:1693-1696`)
   - 只设置了 WARNING 级别
   - 只有基础格式，无文件处理器
   - 启动后看不到执行日志

2. **CLI 应用使用 RichHandler** (`src/app.py:128-135`)
   - 依赖 rich 库进行格式化
   - 同样没有文件日志记录

3. **缺乏统一日志管理**
   - 各模块自行配置 logger
   - 没有统一的日志目录
   - 没有日志轮转机制

### 已发现的配置点
- `src/app.py:setup_logging()` - CLI 入口日志配置
- `src/ui/gui_app.py:main()` - GUI 入口日志配置  
- `src/core/config.py` - 配置管理器（已有 `log_level` 配置项）

## 实施方案

### 阶段一：创建统一日志配置模块

#### 1.1 创建 `src/core/logging_config.py`
**功能**：
- 统一的日志初始化函数
- 同时支持控制台和文件输出
- 支持日志轮转（按大小或时间）
- 可配置的日志级别和格式

**核心特性**：
```python
def setup_logging(
    level: str = "INFO",
    log_dir: Path = None,
    console_output: bool = True,
    file_output: bool = True,
    rotation: str = "daily",  # hourly/daily/size
    max_bytes: int = 10*1024*1024,  # 10MB
    backup_count: int = 7,  # 保留 7 个备份
    format_type: str = "detailed"  # simple/detailed/json
) -> None
```

**日志格式**：
- **简单格式**（适合控制台）：`[LEVEL] message`
- **详细格式**（适合文件）：`%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s`
- **JSON 格式**（可选，适合结构化日志）

#### 1.2 日志目录结构
```
winclaw/
├── logs/                    # 日志根目录（自动创建）
│   ├── winclaw.log         # 主日志文件（最新）
│   ├── winclaw_2026-02-26.log  # 按日期分割
│   ├── error_2026-02-26.log    # 错误日志单独记录
│   └── archive/            # 归档目录（超过 7 天的日志）
```

### 阶段二：集成到应用入口

#### 2.1 修改 `src/ui/gui_app.py`
**修改点**：
```python
from src.core.logging_config import setup_logging

def main() -> int:
    """GUI 应用程序入口。"""
    # 从配置读取日志级别
    from src.core.config import AppConfig
    config = AppConfig.load()
    
    # 设置统一日志
    setup_logging(
        level=config.log_level,  # 支持配置覆盖
        log_dir=Path.cwd() / "logs",
        console_output=True,     # GUI 也显示控制台日志
        file_output=True,
        rotation="daily",
        backup_count=7
    )
    
    logger = logging.getLogger(__name__)
    logger.info("WinClaw GUI 启动...")
    
    app = WinClawGuiApp()
    return app.run()
```

#### 2.2 修改 `src/app.py`
**修改点**：
```python
def setup_logging_wrapper(level: str = "WARNING") -> None:
    """包装统一的日志配置。"""
    from src.core.logging_config import setup_logging as core_setup
    core_setup(
        level=level,
        log_dir=Path.cwd() / "logs",
        console_output=True,
        file_output=True,
        format_type="simple"  # CLI 使用简单格式
    )
```

### 阶段三：配置文件支持

#### 3.1 更新 `config/default.toml`
添加日志配置节：
```toml
[logging]
# 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
level = "INFO"

# 是否启用文件日志
enable_file_log = true

# 日志目录（相对路径或绝对路径）
log_dir = "logs"

# 日志轮转策略：hourly, daily, weekly, size
rotation = "daily"

# 最大文件大小（字节），仅在 rotation="size" 时有效
max_file_size = 10485760  # 10MB

# 保留的日志文件数量
backup_count = 7

# 日志格式：simple, detailed, json
format = "detailed"

# 是否单独记录错误日志
error_log_separate = true
```

### 阶段四：辅助工具

#### 4.1 日志查看脚本 `scripts/view_logs.py`
**功能**：
- 实时查看最新日志（类似 `tail -f`）
- 按级别过滤（只看 ERROR/WARNING）
- 按时间范围过滤
- 关键词搜索

**使用示例**：
```bash
python scripts/view_logs.py              # 实时查看最新日志
python scripts/view_logs.py --level ERROR  # 只看错误
python scripts/view_logs.py --search "browser_use"  # 搜索关键词
python scripts/view_logs.py --today      # 查看今天日志
```

#### 4.2 日志清理脚本 `scripts/cleanup_logs.py`
**功能**：
- 清理超过 N 天的日志
- 压缩旧日志到 zip
- 显示日志目录占用空间

### 阶段五：文档与最佳实践

#### 5.1 日志使用规范
**模块级 logger 命名**：
```python
logger = logging.getLogger(__name__)  # 使用模块全名
# 例如：src.core.agent → "src.core.agent"
```

**日志级别使用指南**：
- `DEBUG`: 详细调试信息（变量值、执行路径）
- `INFO`: 关键流程节点（"任务开始"、"工具调用成功"）
- `WARNING`: 可恢复的异常（"工具调用失败，重试"）
- `ERROR`: 不可恢复的错误（"模型调用失败"）
- `CRITICAL`: 系统级故障（"数据库连接断开"）

**日志消息格式**：
```python
# ✅ 推荐：结构化参数
logger.info("工具调用成功：%s.%s (耗时 %.2fs)", tool_name, action_name, duration)

# ❌ 避免：手动拼接
logger.info(f"工具调用成功：{tool_name}.{action_name} (耗时 {duration:.2f}s)")
```

### 实施计划

| 阶段 | 任务 | 预计时间 | 优先级 |
|------|------|----------|--------|
| 1 | 创建 `src/core/logging_config.py` | 30min | P0 |
| 2 | 修改 GUI 和 CLI 入口集成 | 20min | P0 |
| 3 | 更新配置文件 `config/default.toml` | 10min | P1 |
| 4 | 创建日志查看和清理脚本 | 40min | P2 |
| 5 | 编写日志使用规范文档 | 20min | P3 |

**总计**: 约 2 小时

## 验收标准

✅ **功能完备性**：
- [ ] CMD 窗口能看到实时日志（INFO 级别以上）
- [ ] 日志文件自动保存到 `logs/` 目录
- [ ] 日志按天轮转，保留最近 7 天
- [ ] 错误日志单独记录到 `error_*.log`
- [ ] 支持通过配置调整日志级别

✅ **易用性**：
- [ ] 无需手动配置，开箱即用
- [ ] 提供日志查看脚本
- [ ] 提供日志清理脚本

✅ **可维护性**：
- [ ] 统一的日志接口
- [ ] 清晰的日志格式
- [ ] 完善的文档说明

## 风险与注意事项

⚠️ **性能影响**：
- 日志级别不要设为 DEBUG（输出量太大）
- 生产环境建议使用 INFO 或 WARNING
- 异步写入日志避免阻塞主线程

⚠️ **磁盘空间**：
- 默认保留 7 天日志
- 定期运行清理脚本
- 监控日志目录大小

⚠️ **隐私保护**：
- 日志中不记录敏感信息（API Key、密码等）
- 考虑添加日志脱敏过滤器

---

**请确认此方案是否符合您的需求？如果有特定要求（如日志格式、保留天数等），请告知我进行调整。**