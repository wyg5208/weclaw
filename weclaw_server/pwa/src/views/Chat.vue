<template>
  <div class="chat-page">
    <!-- 顶部导航 -->
    <van-nav-bar title="WeClaw" fixed placeholder>
      <template #left>
        <van-icon name="wap-nav" size="22" @click="showSidebar = true" />
      </template>
      <template #right>
        <van-icon name="plus" size="22" @click="handleNewSession" />
      </template>
    </van-nav-bar>

    <!-- 消息列表 -->
    <div class="message-list" ref="messageListRef">
      <!-- 欢迎消息 -->
      <div v-if="!chatStore.hasMessages" class="welcome">
        <img src="@/assets/logo.svg" alt="WeClaw" class="welcome-logo" />
        <h2>欢迎使用 WeClaw</h2>
        <p>您可以发送消息开始对话，或使用下方工具快速操作</p>
        
        <!-- 设备未绑定提示 -->
        <van-notice-bar
          v-if="!isDeviceBound"
          color="#ff5252"
          background="#fff0f0"
          left-icon="info-o"
          style="margin: 16px 0;"
        >
          请先绑定 WeClaw PC 设备后才能开始对话
        </van-notice-bar>
        
        <div class="quick-actions">
          <van-button size="small" @click="sendQuickMessage('帮我查看当前系统状态')" :disabled="!isDeviceBound">
            查看状态
          </van-button>
          <van-button size="small" @click="sendQuickMessage('最近有什么任务需要处理吗')" :disabled="!isDeviceBound">
            待办任务
          </van-button>
          <van-button size="small" @click="sendQuickMessage('帮我总结一下今天的工作')" :disabled="!isDeviceBound">
            工作总结
          </van-button>
        </div>
      </div>

      <!-- 消息气泡 -->
      <div
        v-for="msg in chatStore.messages"
        :key="msg.message_id"
        :class="['message', msg.role]"
      >
        <div class="avatar">
          <van-icon v-if="msg.role === 'user'" name="user-o" size="20" />
          <van-icon v-else name="service-o" size="20" />
        </div>
        <div class="content">
          <div class="text" v-html="formatMessage(msg.content)"></div>
          
          <!-- 附件 -->
          <div v-if="msg.metadata?.attachments?.length" class="attachments">
            <div
              v-for="att in msg.metadata.attachments"
              :key="att.attachment_id"
              class="attachment"
            >
              <img v-if="att.type === 'image'" :src="att.url" class="preview-image" />
              <div v-else class="file-attachment">
                <van-icon name="description" />
                <span>{{ att.filename }}</span>
              </div>
            </div>
          </div>

          <!-- 工具调用 -->
          <div v-if="msg.metadata?.tool_calls?.length" class="tool-calls">
            <div
              v-for="tool in msg.metadata.tool_calls"
              :key="tool.call_id"
              class="tool-call"
            >
              <van-icon :name="getToolIcon(tool.status)" />
              <span>{{ tool.tool_name }}: {{ tool.action }}</span>
              <van-tag v-if="tool.status === 'running'" type="primary">执行中</van-tag>
              <van-tag v-else-if="tool.status === 'success'" type="success">完成</van-tag>
              <van-tag v-else-if="tool.status === 'failed'" type="danger">失败</van-tag>
            </div>
          </div>

          <!-- 时间戳 -->
          <div v-if="settingsStore.settings.showTimestamps" class="timestamp">
            {{ formatTime(msg.created_at) }}
          </div>
        </div>
      </div>

      <!-- 流式响应 -->
      <div v-if="chatStore.isStreaming" class="message assistant streaming">
        <div class="avatar">
          <van-icon name="service-o" size="20" />
        </div>
        <div class="content">
          <div class="text" v-html="formatMessage(chatStore.streamingContent)"></div>
          <van-loading size="14" />
          
          <!-- 停止按钮 -->
          <van-button
            size="small"
            type="danger"
            plain
            @click="handleStopGeneration"
            style="margin-top: 8px;"
          >
            停止生成
          </van-button>
        </div>
      </div>

      <!-- 加载中 -->
      <div v-if="chatStore.isLoading && !chatStore.isStreaming" class="loading-indicator">
        <van-loading size="20" />
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-area">
      <!-- 设备未绑定提示 -->
      <van-notice-bar
        v-if="!isDeviceBound"
        color="#ff5252"
        background="#fff7e6"
        left-icon="info-o"
        style="margin-bottom: 8px;"
      >
        请先在设置中绑定 WeClaw PC 设备
      </van-notice-bar>
      
      <!-- 附件预览 -->
      <AttachmentPreview
        v-if="pendingAttachments.length > 0"
        :attachments="pendingAttachments"
        @remove="handleRemoveAttachment"
        @clear="handleClearAttachments"
      />
      
      <van-cell-group inset>
        <van-field
          v-model="inputMessage"
          type="textarea"
          :placeholder="isDeviceBound ? '输入消息...' : '请先绑定设备后开始对话'"
          rows="1"
          autosize
          :maxlength="4000"
          show-word-limit
          :disabled="!isDeviceBound"
          @keydown.enter.exact="handleEnterKey"
        >
          <template #button>
            <div class="input-actions">
              <van-icon name="add-o" size="22" @click="handleSelectFile" title="添加附件" :class="{ disabled: !isDeviceBound }" />
              <van-icon 
                :name="isRecording ? 'stop-circle' : 'audio'" 
                size="22" 
                :color="isRecording ? 'red' : ''"
                @click="handleVoiceInput" 
                :class="{ disabled: !isDeviceBound }"
              />
              <van-button
                type="primary"
                size="small"
                :loading="chatStore.isLoading"
                :disabled="!isDeviceBound"
                @click="handleSend"
              >
                发送
              </van-button>
            </div>
          </template>
        </van-field>
      </van-cell-group>
    </div>

    <!-- 侧边栏 -->
    <van-popup v-model:show="showSidebar" position="left" :style="{ width: '80%', height: '100%' }">
      <div class="sidebar">
        <div class="sidebar-header">
          <h3>历史会话</h3>
          <van-icon name="cross" size="22" @click="showSidebar = false" />
        </div>
        
        <div class="sidebar-content">
          <van-cell-group v-if="sessions.length > 0">
            <van-cell
              v-for="session in sessions"
              :key="session.session_id"
              :title="session.title || '新对话'"
              :label="formatTime(session.last_active)"
              is-link
              @click="handleSelectSession(session)"
            />
          </van-cell-group>
          <van-empty v-else description="暂无历史会话" />
        </div>
        
        <!-- 底部操作区 -->
        <div class="sidebar-footer">
          <van-cell-group>
            <van-cell title="设置" icon="setting-o" is-link @click="goToSettings" />
            <van-cell title="退出登录" icon="revoke" is-link @click="handleLogout" />
          </van-cell-group>
        </div>
      </div>
    </van-popup>

    <!-- 隐藏的文件输入 -->
    <input
      type="file"
      ref="fileInputRef"
      accept="image/*,audio/*,video/*,.pdf,.doc,.docx,.txt,.md,.csv,.xlsx,.xls,.pptx,.ppt,.json,.xml,.html,.htm,.py,.js,.ts,.java,.c,.cpp,.go,.rs"
      multiple
      style="display: none"
      @change="handleFileChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useChatStore, type Session, type Attachment } from '@/stores/chat'
import { useSettingsStore } from '@/stores/settings'
import { useDeviceStore } from '@/stores/device'
import { showToast, showLoadingToast, closeToast, showConfirmDialog } from 'vant'
import { fileApi } from '@/api'
import { getSpeechRecognizer, type RecognitionResult } from '@/utils/speech'
import AttachmentPreview from '@/components/AttachmentPreview.vue'
import { marked } from 'marked'  // ✅ 导入 marked 库用于 Markdown 解析

const router = useRouter()
const authStore = useAuthStore()
const chatStore = useChatStore()
const settingsStore = useSettingsStore()
const deviceStore = useDeviceStore()

const inputMessage = ref('')
const showSidebar = ref(false)
const messageListRef = ref<HTMLElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
// 使用 chatStore 的会话列表
const sessions = computed(() => chatStore.sessions)
const pendingAttachments = ref<Attachment[]>([])
const isRecording = ref(false)
// 检查设备绑定状态
const isDeviceBound = computed(() => deviceStore.hasDevice)
const speechRecognizer = getSpeechRecognizer({
  lang: 'zh-CN',
  continuous: false,
  interimResults: true,
  maxDuration: 60000 // 60 秒最大录音时长
})

// 检查登录状态
onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.push('/login')
    return
  }
  
  // 加载历史
  chatStore.loadHistory()
  
  // 加载会话列表（用于侧边栏历史会话）
  chatStore.loadSessions()
  
  // 获取设备信息（检查是否已绑定）
  deviceStore.fetchDeviceInfo()
  
  // 初始化语音识别回调
  setupSpeechRecognizer()
})

// 设置语音识别回调
function setupSpeechRecognizer() {
  speechRecognizer.onResult = (result: RecognitionResult) => {
    if (result.isFinal) {
      // 最终结果，添加到输入框
      if (inputMessage.value) {
        inputMessage.value += ' ' + result.transcript
      } else {
        inputMessage.value = result.transcript
      }
      isRecording.value = false
    } else {
      // 中间结果，可以显示在输入框下方（可选）
      console.log('中间结果:', result.transcript)
    }
  }
  
  speechRecognizer.onError = (error: Error) => {
    isRecording.value = false
    showToast(error.message || '语音识别失败')
  }
  
  speechRecognizer.onStart = () => {
    isRecording.value = true
    showToast('正在录音...')
  }
  
  speechRecognizer.onEnd = () => {
    isRecording.value = false
  }
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value && settingsStore.settings.autoScroll) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

// 发送消息
async function handleSend() {
  const content = inputMessage.value.trim()
  if (!content && pendingAttachments.value.length === 0) return

  inputMessage.value = ''
  
  // 发送消息（包含附件）
  const attachmentsToSend = [...pendingAttachments.value]
  pendingAttachments.value = [] // 清空附件列表
  
  await chatStore.sendMessage(content, attachmentsToSend)
  scrollToBottom()
}

// 停止生成
async function handleStopGeneration() {
  try {
    await chatStore.stopGeneration()
    showToast('已停止生成')
  } catch (error) {
    showToast('停止失败')
  }
}

// 快捷消息
async function sendQuickMessage(content: string) {
  await chatStore.sendMessage(content)
  scrollToBottom()
}

// Enter 键处理
function handleEnterKey(event: KeyboardEvent) {
  if (settingsStore.settings.sendOnEnter && !event.shiftKey) {
    event.preventDefault()
    handleSend()
  }
}

// 新会话
function handleNewSession() {
  // 检查是否有未保存的内容
  const hasUnsavedContent = chatStore.hasMessages
  
  if (hasUnsavedContent) {
    showConfirmDialog({
      title: '创建新对话',
      message: '当前对话将被清空，是否继续？',
      confirmButtonText: '确认创建',
      cancelButtonText: '取消'
    }).then(() => {
      chatStore.newSession()
      showToast('已创建新对话')
    }).catch(() => {
      // 用户取消，不做任何操作
    })
  } else {
    chatStore.newSession()
    showToast('已创建新对话')
  }
}

// 选择会话
function handleSelectSession(session: Session) {
  chatStore.loadHistory(session.session_id)
  showSidebar.value = false
}

// 跳转设置
function goToSettings() {
  showSidebar.value = false
  router.push('/settings')
}

// 退出登录
async function handleLogout() {
  showSidebar.value = false
  await authStore.logout()
  showToast('已退出登录')
  router.push('/login')
}

// 选择文件（支持图片、文档、音频等）
function handleSelectFile() {
  fileInputRef.value?.click()
}

// 文件变化
async function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  const files = target.files
  if (!files || files.length === 0) return

  const loadingToast = showLoadingToast({
    message: '正在上传...',
    forbidClick: true,
    duration: 0
  })

  try {
    // 支持多文件上传
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      
      // 验证文件类型
      if (!isValidFileType(file)) {
        showToast(`不支持的文件类型：${file.name}`)
        continue
      }
      
      // 上传文件
      const response = await fileApi.upload(file, chatStore.currentSessionId || undefined)
      const data = response.data as any
      
      // 添加到待发送附件列表
      pendingAttachments.value.push({
        attachment_id: data.attachment_id,
        type: getFileType(file.type, file.name),
        filename: data.filename,
        mime_type: file.type,
        size_bytes: data.size_bytes,
        url: data.url
      })
    }
    
    if (pendingAttachments.value.length > 0) {
      showToast(`已上传 ${pendingAttachments.value.length} 个文件`)
    }
  } catch (error: any) {
    console.error('文件上传失败:', error)
    showToast(error.response?.data?.detail || '上传失败')
  } finally {
    closeToast()
    target.value = '' // 清空文件选择器
  }
}

// 验证文件类型
function isValidFileType(file: File): boolean {
  // 支持的 MIME 类型
  const allowedMimeTypes = [
    // 图片
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/svg+xml',
    // 音频
    'audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/webm', 'audio/ogg', 'audio/aac',
    // 视频
    'video/mp4', 'video/webm', 'video/ogg',
    // 文档
    'application/pdf', 
    'application/msword', 
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    // 文本和代码
    'text/plain', 'text/markdown', 'text/csv', 'text/html', 'text/xml',
    'application/json', 'application/xml',
  ]
  
  // 支持的文件扩展名（用于 MIME 类型为空或 octet-stream 的情况）
  const allowedExtensions = [
    '.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.py', '.js', '.ts', '.java', '.c', '.cpp', '.go', '.rs', '.rb', '.php',
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg',
    '.mp3', '.wav', '.ogg', '.aac',
    '.mp4', '.webm',
  ]
  
  // 检查 MIME 类型
  if (allowedMimeTypes.includes(file.type)) {
    return true
  }
  
  // 检查扩展名
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  if (allowedExtensions.includes(ext)) {
    return true
  }
  
  // 允许 text/* 和 application/octet-stream（代码文件）
  if (file.type.startsWith('text/')) {
    return true
  }
  
  return false
}

// 获取文件类型
function getFileType(mimeType: string, filename: string): 'image' | 'audio' | 'video' | 'document' | 'code' {
  if (mimeType.startsWith('image/')) return 'image'
  if (mimeType.startsWith('audio/')) return 'audio'
  if (mimeType.startsWith('video/')) return 'video'
  
  // 代码文件
  const codeExtensions = ['.py', '.js', '.ts', '.java', '.c', '.cpp', '.go', '.rs', '.rb', '.php', '.html', '.css', '.json', '.xml']
  const ext = '.' + filename.split('.').pop()?.toLowerCase()
  if (codeExtensions.includes(ext)) return 'code'
  
  // 文档
  if (mimeType.startsWith('text/') || mimeType === 'application/pdf' || 
      mimeType.includes('document') || mimeType.includes('spreadsheet') || 
      mimeType.includes('presentation')) {
    return 'document'
  }
  
  return 'document' // 默认返回 document
}

// 删除附件
function handleRemoveAttachment(index: number) {
  pendingAttachments.value.splice(index, 1)
}

// 清空所有附件
function handleClearAttachments() {
  pendingAttachments.value = []
}

// 语音输入
function handleVoiceInput() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    showToast('您的浏览器不支持语音输入')
    return
  }
  
  if (isRecording.value) {
    // 正在录音，点击停止
    speechRecognizer.stop()
    isRecording.value = false
  } else {
    // 开始录音
    const started = speechRecognizer.start()
    if (!started) {
      showToast('启动录音失败，请检查麦克风权限')
    }
  }
}

// 格式化消息 - 使用 marked 解析 Markdown
function formatMessage(content: string): string {
  try {
    // marked v17+ 直接调用函数，传入配置选项
    return marked(content, {
      breaks: true,  // 启用换行转 <br>
      gfm: true      // GitHub Flavored Markdown
    })
  } catch (error) {
    console.error('Markdown 解析失败:', error)
    // 降级处理：直接返回原始内容
    return content
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
  }
}

// 格式化时间
function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  
  return date.toLocaleDateString()
}

// 工具状态图标
function getToolIcon(status: string): string {
  switch (status) {
    case 'running': return 'replay'
    case 'success': return 'passed'
    case 'failed': return 'cross'
    default: return 'clock'
  }
}

onUnmounted(() => {
  chatStore.disconnectWebSocket()
})
</script>

<style scoped>
.chat-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--van-background);
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  padding-bottom: 80px;
}

.welcome {
  text-align: center;
  padding: 40px 20px;
}

.welcome-logo {
  width: 80px;
  height: 80px;
  margin-bottom: 16px;
}

.welcome h2 {
  margin: 0 0 8px;
}

.welcome p {
  color: var(--van-gray-6);
  font-size: 14px;
  margin: 0 0 24px;
}

.quick-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.message.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--van-gray-2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message.user .avatar {
  background: var(--van-primary-color);
  color: white;
}

.content {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 16px;
  background: var(--van-background-2);
}

.message.user .content {
  background: var(--van-primary-color);
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .content {
  border-bottom-left-radius: 4px;
}

.text {
  word-break: break-word;
  line-height: 1.5;
}

.attachments {
  margin-top: 8px;
}

.preview-image {
  max-width: 100%;
  border-radius: 8px;
}

.file-attachment {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--van-gray-1);
  border-radius: 8px;
}

.tool-calls {
  margin-top: 8px;
}

.tool-call {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--van-gray-1);
  border-radius: 8px;
  font-size: 12px;
  margin-bottom: 4px;
}

.timestamp {
  font-size: 10px;
  color: var(--van-gray-5);
  margin-top: 4px;
  text-align: right;
}

/* ✅ Markdown 样式增强 */
.text :deep(h1), .text :deep(h2), .text :deep(h3), .text :deep(h4), .text :deep(h5), .text :deep(h6) {
  margin: 16px 0 8px;
  font-weight: 600;
  line-height: 1.4;
}

.text :deep(h1) { font-size: 1.5em; }
.text :deep(h2) { font-size: 1.3em; }
.text :deep(h3) { font-size: 1.1em; }
.text :deep(h4) { font-size: 1em; }
.text :deep(h5) { font-size: 0.9em; }
.text :deep(h6) { font-size: 0.85em; }

.text :deep(ul), .text :deep(ol) {
  padding-left: 20px;
  margin: 8px 0;
}

.text :deep(li) {
  margin: 4px 0;
}

.text :deep(blockquote) {
  border-left: 3px solid var(--van-gray-4);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--van-gray-6);
}

.text :deep(pre) {
  background: var(--van-gray-1);
  padding: 12px;
  border-radius: 4px;
  overflow-x: auto;
  margin: 8px 0;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.text :deep(code) {
  background: var(--van-gray-1);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.text :deep(pre code) {
  background: transparent;
  padding: 0;
}

.text :deep(a) {
  color: var(--van-blue);
  text-decoration: none;
}

.text :deep(a:hover) {
  text-decoration: underline;
}

.text :deep(hr) {
  border: none;
  border-top: 1px solid var(--van-gray-3);
  margin: 16px 0;
}

.text :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0;
}

.text :deep(th), .text :deep(td) {
  border: 1px solid var(--van-gray-3);
  padding: 8px;
  text-align: left;
}

.text :deep(th) {
  background: var(--van-gray-1);
  font-weight: 600;
}

.streaming .content {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.loading-indicator {
  text-align: center;
  padding: 16px;
}

.input-area {
  position: fixed;
  bottom: 50px; /* 为底部导航栏留出空间 */
  left: 0;
  right: 0;
  background: var(--van-background);
  padding: 8px;
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.05);
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.input-actions .van-icon {
  cursor: pointer;
  transition: all 0.2s;
}

.input-actions .van-icon:active {
  opacity: 0.7;
  transform: scale(0.95);
}

/* 禁用状态样式 */
.input-actions .van-icon.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  pointer-events: none;
}

/* 录音状态动画 */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.1);
  }
}

.input-actions .van-icon[style*="color: red"] {
  animation: pulse 1s ease-in-out infinite;
}

.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--van-border-color);
}

.sidebar-header h3 {
  margin: 0;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.sidebar-footer {
  border-top: 1px solid var(--van-border-color);
  padding: 8px 0;
}
</style>
