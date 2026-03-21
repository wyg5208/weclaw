/**
 * 聊天状态管理
 * 管理会话、消息和实时通信状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatApi } from '@/api'
import { useWebSocket } from '@/api/websocket'
import { generateUUID } from '@/utils/uuid'
import { useDeviceStore } from '@/stores/device'  // ✅ 新增（Phase 1.3）

export interface Message {
  message_id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  metadata?: {
    tokens?: number
    model?: string
    attachments?: Attachment[]
    tool_calls?: ToolCall[]
    isQueueNotice?: boolean
  }
}

export interface Attachment {
  attachment_id: string
  type: 'image' | 'audio' | 'video' | 'document' | 'code' | 'file'
  filename: string
  mime_type: string
  size_bytes: number
  url?: string
  thumbnail_url?: string
}

export interface ToolCall {
  call_id: string
  tool_name: string
  action: string
  arguments: Record<string, unknown>
  result?: unknown
  status: 'pending' | 'running' | 'success' | 'failed'
}

export interface Session {
  session_id: string
  title?: string
  created_at: string
  last_active: string
  status: string
  message_count: number
}

export const useChatStore = defineStore('chat', () => {
  // State
  const currentSession = ref<Session | null>(null)
  const messages = ref<Message[]>([])
  const sessions = ref<Session[]>([])
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const streamingContent = ref('')
  
  // 记录当前设备发送的消息 ID，用于过滤响应（多设备场景）
  const pendingMessageIds = ref<Set<string>>(new Set())
  const error = ref<string | null>(null)

  // WebSocket
  let ws: ReturnType<typeof useWebSocket> | null = null

  // Getters
  const hasMessages = computed(() => messages.value.length > 0)
  const currentSessionId = computed(() => currentSession.value?.session_id || null)

  // 初始化 WebSocket
  function initWebSocket(sessionId: string) {
    if (ws) {
      ws.disconnect()
    }
    
    // ✅ 获取设备 Store（Phase 1.3）
    const deviceStore = useDeviceStore()

    ws = useWebSocket({
      onMessage: (data) => {
        const payload = data.payload as Record<string, unknown> | undefined
        const requestId = data.request_id as string | undefined
        
        // 多设备场景：只处理本设备发起的请求的响应
        const isMyRequest = !requestId || pendingMessageIds.value.has(requestId)
        
        if (data.type === 'message') {
          messages.value.push(payload as unknown as Message)
        } else if (data.type === 'stream') {
          if (isMyRequest) {
            isStreaming.value = true
            streamingContent.value += (payload?.content as string) || ''
          }
        } else if (data.type === 'stream_end') {
          if (isMyRequest) {
            isStreaming.value = false
            // 将流式内容添加到消息列表
            if (streamingContent.value) {
              messages.value.push({
                message_id: (payload?.message_id as string) || generateUUID(),
                session_id: sessionId,
                role: 'assistant',
                content: streamingContent.value,
                created_at: new Date().toISOString()
              })
              streamingContent.value = ''
            }
            // 清理已完成的请求 ID
            if (requestId) {
              pendingMessageIds.value.delete(requestId)
            }
          }
        } else if (data.type === 'tool_call') {
          if (isMyRequest) {
            // 更新工具调用状态
            const lastMessage = messages.value[messages.value.length - 1]
            if (lastMessage && lastMessage.role === 'assistant') {
              if (!lastMessage.metadata) lastMessage.metadata = {}
              if (!lastMessage.metadata.tool_calls) lastMessage.metadata.tool_calls = []
              lastMessage.metadata.tool_calls.push(data.payload as ToolCall)
            }
          }
        } else if (data.type === 'queued') {
          if (isMyRequest) {
            // AI 正忙，请求已排队 — 在最后一条 assistant 消息或新建一条提示
            const queuedHint = (payload?.message as string) || '⏳ 请求已排队，等待处理...'
            // 如果最后一条消息是用户消息，插入一条系统提示
            const last = messages.value[messages.value.length - 1]
            if (!last || last.role === 'user') {
              messages.value.push({
                message_id: generateUUID(),
                session_id: sessionId,
                role: 'assistant',
                content: `⏳ ${queuedHint}`,
                created_at: new Date().toISOString(),
                metadata: { isQueueNotice: true }
              })
            }
          }
        }
      },
      onStatus: (data) => {
        if (data.type === 'status') {
          // 更新 WinClaw 状态
          console.log('WinClaw status:', data.payload)
        }
      },
      // ✅ 新增：处理 WinClaw 状态变化（Phase 1.3）
      onWinClawStatusChange: (status) => {
        deviceStore.updateWinClawStatus(status)
        console.log(`WinClaw 状态变化：${status}`)
      },
      onError: (err) => {
        error.value = err.message || 'WebSocket 连接错误'
      }
    })

    ws.connect()
  }

  // 断开 WebSocket
  function disconnectWebSocket() {
    if (ws) {
      ws.disconnect()
      ws = null
    }
  }

  // 发送消息
  async function sendMessage(content: string, attachments?: Attachment[]) {
    if (!content.trim() && (!attachments || attachments.length === 0)) {
      return false
    }

    isLoading.value = true
    error.value = null
    isStreaming.value = true
    streamingContent.value = ''

    // 先添加用户消息到列表
    const userMessage: Message = {
      message_id: generateUUID(),
      session_id: currentSessionId.value || '',
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      metadata: attachments && attachments.length > 0 ? { attachments } : undefined
    }
    messages.value.push(userMessage)

    try {
      // ✅ 确保 WebSocket 已连接（优先使用 WebSocket 发送消息）
      if (!ws || !ws.isConnected.value) {
        initWebSocket(currentSessionId.value || `remote_${Date.now()}`)
        // 等待 WebSocket 连接建立
        await new Promise(resolve => setTimeout(resolve, 500))
      }
      
      // ✅ 优先使用 WebSocket 发送消息（实时性更好）
      if (ws && ws.isConnected.value) {
        // 通过 WebSocket 发送消息
        // ✅ 生成 request_id 并发送给服务器，确保响应能正确路由回来
        const requestId = generateUUID()
        pendingMessageIds.value.add(requestId)
        
        ws.send('message', {
          request_id: requestId,  // ✅ 关键：发送 request_id 给服务器
          content,
          attachments: attachments?.map(a => ({
            attachment_id: a.attachment_id,
            type: a.type,
            data: a.url || '',
            filename: a.filename,
            mime_type: a.mime_type
          }))
        })
        
        // 更新或创建会话
        if (!currentSession.value) {
          currentSession.value = {
            session_id: `remote_${Date.now()}`,
            created_at: new Date().toISOString(),
            last_active: new Date().toISOString(),
            status: 'active',
            message_count: 1
          }
        }
        
        return true
      }
      
      // ✅ 降级：使用 HTTP API 发送消息
      const response = await chatApi.sendMessage({
        message: content,
        session_id: currentSessionId.value || undefined,
        attachments: attachments?.map(a => ({
          attachment_id: a.attachment_id,
          type: a.type,
          data: a.url || '',
          filename: a.filename,
          mime_type: a.mime_type
        }))
      })

      const data = response.data as unknown as {
        message_id: string
        session_id: string
        status: string
      }

      if (data.message_id && data.session_id) {
        // 记录此消息 ID，用于过滤 WebSocket 响应（多设备场景）
        pendingMessageIds.value.add(data.message_id)
        
        // 更新或创建会话
        if (!currentSession.value) {
          currentSession.value = {
            session_id: data.session_id,
            created_at: new Date().toISOString(),
            last_active: new Date().toISOString(),
            status: 'active',
            message_count: 1
          }
        }
        
        // ✅ HTTP 路径需要通过 SSE 接收响应
        await fetchStreamResponse(data.message_id, data.session_id)
        
        return true
      } else {
        error.value = '发送失败：响应数据格式错误'
        messages.value.pop()
        return false
      }
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string; error?: { message?: string } } } }
      error.value = axiosError.response?.data?.detail || axiosError.response?.data?.error?.message || '网络错误'
      messages.value.pop()
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 获取流式响应
  async function fetchStreamResponse(messageId: string, sessionId: string) {
    const token = localStorage.getItem('access_token')
    if (!token) {
      error.value = '未登录'
      return
    }

    try {
      const response = await fetch(`/api/chat/stream?session_id=${sessionId}&message_id=${messageId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event:')) {
            // 事件类型
          } else if (line.startsWith('data:')) {
            const dataStr = line.slice(5).trim()
            if (!dataStr) continue
            
            try {
              const payload = JSON.parse(dataStr)
              
              // 处理不同类型的消息
              if (payload.delta) {
                // 流式内容
                streamingContent.value += payload.delta
              } else if (payload.content) {
                // 完整内容
                streamingContent.value += payload.content
              }
            } catch {
              // 忽略解析错误
            }
          }
        }
      }

      // 流式结束，添加 AI 消息
      if (streamingContent.value) {
        messages.value.push({
          message_id: generateUUID(),
          session_id: sessionId,
          role: 'assistant',
          content: streamingContent.value,
          created_at: new Date().toISOString()
        })
        streamingContent.value = ''
      }
      
      isStreaming.value = false
      
    } catch (err) {
      console.error('流式响应错误:', err)
      error.value = '获取响应失败'
      isStreaming.value = false
    }
  }

  // 停止生成
  async function stopGeneration() {
    if (!currentSessionId.value) return

    try {
      await chatApi.stopGeneration(currentSessionId.value)
      isStreaming.value = false
      streamingContent.value = ''
    } catch (err) {
      console.error('停止生成失败:', err)
    }
  }

  // 加载历史消息
  async function loadHistory(sessionId?: string) {
    isLoading.value = true

    try {
      const response = await chatApi.getHistory(sessionId)
      // API 直接返回数据
      const data = response.data as unknown as {
        messages: Message[]
        session_id?: string
      }
      if (data.messages) {
        messages.value = data.messages
        if (!currentSession.value && data.session_id) {
          currentSession.value = {
            session_id: data.session_id,
            created_at: new Date().toISOString(),
            last_active: new Date().toISOString(),
            status: 'active',
            message_count: messages.value.length
          }
          initWebSocket(data.session_id)
        }
        return true
      }
    } catch (err) {
      console.error('加载历史失败:', err)
    } finally {
      isLoading.value = false
    }
    return false
  }

  // 新建会话
  function newSession() {
    disconnectWebSocket()
    currentSession.value = null
    messages.value = []
    streamingContent.value = ''
    isStreaming.value = false
    error.value = null
  }

  // 加载会话列表
  async function loadSessions(limit = 20) {
    try {
      const response = await chatApi.getSessions(limit)
      const data = response.data as unknown as {
        success: boolean
        data: {
          sessions: Session[]
          total: number
        }
      }
      if (data.success && data.data) {
        sessions.value = data.data.sessions
        return true
      }
    } catch (err) {
      console.error('加载会话列表失败:', err)
    }
    return false
  }

  // 删除会话
  async function deleteSession(sessionId: string) {
    try {
      const response = await chatApi.deleteSession(sessionId)
      const data = response.data as unknown as {
        success: boolean
        message: string
      }
      if (data.success) {
        // 从列表中移除
        sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
        return true
      }
    } catch (err) {
      console.error('删除会话失败:', err)
    }
    return false
  }

  return {
    // State
    currentSession,
    messages,
    sessions,
    isLoading,
    isStreaming,
    streamingContent,
    error,
    // Getters
    hasMessages,
    currentSessionId,
    // Actions
    initWebSocket,
    disconnectWebSocket,
    sendMessage,
    stopGeneration,
    loadHistory,
    loadSessions,
    deleteSession,
    newSession
  }
})
