<template>
  <div class="history-page page-container">
    <div class="page-header">
      <h1>搜索历史</h1>
      <el-button type="danger" plain @click="clearAll" :disabled="!histories.length">
        清空全部
      </el-button>
    </div>
    
    <div class="card" v-loading="loading">
      <el-table :data="histories" stripe>
        <el-table-column type="index" width="60" />
        <el-table-column label="关键词" prop="keyword" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="searchKeyword(row.keyword)">
              {{ row.keyword }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column label="结果数" prop="result_count" width="100" />
        <el-table-column label="搜索时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" link type="danger" @click="deleteHistory(row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-empty v-if="!loading && !histories.length" description="暂无搜索历史" />
      
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

const router = useRouter()
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
    ElMessage.error('加载搜索历史失败')
  } finally {
    loading.value = false
  }
}

const searchKeyword = (keyword: string) => {
  router.push({ name: 'search', query: { q: keyword } })
}

const deleteHistory = async (id: number) => {
  await searchApi.deleteHistory(id)
  ElMessage.success('删除成功')
  loadHistory()
}

const clearAll = async () => {
  await ElMessageBox.confirm('确定要清空所有搜索历史吗？', '提示', { type: 'warning' })
  await searchApi.clearHistory()
  ElMessage.success('已清空')
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
