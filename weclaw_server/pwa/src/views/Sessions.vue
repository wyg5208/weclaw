<template>
  <div class="sessions-page">
    <!-- 顶部导航 -->
    <van-nav-bar title="历史会话" fixed placeholder />

    <!-- 会话列表 -->
    <div class="sessions-list" v-if="chatStore.sessions.length > 0">
      <van-cell-group inset>
        <van-swipe-cell v-for="session in chatStore.sessions" :key="session.session_id">
          <van-cell
            :title="session.title || '新对话'"
            :label="formatTime(session.last_active)"
            is-link
            @click="handleSelectSession(session)"
          >
            <template #value>
              <span class="message-count">{{ session.message_count }} 条消息</span>
            </template>
          </van-cell>
          <template #right>
            <van-button
              square
              type="danger"
              text="删除"
              @click="handleDeleteSession(session.session_id)"
            />
          </template>
        </van-swipe-cell>
      </van-cell-group>
    </div>

    <!-- 空状态 -->
    <van-empty
      v-else
      description="暂无历史会话"
      image="https://fastly.jsdelivr.net/npm/@vant/assets/custom-empty.png"
    >
      <van-button type="primary" @click="goToChat">
        开始新对话
      </van-button>
    </van-empty>

    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-container">
      <van-loading size="24px">加载中...</van-loading>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore, type Session } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import { showToast, showConfirmDialog } from 'vant'

const router = useRouter()
const chatStore = useChatStore()
const authStore = useAuthStore()

const isLoading = ref(false)

// 检查登录状态
onMounted(() => {
  if (!authStore.isAuthenticated) {
    router.push('/login')
    return
  }
  
  // 加载会话列表
  loadSessions()
})

// 加载会话列表
async function loadSessions() {
  isLoading.value = true
  await chatStore.loadSessions()
  isLoading.value = false
}

// 选择会话
function handleSelectSession(session: Session) {
  // 切换到选中的会话
  chatStore.loadHistory(session.session_id)
  router.push('/chat')
}

// 删除会话
async function handleDeleteSession(sessionId: string) {
  try {
    await showConfirmDialog({
      title: '确认删除',
      message: '确定要删除这个会话吗？此操作不可恢复。'
    })
    
    const success = await chatStore.deleteSession(sessionId)
    if (success) {
      showToast('会话已删除')
    } else {
      showToast('删除失败')
    }
  } catch {
    // 用户取消
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
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  
  return date.toLocaleDateString()
}

// 跳转到聊天页面
function goToChat() {
  router.push('/chat')
}
</script>

<style scoped>
.sessions-page {
  min-height: 100vh;
  background: var(--van-background);
}

.sessions-list {
  padding: 8px 0;
}

.message-count {
  font-size: 12px;
  color: var(--van-gray-5);
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 0;
}

.van-empty {
  padding-top: 100px;
}
</style>
