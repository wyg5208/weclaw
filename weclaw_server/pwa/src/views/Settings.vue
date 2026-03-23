<template>
  <div class="settings-page">
    <van-nav-bar title="设置" left-arrow @click-left="$router.back()" />

    <!-- 显示设置 -->
    <van-cell-group title="显示设置" inset>
      <van-cell title="主题" :value="getThemeLabel(settings.settings.theme)" @click="showThemePicker = true" />
      <van-cell title="字体大小" :value="getFontSizeLabel(settings.settings.fontSize)" @click="showFontSizePicker = true" />
      <van-cell title="语言" :value="getLanguageLabel(settings.settings.language)" />
    </van-cell-group>

    <!-- 聊天设置 -->
    <van-cell-group title="聊天设置" inset>
      <van-cell title="Enter发送" center>
        <template #right-icon>
          <van-switch v-model="settings.settings.sendOnEnter" size="20px" @change="saveSettings" />
        </template>
      </van-cell>
      <van-cell title="显示时间戳" center>
        <template #right-icon>
          <van-switch v-model="settings.settings.showTimestamps" size="20px" @change="saveSettings" />
        </template>
      </van-cell>
      <van-cell title="流式响应" center>
        <template #right-icon>
          <van-switch v-model="settings.settings.streamResponse" size="20px" @change="saveSettings" />
        </template>
      </van-cell>
    </van-cell-group>

    <!-- 通知设置 -->
    <van-cell-group title="通知设置" inset>
      <van-cell title="消息通知" center>
        <template #right-icon>
          <van-switch v-model="settings.settings.notifications" size="20px" @change="saveSettings" />
        </template>
      </van-cell>
      <van-cell title="声音" center>
        <template #right-icon>
          <van-switch v-model="settings.settings.soundEnabled" size="20px" @change="saveSettings" />
        </template>
      </van-cell>
      <van-cell title="振动" center>
        <template #right-icon>
          <van-switch v-model="settings.settings.vibrationEnabled" size="20px" @change="saveSettings" />
        </template>
      </van-cell>
    </van-cell-group>

    <!-- 隐私设置 -->
    <van-cell-group title="隐私设置" inset>
      <van-cell title="保存历史记录" center>
        <template #right-icon>
          <van-switch v-model="settings.settings.saveHistory" size="20px" @change="saveSettings" />
        </template>
      </van-cell>
      <van-cell title="退出时清除" center>
        <template #right-icon>
          <van-switch v-model="settings.settings.clearOnExit" size="20px" @change="saveSettings" />
        </template>
      </van-cell>
    </van-cell-group>

    <!-- 账号设置 -->
    <van-cell-group title="账号" inset>
      <van-cell title="用户名" :value="authStore.user?.username" />
      <van-cell title="用户ID" :value="authStore.user?.user_id" />
      <van-cell title="修改密码" is-link to="/change-password" />
      <van-cell title="导出设置" @click="handleExportSettings" />
      <van-cell title="重置设置" @click="handleResetSettings" />
    </van-cell-group>

    <!-- 设备管理 -->
    <van-cell-group title="设备管理" inset>
      <van-cell 
        :title="deviceStore.hasDevice ? '已绑定设备' : '未绑定设备'" 
        is-link 
        @click="showDeviceManager = true"
      >
        <template #label>
          <span v-if="deviceStore.hasDevice && deviceStore.deviceInfo">
            {{ deviceStore.deviceInfo.device_name }}
          </span>
          <span v-else class="no-device-hint">
            点击绑定 WeClaw PC 设备
          </span>
        </template>
        <template #right-icon>
          <van-icon 
            :name="deviceStore.hasDevice ? 'success' : 'warning-o'" 
            :color="deviceStore.hasDevice ? '#07c160' : '#ee0a24'" 
            size="18"
            style="margin-right: 4px"
          />
        </template>
      </van-cell>
    </van-cell-group>

    <!-- 关于 -->
    <van-cell-group title="关于" inset>
      <van-cell title="版本" value="1.0.0" />
      <van-cell title="服务端状态" :value="serverStatus" is-link to="/status" />
      <van-cell title="隐私政策" is-link />
      <van-cell title="用户协议" is-link />
    </van-cell-group>

    <!-- 退出登录 -->
    <div class="logout-section">
      <van-button block type="danger" @click="handleLogout">
        退出登录
      </van-button>
    </div>

    <!-- 主题选择器 -->
    <van-action-sheet
      v-model:show="showThemePicker"
      :actions="themeActions"
      @select="onThemeSelect"
    />

    <!-- 字体大小选择器 -->
    <van-action-sheet
      v-model:show="showFontSizePicker"
      :actions="fontSizeActions"
      @select="onFontSizeSelect"
    />

    <!-- 设备管理弹窗 -->
    <van-popup 
      v-model:show="showDeviceManager" 
      position="bottom" 
      :style="{ height: '80%' }"
      round
    >
      <div class="device-popup-header">
        <span class="device-popup-title">设备管理</span>
        <van-icon name="cross" size="20" @click="showDeviceManager = false" />
      </div>
      <DeviceManager />
    </van-popup>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { useDeviceStore } from '@/stores/device'
import { showConfirmDialog, showToast, showSuccessToast } from 'vant'
import DeviceManager from '@/components/DeviceManager.vue'

const router = useRouter()
const authStore = useAuthStore()
const settings = useSettingsStore()
const deviceStore = useDeviceStore()

const showThemePicker = ref(false)
const showFontSizePicker = ref(false)
const showDeviceManager = ref(false)
const serverStatus = ref('未知')

const themeActions = [
  { name: '跟随系统', value: 'auto' },
  { name: '浅色模式', value: 'light' },
  { name: '深色模式', value: 'dark' }
]

const fontSizeActions = [
  { name: '小', value: 'small' },
  { name: '中', value: 'medium' },
  { name: '大', value: 'large' }
]

function getThemeLabel(theme: string): string {
  const item = themeActions.find(a => a.value === theme)
  return item?.name || '跟随系统'
}

function getFontSizeLabel(size: string): string {
  const item = fontSizeActions.find(a => a.value === size)
  return item?.name || '中'
}

function getLanguageLabel(lang: string): string {
  return lang === 'zh-CN' ? '简体中文' : 'English'
}

function saveSettings() {
  settings.settings // 触发 watch 自动保存
}

function onThemeSelect(action: { value: string }) {
  settings.updateSetting('theme', action.value as 'light' | 'dark' | 'auto')
  settings.applyTheme()
}

function onFontSizeSelect(action: { value: string }) {
  settings.updateSetting('fontSize', action.value as 'small' | 'medium' | 'large')
}

function handleExportSettings() {
  const data = settings.exportSettings()
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'weclaw-settings.json'
  a.click()
  URL.revokeObjectURL(url)
  showSuccessToast('导出成功')
}

function handleResetSettings() {
  showConfirmDialog({
    title: '重置设置',
    message: '确定要重置所有设置吗？'
  }).then(() => {
    settings.resetSettings()
    showSuccessToast('已重置')
  }).catch(() => {})
}

async function handleLogout() {
  try {
    await showConfirmDialog({
      title: '退出登录',
      message: '确定要退出登录吗？'
    })
    await authStore.logout()
    router.push('/login')
    showToast('已退出登录')
  } catch {
    // 取消
  }
}

onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.push('/login')
  }
})
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  background: var(--van-background);
  padding-bottom: 80px;
}

.logout-section {
  padding: 32px 16px;
}

.no-device-hint {
  color: #969799;
  font-size: 12px;
}

.device-popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #ebedf0;
  background: white;
}

.device-popup-title {
  font-size: 16px;
  font-weight: 600;
  color: #323233;
}
</style>
