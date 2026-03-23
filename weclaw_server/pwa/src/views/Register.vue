<template>
  <div class="register-page">
    <div class="register-container">
      <!-- Logo -->
      <div class="logo">
        <h1 class="title">注册账号</h1>
        <p class="subtitle">创建您的 WeClaw 账号</p>
      </div>

      <!-- 注册表单 -->
      <van-form @submit="handleRegister" class="register-form">
        <van-cell-group inset>
          <van-field
            v-model="username"
            name="username"
            label="用户名"
            placeholder="3-32位字母数字下划线"
            :rules="[
              { required: true, message: '请输入用户名' },
              { pattern: /^[a-zA-Z0-9_]{3,32}$/, message: '用户名格式不正确' }
            ]"
            clearable
          />
          <van-field
            v-model="password"
            type="password"
            name="password"
            label="密码"
            placeholder="至少 8 位字符"
            :rules="[
              { required: true, message: '请输入密码' },
              { validator: (val: string) => val.length >= 8, message: '密码至少 8 位' }
            ]"
            clearable
          />
          <van-field
            v-model="confirmPassword"
            type="password"
            name="confirmPassword"
            label="确认密码"
            placeholder="再次输入密码"
            :rules="[
              { required: true, message: '请确认密码' },
              { validator: (val: string) => val === password, message: '两次密码不一致' }
            ]"
            clearable
          />
        </van-cell-group>

        <!-- 错误提示 -->
        <div v-if="authStore.error" class="error-message">
          <van-notice-bar color="#ff5252" background="#fff0f0">
            {{ authStore.error }}
          </van-notice-bar>
        </div>

        <div class="form-actions">
          <van-button
            round
            block
            type="primary"
            native-type="submit"
            :loading="authStore.isLoading"
          >
            注册
          </van-button>
        </div>
      </van-form>

      <!-- 登录链接 -->
      <div class="login-link">
        <span>已有账号？</span>
        <router-link to="/login">立即登录</router-link>
      </div>

      <!-- 安全提示 -->
      <div class="security-tips">
        <van-icon name="shield-o" size="16" />
        <span>您的数据将通过端到端加密进行保护</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { showToast, showSuccessToast } from 'vant'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')

async function handleRegister() {
  if (password.value !== confirmPassword.value) {
    showToast('两次密码不一致')
    return
  }

  const success = await authStore.register(username.value, password.value)
  if (success) {
    showSuccessToast('注册成功，请登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.register-container {
  width: 100%;
  max-width: 400px;
}

.logo {
  text-align: center;
  margin-bottom: 32px;
}

.title {
  color: white;
  font-size: 28px;
  margin: 0;
  font-weight: bold;
}

.subtitle {
  color: rgba(255, 255, 255, 0.8);
  font-size: 14px;
  margin-top: 8px;
}

.register-form {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.error-message {
  margin-top: 16px;
}

.form-actions {
  margin-top: 24px;
}

.login-link {
  text-align: center;
  margin-top: 24px;
  color: rgba(255, 255, 255, 0.9);
}

.login-link a {
  color: white;
  font-weight: bold;
  margin-left: 8px;
  text-decoration: underline;
}

.security-tips {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 24px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
}
</style>
