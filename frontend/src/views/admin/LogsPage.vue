<template>
  <div class="logs-page page-container">
    <div class="page-header">
      <h1>{{ t('logs.title') }}</h1>
    </div>
    
    <div class="filter-bar card">
      <el-select v-model="filters.action" :placeholder="t('logs.actionType')" clearable @change="loadLogs">
        <el-option :label="t('logs.login')" value="login" />
        <el-option :label="t('logs.logout')" value="logout" />
        <el-option :label="t('logs.search')" value="search" />
        <el-option :label="t('logs.download')" value="file_download" />
        <el-option :label="t('logs.upload')" value="file_upload" />
      </el-select>
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        :range-separator="t('logs.dateRangeSeparator')"
        :start-placeholder="t('logs.dateFrom')"
        :end-placeholder="t('logs.dateTo')"
        @change="loadLogs"
      />
      <el-button @click="loadLogs">{{ t('logs.query') }}</el-button>
    </div>
    
    <div class="card" v-loading="loading">
      <el-table :data="logs" stripe>
        <el-table-column type="index" width="60" />
        <el-table-column :label="t('logs.user')" prop="user_id" width="100" />
        <el-table-column :label="t('logs.action')" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getActionText(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('logs.resource')" prop="resource_type" width="100" />
        <el-table-column :label="t('logs.details')" min-width="200">
          <template #default="{ row }">
            {{ JSON.stringify(row.details) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('logs.ip')" prop="ip_address" width="130" />
        <el-table-column :label="t('logs.time')" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadLogs"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import http from '@/api/http'
import dayjs from 'dayjs'
import { useI18n } from '@/i18n'

const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const logs = ref<any[]>([])

const filters = reactive({
  action: '',
  dateRange: null as [Date, Date] | null,
})
const { t } = useI18n()

const loadLogs = async () => {
  loading.value = true
  try {
    const response = await http.get('/admin/logs', {
      params: { page: page.value, page_size: pageSize.value, action: filters.action },
    })
    logs.value = (response as any).data || []
    total.value = (response as any).total || 0
  } finally {
    loading.value = false
  }
}

const getActionText = (action: string) => {
  const texts: Record<string, string> = {
    login: t('logs.login'),
    logout: t('logs.logout'),
    search: t('logs.search'),
    file_download: t('logs.download'),
    file_upload: t('logs.upload'),
  }
  return texts[action] || action
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss')

onMounted(() => loadLogs())
</script>

<style scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; }
.pagination { margin-top: 16px; display: flex; justify-content: center; }
</style>
