# PWA-PC 离线容错与人性化交互优化方案

## 一、现状分析

### 1.1 系统架构
```
PWA 前端 <---> 远程服务器 <---> WinClaw 本地 GUI
 (手机)        (云端)          (PC桌面)
```

### 1.2 关键场景梳理

| 场景 | 当前处理 | 问题 |
|------|----------|------|
| **本地GUI未启动** | 返回 `NO_DEVICE_BOUND` 错误 | 错误提示不准确（设备可能已绑定，只是离线） |
| **GUI重启中** | 静默失败 | PWA无感知，消息丢失 |
| **消息处理中GUI崩溃** | 120秒超时后返回错误 | 超时过长，无主动检测 |
| **网络闪断** | WebSocket断开，PWA重连 | 不同步WinClaw状态 |
| **GUI恢复连接** | 仅记录日志 | 不通知PWA，不恢复中断任务 |

### 1.3 当前代码位置

- **服务器端消息处理**: [winclaw_server/remote_server/websocket/handlers.py](file:///d:/python_projects/openclaw_demo/winclaw/winclaw_server/remote_server/websocket/handlers.py#L174-L238)
- **Bridge连接管理**: [winclaw_server/remote_server/websocket/bridge_handler.py](file:///d:/python_projects/openclaw_demo/winclaw/winclaw_server/remote_server/websocket/bridge_handler.py#L161-L174)
- **PWA聊天Store**: [winclaw_server/pwa/src/stores/chat.ts](file:///d:/python_projects/openclaw_demo/winclaw/winclaw_server/pwa/src/stores/chat.ts)

---

## 二、优化方案

### 2.1 实时状态同步机制

**目标**: PWA实时感知WinClaw在线状态变化

**修改文件**: 
- `winclaw_server/remote_server/websocket/bridge_handler.py`
- `winclaw_server/remote_server/websocket/handlers.py`
- `winclaw_server/pwa/src/stores/device.ts`

**实现要点**:
```python
# bridge_handler.py - 添加 WinClaw 状态广播
async def broadcast_winclaw_status_change(user_id: str, status: str):
    """广播 WinClaw 状态变化到 PWA"""
    pwa_manager = context.get_connection_manager()
    if pwa_manager:
        await pwa_manager.send_message(user_id, {
            "type": "winclaw_status",
            "payload": {
                "status": status,  # online/offline/reconnecting
                "timestamp": datetime.now().isoformat()
            }
        })
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

**修改位置**: [handlers.py#L188-L200](file:///d:/python_projects/openclaw_demo/winclaw/winclaw_server/remote_server/websocket/handlers.py#L188-L200)
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

### 2.3 离线消息队列

**目标**: WinClaw离线时暂存消息，恢复后自动发送

**新增文件**: `winclaw_server/remote_server/services/message_queue.py`

**数据结构设计**:
```python
@dataclass
class PendingMessage:
    message_id: str
    user_id: str
    content: str
    attachments: list
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    ttl_minutes: int = 30  # 消息最长存活时间
```

**核心逻辑**:
```python
class OfflineMessageQueue:
    def __init__(self):
        self._queues: dict[str, deque[PendingMessage]] = {}
        
    async def enqueue(self, user_id: str, message: PendingMessage):
        """入队消息"""
        if user_id not in self._queues:
            self._queues[user_id] = deque(maxlen=50)  # 最多50条
        self._queues[user_id].append(message)
        
    async def flush_to_winclaw(self, user_id: str, connection):
        """WinClaw 上线后发送所有待处理消息"""
        queue = self._queues.get(user_id)
        if not queue:
            return
            
        while queue:
            msg = queue.popleft()
            if msg.is_expired():
                continue  # 跳过过期消息
            # 发送到 WinClaw
            await bridge_manager.send_to_winclaw(connection.session_id, {...})
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

**客户端改进**: [client.py#L50](file:///d:/python_projects/openclaw_demo/winclaw/src/remote_client/client.py#L50)
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

### 2.5 PWA界面优化

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

**UI组件改进**:
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

---

## 三、实施步骤

### Phase 1: 基础容错（建议优先实施）
1. **差异化错误提示** - 修改 `handlers.py`，区分离线/未绑定
2. **状态广播机制** - 修改 `bridge_handler.py`，添加状态变化通知
3. **PWA状态显示** - 修改 `device.ts` 和相关组件

### Phase 2: 离线消息队列
4. **新建消息队列服务** - 创建 `message_queue.py`
5. **集成到消息处理流程** - 修改 `handlers.py` 和 `bridge_handler.py`
6. **自动恢复逻辑** - 修改 WinClaw 重连后的处理

### Phase 3: 高级特性
7. **消息持久化** - 支持服务器重启后恢复队列
8. **PWA本地队列** - PWA端也维护本地消息队列
9. **重试策略优化** - 指数退避、最大重试次数

---

## 四、测试用例

| 测试场景 | 预期行为 |
|----------|----------|
| GUI关闭后发消息 | 显示"PC端离线"，消息暂存 |
| GUI重新启动 | 自动发送暂存消息 |
| GUI崩溃（处理中） | PWA收到连接断开通知，显示重连提示 |
| 消息超过TTL | 消息过期不发送，通知用户 |
| 多条离线消息 | 按顺序依次发送 |

---

## 五、影响范围

- **服务器端**: `handlers.py`, `bridge_handler.py`, 新增 `message_queue.py`
- **客户端**: `client.py` 重连逻辑
- **PWA端**: `device.ts`, `chat.ts`, `Chat.vue`, `StatusPanel.vue`
- **无破坏性变更**: 保持现有API兼容