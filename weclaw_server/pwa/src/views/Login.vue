<template>
  <div class="login-page">
    <div class="login-container">
      <!-- Logo -->
      <div class="logo">
        <img src="@/assets/logo.svg" alt="WeClaw" class="logo-img" />
        <h1 class="title">WeClaw</h1>
        <p class="subtitle">远程控制助手</p>
      </div>

      <!-- 登录表单 -->
      <van-form @submit="handleLogin" class="login-form">
        <van-cell-group inset>
          <van-field
            v-model="username"
            name="username"
            label="用户名"
            placeholder="请输入用户名"
            :rules="[{ required: true, message: '请输入用户名' }]"
            clearable
          />
          <van-field
            v-model="password"
            type="password"
            name="password"
            label="密码"
            placeholder="请输入密码"
            :rules="[{ required: true, message: '请输入密码' }]"
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
            登录
          </van-button>
        </div>
      </van-form>

      <!-- 注册链接 -->
      <div class="register-link">
        <span>还没有账号？</span>
        <router-link to="/register">立即注册</router-link>
      </div>

      <!-- 功能说明 -->
      <div class="features">
        <div class="feature-item">
          <van-icon name="lock" size="20" />
          <span>端到端加密</span>
        </div>
        <div class="feature-item">
          <van-icon name="chat-o" size="20" />
          <span>实时对话</span>
        </div>
        <div class="feature-item">
          <van-icon name="phone-circle-o" size="20" />
          <span>远程控制</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { showToast } from 'vant'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('')
const password = ref('')

async function handleLogin() {
  const success = await authStore.login(username.value, password.value)
  if (success) {
    showToast('登录成功')
    router.push('/chat')
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-container {
  width: 100%;
  max-width: 400px;
}

.logo {
  text-align: center;
  margin-bottom: 40px;
}

.logo-img {
  width: 80px;
  height: 80px;
  margin-bottom: 16px;
}

.title {
  color: white;
  font-size: 32px;
  margin: 0;
  font-weight: bold;
}

.subtitle {
  color: rgba(255, 255, 255, 0.8);
  font-size: 16px;
  margin-top: 8px;
}

.login-form {
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

.register-link {
  text-align: center;
  margin-top: 24px;
  color: rgba(255, 255, 255, 0.9);
}

.register-link a {
  color: white;
  font-weight: bold;
  margin-left: 8px;
  text-decoration: underline;
}

.features {
  display: flex;
  justify-content: center;
  gap: 32px;
  margin-top: 40px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
}
</style>
