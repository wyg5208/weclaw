/**
 * API 客户端
 * 封装所有与后端的 API 交互
 */

import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/auth'

// API 响应类型
interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
  }
}

// 创建 axios 实例
const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加 Token
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器 - 处理错误
let isRefreshing = false  // 刷新锁
let refreshFailCount = 0  // 刷新失败计数
const MAX_REFRESH_RETRIES = 3  // 最大重试次数

client.interceptors.response.use(
  (response) => {
    // 成功响应，重置失败计数
    refreshFailCount = 0
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }
    
    // 排除 refresh 请求本身，避免无限循环
    if (originalRequest?.url?.includes('/auth/refresh')) {
      return Promise.reject(error)
    }
    
    // 排除登录和注册请求
    if (originalRequest?.url?.includes('/auth/login') || originalRequest?.url?.includes('/auth/register')) {
      return Promise.reject(error)
    }
    
    if (error.response?.status === 401 && !originalRequest?._retry) {
      // 检查重试次数
      if (refreshFailCount >= MAX_REFRESH_RETRIES) {
        console.warn('Token 刷新失败次数过多，跳转到登录页')
        const authStore = useAuthStore()
        authStore.logout()
        window.location.href = '/login'
        return Promise.reject(error)
      }
      
      // 防止并发刷新
      if (isRefreshing) {
        return Promise.reject(error)
      }
      
      originalRequest._retry = true
      isRefreshing = true
      
      try {
        const authStore = useAuthStore()
        const refreshed = await authStore.refreshTokenSilent()
        
        if (refreshed && originalRequest) {
          // 刷新成功，重置计数并重试原请求
          refreshFailCount = 0
          const token = localStorage.getItem('access_token')
          if (token && originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${token}`
          }
          return client.request(originalRequest)
        } else {
          // 刷新失败
          refreshFailCount++
          authStore.logout()
          window.location.href = '/login'
        }
      } catch {
        refreshFailCount++
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)

// ========== 认证 API ==========

export const authApi = {
  register: (data: {
    username: string
    password: string
    public_key?: string
    device_fingerprint?: string
  }) => client.post<ApiResponse<{ user_id: string; username: string }>>('/auth/register', data),

  login: (data: {
    username: string
    password: string
    device_fingerprint?: string
  }) => client.post<ApiResponse<{
    access_token: string
    refresh_token: string
    token_type: string
    expires_in: number
    user: { user_id: string; username: string; settings: Record<string, unknown> }
  }>>('/auth/login', data),

  refresh: () => client.post<ApiResponse<{ access_token: string; expires_in: number }>>(
    '/auth/refresh',
    {},
    { headers: { Authorization: `Bearer ${localStorage.getItem('refresh_token')}` } }
  ),

  logout: () => client.post('/auth/logout'),

  getMe: () => client.get<ApiResponse<{
    user_id: string
    username: string
    settings: Record<string, unknown>
  }>>('/auth/me'),

  // 设备绑定相关
  generateBindingToken: () => client.post<ApiResponse<{
    binding_token: string
    expires_in: number
    message: string
  }>>('/auth/binding-token'),

  getDeviceInfo: () => client.get<ApiResponse<{
    device_id: string
    device_name: string
    bound_at: string
    last_connected: string | null
    status: string
  }>>('/auth/device'),

  unbindDevice: () => client.delete<ApiResponse<{
    success: boolean
    message: string
  }>>('/auth/device')
}

// ========== 聊天 API ==========

export const chatApi = {
  sendMessage: (data: {
    message: string
    session_id?: string
    attachments?: Array<{
      type: string
      data: string
      filename: string
      mime_type: string
    }>
    options?: Record<string, unknown>
  }) => client.post<ApiResponse<{
    message_id: string
    session_id: string
    status: string
  }>>('/chat', data),

  getHistory: (sessionId?: string, limit = 50) => 
    client.get<ApiResponse<{
      session_id: string
      messages: Array<Record<string, unknown>>
      has_more: boolean
    }>>('/chat/history', { params: { session_id: sessionId, limit } }),

  stopGeneration: (sessionId: string) =>
    client.post<ApiResponse<{ success: boolean }>>('/chat/stop', null, { params: { session_id: sessionId } }),

  // 获取会话列表
  getSessions: (limit = 20) =>
    client.get<ApiResponse<{
      sessions: Array<{
        session_id: string
        title: string
        created_at: string
        last_active: string
        message_count: number
      }>
      total: number
    }>>('/chat/sessions', { params: { limit } }),

  // 删除会话
  deleteSession: (sessionId: string) =>
    client.delete<ApiResponse<{ success: boolean; message: string }>>(`/chat/sessions/${sessionId}`)
}

// ========== 状态 API ==========

export const statusApi = {
  getStatus: () => client.get<ApiResponse<{
    status: string
    version: string
    uptime_seconds: number
    current_task: Record<string, unknown> | null
    model: Record<string, unknown> | null
    statistics: Record<string, unknown> | null
  }>>('/status'),

  getTools: () => client.get<ApiResponse<{
    tools: Array<{
      name: string
      description: string
      actions: string[]
      category: string
    }>
    total: number
  }>>('/tools'),

  getHealth: () => client.get<{
    status: string
    components: Record<string, string>
    active_connections: number
  }>('/health')
}

// ========== 文件 API ==========

export const fileApi = {
  upload: (file: File, sessionId?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (sessionId) {
      formData.append('session_id', sessionId)
    }
    return client.post<ApiResponse<{
      attachment_id: string
      filename: string
      size_bytes: number
      url: string
    }>>('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  getUrl: (attachmentId: string) => `/api/files/${attachmentId}`,

  getThumbnailUrl: (attachmentId: string) => `/api/files/${attachmentId}/thumbnail`,

  delete: (attachmentId: string) => client.delete(`/files/${attachmentId}`)
}

export default client
