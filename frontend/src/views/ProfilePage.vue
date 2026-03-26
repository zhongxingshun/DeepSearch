<template>
  <div class="profile-page page-container">
    <div class="page-header">
      <h1>{{ t('profile.title') }}</h1>
    </div>
    
    <el-tabs v-model="activeTab">
      <el-tab-pane :label="t('profile.basicInfo')" name="info">
        <div class="card">
          <el-descriptions :column="2" border>
            <el-descriptions-item :label="t('profile.username')">{{ user?.username }}</el-descriptions-item>
            <el-descriptions-item :label="t('profile.email')">{{ user?.email }}</el-descriptions-item>
            <el-descriptions-item :label="t('profile.role')">
              <el-tag :type="getRoleTagType(user?.role)">
                {{ getRoleText(user?.role) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('profile.status')">
              <el-tag :type="user?.is_active ? 'success' : 'info'">
                {{ user?.is_active ? t('profile.active') : t('profile.disabled') }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('profile.createdAt')">{{ formatDate(user?.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>
      
      <el-tab-pane :label="t('profile.password')" name="password">
        <div class="card" style="max-width: 500px">
          <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
            <el-form-item :label="t('profile.currentPassword')" prop="currentPassword">
              <el-input v-model="form.currentPassword" type="password" show-password />
            </el-form-item>
            <el-form-item :label="t('profile.newPassword')" prop="newPassword">
              <el-input v-model="form.newPassword" type="password" show-password />
            </el-form-item>
            <el-form-item :label="t('profile.confirmPassword')" prop="confirmPassword">
              <el-input v-model="form.confirmPassword" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleSubmit">
                {{ t('profile.submit') }}
              </el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import dayjs from 'dayjs'
import { useI18n } from '@/i18n'

const route = useRoute()
const authStore = useAuthStore()
const { t } = useI18n()

const activeTab = ref(route.query.tab as string || 'info')
const formRef = ref<FormInstance>()
const loading = ref(false)
const user = computed(() => authStore.user)

const form = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const validatePass = (_: any, value: string, callback: Function) => {
  if (value !== form.newPassword) {
    callback(new Error(t('profile.passwordMismatch')))
  } else {
    callback()
  }
}

const rules: FormRules = {
  currentPassword: [{ required: true, message: t('profile.currentPasswordRequired'), trigger: 'blur' }],
  newPassword: [
    { required: true, message: t('profile.newPasswordRequired'), trigger: 'blur' },
    { min: 8, message: t('profile.passwordMin'), trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: t('profile.confirmPasswordRequired'), trigger: 'blur' },
    { validator: validatePass, trigger: 'blur' },
  ],
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  try {
    await authStore.changePassword(form.currentPassword, form.newPassword)
    ElMessage.success(t('profile.passwordChanged'))
    form.currentPassword = ''
    form.newPassword = ''
    form.confirmPassword = ''
  } catch {
    ElMessage.error(t('profile.passwordChangeFailed'))
  } finally {
    loading.value = false
  }
}

const formatDate = (date?: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'
const getRoleText = (role?: string) => {
  const roleTextMap: Record<string, string> = {
    super_admin: t('profile.roles.super_admin'),
    admin: t('profile.roles.admin'),
    user: t('profile.roles.user'),
  }
  return role ? (roleTextMap[role] || role) : '-'
}
const getRoleTagType = (role?: string) => {
  const roleTypeMap: Record<string, '' | 'danger' | 'warning'> = {
    super_admin: 'danger',
    admin: 'warning',
    user: '',
  }
  return role ? (roleTypeMap[role] || '') : ''
}
</script>
