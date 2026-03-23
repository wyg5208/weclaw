/**
 * WebSocket 客户端
 * 处理实时通信和流式响应
 */

import { ref } from 'vue'
import { generateUUID } from '@/utils/uuid'

interface WebSocketOptions {
  onMessage?: (data: WebSocketMessage) => void
  onStatus?: (data: WebSocketMessage) => void
  onError?: (error: Error) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onWeClawStatusChange?: (status: 'online' | 'offline' | 'reconnecting' | 'unknown') => void  // ✅ 新增（Phase 1.3）
  reconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

interface WebSocketMessage {
  type: string
  payload?: unknown
  timestamp?: string
  request_id?: string  // 用于多设备场景的消息路由
}

export function useWebSocket(options: WebSocketOptions = {}) {
  const {
    onMessage,
    onStatus,
    onError,
    onConnect,
    onDisconnect,
    onWeClawStatusChange,  // ✅ 新增（Phase 1.3）
    reconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5
  } = options

  const isConnected = ref(false)
  const connectionId = ref<string | null>(null)

  let ws: WebSocket | null = null
  let reconnectAttempts = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let pingTimer: ReturnType<typeof setInterval> | null = null
  let lastPongTime = 0  // 上次收到 pong 的时间
  let pongCheckTimer: ReturnType<typeof setInterval> | null = null

  // 获取 WebSocket URL
  function getWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    // 从 localStorage 获取 token
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.error('WebSocket: 未找到 access_token')
      return ''
    }
    return `${protocol}//${host}/ws/chat?token=${encodeURIComponent(token)}`
  }

  // 连接
  function connect() {
    if (ws?.readyState === WebSocket.OPEN) {
      return
    }

    const url = getWebSocketUrl()
    if (!url) {
      console.error('WebSocket: 无法生成连接 URL')
      onError?.(new Error('未登录或 Token 已过期'))
      return
    }
    ws = new WebSocket(url)

    ws.onopen = () => {
      isConnected.value = true
      reconnectAttempts = 0
      connectionId.value = generateUUID()
      
      // 开始心跳
      startPing()
      
      onConnect?.()
    }

    ws.onclose = (_event) => {
      isConnected.value = false
      stopPing()
      
      onDisconnect?.()

      // 自动重连
      if (reconnect && reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++
        reconnectTimer = setTimeout(() => {
          connect()
        }, reconnectInterval)
      }
    }

    ws.onerror = (_event) => {
      onError?.(new Error('WebSocket error'))
    }

    ws.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data)
        
        switch (data.type) {
          case 'message':
          case 'stream':
          case 'stream_end':
          case 'tool_call':
            onMessage?.(data)
            break
          case 'status':
            onStatus?.(data)
            break
          case 'pong':
            // 心跳响应 - 更新最后 pong 时间
            lastPongTime = Date.now()
            break
          // ✅ 新增：处理 WeClaw 状态变化（Phase 1.3）
          case 'weclaw_status':
            const payload = data.payload as { status?: string } | undefined
            if (payload?.status) {
              onWeClawStatusChange?.(payload.status as 'online' | 'offline' | 'reconnecting' | 'unknown')
            }
            break
          default:
            console.log('Unknown message type:', data.type)
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
      }
    }
  }

  // 断开连接
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    stopPing()
    
    if (ws) {
      ws.close(1000, 'Client disconnect')
      ws = null
    }
    
    isConnected.value = false
    connectionId.value = null
  }

  // 发送消息
  function send(type: string, payload?: unknown) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type, payload }))
    }
  }

  // 开始心跳
  function startPing() {
    stopPing()
    lastPongTime = Date.now()
    
    // 每 15 秒发送一次心跳
    pingTimer = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        send('ping')
      }
    }, 15000) // 15秒
    
    // 检查 pong 响应超时（如果 45 秒没有收到 pong，重连）
    pongCheckTimer = setInterval(() => {
      const elapsed = Date.now() - lastPongTime
      if (elapsed > 45000) {
        console.warn(`WebSocket 心跳超时 (${elapsed}ms)，尝试重连...`)
        // 强制重连
        if (ws) {
          ws.close(4000, 'Heartbeat timeout')
        }
      }
    }, 15000)
  }

  // 停止心跳
  function stopPing() {
    if (pingTimer) {
      clearInterval(pingTimer)
      pingTimer = null
    }
    if (pongCheckTimer) {
      clearInterval(pongCheckTimer)
      pongCheckTimer = null
    }
  }

  // 发送聊天消息
  function sendChatMessage(content: string, attachments?: unknown[]) {
    send('chat', { content, attachments })
  }

  // 请求状态更新
  function requestStatus() {
    send('status_request')
  }

  return {
    isConnected,
    connectionId,
    connect,
    disconnect,
    send,
    sendChatMessage,
    requestStatus
  }
}
