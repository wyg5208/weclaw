# 设备绑定 UNIQUE 约束冲突修复说明

## 问题描述

在 PWA 手机端绑定设备到 WinClaw 桌面端时，输入 64 位 TOKEN 后绑定失败，服务器报错：

```
sqlite3.IntegrityError: UNIQUE constraint failed: device_bindings.binding_token
```

## 问题原因

1. **历史遗留问题**：之前的代码在绑定成功后，将 `binding_token` 字段更新为空字符串 `''`，而不是设置为 `NULL` 或删除记录
2. **唯一约束冲突**：数据库表定义中 `binding_token` 有 `UNIQUE` 约束，当多次使用同一个 token 尝试绑定时，会导致唯一性冲突
3. **重复记录**：用户可能多次生成绑定 token，导致存在多条 `status='pending'` 的记录

## 修复方案

### 1. 代码层面修复（已完成）

修改了 `user_manager.py` 中的两个关键方法：

#### `generate_binding_token()` 方法
- 添加了过期记录清理逻辑（清理超过 10 分钟的 pending 记录）
- 确保每次生成的 token 都是唯一的

#### `bind_device()` 方法
- 将绑定成功后的 `binding_token` 设置为 `NULL` 而不是空字符串
- 添加并发检查，防止同一用户同时有多个活跃绑定
- 清理该用户的其他所有 pending 记录

### 2. 数据修复脚本

创建了 `fix_device_bindings.py` 脚本，用于清理历史遗留问题数据：

```bash
# 在服务器目录下执行
cd remote_server
python scripts/fix_device_bindings.py
```

脚本功能：
1. 将 `binding_token = ''` 的记录更新为 `binding_token IS NULL`
2. 删除重复的 pending 记录
3. 检查并报告剩余的重复 token

### 3. 服务器启动时自动修复

修改了 `main.py`，在服务器启动时自动执行修复逻辑：

```python
# 修复设备绑定表的历史遗留问题（UNIQUE 约束冲突）
try:
    from .scripts.fix_device_bindings import fix_database
    fix_database()
    logger.info("设备绑定表修复完成")
except Exception as e:
    logger.warning(f"修复设备绑定表失败：{e}")
```

## 操作步骤

### 对于新用户（数据库未创建）

无需任何操作，服务器启动时会自动创建正确的表结构。

### 对于已有用户（数据库已存在）

1. **停止服务器**（如果正在运行）
2. **备份数据库**（可选但推荐）：
   ```bash
   cp data/remote_users.db data/remote_users.db.backup
   ```
3. **重启服务器**：
   ```bash
   # 在项目根目录
   python -m winclaw_server.remote_server.main
   ```
   
   服务器会自动执行修复脚本，日志中会显示：
   ```
   [INFO] 设备绑定表修复完成
   ```

4. **验证修复结果**：
   - 查看服务器日志，确认没有 UNIQUE constraint 错误
   - 尝试重新绑定设备，应该可以正常工作

### 手动执行修复（可选）

如果服务器启动失败或想手动修复：

```bash
cd remote_server
python scripts/fix_device_bindings.py
```

输出示例：
```
使用数据库：D:\python_projects\weclaw\winclaw_server\remote_server\data\remote_users.db

=== 修复前的数据状态 ===
总记录数：5
binding_token 为空字符串的记录数：3
binding_token 为 NULL 的记录数：2
status 为 pending 的记录数：3
status 为 active 的记录数：2

=== 开始修复 ===
已更新 3 条记录：binding_token 从空字符串设为 NULL
已删除 1 条重复的 pending 记录

✓ 未发现重复的 binding_token

=== 修复后的数据状态 ===
总记录数：4
binding_token 为空字符串的记录数：0
binding_token 为 NULL 的记录数：4
status 为 pending 的记录数：2
status 为 active 的记录数：2

✓ 数据库修复完成！
```

## 预防措施

为避免此类问题再次发生，代码中已添加以下预防措施：

1. **Token 过期机制**：生成的绑定 token 有效期为 10 分钟，超时自动清理
2. **唯一用户绑定限制**：每个用户只能有一个活跃的设备绑定
3. **并发控制**：绑定过程中检查是否存在其他活跃绑定
4. **数据清理**：绑定成功后自动清理相关的 pending 记录

## 技术细节

### 数据库表结构

```sql
CREATE TABLE device_bindings (
    binding_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    device_id TEXT,
    device_name TEXT,
    device_fingerprint TEXT,
    binding_token TEXT UNIQUE,  -- 允许为 NULL
    status TEXT DEFAULT 'pending',
    bound_at TEXT,
    last_connected TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
)
```

### 关键修改点

1. **`user_manager.py` 第 373-404 行**：`generate_binding_token()` 方法
2. **`user_manager.py` 第 425-492 行**：`bind_device()` 方法
3. **`main.py` 第 92-98 行**：服务器启动时自动修复

## 相关文件

- `remote_server/auth/user_manager.py` - 用户管理器，处理绑定逻辑
- `remote_server/api/auth.py` - 认证 API，提供绑定接口
- `remote_server/scripts/fix_device_bindings.py` - 数据修复脚本
- `remote_server/main.py` - 服务器入口，集成自动修复

## 联系支持

如遇到问题，请查看服务器日志文件：
- `logs/remote_server.log` - 主日志
- `logs/remote_server.error.log` - 错误日志
