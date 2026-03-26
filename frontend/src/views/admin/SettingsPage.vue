<template>
  <div class="settings-page page-container">
    <div class="page-header">
      <h1>{{ t('settings.title') }}</h1>
    </div>
    
    <el-tabs>
      <el-tab-pane :label="t('settings.basic')">
        <div class="card" style="max-width: 600px">
          <el-form label-width="120px">
            <el-form-item :label="t('settings.systemName')">
              <el-input v-model="settings.appName" />
            </el-form-item>
            <el-form-item :label="t('settings.maxUploadSize')">
              <el-input-number v-model="settings.maxUploadSize" :min="1" :max="1024" />
              <span style="margin-left: 8px">MB</span>
            </el-form-item>
            <el-form-item :label="t('settings.backupRetentionDays')">
              <el-input-number v-model="settings.backupRetentionDays" :min="1" :max="90" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary">{{ t('settings.saveSettings') }}</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
      
      <el-tab-pane :label="t('settings.maintenance')">
        <div class="card" style="max-width: 600px">
          <el-space direction="vertical" fill>
            <div class="maintenance-item">
              <div>
                <h4>{{ t('settings.createBackup') }}</h4>
                <p>{{ t('settings.createBackupDesc') }}</p>
              </div>
              <el-button type="primary" @click="runBackup">{{ t('settings.runBackup') }}</el-button>
            </div>
            <el-divider />
            <div class="maintenance-item">
              <div>
                <h4>{{ t('settings.rebuildIndex') }}</h4>
                <p>{{ t('settings.rebuildIndexDesc') }}</p>
              </div>
              <el-button type="warning" @click="reindexAll">{{ t('settings.runRebuildIndex') }}</el-button>
            </div>
            <el-divider />
            <div class="maintenance-item">
              <div>
                <h4>{{ t('settings.cleanupLogs') }}</h4>
                <p>{{ t('settings.cleanupLogsDesc') }}</p>
              </div>
              <el-button @click="runCleanup">{{ t('settings.runCleanup') }}</el-button>
            </div>
          </el-space>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import http from '@/api/http'
import { ElMessage } from 'element-plus'
import { useI18n } from '@/i18n'

const settings = reactive({
  appName: 'DeepSearch',
  maxUploadSize: 500,
  backupRetentionDays: 7,
})
const { t } = useI18n()

const runBackup = async () => {
  try {
    await http.post('/admin/maintenance/backup')
    ElMessage.success(t('settings.backupStarted'))
  } catch {
    ElMessage.error(t('settings.backupFailed'))
  }
}

const reindexAll = async () => {
  try {
    await http.post('/admin/maintenance/reindex')
    ElMessage.success(t('settings.reindexStarted'))
  } catch {
    ElMessage.error(t('settings.taskStartFailed'))
  }
}

const runCleanup = async () => {
  try {
    await http.post('/admin/maintenance/cleanup')
    ElMessage.success(t('settings.cleanupStarted'))
  } catch {
    ElMessage.error(t('settings.taskStartFailed'))
  }
}
</script>

<style scoped>
.maintenance-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.maintenance-item h4 { margin: 0 0 4px; }
.maintenance-item p { margin: 0; color: var(--ds-text-secondary); font-size: 13px; }
</style>
