<template>
  <div v-if="attachments.length > 0" class="attachment-preview">
    <div class="attachment-header">
      <span class="attachment-title">📎 附件 ({{ attachments.length }})</span>
      <van-icon name="clear" size="18" @click="handleClear" />
    </div>
    
    <div class="attachment-list">
      <div
        v-for="(att, index) in attachments"
        :key="index"
        class="attachment-item"
      >
        <!-- 图片预览 -->
        <div v-if="att.type === 'image'" class="image-preview">
          <img :src="att.url" :alt="att.filename" />
        </div>
        
        <!-- 文件图标 -->
        <div v-else class="file-icon">
          <van-icon 
            :name="getFileIcon(att.type)" 
            size="32" 
            color="var(--van-primary-color)"
          />
        </div>
        
        <!-- 文件信息 -->
        <div class="file-info">
          <div class="file-name">{{ att.filename }}</div>
          <div class="file-meta">
            <span>{{ formatSize(att.size_bytes) }}</span>
            <span v-if="att.type !== 'image'">{{ att.mime_type }}</span>
          </div>
        </div>
        
        <!-- 删除按钮 -->
        <van-icon 
          name="cross" 
          size="18" 
          class="remove-btn"
          @click="handleRemove(index)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Attachment } from '@/stores/chat'

interface Props {
  attachments: Attachment[]
}

const props = defineProps<Props>()

// 定义事件
const emit = defineEmits<{
  remove: [index: number]
  clear: []
}>()

/**
 * 获取文件类型对应的图标
 */
function getFileIcon(type: string): string {
  const icons: Record<string, string> = {
    'audio': 'volume-o',
    'video': 'video-o',
    'document': 'description',
    'code': 'orders-o',  // 代码文件使用列表图标
    'file': 'description-o'
  }
  return icons[type] || 'description-o'
}

/**
 * 格式化文件大小
 */
function formatSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  } else if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  } else {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }
}

/**
 * 删除附件
 */
function handleRemove(index: number) {
  emit('remove', index)
}

/**
 * 清空所有附件
 */
function handleClear() {
  emit('clear')
}
</script>

<style scoped>
.attachment-preview {
  background: var(--van-background-2);
  border-radius: 8px;
  margin: 8px;
  padding: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.attachment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--van-gray-7);
}

.attachment-title {
  font-weight: 500;
}

.attachment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  background: var(--van-background);
  border-radius: 8px;
  position: relative;
}

.image-preview {
  flex-shrink: 0;
  width: 60px;
  height: 60px;
  border-radius: 6px;
  overflow: hidden;
  background: var(--van-gray-1);
}

.image-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.file-icon {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--van-gray-1);
  border-radius: 6px;
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-size: 14px;
  color: var(--van-text-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-meta {
  font-size: 12px;
  color: var(--van-gray-5);
  display: flex;
  gap: 8px;
}

.remove-btn {
  flex-shrink: 0;
  padding: 4px;
  cursor: pointer;
  color: var(--van-gray-5);
  transition: color 0.2s;
}

.remove-btn:hover {
  color: var(--van-danger-color);
}
</style>
