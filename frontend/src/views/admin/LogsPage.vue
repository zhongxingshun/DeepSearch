<template>
  <div class="logs-page page-container">
    <div class="page-header">
      <h1>审计日志</h1>
    </div>
    
    <div class="filter-bar card">
      <el-select v-model="filters.action" placeholder="操作类型" clearable @change="loadLogs">
        <el-option label="登录" value="login" />
        <el-option label="登出" value="logout" />
        <el-option label="搜索" value="search" />
        <el-option label="下载" value="file_download" />
        <el-option label="上传" value="file_upload" />
      </el-select>
      <el-date-picker
        v-model="filters.dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="loadLogs"
      />
      <el-button @click="loadLogs">查询</el-button>
    </div>
    
    <div class="card" v-loading="loading">
      <el-table :data="logs" stripe>
        <el-table-column type="index" width="60" />
        <el-table-column label="用户" prop="user_id" width="100" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ getActionText(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="资源" prop="resource_type" width="100" />
        <el-table-column label="详情" min-width="200">
          <template #default="{ row }">
            {{ JSON.stringify(row.details) }}
          </template>
        </el-table-column>
        <el-table-column label="IP" prop="ip_address" width="130" />
        <el-table-column label="时间" width="160">
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

const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const logs = ref<any[]>([])

const filters = reactive({
  action: '',
  dateRange: null as [Date, Date] | null,
})

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
    login: '登录', logout: '登出', search: '搜索',
    file_download: '下载', file_upload: '上传',
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
