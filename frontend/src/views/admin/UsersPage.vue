<template>
  <div class="users-page page-container">
    <div class="page-header">
      <h1>{{ t('users.title') }}</h1>
      <el-button type="primary" @click="showDialog = true">{{ t('users.addUser') }}</el-button>
    </div>
    
    <div class="card" v-loading="loading">
      <el-table :data="users" stripe>
        <el-table-column type="index" width="60" />
        <el-table-column :label="t('users.username')" prop="username" min-width="120" />
        <el-table-column :label="t('users.email')" prop="email" min-width="180" />
        <el-table-column :label="t('users.role')" width="100">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)">
              {{ getRoleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('users.status')" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? t('users.active') : t('users.inactive') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('users.createdAt')" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('users.actions')" width="180">
          <template #default="{ row }">
            <el-button
              size="small"
              link
              :disabled="cannotToggleStatus(row)"
              @click="toggleStatus(row)"
            >
              {{ row.is_active ? t('users.disable') : t('users.enable') }}
            </el-button>
            <el-button
              v-if="isSuperAdmin"
              size="small"
              link
              :disabled="isCurrentUser(row)"
              @click="openRoleDialog(row)"
            >
              {{ t('users.setRole') }}
            </el-button>
            <el-button size="small" link @click="resetPassword(row)">{{ t('users.resetPassword') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
    
    <!-- 添加用户对话框 -->
    <el-dialog v-model="showDialog" :title="t('users.addDialog')" width="450px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item :label="t('users.username')" prop="username">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item :label="t('users.email')" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item :label="t('users.password')" prop="password">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item :label="t('users.role')" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio value="internal_employee">{{ t('users.internalEmployee') }}</el-radio>
            <el-radio value="external_customer">{{ t('users.externalCustomer') }}</el-radio>
            <el-radio v-if="isSuperAdmin" value="admin">{{ t('users.admin') }}</el-radio>
            <el-radio v-if="isSuperAdmin" value="super_admin">{{ t('users.superAdmin') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleSubmit">{{ t('common.ok') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRoleDialog" :title="t('users.roleDialog')" width="420px">
      <el-form label-width="90px">
        <el-form-item :label="t('users.username')">
          <span>{{ selectedUser?.username }}</span>
        </el-form-item>
        <el-form-item :label="t('users.role')">
          <el-radio-group v-model="roleForm.role">
            <el-radio value="internal_employee">{{ t('users.internalEmployee') }}</el-radio>
            <el-radio value="external_customer">{{ t('users.externalCustomer') }}</el-radio>
            <el-radio v-if="isSuperAdmin" value="admin">{{ t('users.admin') }}</el-radio>
            <el-radio v-if="isSuperAdmin" value="super_admin">{{ t('users.superAdmin') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRoleDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleRoleSubmit">{{ t('common.ok') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showPasswordDialog" :title="t('users.passwordResetDialog')" width="460px">
      <div class="reset-password-result">
        <div class="reset-row">
          <span class="reset-label">{{ t('users.username') }}</span>
          <span class="reset-value">{{ resetPasswordResult.username }}</span>
        </div>
        <div class="reset-row">
          <span class="reset-label">{{ t('users.newPassword') }}</span>
          <code class="password-code">{{ resetPasswordResult.password }}</code>
        </div>
      </div>
      <template #footer>
        <el-button @click="showPasswordDialog = false">{{ t('common.close') }}</el-button>
        <el-button type="primary" @click="copyResetPassword">{{ t('users.copyPassword') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import dayjs from 'dayjs'
import type { User } from '@/types'
import { useI18n } from '@/i18n'

const loading = ref(false)
const showDialog = ref(false)
const showRoleDialog = ref(false)
const showPasswordDialog = ref(false)
const formRef = ref<FormInstance>()
const users = ref<User[]>([])
const authStore = useAuthStore()
const selectedUser = ref<User | null>(null)
const isSuperAdmin = authStore.isSuperAdmin
const { t } = useI18n()

const form = reactive({
  username: '',
  email: '',
  password: '',
  role: 'internal_employee',
})

const roleForm = reactive({
  role: 'internal_employee',
})

const resetPasswordResult = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: t('users.usernameRequired'), trigger: 'blur' }],
  email: [
    { required: true, message: t('users.emailRequired'), trigger: 'blur' },
    { type: 'email', message: t('users.emailInvalid'), trigger: 'blur' },
  ],
  password: [
    { required: true, message: t('users.passwordRequired'), trigger: 'blur' },
    { min: 8, message: t('users.passwordMin'), trigger: 'blur' },
  ],
}

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await http.get('/admin/users') as any
    users.value = response.data || []
  } catch {
    ElMessage.error(t('users.loadFailed'))
  } finally {
    loading.value = false
  }
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  
  try {
    await http.post('/admin/users', form)
    ElMessage.success(t('users.addSuccess'))
    showDialog.value = false
    form.username = ''
    form.email = ''
    form.password = ''
    form.role = 'internal_employee'
    loadUsers()
  } catch {
    ElMessage.error(t('users.addFailed'))
  }
}

const toggleStatus = async (user: any) => {
  if (cannotToggleStatus(user)) {
    ElMessage.warning(isCurrentUser(user) ? t('users.cannotDisableSelf') : t('users.cannotManageAdmin'))
    return
  }

  try {
    await http.put(`/admin/users/${user.id}/status`, { is_active: !user.is_active })
    ElMessage.success(t('users.operationSuccess'))
    loadUsers()
  } catch {
    ElMessage.error(t('users.operationFailed'))
  }
}

const resetPassword = async (user: any) => {
  if (!canManageUser(user)) {
    ElMessage.warning(t('users.cannotManageAdmin'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('users.confirmResetPassword', { username: user.username }),
      t('users.resetPassword'),
      { type: 'warning' },
    )
    const response = await http.post(`/admin/users/${user.id}/reset-password`) as any
    const newPassword = response.new_password || response.data?.new_password || 'deepsearch123'
    resetPasswordResult.username = user.username
    resetPasswordResult.password = newPassword
    showPasswordDialog.value = true
    ElMessage.success(t('users.passwordReset'))
    loadUsers()
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(t('users.resetFailed'))
  }
}

const copyText = async (text: string): Promise<void> => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.style.position = 'fixed'
  textArea.style.opacity = '0'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  document.execCommand('copy')
  document.body.removeChild(textArea)
}

const copyResetPassword = async () => {
  try {
    await copyText(resetPasswordResult.password)
    ElMessage.success(t('users.passwordCopied'))
  } catch {
    ElMessage.error(t('users.passwordCopyFailed'))
  }
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm')
const isCurrentUser = (user: User) => user.id === authStore.user?.id
const isEndUserRole = (role?: string) => ['internal_employee', 'external_customer', 'user'].includes(role || '')
const canManageUser = (user: User) => isSuperAdmin.value || isEndUserRole(user.role)
const cannotToggleStatus = (user: User) => isCurrentUser(user) || !canManageUser(user)
const getRoleText = (role: User['role']) => ({
  super_admin: t('users.superAdmin'),
  admin: t('users.admin'),
  internal_employee: t('users.internalEmployee'),
  external_customer: t('users.externalCustomer'),
  user: t('users.internalEmployee'),
}[role] || role)
const getRoleTagType = (role: User['role']) => ({
  super_admin: 'danger',
  admin: 'warning',
  internal_employee: '',
  external_customer: 'info',
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
    ElMessage.success(t('users.roleUpdated'))
    showRoleDialog.value = false
    selectedUser.value = null
    loadUsers()
  } catch {
    ElMessage.error(t('users.roleUpdateFailed'))
  }
}

onMounted(() => loadUsers())
</script>

<style scoped>
.reset-password-result {
  display: grid;
  gap: 14px;
}

.reset-row {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.reset-label {
  color: var(--el-text-color-secondary);
}

.reset-value {
  min-width: 0;
  overflow-wrap: anywhere;
}

.password-code {
  min-width: 0;
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 14px;
  overflow-wrap: anywhere;
}
</style>
