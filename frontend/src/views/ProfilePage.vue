<template>
  <div class="profile-page page-container">
    <div class="page-header">
      <h1>个人中心</h1>
    </div>
    
    <el-tabs v-model="activeTab">
      <el-tab-pane label="基本信息" name="info">
        <div class="card">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="用户名">{{ user?.username }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ user?.email }}</el-descriptions-item>
            <el-descriptions-item label="角色">
              <el-tag :type="user?.role === 'admin' ? 'danger' : ''">
                {{ user?.role === 'admin' ? '管理员' : '普通用户' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="user?.is_active ? 'success' : 'info'">
                {{ user?.is_active ? '正常' : '已禁用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="注册时间">{{ formatDate(user?.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="修改密码" name="password">
        <div class="card" style="max-width: 500px">
          <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
            <el-form-item label="当前密码" prop="currentPassword">
              <el-input v-model="form.currentPassword" type="password" show-password />
            </el-form-item>
            <el-form-item label="新密码" prop="newPassword">
              <el-input v-model="form.newPassword" type="password" show-password />
            </el-form-item>
            <el-form-item label="确认密码" prop="confirmPassword">
              <el-input v-model="form.confirmPassword" type="password" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loading" @click="handleSubmit">
                修改密码
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

const route = useRoute()
const authStore = useAuthStore()

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
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  currentPassword: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度不能少于8位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validatePass, trigger: 'blur' },
  ],
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  try {
    await authStore.changePassword(form.currentPassword, form.newPassword)
    ElMessage.success('密码修改成功')
    form.currentPassword = ''
    form.newPassword = ''
    form.confirmPassword = ''
  } catch {
    ElMessage.error('密码修改失败')
  } finally {
    loading.value = false
  }
}

const formatDate = (date?: string) => date ? dayjs(date).format('YYYY-MM-DD HH:mm') : '-'
</script>
