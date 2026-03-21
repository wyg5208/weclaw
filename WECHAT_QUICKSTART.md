# 微信工具快速开始指南

## 🚀 5 分钟快速上手

### 1. 安装依赖

```bash
pip install pyautogui pyperclip pyyaml
```

### 2. 配置 API Key

在 `.env` 文件中添加：

```bash
GLM_API_KEY=your_api_key_here
```

### 3. 验证安装

```bash
python -c "from src.tools.wechat import WeChatTool; t = WeChatTool(); print(f'✓ 已加载 {len(t.get_actions())} 个动作')"
```

输出：
```
✓ 已加载 8 个动作
```

### 4. 开始使用

#### 方式一：通过对话（推荐）

直接与 Weclaw 助手对话：

```
你：帮我给张三发个消息，说晚上 7 点吃饭
助手：💬 微信消息管理 → send_message
      ✓ 消息已发送

你：查看一下最近的消息
助手：💬 微信消息管理 → view_messages
      ✓ 收到 3 条新消息...

你：启用自动回复
助手：💬 微信消息管理 → enable_auto_reply
      ✓ 自动回复已启用
```

#### 方式二：通过代码

```python
from src.tools.wechat import WeChatTool
import asyncio

async def demo():
    tool = WeChatTool()
    
    # 1. 查看消息
    result = await tool.execute("view_messages", {
        "limit": 10,
        "include_images": True
    })
    print(f"收到 {result.result['count']} 条消息")
    
    # 2. 发送消息
    await tool.execute("send_message", {
        "message": "你好，这是一条测试消息",
        "chat_name": "张三",
        "delay": 2.0
    })
    print("✓ 消息已发送")
    
    # 3. 启用自动回复
    await tool.execute("enable_auto_reply", {
        "enabled": True,
        "reply_delay_min": 3.0,
        "reply_delay_max": 6.0
    })
    print("✓ 自动回复已启用")

asyncio.run(demo())
```

---

## 📋 核心功能速览

### 8 个主要动作

| 动作 | 说明 | 示例 |
|------|------|------|
| `view_messages` | 查看消息 | "看看谁给我发了消息" |
| `send_message` | 发送消息 | "给李四说会议取消了" |
| `switch_chat` | 切换聊天 | "切换到家人群" |
| `search_messages` | 搜索消息 | "找一下张三上周的消息" |
| `enable_auto_reply` | 自动回复 | "启用自动回复" |
| `get_chat_list` | 获取聊天列表 | "显示所有聊天" |
| `customer_service` | 客服模式 | "启用客服模式" |
| `add_to_knowledge` | 添加知识库 | "把这个问答存到知识库" |

---

## ⚙️ 基础配置

### 编辑 `config/wechat_config.yaml`

```yaml
# 智能回复配置
llm:
  enabled: true
  delay_min: 3.0    # 最小回复延迟（秒）
  delay_max: 8.0    # 最大回复延迟（秒）
  
  # 排除这些聊天（不回复）
  exclude_chats:
    - "文件传输助手"
    - "服务通知"
    - "订阅号消息"
  
  glm:
    vision_model: "glm-4.5v"  # OCR 模型
    chat_model: "glm-4-flash" # 对话模型

# 知识库配置
knowledge_base:
  enabled: true
  confidence_threshold: 0.7  # 置信度阈值
  fallback_to_llm: true      # 无匹配时使用 LLM
```

---

## 🔧 常用场景

### 场景 1：办公助理

```python
# 每 2 小时检查一次未读消息
await tool.execute("enable_auto_reply", {
    "enabled": True,
    "target_chats": ["工作群", "项目组"],
    "exclude_keywords": ["快递", "外卖"]
})
```

### 场景 2：智能客服

```python
# 启用客服模式
await tool.execute("customer_service", {
    "enabled": True,
    "knowledge_base": "data/product_knowledge.db",
    "confidence_threshold": 0.7,
    "working_hours": "09:00-18:00"
})

# 添加常见问题
await tool.execute("add_to_knowledge", {
    "question": "产品价格是多少？",
    "answer": "我们的标准版价格是 199 元/年",
    "category": "产品咨询"
})
```

### 场景 3：定时任务

```python
from src.tools.cron import CronTool

cron = CronTool()

# 每天早上 9 点发送早安问候
await cron.execute("add_cron", {
    "name": "morning_greeting",
    "schedule": "0 9 * * *",
    "task_type": "tool_call",
    "tool_name": "wechat",
    "action": "send_message",
    "params": {
        "message": "早上好！今天也要加油哦~",
        "chat_name": "家人群"
    }
})

# 每 10 分钟检查一次消息
await cron.execute("add_cron", {
    "name": "check_messages",
    "schedule": "*/10 * * * *",
    "task_type": "tool_call",
    "tool_name": "wechat",
    "action": "view_messages",
    "params": {"limit": 50}
})
```

---

## 🛠️ 故障排查

### 问题 1：消息发送失败

**症状**：提示发送失败或输入框为空

**解决**：
1. 确保微信已登录并正常运行
2. 检查窗口激活快捷键：`Ctrl+Alt+W`
3. 手动激活一次微信窗口再试

### 问题 2：OCR 识别不准确

**症状**：图片消息识别错误

**解决**：
1. 使用更强大的模型：`glm-4.5v`
2. 调整截图区域配置
3. 确保聊天窗口可见

### 问题 3：自动回复不生效

**症状**：收到消息但没有自动回复

**解决**：
1. 检查是否启用了自动回复：`enable_auto_reply(enabled=True)`
2. 检查排除规则（`exclude_chats`）
3. 查看日志文件：`logs/wechat_tool.log`

---

## 📖 进阶学习

详细文档：[`docs/WECHAT_TOOL_GUIDE.md`](docs/WECHAT_TOOL_GUIDE.md)

包含：
- ✅ 完整功能说明
- ✅ 高级配置选项
- ✅ 性能优化技巧
- ✅ 最佳实践案例
- ✅ API 参考手册

开发报告：[`tools/WECHAT_DEVELOPMENT_REPORT.md`](tools/WECHAT_DEVELOPMENT_REPORT.md)

包含：
- ✅ 技术架构详解
- ✅ 代码统计
- ✅ 测试报告
- ✅ 后续优化建议

---

## 💡 提示

### 最佳实践

1. **首次使用**：先手动测试基础功能（发送、查看）
2. **自动回复**：从小范围开始（如只回复特定聊天）
3. **客服模式**：先添加 10-20 个常见 FAQ 再启用
4. **定时任务**：设置较长的间隔（如 10 分钟），避免频繁打扰

### 安全提醒

- ⚠️ 不要设置过短的回复延迟（建议 ≥ 3 秒）
- ⚠️ 排除重要聊天（如文件传输助手、银行通知）
- ⚠️ 定期查看日志，确保工具正常运行
- ⚠️ 敏感操作需要确认（可在配置中开启）

---

## 🎯 下一步

完成快速入门后，可以尝试：

1. **定制回复策略**：为不同聊天设置不同的回复风格
2. **构建知识库**：导入你的 FAQ 数据，实现智能客服
3. **集成工作流**：与其他工具配合（如 browser、doc_generator）
4. **创建自动化**：使用定时任务实现定期发送、自动检查

---

**最后更新**: 2026-03-12  
**版本**: v1.0.0

祝你使用愉快！如有问题请查看文档或联系支持。
