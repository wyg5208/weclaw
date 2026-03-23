<template>
  <div class="device-manager">
    <!-- 已绑定设备信息 -->
    <div v-if="deviceStore.hasDevice && deviceStore.deviceInfo" class="device-info-card">
      <div class="device-header">
        <van-icon name="desktop-o" size="32" color="#1989fa" />
        <div class="device-status">
          <div class="device-name">{{ deviceStore.deviceInfo.device_name }}</div>
          <van-tag :type="deviceStore.isDeviceOnline ? 'success' : 'default'" size="medium">
            {{ deviceStore.isDeviceOnline ? '在线' : '离线' }}
          </van-tag>
        </div>
      </div>
      
      <div class="device-details">
        <div class="detail-row">
          <span class="label">设备 ID</span>
          <span class="value">{{ formatDeviceId(deviceStore.deviceInfo.device_id) }}</span>
        </div>
        <div class="detail-row">
          <span class="label">绑定时间</span>
          <span class="value">{{ formatTime(deviceStore.deviceInfo.bound_at) }}</span>
        </div>
        <div class="detail-row">
          <span class="label">最后连接</span>
          <span class="value">{{ formatLastConnected(deviceStore.deviceInfo.last_connected) }}</span>
        </div>
      </div>

      <van-button block type="danger" plain @click="handleUnbind">
        解绑设备
      </van-button>
    </div>

    <!-- 未绑定状态 -->
    <div v-else class="no-device-card">
      <van-empty
        description="未绑定 WeClaw PC 设备"
        image="network"
      >
        <van-button type="primary" @click="showBindDialog = true">
          绑定新设备
        </van-button>
      </van-empty>
    </div>

    <!-- 绑定对话框 -->
    <van-dialog
      v-model:show="showBindDialog"
      title="绑定 WeClaw PC"
      :show-confirm-button="false"
      :close-on-click-overlay="true"
    >
      <div class="bind-dialog-content">
        <!-- 步骤1：生成 Token -->
        <div v-if="!deviceStore.bindingToken || deviceStore.isTokenExpired()" class="step-generate">
          <div class="step-description">
            <van-icon name="info-o" size="20" />
            <span>点击下方按钮生成绑定 Token，然后在 WeClaw PC 端输入该 Token 完成绑定</span>
          </div>
          <van-button 
            block 
            type="primary" 
            :loading="deviceStore.isLoading"
            @click="handleGenerateToken"
          >
            生成绑定 Token
          </van-button>
        </div>

        <!-- 步骤2：显示 Token -->
        <div v-else class="step-show-token">
          <div class="token-container">
            <div class="token-label">绑定 Token：</div>
            <div class="token-display">{{ formatToken(deviceStore.bindingToken.token) }}</div>
            <van-button 
              size="small" 
              type="primary" 
              plain 
              @click="copyToken"
            >
              <van-icon name="notes-o" />
              复制
            </van-button>
          </div>

          <div class="token-hint">
            <van-count-down :time="remainingTime" @finish="handleTokenExpired">
              <template #default="timeData">
                <span class="countdown-text">
                  Token 有效期：{{ timeData.minutes }}:{{ timeData.seconds }}
                </span>
              </template>
            </van-count-down>
          </div>

          <div class="bind-steps">
            <div class="step-title">绑定步骤：</div>
            <ol>
              <li>复制上方的绑定 Token</li>
              <li>打开 WeClaw PC 端</li>
              <li>在设置中找到"设备绑定"</li>
              <li>输入 Token 并确认</li>
            </ol>
          </div>

          <van-button 
            block 
            plain
            @click="handleCancelBind"
          >
            取消绑定
          </van-button>
        </div>
      </div>
    </van-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useDeviceStore } from '@/stores/device'
import { showConfirmDialog, showToast, showSuccessToast } from 'vant'

const deviceStore = useDeviceStore()
const showBindDialog = ref(false)

// 剩余时间（毫秒）
const remainingTime = computed(() => {
  if (!deviceStore.bindingToken) return 0
  const remaining = deviceStore.bindingToken.expires_at - Date.now()
  return remaining > 0 ? remaining : 0
})

// 格式化设备 ID
function formatDeviceId(deviceId: string): string {
  if (!deviceId) return '未知'
  return deviceId.length > 16 ? `${deviceId.substring(0, 16)}...` : deviceId
}

// 格式化 Token（分段显示）
function formatToken(token: string): string {
  if (!token) return ''
  // 每16个字符换行
  const parts = []
  for (let i = 0; i < token.length; i += 16) {
    parts.push(token.substring(i, i + 16))
  }
  return parts.join('\n')
}

// 格式化时间
function formatTime(dateStr: string): string {
  if (!dateStr) return '未知'
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 格式化最后连接时间
function formatLastConnected(dateStr: string | null): string {
  if (!dateStr) return '从未连接'
  const time = new Date(dateStr).getTime()
  const now = Date.now()
  const diff = now - time
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return `${Math.floor(diff / 86400000)} 天前`
}

// 生成绑定 Token
async function handleGenerateToken() {
  const token = await deviceStore.generateBindingToken()
  if (token) {
    showSuccessToast('Token 生成成功')
  } else {
    showToast(deviceStore.error || '生成失败')
  }
}

// 复制 Token
async function copyToken() {
  if (!deviceStore.bindingToken) return
  
  try {
    await navigator.clipboard.writeText(deviceStore.bindingToken.token)
    showSuccessToast('已复制到剪贴板')
  } catch {
    showToast('复制失败，请手动复制')
  }
}

// Token 过期
function handleTokenExpired() {
  deviceStore.clearBindingToken()
  showToast('Token 已过期，请重新生成')
}

// 取消绑定
function handleCancelBind() {
  deviceStore.clearBindingToken()
  showBindDialog.value = false
}

// 解绑设备
async function handleUnbind() {
  try {
    await showConfirmDialog({
      title: '解绑设备',
      message: '确定要解绑当前设备吗？解绑后需要重新生成 Token 才能再次绑定。'
    })
    
    const success = await deviceStore.unbindDevice()
    if (success) {
      showSuccessToast('设备已解绑')
    } else {
      showToast(deviceStore.error || '解绑失败')
    }
  } catch {
    // 取消
  }
}

// 初始化
onMounted(() => {
  deviceStore.fetchDeviceInfo()
})
</script>

<style scoped>
.device-manager {
  padding: 16px;
}

.device-info-card {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.device-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.device-status {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.device-name {
  font-size: 18px;
  font-weight: 600;
  color: #323233;
}

.device-details {
  margin-bottom: 16px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 14px;
}

.detail-row .label {
  color: #969799;
}

.detail-row .value {
  color: #323233;
  font-weight: 500;
}

.no-device-card {
  background: white;
  border-radius: 12px;
  padding: 32px 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

/* 绑定对话框 */
.bind-dialog-content {
  padding: 16px;
}

.step-generate {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.step-description {
  display: flex;
  gap: 8px;
  padding: 12px;
  background: #f7f8fa;
  border-radius: 8px;
  font-size: 14px;
  color: #646566;
  line-height: 1.6;
}

.step-show-token {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.token-container {
  background: #f7f8fa;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.token-label {
  font-size: 14px;
  font-weight: 600;
  color: #323233;
}

.token-display {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  color: #1989fa;
  word-break: break-all;
  white-space: pre-wrap;
  line-height: 1.8;
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #ebedf0;
}

.token-hint {
  text-align: center;
  padding: 8px;
  background: #fff7e6;
  border-radius: 6px;
}

.countdown-text {
  font-size: 14px;
  color: #ff976a;
  font-weight: 500;
}

.bind-steps {
  padding: 12px;
  background: #f7f8fa;
  border-radius: 8px;
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  color: #323233;
  margin-bottom: 8px;
}

.bind-steps ol {
  margin: 0;
  padding-left: 20px;
  font-size: 14px;
  color: #646566;
  line-height: 1.8;
}

.bind-steps li {
  margin: 4px 0;
}
</style>
