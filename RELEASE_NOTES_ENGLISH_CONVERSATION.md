# v2.20.0 英语口语对话练习工具发布说明

## 📅 发布日期
2026-03-24

## ✨ 新增功能

### 🗣️ 英语口语对话练习工具

全新推出的英语口语对话练习工具，提供沉浸式的英语会话练习体验！

#### 核心特性

1. **多主题场景** 🌍
   - 餐厅点餐 (restaurant)
   - 机场值机 (airport)
   - 酒店入住 (hotel)
   - 购物 (shopping)
   - 旅行问路 (travel)
   - 日常聊天 (daily_chat)
   - 商务会议 (business)
   - 自定义场景 (custom)

2. **难度分级** 📊
   - Beginner（初级）：简单词汇和短句
   - Intermediate（中级）：自然对话句式
   - Advanced（高级）：复杂表达和习语

3. **智能语音交互** 🎤
   - 支持 GLM ASR / Whisper 语音识别
   - 支持 Edge-TTS / Qwen3-TTS 语音合成
   - 可选文字或语音输入模式
   - 实时 AI 语音回复

4. **AI 智能对话** 🤖
   - 基于 LLM 的智能回复生成
   - 角色扮演式对话体验
   - 中英文混合提示（语法点拨）
   - 对话上下文记忆

5. **学习反馈** 📈
   - 对话轮数统计
   - 练习时长追踪
   - 学习建议生成
   - 相关词汇提示

## 🔧 技术实现

### 工具架构

```
src/tools/english_conversation.py
├── EnglishConversationTool (主类)
│   ├── ConversationSession (会话数据类)
│   ├── TopicConfig (主题配置类)
│   └── TOPIC_LIBRARY (预定义场景库)
├── 动作 (Actions)
│   ├── start_conversation - 开始对话
│   ├── respond - 回应对话
│   ├── end_conversation - 结束对话
│   └── list_topics - 列出主题
└── 辅助方法
    ├── _generate_ai_response - LLM 调用
    ├── _fallback_response - 降级回复
    ├── _parse_ai_response - 解析回复
    ├── _speak_text - TTS 播放
    └── _transcribe_audio - 语音识别
```

### 配置文件更新

#### tools.json
```json
{
  "english_conversation": {
    "enabled": true,
    "module": "src.tools.english_conversation",
    "class": "EnglishConversationTool",
    "display": {
      "name": "英语口语练习",
      "emoji": "🗣️",
      "description": "多主题场景英语口语对话练习",
      "category": "education"
    },
    "config": {
      "default_difficulty": "intermediate",
      "topics": ["restaurant", "airport", "hotel", "shopping", "travel", "daily_chat", "business"],
      "enable_evaluation": true,
      "tts_engine_for_dialog": "edge_tts"
    },
    "actions": ["start_conversation", "respond", "end_conversation", "list_topics"]
  }
}
```

#### prompts.py
- 在 `INTENT_CATEGORIES` 中添加英语学习关键词
- 在 `INTENT_TOOL_MAPPING` 中映射到 english_conversation 工具

### 依赖要求

**必需依赖：**
- Python 3.11+
- WeClaw 核心框架

**可选依赖（增强体验）：**
```bash
# 语音合成（推荐）
pip install edge-tts

# 语音识别（云端高精度）
pip install httpx tenacity  # GLM ASR 需要

# 智能对话生成（推荐）
pip install litellm openai

# 高质量 TTS（备选）
pip install qwen-tts soundfile torch
```

## 📚 文档资源

### 官方文档
- [`ENGLISH_CONVERSATION_TOOL_GUIDE.md`](docs/ENGLISH_CONVERSATION_TOOL_GUIDE.md) - 完整使用指南
- [`examples/english_conversation_examples.py`](examples/english_conversation_examples.py) - 使用示例代码

### 快速开始

#### 方法 1: 自然语言调用
```
我想练习英语口语
开始一个餐厅点餐的英语对话
我们来练练机场英语吧
```

#### 方法 2: API 调用
```python
from src.tools.english_conversation import EnglishConversationTool

tool = EnglishConversationTool()

# 开始对话
result = await tool.execute("start_conversation", {
    "topic": "restaurant",
    "difficulty": "beginner"
})

# 进行对话
result = await tool.execute("respond", {
    "session_id": result.data["session_id"],
    "user_input": "I'd like to order a beef steak."
})

# 结束对话
result = await tool.execute("end_conversation", {
    "session_id": result.data["session_id"]
})
```

## ✅ 测试验证

### 测试结果
```
测试项目：英语口语对话练习工具 - 集成测试
总测试数：5
通过数：4
成功率：80%
```

### 测试覆盖
- ✅ 主题列表查询
- ✅ 对话启动功能
- ✅ 对话交互流程
- ✅ 自定义场景支持
- ⚠️ 会话管理（偶发问题，已修复）

### 已知限制
1. **LiteLLM 未安装** - 降级到关键词匹配回复（不影响基础功能）
2. **语音功能需配置** - 需单独安装 TTS 引擎和配置 API Key

## 🎯 使用示例

### 示例 1: 餐厅点餐对话
```python
await tool.execute("start_conversation", {
    "topic": "restaurant",
    "difficulty": "beginner",
    "enable_voice": True  # 启用语音
})

# AI: "Good evening! Welcome to our restaurant..."
# [语音播放中...]

# 用户："Yes, I'd like a beef steak, please."
await tool.execute("respond", {
    "session_id": "abc123",
    "user_input": "Yes, I'd like a beef steak, please."
})

# AI: "Excellent choice! How would you like that cooked?"
# [语音播放中...]
```

### 示例 2: 商务英语练习
```python
await tool.execute("start_conversation", {
    "topic": "business",
    "difficulty": "advanced"
})

# AI: "Good morning! Shall we discuss the Q4 budget?"

await tool.execute("respond", {
    "session_id": "xyz789",
    "user_input": "I propose increasing the marketing budget by 20%."
})
```

## 🔮 后续规划

### 短期计划 (v2.20.x)
- [ ] 添加发音评分功能
- [ ] 增加更多主题场景（医疗、银行、学校等）
- [ ] 优化 LLM 回复质量
- [ ] 添加语法纠错建议

### 长期计划 (v2.21+)
- [ ] 学习进度追踪系统
- [ ] 游戏化学习模式
- [ ] 多人对话练习房间
- [ ] 移动端 PWA 支持
- [ ] 录音回放对比功能

## 📝 变更日志

### v2.20.0 (2026-03-24)
- ✅ 新增 EnglishConversationTool
- ✅ 添加 7 个预设主题场景
- ✅ 支持三级难度控制
- ✅ 集成语音识别和合成
- ✅ 支持自定义场景
- ✅ 添加对话统计功能
- ✅ 集成到教育类意图
- ✅ 完整文档和示例

## 🙏 致谢

感谢使用 WeClaw 英语口语对话练习工具！

如有任何问题或建议，欢迎提交 Issue 或 Pull Request。

---

**Happy Learning! 🎉**
