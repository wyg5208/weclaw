# WinClaw 服务器日志系统使用指南

## 目录结构

```
winclaw_server/
├── logs/                          # 日志目录（自动创建）
│   ├── remote_server.log          # 主日志文件
│   ├── remote_server_2026-02-26.log  # 历史日志
│   └── error_2026-02-26.log       # 错误日志
├── config/
│   └── logging.toml               # 日志配置文件
├── scripts/
│   └── view_logs.py               # 日志查看脚本
└── pwa/
    ├── .env                       # 开发环境日志配置
    └── .env.production            # 生产环境日志配置
```

## 后端日志系统特性

### ✅ 已实现功能

1. **双路输出**
   - 控制台输出（简单格式）
   - 文件输出（详细格式）

2. **自动轮转**
   - 按天轮转（可配置为小时/周）
   - 保留最近 7 天（可配置）
   - 自动清理过期日志

3. **错误分离**
   - 错误日志单独记录到 `error_*.log`
   - 便于快速定位问题

4. **HTTP 请求日志**
   - 自动记录所有 HTTP 请求
   - 包含请求方法、路径、耗时、状态码
   - 中间件自动注入，无需手动调用

5. **PWA 日志接收**
   - 提供 `/api/logs/pwa` 接口
   - 接收 PWA 端上报的日志
   - 自动分类记录到服务器日志

## 前端日志系统特性

### ✅ 已实现功能

1. **统一 Logger**
   - `logger.debug()` / `logger.info()` / `logger.warn()` / `logger.error()`
   - 支持级别控制
   - 自动过滤敏感信息

2. **智能上报**
   - ERROR 级别立即上报
   - 其他级别批量上报（20 条或 5 秒）
   - 离线缓存（网络恢复后上报）

3. **会话追踪**
   - 自动生成 session ID
   - 记录用户操作上下文
   - 便于问题复现和追踪

## 使用方法

### 1. 启动服务器（自动初始化日志）

```bash
cd winclaw_server/remote_server
python main.py
```

启动后会看到：
```
[INFO] root: ============================================================
[INFO] root: WinClaw 远程服务启动
[INFO] root: ============================================================
[INFO] root: 监听地址：127.0.0.1:8188
[INFO] root: 日志系统初始化完成
[INFO] root: 日志目录：D:\...\winclaw_server\logs
[INFO] root: 日志级别：INFO
[INFO] root: 轮转策略：daily
[INFO] root: 保留天数：7
[INFO] root: 错误日志已启用单独记录
```

### 2. 查看实时日志

```bash
# 查看最新 100 行
python scripts/view_logs.py --tail 100

# 只看今天的日志
python scripts/view_logs.py --today

# 持续跟踪（类似 tail -f）
python scripts/view_logs.py --follow

# 只看 ERROR 级别
python scripts/view_logs.py --level ERROR --follow

# 搜索关键词
python scripts/view_logs.py --search "WebSocket" --follow

# 查看 PWA 上报的日志
python scripts/view_logs.py --source pwa --follow
```

### 3. 配置日志级别

编辑 `config/logging.toml`:
```toml
[logging]
level = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
rotation = "daily"  # hourly, daily, weekly
backup_count = 7  # 保留天数
separate_error_log = true  # 是否单独记录错误日志
```

### 4. PWA 前端使用示例

```typescript
import { logger } from '@/utils/logger';

// 记录 API 请求
logger.info('API 请求', {
  url: '/api/chat',
  method: 'POST',
  params: { sessionId: 'xxx' }
});

// 记录错误
logger.error('WebSocket 连接失败', {
  retryCount: 3,
  lastError: 'timeout'
});

// 记录用户操作
logger.info('用户发送消息', {
  messageLength: 100,
  hasAttachment: false
});
```

## 日志文件说明

### remote_server.log
主日志文件，包含：
- 应用启动/关闭信息
- HTTP 请求日志
- WebSocket 连接事件
- 组件初始化信息
- 错误日志摘要

### error_YYYY-MM-DD.log
错误日志文件，包含：
- ERROR 级别及以上的所有日志
- 异常堆栈信息
- PWA 上报的错误

## 最佳实践

### 后端

✅ **推荐**
```python
from .logging_config import get_logger

logger = get_logger(__name__)

# 结构化日志
logger.info("工具调用成功：%s.%s (耗时 %.2fs)", tool_name, action_name, duration)

# 带上下文的错误日志
try:
    result = await call_tool()
except Exception as e:
    logger.error(f"工具调用失败：{e}", extra={
        "tool_name": tool_name,
        "params": params,
        "user_id": user_id
    }, exc_info=True)
```

❌ **避免**
```python
# 手动拼接字符串
logger.info(f"工具调用成功：{tool_name}.{action_name}")

# 捕获异常但不记录详情
try:
    ...
except Exception as e:
    logger.error("出错了")
```

### 前端

✅ **推荐**
```typescript
// 关键操作记录日志
logger.info('[Chat] 发送消息', { sessionId, length: message.length });

// 错误带上上下文
logger.error('[API] 请求失败', { 
  url, 
  method, 
  statusCode: error.status 
});

// 性能埋点
logger.debug('[Perf] 页面加载完成', {
  loadTime: performance.now(),
  resourceCount: resources.length
});
```

❌ **避免**
```typescript
// 记录敏感信息
logger.info('用户登录', { password: user.password });

// 过度详细的调试日志
logger.debug('循环第 1 次');
logger.debug('循环第 2 次');
...
```

## 故障排查

### 问题 1：看不到日志输出

**检查清单**：
1. 确认日志级别设置正确（INFO 能看到 INFO/WARNING/ERROR）
2. 检查 `logs/` 目录是否存在
3. 查看控制台是否有 `[Logger] 日志上报失败` 错误

### 问题 2：日志文件过大

**解决方案**：
1. 调整 `backup_count` 减少保留天数
2. 生产环境日志级别设为 WARNING 或以上
3. 关闭 WebSocket 消息日志（`log_websocket_messages = false`）
4. 定期运行清理脚本

### 问题 3：PWA 日志不上报

**检查步骤**：
1. 浏览器控制台是否有网络错误
2. 检查 `.env` 中的 `VITE_ENABLE_LOG_REPORTING` 是否为 `true`
3. 确认后端 `/api/logs/pwa` 接口可访问
4. 查看 Network 面板是否有 4xx/5xx 错误

## 性能影响

### 后端
- 日志系统开销：< 1ms/条
- 文件轮转：每天一次，影响可忽略
- HTTP 中间件：增加约 0.5ms 延迟

### 前端
- 控制台输出：< 0.1ms/条
- 批量上报：每 5 秒一次，约 10-50ms
- 内存占用：缓冲区最大 20 条约 10KB

## 隐私保护

⚠️ **重要提醒**：

1. **不上报敏感信息**
   - 密码、token、密钥
   - 个人隐私数据
   - 完整的用户 ID（只显示前 8 位）

2. **生产环境建议**
   - 日志级别设为 WARNING
   - 关闭详细请求日志
   - 定期清理旧日志
   - 监控磁盘空间

3. **GDPR 合规**
   - 用户有权知道记录了什么
   - 提供日志删除机制
   - 不记录个人身份信息

---

**最后更新**: 2026-02-26
**维护者**: WinClaw Team
