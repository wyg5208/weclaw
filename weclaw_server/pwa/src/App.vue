<template>
  <van-config-provider :theme="currentTheme">
    <router-view />
    <!-- 底部导航栏 -->
    <van-tabbar v-if="showTabbar" route>
      <van-tabbar-item to="/chat" icon="chat-o">聊天</van-tabbar-item>
      <van-tabbar-item to="/sessions" icon="records">会话</van-tabbar-item>
      <van-tabbar-item to="/status" icon="bar-chart-o">状态</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="setting-o">设置</van-tabbar-item>
    </van-tabbar>
  </van-config-provider>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const settingsStore = useSettingsStore()
const authStore = useAuthStore()

const currentTheme = computed(() => {
  const theme = settingsStore.settings.theme
  if (theme === 'auto') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return theme
})

// 判断是否显示底部导航栏（登录/注册页面不显示）
const showTabbar = computed(() => {
  // 未登录时不显示
  if (!authStore.isAuthenticated) {
    return false
  }
  // 登录和注册页面不显示
  const path = route.path
  if (path === '/login' || path === '/register') {
    return false
  }
  return true
})

onMounted(() => {
  // 初始化主题
  settingsStore.applyTheme()
})
</script>

<style>
#app {
  width: 100%;
  min-height: 100vh;
  background-color: var(--van-background);
  padding-bottom: 50px; /* 为底部导航栏留出空间 */
}
</style>
