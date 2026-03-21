/**
 * 设备绑定状态管理
 * 管理 PWA 用户与 WinClaw PC 设备的绑定关系
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

interface DeviceInfo {
  device_id: string
  device_name: string
  bound_at: string
  last_connected: string | null
  status: string
}

interface BindingToken {
  token: string
  expires_at: number
  message: string
}

export const useDeviceStore = defineStore('device', () => {
  // State
  const deviceInfo = ref<DeviceInfo | null>(null)
  const bindingToken = ref<BindingToken | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  
  // ✅ 新增：WinClaw 实时状态（Phase 1.3）
  const winclawStatus = ref<'online' | 'offline' | 'reconnecting' | 'unknown'>('unknown')
  const lastStatusChangeAt = ref<string | null>(null)

  // Getters
  const hasDevice = computed(() => !!deviceInfo.value && deviceInfo.value.status === 'active')
  const isDeviceOnline = computed(() => {
    // 优先使用服务器返回的 is_online 字段
    if (deviceInfo.value && 'is_online' in deviceInfo.value) {
      return (deviceInfo.value as DeviceInfo & { is_online?: boolean }).is_online === true
    }
    // 降级使用最后连接时间判断
    if (!deviceInfo.value?.last_connected) return false
    const lastConnected = new Date(deviceInfo.value.last_connected).getTime()
    const now = Date.now()
    // 5 分钟内有连接认为在线
    return now - lastConnected < 5 * 60 * 1000
  })
  
  // ✅ 新增：计算属性（综合判断在线状态）
  const comprehensiveOnlineStatus = computed(() => {
    // 优先使用实时 WebSocket 状态
    if (winclawStatus.value !== 'unknown') {
      return winclawStatus.value === 'online'
    }
    // 降级使用最后连接时间判断
    return isDeviceOnline.value
  })

  // 生成绑定 Token
  async function generateBindingToken() {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.generateBindingToken()
      const data = response.data as unknown as {
        binding_token: string
        expires_in: number
        message: string
      }

      if (data.binding_token) {
        const expiresAt = Date.now() + data.expires_in * 1000
        bindingToken.value = {
          token: data.binding_token,
          expires_at: expiresAt,
          message: data.message
        }
        return data.binding_token
      } else {
        error.value = '生成 Token 失败'
        return null
      }
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      error.value = axiosError.response?.data?.detail || '网络错误，请稍后重试'
      return null
    } finally {
      isLoading.value = false
    }
  }

  // 获取设备信息
  async function fetchDeviceInfo() {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.getDeviceInfo()
      const data = response.data as unknown as DeviceInfo

      if (data.device_id) {
        deviceInfo.value = data
        return true
      }
    } catch (err) {
      const axiosError = err as { response?: { status?: number; data?: { detail?: string } } }
      // 404 表示未绑定设备，不算错误
      if (axiosError.response?.status === 404) {
        deviceInfo.value = null
        return false
      }
      error.value = axiosError.response?.data?.detail || '获取设备信息失败'
    } finally {
      isLoading.value = false
    }
    return false
  }

  // 解绑设备
  async function unbindDevice() {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.unbindDevice()
      const data = response.data as unknown as { success: boolean }

      if (data.success) {
        deviceInfo.value = null
        bindingToken.value = null
        return true
      }
      return false
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } }
      error.value = axiosError.response?.data?.detail || '解绑失败'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // 清除绑定 Token
  function clearBindingToken() {
    bindingToken.value = null
  }

  // 检查 Token 是否过期
  function isTokenExpired(): boolean {
    if (!bindingToken.value) return true
    return Date.now() > bindingToken.value.expires_at
  }
  
  // ✅ 新增：更新 WinClaw 实时状态（Phase 1.3）
  function updateWinClawStatus(status: 'online' | 'offline' | 'reconnecting' | 'unknown') {
    winclawStatus.value = status
    lastStatusChangeAt.value = new Date().toISOString()
  }

  return {
    // State
    deviceInfo,
    bindingToken,
    isLoading,
    error,
    // ✅ 新增：WinClaw 状态
    winclawStatus,
    lastStatusChangeAt,
    // Getters
    hasDevice,
    isDeviceOnline,
    comprehensiveOnlineStatus,
    // Actions
    generateBindingToken,
    fetchDeviceInfo,
    unbindDevice,
    clearBindingToken,
    isTokenExpired,
    // ✅ 新增：状态更新方法
    updateWinClawStatus
  }
})
