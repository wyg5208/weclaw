<template>
  <div class="status-page">
    <van-nav-bar title="状态监控" left-arrow @click-left="$router.back()" />

    <!-- 连接状态 -->
    <div class="status-card">
      <div class="status-header">
        <van-icon :name="statusData.connected ? 'success' : 'cross'" :color="statusData.connected ? '#07c160' : '#ee0a24'" size="24" />
        <span class="status-text">{{ statusData.connected ? '已连接' : '未连接' }}</span>
      </div>
      <div class="status-details">
        <div class="detail-item">
          <span class="label">服务器</span>
          <span class="value">{{ statusData.serverUrl || '未配置' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">延迟</span>
          <span class="value">{{ statusData.latency }}ms</span>
        </div>
      </div>
    </div>

    <!-- WinClaw 状态 -->
    <van-cell-group title="WinClaw 状态" inset>
      <van-cell title="运行状态" :value="winclawStatus.status">
        <template #icon>
          <van-icon :name="getStatusIcon(winclawStatus.status)" :color="getStatusColor(winclawStatus.status)" size="20" style="margin-right: 8px" />
        </template>
      </van-cell>
      <van-cell title="版本" :value="winclawStatus.version" />
      <van-cell title="运行时间" :value="formatUptime(winclawStatus.uptime_seconds)" />
      <van-cell title="当前模型" :value="winclawStatus.model?.name || '无'" />
    </van-cell-group>

    <!-- 当前任务 -->
    <van-cell-group v-if="winclawStatus.current_task" title="当前任务" inset>
      <van-cell title="任务类型" :value="winclawStatus.current_task.type" />
      <van-cell title="任务状态" :value="winclawStatus.current_task.status" />
      <van-cell title="开始时间" :value="formatTime(winclawStatus.current_task.started_at)" />
      <van-cell v-if="winclawStatus.current_task.progress" title="进度">
        <van-progress :percentage="winclawStatus.current_task.progress" />
      </van-cell>
    </van-cell-group>

    <!-- 统计信息 -->
    <van-cell-group title="统计信息" inset>
      <van-cell title="总会话数" :value="statistics.total_sessions" />
      <van-cell title="今日消息" :value="statistics.today_messages" />
      <van-cell title="总消息数" :value="statistics.total_messages" />
      <van-cell title="工具调用" :value="statistics.tool_calls" />
    </van-cell-group>

    <!-- 可用工具 -->
    <van-cell-group title="可用工具" inset>
      <van-cell
        v-for="tool in tools"
        :key="tool.name"
        :title="tool.name"
        :label="tool.description"
      >
        <template #right-icon>
          <van-tag type="primary">{{ tool.category }}</van-tag>
        </template>
      </van-cell>
    </van-cell-group>

    <!-- 操作按钮 -->
    <div class="actions">
      <van-button block type="primary" @click="refreshStatus">
        刷新状态
      </van-button>
      <van-button block @click="goToChat">
        开始对话
      </van-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { statusApi } from '@/api'
import { showToast } from 'vant'

const router = useRouter()

const statusData = ref({
  connected: false,
  serverUrl: '',
  latency: 0
})

const winclawStatus = ref<{
  status: string
  version: string
  uptime_seconds: number
  current_task: {
    type: string
    status: string
    started_at: string
    progress?: number
  } | null
  model: { name: string } | null
}>({
  status: 'unknown',
  version: '',
  uptime_seconds: 0,
  current_task: null,
  model: null
})

const statistics = ref({
  total_sessions: 0,
  today_messages: 0,
  total_messages: 0,
  tool_calls: 0
})

const tools = ref<Array<{ name: string; description: string; category: string }>>([])

// 刷新状态
async function refreshStatus() {
  showToast('刷新中...')
  
  try {
    // 获取 WinClaw 状态
    const statusRes = await statusApi.getStatus()
    // API 直接返回数据
    const data = statusRes.data as unknown as {
      status: string
      version: string
      uptime_seconds: number
      current_task: {
        type: string
        status: string
        started_at: string
        progress?: number
      } | null
      model: { name: string } | null
    }
    if (data.status) {
      winclawStatus.value = {
        status: data.status || 'unknown',
        version: data.version || '',
        uptime_seconds: data.uptime_seconds || 0,
        current_task: data.current_task || null,
        model: data.model || null
      }
      statusData.value.connected = true
    }

    // 获取健康状态
    const healthRes = await statusApi.getHealth()
    const healthData = healthRes.data as unknown as { status: string }
    statusData.value.connected = healthData.status === 'healthy'

    // 获取工具列表
    const toolsRes = await statusApi.getTools()
    const toolsData = toolsRes.data as unknown as { tools: Array<{ name: string; description: string; category: string }> }
    if (toolsData.tools) {
      tools.value = toolsData.tools
    }

    showToast('刷新成功')
  } catch (err) {
    statusData.value.connected = false
    showToast('连接失败')
  }
}

// 跳转到聊天
function goToChat() {
  router.push('/chat')
}

// 格式化运行时间
function formatUptime(seconds: number): string {
  if (!seconds) return '未知'
  
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) return `${days}天 ${hours}小时`
  if (hours > 0) return `${hours}小时 ${mins}分钟`
  return `${mins}分钟`
}

// 格式化时间
function formatTime(dateStr: string): string {
  if (!dateStr) return '未知'
  return new Date(dateStr).toLocaleString()
}

// 获取状态图标
function getStatusIcon(status: string): string {
  switch (status) {
    case 'active': return 'success'
    case 'idle': return 'clock'
    case 'busy': return 'replay'
    case 'error': return 'warning'
    default: return 'question'
  }
}

// 获取状态颜色
function getStatusColor(status: string): string {
  switch (status) {
    case 'active': return '#07c160'
    case 'idle': return '#ff976a'
    case 'busy': return '#1989fa'
    case 'error': return '#ee0a24'
    default: return '#969799'
  }
}

let refreshTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  refreshStatus()
  // 每30秒刷新一次
  refreshTimer = setInterval(refreshStatus, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.status-page {
  min-height: 100vh;
  background: var(--van-background);
  padding-bottom: 100px;
}

.status-card {
  margin: 16px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.status-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.status-text {
  font-size: 18px;
  font-weight: bold;
}

.status-details {
  display: flex;
  gap: 24px;
}

.detail-item {
  display: flex;
  flex-direction: column;
}

.detail-item .label {
  font-size: 12px;
  color: var(--van-gray-6);
}

.detail-item .value {
  font-size: 16px;
  font-weight: 500;
}

.actions {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px;
  background: var(--van-background);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
