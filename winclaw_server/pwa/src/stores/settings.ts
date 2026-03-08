/**
 * 设置状态管理
 * 管理用户偏好和应用设置
 */

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export interface AppSettings {
  // 显示设置
  theme: 'light' | 'dark' | 'auto'
  fontSize: 'small' | 'medium' | 'large'
  language: 'zh-CN' | 'en-US'
  
  // 通知设置
  notifications: boolean
  soundEnabled: boolean
  vibrationEnabled: boolean
  
  // 聊天设置
  sendOnEnter: boolean
  showTimestamps: boolean
  showTokenCount: boolean
  autoScroll: boolean
  
  // 隐私设置
  saveHistory: boolean
  clearOnExit: boolean
  
  // 高级设置
  serverUrl: string
  streamResponse: boolean
  maxAttachments: number
}

const defaultSettings: AppSettings = {
  theme: 'auto',
  fontSize: 'medium',
  language: 'zh-CN',
  notifications: true,
  soundEnabled: true,
  vibrationEnabled: true,
  sendOnEnter: true,
  showTimestamps: true,
  showTokenCount: false,
  autoScroll: true,
  saveHistory: true,
  clearOnExit: false,
  serverUrl: '',
  streamResponse: true,
  maxAttachments: 5
}

export const useSettingsStore = defineStore('settings', () => {
  // 从 localStorage 加载设置
  function loadSettings(): AppSettings {
    const stored = localStorage.getItem('app_settings')
    if (stored) {
      try {
        return { ...defaultSettings, ...JSON.parse(stored) }
      } catch {
        return defaultSettings
      }
    }
    return defaultSettings
  }

  // State
  const settings = ref<AppSettings>(loadSettings())

  // 监听变化并保存
  watch(settings, (newSettings) => {
    localStorage.setItem('app_settings', JSON.stringify(newSettings))
  }, { deep: true })

  // 更新设置
  function updateSetting<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    settings.value[key] = value
  }

  // 批量更新设置
  function updateSettings(newSettings: Partial<AppSettings>) {
    settings.value = { ...settings.value, ...newSettings }
  }

  // 重置设置
  function resetSettings() {
    settings.value = { ...defaultSettings }
  }

  // 导出设置
  function exportSettings(): string {
    return JSON.stringify(settings.value, null, 2)
  }

  // 导入设置
  function importSettings(json: string): boolean {
    try {
      const imported = JSON.parse(json) as Partial<AppSettings>
      settings.value = { ...defaultSettings, ...imported }
      return true
    } catch {
      return false
    }
  }

  // 应用主题
  function applyTheme() {
    const theme = settings.value.theme
    const root = document.documentElement
    
    if (theme === 'auto') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      root.classList.toggle('dark', prefersDark)
    } else {
      root.classList.toggle('dark', theme === 'dark')
    }
  }

  // 初始化主题
  applyTheme()

  // 监听系统主题变化
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (settings.value.theme === 'auto') {
      applyTheme()
    }
  })

  return {
    settings,
    updateSetting,
    updateSettings,
    resetSettings,
    exportSettings,
    importSettings,
    applyTheme
  }
})
