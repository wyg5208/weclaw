# PWA-PC 离线容错与人性化交互优化方案（修订版）

## 一、现状分析

### 1.1 系统架构
```
PWA 前端 <---> 远程服务器 <---> WinClaw 本地 GUI
 (手机)        (云端)          (PC桌面)
```

### 1.2 关键场景梳理

| 场景 | 当前处理 | 问题 |
|------|----------|------|
| **本地 GUI 未启动** | 返回 `NO_DEVICE_BOUND` 错误 | 错误提示不准确（设备可能已绑定，只是离线） |
| **GUI 重启中** | 静默失败 | PWA 无感知，消息丢失 |
| **消息处理中 GUI 崩溃** | 120 秒超时后返回错误 | 超时过长，无主动检测 |
| **网络闪断** | WebSocket 断开，PWA 重连 | 不同步 WinClaw 状态 |
| **GUI 恢复连接** | 仅记录日志 | 不通知 PWA，不恢复中断任务 |

### 1.3 当前代码位置

- **服务器端消息处理**: [winclaw_server/remote_server/websocket/handlers.py](file:///d:/python_projects/openclaw_demo/winclaw/winclaw_server/remote_server/websocket/handlers.py#L174-L238)
- **Bridge 连接管理**: [winclaw_server/remote_server/websocket/bridge_handler.py](file:///d:/python_projects/openclaw_demo/winclaw/winclaw_server/remote_server/websocket/bridge_handler.py#L161-L174)
- **PWA 聊天 Store**: [winclaw_server/pwa/src/stores/chat.ts](file:///d:/python_projects/openclaw_demo/winclaw/winclaw_server/pwa/src/stores/chat.ts)

---

## 二、优化方案

### 2.1 实时状态同步机制

**目标**: PWA 实时感知 WinClaw 在线状态变化

**修改文件**: 
- `winclaw_server/remote_server/websocket/bridge_handler.py`
- `winclaw_server/remote_server/websocket/handlers.py`
- `winclaw_server/pwa/src/stores/device.ts`

**实现要点**:
```python
# bridge_handler.py - 添加 WinClaw 状态广播（带超时控制）
async def broadcast_winclaw_status_change(user_id: str, status: str):
    """广播 WinClaw 状态变化到 PWA（带超时保护）"""
    pwa_manager = context.get_connection_manager()
    if not pwa_manager:
        return
    
    try:
        # ✅ 添加超时控制，避免阻塞
        await asyncio.wait_for(
            pwa_manager.send_message(user_id, {
                "type": "winclaw_status",
                "payload": {
                    "status": status,  # online/offline/reconnecting
                    "timestamp": datetime.now().isoformat()
                }
            }),
            timeout=5.0  # 5 秒超时
        )
    except asyncio.TimeoutError:
        logger.warning(f"广播状态变化超时：user={user_id[:8]}")
    except Exception as e:
        logger.error(f"广播状态变化失败：{e}")
```

**国际化支持**（新增）:
```python
# handlers.py - 使用翻译函数
from ..i18n import get_user_language, t

async def handle_chat_message(...):
    # 获取用户语言偏好
    lang = get_user_language(user_id)  # 'zh_CN' or 'en_US'
    
    if not winclaw_conn:
        user_manager = context.get_user_manager()
        has_bound_device = user_manager and user_manager.has_bound_device(user_id)
        
        if has_bound_device:
            error_code = "DEVICE_OFFLINE"
            # ✅ 使用翻译函数
            message = t("device_offline_msg", lang, 
                       default="您的 WinClaw PC 端当前离线，消息将在其上线后自动发送")
        else:
            error_code = "NO_DEVICE_BOUND"
            message = t("no_device_bound_msg", lang,
                       default="您还没有绑定 WinClaw PC 端，请在设置中完成设备绑定")
```

**i18n 配置文件** (`winclaw_server/i18n/messages.json`):
```json
{
  "zh_CN": {
    "device_offline_msg": "您的 WinClaw PC 端当前离线，消息将在其上线后自动发送",
    "no_device_bound_msg": "您还没有绑定 WinClaw PC 端，请在设置中完成设备绑定"
  },
  "en_US": {
    "device_offline_msg": "Your WinClaw PC is currently offline. Messages will be sent automatically when it comes online.",
    "no_device_bound_msg": "You haven't bound a WinClaw PC yet. Please complete device binding in settings."
  }
}
```

### 2.2 差异化错误提示

**目标**: 区分"未绑定"、"离线"、"忙碌"等状态，提供准确提示

**修改文件**: `winclaw_server/remote_server/websocket/handlers.py`

**错误码设计**:
| 错误码 | 中文提示 | 英文提示 |
|--------|----------|----------|
| `NO_DEVICE_BOUND` | 您还没有绑定 WinClaw PC 端 | No device bound |
| `DEVICE_OFFLINE` | 您的 WinClaw PC 端当前离线 | Device offline |
| `DEVICE_BUSY` | 您的 WinClaw PC 端正忙 | Device busy |
| `DEVICE_RECONNECTING` | WinClaw PC 端正在重连中 | Device reconnecting |

**修改位置**: handlers.py#L188-L200
```python
async def handle_chat_message(...):
    # 优化错误检测逻辑
    winclaw_conn = bridge_manager.get_user_connection(user_id)
    
    if not winclaw_conn:
        # 检查是否有绑定设备
        user_manager = context.get_user_manager()
        has_bound_device = user_manager and user_manager.has_bound_device(user_id)
        
        if has_bound_device:
            error_code = "DEVICE_OFFLINE"
            message = "您的 WinClaw PC 端当前离线，消息将在其上线后自动发送"
        else:
            error_code = "NO_DEVICE_BOUND"
            message = "您还没有绑定 WinClaw PC 端，请在设置中完成设备绑定"
        
        # 存入离线消息队列（如果已绑定）
        if has_bound_device:
            await queue_offline_message(user_id, content, attachments)
        
        await connection_manager.send_to_session(session_id, {
            "type": "error",
            "payload": {"code": error_code, "message": message}
        })
```

### 2.3 离线消息队列（持久化）⭐ 关键修订

**目标**: WinClaw 离线时暂存消息到数据库，恢复后自动发送，**支持服务器重启后数据不丢失**

**新增文件**: 
- `winclaw_server/remote_server/services/message_queue.py`
- `winclaw_server/remote_server/database/models.py` (新增数据模型)

**数据结构设计**:
```python
# database/models.py - 数据库模型
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta

Base = declarative_base()

class OfflineMessage(Base):
    """离线消息表"""
    __tablename__ = "offline_messages"
    
    id = Column(String, primary_key=True)  # message_id
    user_id = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    attachments = Column(Text)  # JSON 字符串
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=False)  # TTL 过期时间
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    priority = Column(String, default="normal")  # high/normal/low
    status = Column(String, default="pending")  # pending/sent/expired/failed
    
@dataclass
class PendingMessage:
    """内存中的消息对象（用于临时处理）"""
    message_id: str
    user_id: str
    content: str
    attachments: list
    created_at: datetime
    expires_at: datetime  # TTL 过期时间
    retry_count: int = 0
    max_retries: int = 3
    priority: str = "normal"  # high/normal/low
    
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
```

**核心逻辑**:
```python
# message_queue.py
from collections import deque
from ..database import get_db_session
from .models import OfflineMessage
import json

class OfflineMessageQueue:
    """离线消息队列服务（内存 + 数据库双写）"""
    
    def __init__(self):
        self.db_session = get_db_session()
        # 内存缓存：用于快速访问
        self._memory_queues: dict[str, deque[PendingMessage]] = {}
        
    async def enqueue(self, user_id: str, message: PendingMessage):
        """入队消息（同时写入数据库和内存）"""
        # 1. 写入数据库
        db_message = OfflineMessage(
            id=message.message_id,
            user_id=user_id,
            content=message.content,
            attachments=json.dumps(message.attachments),
            created_at=message.created_at,
            expires_at=message.expires_at,
            retry_count=message.retry_count,
            priority=message.priority
        )
        self.db_session.add(db_message)
        await self.db_session.commit()
        
        # 2. 写入内存缓存
        if user_id not in self._memory_queues:
            self._memory_queues[user_id] = deque(maxlen=50)  # 最多 50 条
        self._memory_queues[user_id].append(message)
        
        logger.info(f"离线消息已保存：user={user_id[:8]}, msg={message.message_id[:8]}")
        
    async def flush_to_winclaw(self, user_id: str, connection):
        """WinClaw 上线后发送所有待处理消息"""
        # 从数据库查询未过期的消息
        from sqlalchemy import select
        
        result = await self.db_session.execute(
            select(OfflineMessage)
            .where(OfflineMessage.user_id == user_id)
            .where(OfflineMessage.status == "pending")
            .where(OfflineMessage.expires_at > datetime.utcnow())
            .order_by(OfflineMessage.created_at.asc())
        )
        
        messages = result.scalars().all()
        
        for db_msg in messages:
            try:
                # 构建消息
                msg = PendingMessage(
                    message_id=db_msg.id,
                    user_id=user_id,
                    content=db_msg.content,
                    attachments=json.loads(db_msg.attachments),
                    created_at=db_msg.created_at,
                    expires_at=db_msg.expires_at,
                    retry_count=db_msg.retry_count
                )
                
                # 发送到 WinClaw
                await bridge_manager.send_to_winclaw(connection.session_id, {
                    "type": "chat",
                    "request_id": msg.message_id,
                    "payload": {
                        "content": msg.content,
                        "attachments": msg.attachments,
                        "user_id": user_id
                    }
                })
                
                # 更新状态
                db_msg.status = "sent"
                db_msg.retry_count += 1
                await self.db_session.commit()
                
                logger.info(f"离线消息已发送：msg={msg.message_id[:8]}")
                
            except Exception as e:
                logger.error(f"发送离线消息失败：{e}")
                db_msg.retry_count += 1
                if db_msg.retry_count >= db_msg.max_retries:
                    db_msg.status = "failed"
                await self.db_session.commit()
    
    async def cleanup_expired(self):
        """定期清理过期消息（定时任务）"""
        from sqlalchemy import delete
        
        await self.db_session.execute(
            delete(OfflineMessage)
            .where(OfflineMessage.expires_at < datetime.utcnow())
        )
        await self.db_session.commit()
        
        logger.info("已清理过期离线消息")
```

**配置示例** (`config/remote_server.toml`)：
```toml
[offline_messages]
# 消息存活时间（分钟）
default_ttl_minutes = 30
high_priority_ttl_minutes = 60   # 高优先级消息保留更久
low_priority_ttl_minutes = 10    # 低优先级消息快速过期

# 队列限制
max_queue_size_per_user = 50     # 每用户最多 50 条待处理消息
flush_on_reconnect = true        # 重连后立即刷新

# 清理策略
cleanup_interval_minutes = 60    # 每小时清理一次过期消息
```

**使用示例**：
```python
# handlers.py - 在 handle_chat_message 中调用
async def handle_chat_message(...):
    winclaw_conn = bridge_manager.get_user_connection(user_id)
    
    if not winclaw_conn:
        user_manager = context.get_user_manager()
        has_bound_device = user_manager and user_manager.has_bound_device(user_id)
        
        if has_bound_device:
            # ✅ 存入离线消息队列
            from ..services.message_queue import get_queue
            queue = get_queue()
            
            # 根据用户等级设置优先级
            priority = "high" if user.is_vip else "normal"
            ttl_minutes = config.offline_messages[f"{priority}_priority_ttl_minutes"]
            
            message = PendingMessage(
                message_id=str(uuid.uuid4()),
                user_id=user_id,
                content=content,
                attachments=attachments,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
                priority=priority
            )
            
            await queue.enqueue(user_id, message)
            
            error_code = "DEVICE_OFFLINE"
            message_text = "您的 WinClaw PC 端当前离线，消息将在其上线后自动发送"
        else:
            error_code = "NO_DEVICE_BOUND"
            message_text = "您还没有绑定 WinClaw PC 端，请在设置中完成设备绑定"
        
        await connection_manager.send_to_session(session_id, {
            "type": "error",
            "payload": {"code": error_code, "message": message_text}
        })
```

### 2.4 断线检测与自动恢复

**目标**: 主动检测连接断开，自动恢复未完成任务

**修改文件**: 
- `winclaw_server/remote_server/websocket/bridge_handler.py`
- `src/remote_client/client.py`

**服务器端改进**:
```python
# bridge_handler.py - 在 disconnect 时
def disconnect(self, session_id: str):
    connection = self._connections.pop(session_id, None)
    
    if connection and connection.user_id:
        # 1. 广播状态变化
        asyncio.create_task(
            broadcast_winclaw_status_change(connection.user_id, "offline")
        )
        
        # 2. 标记进行中的请求为"待重试"
        for request_id in connection.pending_requests:
            mark_request_pending_retry(request_id)
```

**客户端改进**: client.py#L50
```python
# 重连后自动恢复
async def _on_reconnected(self):
    """重连成功后的处理"""
    # 通知服务器恢复连接
    await self._send_message({
        "type": "reconnected",
        "payload": {"device_id": self.config.device_id}
    })
    # 服务器会自动发送待处理消息
```

### 2.5 PWA 界面优化 ⚠️ 简化版本

**目标**: 直观显示连接状态，提供友好的离线体验

**修改文件**: 
- `winclaw_server/pwa/src/stores/device.ts`
- `winclaw_server/pwa/src/views/Chat.vue`
- `winclaw_server/pwa/src/components/StatusPanel.vue`

**新增状态**: 
```typescript
// device.ts
interface DeviceState {
  winclawStatus: 'online' | 'offline' | 'reconnecting' | 'unknown'
  lastOnlineAt: string | null
  pendingMessages: number
}
```

**UI 组件改进**:
```vue
<!-- Chat.vue - 添加离线提示横幅 -->
<template>
  <div class="chat-container">
    <!-- 离线提示 -->
    <div v-if="deviceStore.winclawStatus === 'offline'" class="offline-banner">
      <span class="icon">⚠️</span>
      <span>您的 WinClaw PC 端离线，消息将在其上线后发送</span>
    </div>
    
    <!-- 重连中提示 -->
    <div v-if="deviceStore.winclawStatus === 'reconnecting'" class="reconnecting-banner">
      <span class="spinner"></span>
      <span>WinClaw PC 端正在重新连接...</span>
    </div>
    ...
  </div>
</template>
```

**❌ 移除 PWA 本地队列**：改为简单缓存最近一条消息
```typescript
// 简化方案：只缓存最后一条失败的消息（IndexedDB）
const lastMessageCache = {
  save(msg) { await idb.setItem('last_pending_msg', msg) },
  async get() { return await idb.getItem('last_pending_msg') },
  async clear() { await idb.removeItem('last_pending_msg') }
}

// 用于网络失败时快速重试，而不是完整队列
```

---

## 三、实施步骤

### Phase 1: 基础容错（建议优先实施）⭐ P0 级
1. **差异化错误提示** - 修改 `handlers.py`，区分离线/未绑定（2h）
2. **状态广播机制** - 修改 `bridge_handler.py`，添加状态变化通知（3h）
3. **PWA 状态显示** - 修改 `device.ts` 和相关组件（4h）

### Phase 2: 离线消息队列 ⭐ P1 级
4. **新建消息队列服务** - 创建 `message_queue.py` 和数据库模型（6h）
5. **集成到消息处理流程** - 修改 `handlers.py` 和 `bridge_handler.py`（4h）
6. **自动恢复逻辑** - 修改 WinClaw 重连后的处理（3h）

### Phase 3: 高级特性 ⭐ P2 级
7. **国际化支持** - 新增 i18n 模块和多语言文件（3h）
8. **监控系统** - 新增监控告警模块（8h）
9. **TTL 策略优化** - 根据用户等级差异化服务（2h）

**❌ 已移除**: PWA 本地队列（复杂度高于价值）

---

## 四、测试用例

| 测试场景 | 预期行为 |
|----------|----------|
| GUI 关闭后发消息 | 显示"PC 端离线"，消息暂存数据库 |
| GUI 重新启动 | 自动发送暂存消息 |
| GUI 崩溃（处理中） | PWA 收到连接断开通知，显示重连提示 |
| 消息超过 TTL | 消息过期不发送，通知用户 |
| 多条离线消息 | 按顺序依次发送 |
| 服务器重启 | 离线消息不丢失，可从数据库恢复 |

---

## 五、影响范围

- **服务器端**: `handlers.py`, `bridge_handler.py`, 新增 `message_queue.py`, `models.py`, `i18n/`
- **客户端**: `client.py` 重连逻辑
- **PWA 端**: `device.ts`, `chat.ts`, `Chat.vue`, `StatusPanel.vue`
- **数据库**: 新增 `offline_messages` 表
- **无破坏性变更**: 保持现有 API 兼容

---

## 六、技术评审意见采纳情况

| 评审意见 | 采纳状态 | 说明 |
|----------|----------|------|
| ✅ 离线消息队列必须持久化 | **已采纳** | 改用 SQLAlchemy + 数据库存储 |
| ✅ 状态广播需添加超时控制 | **已采纳** | 添加 5 秒超时保护 |
| ✅ 错误提示需支持国际化 | **已采纳** | 新增 i18n 模块和 messages.json |
| ✅ TTL 策略改为可配置 | **已采纳** | 支持 high/normal/low三级优先级 |
| ✅ 移除 PWA 本地队列 | **已采纳** | 改为简单 IndexedDB 缓存 |
| ✅ 新增监控告警模块 | **已采纳** | Phase 3 新增监控系统 |

---

## 七、工作量评估（修订后）

| 模块 | 技术难度 | 工作量 | 优先级 |
|------|----------|--------|--------|
| 差异化错误提示 | ⭐⭐ 低 | 2h | 🔥 P0 |
| 状态广播机制（带超时） | ⭐⭐ 低 | 3h | 🔥 P0 |
| PWA 状态显示 | ⭐⭐ 低 | 4h | 🔥 P0 |
| 离线消息队列（持久化） | ⭐⭐⭐⭐ 中高 | 12h | 🟡 P1 |
| 自动恢复逻辑 | ⭐⭐⭐ 中 | 5h | 🟢 P2 |
| 国际化支持 | ⭐⭐ 低 | 3h | 🟢 P2 |
| 监控系统 | ⭐⭐⭐⭐ 中高 | 8h | ⚪ P3 |

**推荐实施顺序**:
- **Week 1**: Phase 1（基础容错）
- **Week 2**: Phase 2（离线队列 + 持久化）
- **Week 3**: Phase 3（高级特性，裁剪版）
