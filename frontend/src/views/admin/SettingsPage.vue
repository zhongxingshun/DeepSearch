<template>
  <div class="settings-page page-container">
    <div class="page-header">
      <h1>系统设置</h1>
    </div>
    
    <el-tabs>
      <el-tab-pane label="基本设置">
        <div class="card" style="max-width: 600px">
          <el-form label-width="120px">
            <el-form-item label="系统名称">
              <el-input v-model="settings.appName" />
            </el-form-item>
            <el-form-item label="最大上传大小">
              <el-input-number v-model="settings.maxUploadSize" :min="1" :max="1024" />
              <span style="margin-left: 8px">MB</span>
            </el-form-item>
            <el-form-item label="备份保留天数">
              <el-input-number v-model="settings.backupRetentionDays" :min="1" :max="90" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary">保存设置</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
      
      <el-tab-pane label="维护操作">
        <div class="card" style="max-width: 600px">
          <el-space direction="vertical" fill>
            <div class="maintenance-item">
              <div>
                <h4>创建备份</h4>
                <p>立即创建数据库和搜索引擎备份</p>
              </div>
              <el-button type="primary" @click="runBackup">执行备份</el-button>
            </div>
            <el-divider />
            <div class="maintenance-item">
              <div>
                <h4>重建索引</h4>
                <p>重新索引所有文档到 Meilisearch</p>
              </div>
              <el-button type="warning" @click="reindexAll">重建索引</el-button>
            </div>
            <el-divider />
            <div class="maintenance-item">
              <div>
                <h4>清理日志</h4>
                <p>清理过期的审计日志和临时文件</p>
              </div>
              <el-button @click="runCleanup">执行清理</el-button>
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

const settings = reactive({
  appName: 'DeepSearch',
  maxUploadSize: 500,
  backupRetentionDays: 7,
})

const runBackup = async () => {
  try {
    await http.post('/admin/maintenance/backup')
    ElMessage.success('备份任务已启动')
  } catch {
    ElMessage.error('备份启动失败')
  }
}

const reindexAll = async () => {
  try {
    await http.post('/admin/maintenance/reindex')
    ElMessage.success('重建索引任务已启动')
  } catch {
    ElMessage.error('任务启动失败')
  }
}

const runCleanup = async () => {
  try {
    await http.post('/admin/maintenance/cleanup')
    ElMessage.success('清理任务已启动')
  } catch {
    ElMessage.error('任务启动失败')
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
