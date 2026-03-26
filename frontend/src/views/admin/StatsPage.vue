<template>
  <div class="stats-page page-container">
    <div class="page-header">
      <h1>{{ t('stats.title') }}</h1>
    </div>
    
    <!-- 概览卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background: #e3f2fd">
          <el-icon :size="32" color="#2196f3"><Folder /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ fileStats.total_files || 0 }}</div>
          <div class="stat-label">{{ t('stats.totalFiles') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #e8f5e9">
          <el-icon :size="32" color="#4caf50"><Upload /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ fileStats.total_size_human || '0 B' }}</div>
          <div class="stat-label">{{ t('stats.storage') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff3e0">
          <el-icon :size="32" color="#ff9800"><User /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ userCount || 0 }}</div>
          <div class="stat-label">{{ t('stats.userCount') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fce4ec">
          <el-icon :size="32" color="#e91e63"><Search /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ searchCount || 0 }}</div>
          <div class="stat-label">{{ t('stats.todaySearches') }}</div>
        </div>
      </div>
    </div>
    
    <!-- 文件类型分布 -->
    <div class="card mt-4">
      <h3>{{ t('stats.fileTypeDistribution') }}</h3>
      <div class="type-grid">
        <div v-for="(count, type) in fileStats.by_type" :key="type" class="type-item">
          <div class="type-bar" :style="{ width: getPercent(count) + '%' }"></div>
          <span class="type-name">{{ type }}</span>
          <span class="type-count">{{ count }}</span>
        </div>
      </div>
    </div>
    
    <!-- 索引状态 -->
    <div class="card mt-4">
      <h3>{{ t('stats.indexStatus') }}</h3>
      <div class="status-grid">
        <div class="status-item" v-for="(count, status) in fileStats.by_status" :key="status">
          <el-tag :type="getStatusType(status as string)" size="large">
            {{ getStatusText(status as string) }}: {{ count }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fileApi } from '@/api/files'
import http from '@/api/http'
import { Folder, Upload, User, Search } from '@element-plus/icons-vue'
import { useI18n } from '@/i18n'

const fileStats = ref<any>({})
const userCount = ref(0)
const searchCount = ref(0)
const { t } = useI18n()

const loadStats = async () => {
  try {
    const response = await fileApi.getStats()
    fileStats.value = response.data || {}
  } catch {}
  
  try {
    const response = await http.get('/admin/stats')
    userCount.value = (response as any).user_count || 0
    searchCount.value = (response as any).today_search_count || 0
  } catch {}
}

const getPercent = (count: number) => {
  const total = fileStats.value.total_files || 1
  return Math.min((count / total) * 100, 100)
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'warning', processing: '', completed: 'success', failed: 'danger',
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: t('stats.pending'),
    processing: t('stats.processing'),
    completed: t('stats.completed'),
    failed: t('stats.failed'),
  }
  return texts[status] || status
}

onMounted(() => loadStats())
</script>

<style lang="scss" scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  background: #fff;
  padding: 24px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: var(--ds-shadow-base);
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-content {
  .stat-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--ds-text-primary);
  }
  .stat-label {
    color: var(--ds-text-secondary);
    margin-top: 4px;
  }
}

.type-grid {
  margin-top: 16px;
}

.type-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  position: relative;
  
  .type-bar {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: var(--ds-primary);
    opacity: 0.1;
    border-radius: 4px;
  }
  
  .type-name {
    flex: 1;
    z-index: 1;
    padding-left: 8px;
  }
  
  .type-count {
    z-index: 1;
    font-weight: 500;
    padding-right: 8px;
  }
}

.status-grid {
  display: flex;
  gap: 16px;
  margin-top: 16px;
}
</style>
