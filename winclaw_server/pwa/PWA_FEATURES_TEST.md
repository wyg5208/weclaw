# PWA 移动端图片上传和语音输入功能测试指南

## 功能概述

本次开发为 WinClaw PWA 移动端添加了两个重要功能：

1. **图片/文件上传及问答** - 支持上传图片、音频、文档等文件，并基于文件内容进行 AI 问答
2. **语音识别输入** - 利用浏览器的 Web Speech API 将语音转换为文字输入

## 新增文件

### 前端文件

1. **`weclaw_server/pwa/src/utils/speech.ts`**
   - 语音识别工具类
   - 封装 Web Speech API
   - 提供开始/停止录音、错误处理等功能

2. **`weclaw_server/pwa/src/components/AttachmentPreview.vue`**
   - 附件预览组件
   - 显示已上传文件的缩略图、文件名、大小
   - 支持删除单个文件或清空所有附件

### 修改的文件

1. **`weclaw_server/pwa/src/views/Chat.vue`**
   - 实现文件选择和上传功能
   - 集成附件预览面板
   - 实现语音输入 UI 交互
   - 添加录音状态动画

2. **`weclaw_server/pwa/src/stores/chat.ts`**
   - 修改 `sendMessage` 方法支持发送带附件的消息

## 功能使用说明

### 1. 图片/文件上传

#### 操作步骤：

1. **选择文件**
   - 点击输入框左侧的 📎 图标
   - 在弹出的文件选择器中选择要上传的文件
   - 支持多选（按住 Ctrl/Cmd 键选择多个文件）

2. **查看附件预览**
   - 上传成功后，附件会显示在输入框上方
   - 图片会显示缩略图预览
   - 其他文件类型显示文件图标和名称
   - 显示文件大小和 MIME 类型

3. **管理附件**
   - 点击单个附件右侧的 ✕ 按钮可删除该附件
   - 点击附件面板右上角的清除图标可清空所有附件

4. **发送消息**
   - 在输入框中输入问题或指令
   - 点击"发送"按钮
   - 消息会连同附件一起发送给 AI

5. **AI 响应**
   - AI 会分析附件内容并回答相关问题
   - 图片会被识别和分析
   - 文档内容会被提取和理解

#### 支持的文件类型：

- **图片**: JPEG, PNG, GIF, WebP
- **音频**: WAV, MP3, MPEG, WebM
- **文档**: PDF, TXT
- **单文件大小限制**: 50MB

### 2. 语音输入

#### 操作步骤：

1. **开始录音**
   - 点击输入框右侧的 🎤 图标
   - 浏览器会请求麦克风权限（首次使用）
   - 允许后，麦克风图标变为红色并开始脉动动画
   - 显示"正在录音..."提示

2. **说话**
   - 对着麦克风清晰说话
   - 识别结果会实时显示在输入框中
   - 支持连续说话（中间结果会实时更新）

3. **停止录音**
   - 再次点击 🎤 图标停止录音
   - 或者等待 60 秒自动停止（最大录音时长）
   - 识别结果会自动填入输入框

4. **编辑和发送**
   - 可以编辑识别结果
   - 确认无误后点击"发送"按钮

#### 浏览器兼容性：

- ✅ **Chrome** (推荐) - 完整支持
- ✅ **Edge** (推荐) - 完整支持（基于 Chromium）
- ⚠️ **Firefox** - 可能需要 polyfill
- ⚠️ **Safari** - iOS 设备支持有限

#### 语音识别配置：

- **语言**: 中文（zh-CN）
- **连续识别**: 关闭
- **中间结果**: 开启
- **最大录音时长**: 60 秒

## 技术实现细节

### 文件上传流程

```
用户选择文件
    ↓
前端验证文件类型和大小
    ↓
调用 fileApi.upload() 上传到服务器
    ↓
服务器保存文件并返回 attachment_id 和 URL
    ↓
前端添加到 pendingAttachments 列表
    ↓
显示附件预览面板
    ↓
用户点击发送
    ↓
调用 chatStore.sendMessage(content, attachments)
    ↓
后端接收并处理附件
    ↓
WinClaw Agent 分析附件并回复
```

### 语音识别流程

```
用户点击麦克风图标
    ↓
检查浏览器支持性
    ↓
请求麦克风权限
    ↓
创建 SpeechRecognition 实例
    ↓
开始录音并监听 onresult 事件
    ↓
实时获取识别结果（interim results）
    ↓
用户停止录音或超时
    ↓
最终识别结果填入输入框
    ↓
用户可以编辑后发送
```

### 关键代码位置

#### 文件上传
```typescript
// Chat.vue line ~370
async function handleFileChange(event: Event) {
  const files = target.files
  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    const response = await fileApi.upload(file, sessionId)
    pendingAttachments.value.push({
      attachment_id: response.data.attachment_id,
      type: getFileType(file.type),
      filename: response.data.filename,
      mime_type: file.type,
      size_bytes: response.data.size_bytes,
      url: response.data.url
    })
  }
}
```

#### 语音识别
```typescript
// Chat.vue line ~260
function setupSpeechRecognizer() {
  speechRecognizer.onResult = (result: RecognitionResult) => {
    if (result.isFinal) {
      inputMessage.value += ' ' + result.transcript
      isRecording.value = false
    } else {
      console.log('中间结果:', result.transcript)
    }
  }
  
  speechRecognizer.onStart = () => {
    isRecording.value = true
    showToast('正在录音...')
  }
}
```

#### 发送带附件的消息
```typescript
// chat.ts line ~131
async function sendMessage(content: string, attachments?: Attachment[]) {
  const userMessage: Message = {
    role: 'user',
    content,
    metadata: attachments && attachments.length > 0 ? { attachments } : undefined
  }
  
  const response = await chatApi.sendMessage({
    message: content,
    attachments: attachments?.map(a => ({
      type: a.type,
      data: a.url,
      filename: a.filename,
      mime_type: a.mime_type
    }))
  })
}
```

## 测试场景

### 场景 1：上传图片并询问

1. 点击 📎 选择一张图片
2. 等待上传完成并看到预览
3. 输入："这张图片里有什么？"
4. 点击发送
5. AI 应该能识别图片内容并回答

### 场景 2：上传文档并总结

1. 点击 📎 选择一个 PDF 或 TXT 文件
2. 等待上传完成
3. 输入："请总结这个文档的主要内容"
4. 点击发送
5. AI 应该能提取文档内容并总结

### 场景 3：语音输入提问

1. 点击 🎤 开始录音
2. 对着麦克风说："今天天气怎么样？"
3. 看到文字实时填入输入框
4. 再次点击 🎤 停止录音
5. 确认文字正确后发送

### 场景 4：多文件上传

1. 点击 📎 同时选择多个文件（如 3 张图片）
2. 看到所有附件的预览
3. 输入："比较这几张图片的异同"
4. 点击发送
5. AI 应该能分析所有图片并比较

## 已知限制和注意事项

### 文件上传限制

1. **文件大小**: 单个文件最大 50MB
2. **文件类型**: 仅支持配置中允许的 MIME 类型
3. **网络依赖**: 需要稳定的网络连接
4. **浏览器兼容性**: 所有现代浏览器都应该支持

### 语音识别限制

1. **浏览器支持**: 
   - 仅 Chrome/Edge 完美支持
   - Firefox/Safari 可能需要额外配置
   - 不支持 IE

2. **网络要求**: 
   - Web Speech API 需要联网使用
   - 离线环境无法使用

3. **隐私考虑**:
   - 语音数据会发送到 Google 进行识别
   - 敏感信息建议使用文字输入

4. **环境噪音**:
   - 嘈杂环境可能影响识别准确率
   - 建议在安静环境使用

### 性能考虑

1. **大文件上传**: 接近 50MB 的文件上传时间较长
2. **并发上传**: 多文件同时上传可能占用带宽
3. **内存占用**: 大量高清图片可能占用较多内存

## 故障排查

### 文件上传失败

**问题**: 上传时显示"上传失败"

**解决方案**:
1. 检查网络连接
2. 确认文件大小不超过 50MB
3. 确认文件类型在允许列表中
4. 检查浏览器控制台是否有错误信息
5. 确认服务器正常运行

### 语音识别不可用

**问题**: 点击麦克风显示"您的浏览器不支持语音输入"

**解决方案**:
1. 使用 Chrome 或 Edge 浏览器
2. 确保浏览器版本较新
3. 检查是否授予麦克风权限
4. 在浏览器设置中启用语音识别功能

### 麦克风权限被拒绝

**问题**: 显示"麦克风权限被拒绝"

**解决方案**:
1. 在浏览器地址栏右侧点击锁形图标
2. 找到麦克风权限设置
3. 选择"允许"
4. 刷新页面重试

### 识别结果不准确

**问题**: 语音识别结果与说的不符

**解决方案**:
1. 在安静环境使用
2. 说话清晰、语速适中
3. 避免背景噪音
4. 检查麦克风是否正常工作
5. 尝试靠近麦克风说话

## 后续优化方向

1. **图片压缩**: 上传前自动压缩图片减少带宽
2. **分片上传**: 大文件分片上传支持断点续传
3. **上传进度**: 显示实时上传进度条
4. **离线识别**: 探索本地语音识别方案
5. **多语言支持**: 支持更多语言选择
6. **语音命令**: 支持语音快捷指令

## 更新日志

**v1.0 - 2026-02-26**
- ✅ 实现文件上传功能
- ✅ 实现附件预览面板
- ✅ 实现语音识别输入
- ✅ 添加录音状态动画
- ✅ 支持多文件上传
- ✅ 支持发送带附件的消息

---

## 技术支持

如有问题或建议，请访问 GitHub Issues:
https://github.com/wyg5208/WinClaw/issues
