<template>
  <div class="history-page page-container">
    <div class="page-header">
      <h1>{{ t('history.title') }}</h1>
      <el-button type="danger" plain @click="clearAll" :disabled="!histories.length">
        {{ t('history.clearAll') }}
      </el-button>
    </div>
    
    <div class="card" v-loading="loading">
      <el-table :data="histories" stripe>
        <el-table-column type="index" width="60" />
        <el-table-column :label="t('history.keyword')" prop="keyword" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="searchKeyword(row.keyword)">
              {{ row.keyword }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column :label="t('history.resultCount')" prop="result_count" width="100" />
        <el-table-column :label="t('history.searchedAt')" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('history.actions')" width="100">
          <template #default="{ row }">
            <el-button size="small" link type="danger" @click="deleteHistory(row.id)">
              {{ t('common.delete') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-empty v-if="!loading && !histories.length" :description="t('history.empty')" />
      
      <div class="pagination" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="loadHistory"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { searchApi } from '@/api/search'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import type { SearchHistoryItem } from '@/types'
import { useI18n } from '@/i18n'

const router = useRouter()
const { t } = useI18n()
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const histories = ref<SearchHistoryItem[]>([])

const loadHistory = async () => {
  loading.value = true
  try {
    const response = await searchApi.getHistory({ page: page.value, page_size: pageSize.value })
    histories.value = response.data
    total.value = response.total
  } catch {
    ElMessage.error(t('history.loadFailed'))
  } finally {
    loading.value = false
  }
}

const searchKeyword = (keyword: string) => {
  router.push({ name: 'search', query: { q: keyword } })
}

const deleteHistory = async (id: number) => {
  await searchApi.deleteHistory(id)
  ElMessage.success(t('history.deleted'))
  loadHistory()
}

const clearAll = async () => {
  await ElMessageBox.confirm(t('history.confirmClear'), t('history.title'), { type: 'warning' })
  await searchApi.clearHistory()
  ElMessage.success(t('history.cleared'))
  loadHistory()
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm')

onMounted(() => loadHistory())
</script>

<style scoped>
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
</style>
