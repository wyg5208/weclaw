<template>
  <div class="status-panel" :class="{ 'is-connected': isConnected }">
    <div class="status-indicator">
      <span class="dot" :class="statusClass"></span>
      <span class="text">{{ statusText }}</span>
    </div>
    <div v-if="showDetails && isConnected" class="status-details">
      <span class="latency">{{ latency }}ms</span>
      <span class="separator">|</span>
      <span class="model">{{ model }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  isConnected?: boolean
  latency?: number
  model?: string
  showDetails?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isConnected: false,
  latency: 0,
  model: '',
  showDetails: false
})

const statusClass = computed(() => ({
  'connected': props.isConnected,
  'disconnected': !props.isConnected
}))

const statusText = computed(() => props.isConnected ? '已连接' : '未连接')
</script>

<style scoped>
.status-panel {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 16px;
  font-size: 12px;
}

.status-panel.is-connected {
  background: rgba(7, 193, 96, 0.1);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.connected {
  background: #07c160;
  box-shadow: 0 0 6px rgba(7, 193, 96, 0.5);
}

.dot.disconnected {
  background: #ee0a24;
}

.text {
  color: var(--van-text-color);
}

.status-details {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--van-gray-6);
}

.separator {
  color: var(--van-gray-4);
}

.latency {
  color: var(--van-primary-color);
}
</style>
