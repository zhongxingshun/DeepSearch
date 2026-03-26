<template>
  <div class="login-page">
    <div class="login-container">
      <!-- Logo -->
      <div class="login-header">
        <div class="language-switcher">
          <el-select v-model="locale" size="small" @change="handleLocaleChange">
            <el-option value="zh-CN" :label="t('common.chinese')" />
            <el-option value="en-US" :label="t('common.english')" />
          </el-select>
        </div>
        <div class="logo">
          <el-icon :size="48" color="#409eff"><Search /></el-icon>
        </div>
        <h1>DeepSearch</h1>
        <p class="subtitle">{{ t('login.subtitle') }}</p>
      </div>
      
      <!-- 登录表单 -->
      <el-card class="login-card" shadow="hover">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          @submit.prevent="handleLogin"
        >
          <el-form-item :label="t('login.username')" prop="username">
            <el-input
              v-model="form.username"
              :prefix-icon="User"
              :placeholder="t('login.enterUsername')"
              size="large"
              autofocus
            />
          </el-form-item>
          
          <el-form-item :label="t('login.password')" prop="password">
            <el-input
              v-model="form.password"
              :prefix-icon="Lock"
              type="password"
              :placeholder="t('login.enterPassword')"
              size="large"
              show-password
            />
          </el-form-item>
          
          <el-form-item>
            <el-checkbox v-model="rememberMe">{{ t('login.rememberMe') }}</el-checkbox>
          </el-form-item>
          
          <el-button
            type="primary"
            native-type="submit"
            size="large"
            :loading="loading"
            class="login-btn"
          >
            {{ loading ? t('login.loggingIn') : t('login.login') }}
          </el-button>
        </el-form>
      </el-card>
      
      <!-- 版权信息 -->
      <div class="footer">
        <p>&copy; 2026 DeepSearch. All rights reserved.</p>
      </div>
    </div>
    
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Search, User, Lock } from '@element-plus/icons-vue'
import { useI18n } from '@/i18n'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { locale, setLocale, t } = useI18n()

const formRef = ref<FormInstance>()
const loading = ref(false)
const rememberMe = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: t('login.usernameRequired'), trigger: 'blur' },
  ],
  password: [
    { required: true, message: t('login.passwordRequired'), trigger: 'blur' },
    { min: 8, message: t('login.passwordMin'), trigger: 'blur' },
  ],
}

const handleLocaleChange = (value: 'zh-CN' | 'en-US') => {
  setLocale(value)
}

const handleLogin = async () => {
  if (!formRef.value || loading.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  
  try {
    await authStore.login({
      username: form.username,
      password: form.password,
    })
    
    ElMessage.success(t('login.loginSuccess'))
    
    // 跳转到之前的页面或首页
    const redirect = route.query.redirect as string
    router.push(redirect || '/')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || t('login.loginFailed'))
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

.login-container {
  width: 100%;
  max-width: 420px;
  padding: 20px;
  position: relative;
  z-index: 1;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;

  .language-switcher {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 16px;
  }
  
  .logo {
    width: 80px;
    height: 80px;
    margin: 0 auto 16px;
    background: rgba(255, 255, 255, 0.9);
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  }
  
  h1 {
    color: #fff;
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 8px;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  }
  
  .subtitle {
    color: rgba(255, 255, 255, 0.8);
    font-size: 14px;
  }
}

.login-card {
  border-radius: 16px;
  border: none;
  
  :deep(.el-card__body) {
    padding: 32px;
  }
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  margin-top: 8px;
}

.footer {
  text-align: center;
  margin-top: 24px;
  
  p {
    color: rgba(255, 255, 255, 0.6);
    font-size: 12px;
  }
}

/* 背景装饰 */
.bg-decoration {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}

.circle-1 {
  width: 400px;
  height: 400px;
  top: -100px;
  right: -100px;
}

.circle-2 {
  width: 300px;
  height: 300px;
  bottom: -50px;
  left: -50px;
}

.circle-3 {
  width: 200px;
  height: 200px;
  top: 40%;
  left: 10%;
}
</style>
