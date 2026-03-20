<template>
  <div class="users-page page-container">
    <div class="page-header">
      <h1>用户管理</h1>
      <el-button type="primary" @click="showDialog = true">添加用户</el-button>
    </div>
    
    <div class="card" v-loading="loading">
      <el-table :data="users" stripe>
        <el-table-column type="index" width="60" />
        <el-table-column label="用户名" prop="username" min-width="120" />
        <el-table-column label="邮箱" prop="email" min-width="180" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">
              {{ getRoleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button
              size="small"
              link
              :disabled="cannotToggleStatus(row)"
              @click="toggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button
              v-if="isSuperAdmin"
              size="small"
              link
              :disabled="isCurrentUser(row)"
              @click="openRoleDialog(row)"
            >
              设置角色
            </el-button>
            <el-button size="small" link @click="resetPassword(row)">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 添加用户对话框 -->
    <el-dialog v-model="showDialog" title="添加用户" width="450px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio value="user">普通用户</el-radio>
            <el-radio v-if="isSuperAdmin" value="admin">管理员</el-radio>
            <el-radio v-if="isSuperAdmin" value="super_admin">超级管理员</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRoleDialog" title="设置角色" width="420px">
      <el-form label-width="90px">
        <el-form-item label="用户名">
          <span>{{ selectedUser?.username }}</span>
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="roleForm.role">
            <el-radio value="user">普通用户</el-radio>
            <el-radio value="admin">管理员</el-radio>
            <el-radio value="super_admin">超级管理员</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRoleDialog = false">取消</el-button>
        <el-button type="primary" @click="handleRoleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import dayjs from 'dayjs'
import type { User } from '@/types'

const loading = ref(false)
const showDialog = ref(false)
const showRoleDialog = ref(false)
const formRef = ref<FormInstance>()
const users = ref<User[]>([])
const authStore = useAuthStore()
const selectedUser = ref<User | null>(null)
const isSuperAdmin = authStore.isSuperAdmin

const form = reactive({
  username: '',
  email: '',
  password: '',
  role: 'user',
})

const roleForm = reactive({
  role: 'user',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度不能少于8位', trigger: 'blur' },
  ],
}

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await http.get('/admin/users') as any
    users.value = response.data || []
  } catch {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  
  try {
    await http.post('/admin/users', form)
    ElMessage.success('添加成功')
    showDialog.value = false
    form.username = ''
    form.email = ''
    form.password = ''
    form.role = 'user'
    loadUsers()
  } catch {
    ElMessage.error('添加失败')
  }
}

const toggleStatus = async (user: any) => {
  if (cannotToggleStatus(user)) {
    ElMessage.warning(isCurrentUser(user) ? '不能禁用当前登录账号' : '没有权限管理管理员账号')
    return
  }

  try {
    await http.put(`/admin/users/${user.id}/status`, { is_active: !user.is_active })
    ElMessage.success('操作成功')
    loadUsers()
  } catch {
    ElMessage.error('操作失败')
  }
}

const resetPassword = async (user: any) => {
  if (!canManageUser(user)) {
    ElMessage.warning('没有权限管理管理员账号')
    return
  }

  try {
    await http.post(`/admin/users/${user.id}/reset-password`)
    ElMessage.success('密码已重置')
  } catch {
    ElMessage.error('重置失败')
  }
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm')
const isCurrentUser = (user: User) => user.id === authStore.user?.id
const canManageUser = (user: User) => isSuperAdmin.value || user.role === 'user'
const cannotToggleStatus = (user: User) => isCurrentUser(user) || !canManageUser(user)
const getRoleText = (role: User['role']) => ({
  super_admin: '超级管理员',
  admin: '管理员',
  user: '普通用户',
}[role] || role)
const getRoleTagType = (role: User['role']) => ({
  super_admin: 'danger',
  admin: 'warning',
  user: '',
}[role] || '')

const openRoleDialog = (user: User) => {
  selectedUser.value = user
  roleForm.role = user.role
  showRoleDialog.value = true
}

const handleRoleSubmit = async () => {
  if (!selectedUser.value) return

  try {
    await http.put(`/admin/users/${selectedUser.value.id}/role`, { role: roleForm.role })
    ElMessage.success('角色更新成功')
    showRoleDialog.value = false
    selectedUser.value = null
    loadUsers()
  } catch {
    ElMessage.error('角色更新失败')
  }
}

onMounted(() => loadUsers())
</script>
