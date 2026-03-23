/**
 * 认证状态管理
 * 使用 Pinia 管理用户登录状态和Token
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

interface User {
  user_id: string
  username: string
  settings: Record<string, unknown>
}

interface TokenInfo {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const tokenInfo = ref<TokenInfo | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!tokenInfo.value?.access_token)
  const accessToken = computed(() => tokenInfo.value?.access_token || null)
  const refreshToken = computed(() => tokenInfo.value?.refresh_token || null)

  // 从 localStorage 恢复状态
  function loadFromStorage() {
    const stored = localStorage.getItem('auth_state')
    if (stored) {
      try {
        const parsed = JSON.parse(stored)
        user.value = parsed.user
        tokenInfo.value = parsed.tokenInfo
      } catch {
        clearAuth()
      }
    }
  }

  // 保存到 localStorage
  function saveToStorage() {
    if (user.value && tokenInfo.value) {
      localStorage.setItem('auth_state', JSON.stringify({
        user: user.value,
        tokenInfo: tokenInfo.value
      }))
      localStorage.setItem('access_token', tokenInfo.value.access_token)
      localStorage.setItem('refresh_token', tokenInfo.value.refresh_token)
    }
  }

  // 清除认证状态
  function clearAuth() {
    user.value = null
    tokenInfo.value = null
    error.value = null
    localStorage.removeItem('auth_state')
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  // 登录
  async function login(username: string, password: string, deviceFingerprint?: string) {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.login({
        username,
        password,
        device_fingerprint: deviceFingerprint
      })

      // API 直接返回数据，不在 data 包装内
      const data = response.data as unknown as {
        access_token: string
        refresh_token: string
        token_type: string
        expires_in: number
        user: User
      }

      if (data.access_token && data.user) {
        user.value = data.user
        tokenInfo.value = {
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          token_type: data.token_type,
          expires_in: data.expires_in
        }
        saveToStorage()
        return true
      } else {
        error.value = '登录失败：响应数据格式错误'
        return false
      }
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string; error?: { message?: string } } } }
      error.value = axiosError.response?.data?.detail || axiosError.response?.data?.error?.message || '网络错误，请稍后重试'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 注册
  async function register(username: string, password: string, publicKey?: string) {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.register({
        username,
        password,
        public_key: publicKey
      })

      // API 返回格式：{ success: true, data: { user_id, username, created_at } }
      const responseData = response.data as unknown as {
        success: boolean
        data: {
          user_id: string
          username: string
          created_at: string
        }
      }

      if (responseData.success && responseData.data.user_id) {
        return true
      } else {
        error.value = '注册失败'
        return false
      }
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string; error?: { message?: string } } } }
      error.value = axiosError.response?.data?.detail || axiosError.response?.data?.error?.message || '网络错误，请稍后重试'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 刷新 Token
  async function refreshTokenSilent() {
    const storedRefreshToken = localStorage.getItem('refresh_token')
    if (!storedRefreshToken) {
      console.warn('refresh_token 不存在，无法刷新')
      clearAuth()
      return false
    }

    try {
      const response = await authApi.refresh()
      // API 直接返回数据
      const data = response.data as unknown as {
        access_token: string
        expires_in: number
      }
      if (data.access_token) {
        if (tokenInfo.value) {
          tokenInfo.value.access_token = data.access_token
          tokenInfo.value.expires_in = data.expires_in
        } else {
          tokenInfo.value = {
            access_token: data.access_token,
            refresh_token: storedRefreshToken,
            token_type: 'Bearer',
            expires_in: data.expires_in
          }
        }
        localStorage.setItem('access_token', data.access_token)
        console.log('Token 刷新成功')
        return true
      }
    } catch (err) {
      // 刷新失败，清除认证状态
      console.warn('Token 刷新失败，清除认证状态', err)
      clearAuth()
    }
    return false
  }

  // 登出
  async function logout() {
    try {
      await authApi.logout()
    } catch {
      // 忽略登出错误
    }
    clearAuth()
  }

  // 获取当前用户信息
  async function fetchCurrentUser() {
    if (!isAuthenticated.value) return false

    try {
      const response = await authApi.getMe()
      // API 直接返回数据
      const data = response.data as unknown as User
      if (data.user_id) {
        user.value = data
        return true
      }
    } catch {
      // Token 无效
    }
    return false
  }

  // 初始化 - 从存储恢复
  loadFromStorage()

  return {
    // State
    user,
    tokenInfo,
    isLoading,
    error,
    // Getters
    isAuthenticated,
    accessToken,
    refreshToken,
    // Actions
    login,
    register,
    logout,
    refreshTokenSilent,
    fetchCurrentUser,
    clearAuth
  }
})
