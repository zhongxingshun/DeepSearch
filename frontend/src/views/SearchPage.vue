<template>
  <div class="search-page">
    <!-- 搜索区域 -->
    <div class="search-area">
      <div class="search-box">
        <el-input
          v-model="keyword"
          size="large"
          placeholder="输入关键词搜索文档内容..."
          class="search-input"
          clearable
          @keyup.enter="handleSearch"
          @input="handleInputChange"
        >
          <template #prefix>
            <el-icon :size="20"><Search /></el-icon>
          </template>
          <template #append>
            <el-button type="primary" :loading="loading" @click="handleSearch">
              搜索
            </el-button>
          </template>
        </el-input>
        
        <!-- 搜索建议 -->
        <div v-if="showSuggestions && suggestions.length" class="suggestions">
          <div
            v-for="(item, index) in suggestions"
            :key="index"
            class="suggestion-item"
            @click="selectSuggestion(item)"
          >
            <el-icon :size="14"><Clock /></el-icon>
            <span>{{ item.keyword }}</span>
            <el-tag size="small" v-if="item.type === 'popular'">热门</el-tag>
          </div>
        </div>
      </div>
      
      <!-- 筛选条件 -->
      <div class="filters">
        <el-select v-model="filters.file_type" placeholder="文件类型" clearable size="small">
          <el-option label="PDF" value="pdf" />
          <el-option label="Word" value="word" />
          <el-option label="Excel" value="excel" />
          <el-option label="PowerPoint" value="powerpoint" />
          <el-option label="图片" value="image" />
          <el-option label="文本" value="text" />
          <el-option label="压缩包" value="archive" />
        </el-select>
        
        <el-select v-model="filters.sort_by" placeholder="排序方式" clearable size="small">
          <el-option label="相关性" value="" />
          <el-option label="时间最新" value="created_at" />
          <el-option label="文件最大" value="file_size" />
        </el-select>
      </div>
    </div>
    
    <!-- 搜索结果 -->
    <div class="results-area" v-loading="loading">
      <template v-if="hasSearched">
        <!-- 结果统计 -->
        <div class="results-header">
          <span class="results-count">
            找到 <strong>{{ total }}</strong> 个结果
          </span>
          <span class="results-time">
            耗时 {{ queryTime }} ms
          </span>
        </div>
        
        <!-- 结果列表 -->
        <div class="results-list" v-if="results.length">
          <div
            v-for="result in results"
            :key="result.id"
            class="result-item card"
          >
            <div class="result-header">
              <div class="file-info" :class="{ clickable: supportsPreview(result.file_type) }" @click="openPreview(result)">
                <div :class="['file-type-icon-sm', `ft-${result.file_type}`]">
                  <el-icon :size="22">
                    <component :is="getFileIcon(result.file_type)" />
                  </el-icon>
                </div>
                <div class="file-meta">
                  <h3 class="filename" v-html="highlightKeyword(getDisplayName(result.filename))"></h3>
                  <div class="meta-row">
                    <span class="file-type-label">{{ getFileTypeLabel(result.file_type) }}</span>
                    <span class="file-size">{{ formatSize(result.file_size) }}</span>
                    <span class="file-date">{{ formatDate(result.created_at) }}</span>
                  </div>
                </div>
              </div>
              <div class="result-actions">
                <el-button v-if="supportsPreview(result.file_type)" size="small" type="primary" link @click="openPreview(result)">
                  <el-icon><View /></el-icon>
                  预览
                </el-button>
                <el-button size="small" type="primary" link @click.stop="downloadFile(result)">
                  <el-icon><Download /></el-icon>
                  下载
                </el-button>
              </div>
            </div>

            <!-- 搜索结果内容片段 -->
            <div class="result-content" v-html="result.content_snippet"></div>

            <!-- 图片类型：内联缩略图 -->
            <div v-if="result.file_type === 'image'" class="result-thumbnail" @click="openPreview(result)">
              <img :src="getPreviewUrl(result.file_id)" :alt="result.filename" loading="lazy" />
            </div>
          </div>
        </div>
        
        <!-- 无结果 -->
        <el-empty v-else description="没有找到匹配的文档" />
        
        <!-- 分页 -->
        <div class="pagination" v-if="total > pageSize">
          <el-pagination
            v-model:current-page="page"
            :page-size="pageSize"
            :total="total"
            layout="prev, pager, next"
            @current-change="handlePageChange"
          />
        </div>
      </template>
      
      <!-- 未搜索时显示热门关键词 -->
      <div v-else class="welcome-area">
        <div class="welcome-icon">
          <el-icon :size="80" color="#409eff"><Search /></el-icon>
        </div>
        <h2>开始搜索</h2>
        <p>输入关键词，在所有文档中深度搜索内容</p>
        
        <div class="hot-keywords" v-if="hotKeywords.length">
          <h4>热门搜索</h4>
          <div class="keyword-tags">
            <el-tag
              v-for="kw in hotKeywords"
              :key="kw.keyword"
              class="keyword-tag"
              effect="plain"
              @click="selectHotKeyword(kw.keyword)"
            >
              {{ kw.keyword }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 预览抽屉 -->
    <el-drawer
      v-model="showPreview"
      :title="previewFile?.filename || '文件预览'"
      size="55%"
      direction="rtl"
      :close-on-click-modal="true"
    >
      <div class="preview-container" v-if="previewFile">
        <!-- 文件信息头 -->
        <div class="preview-file-info">
          <div :class="['file-type-icon-lg', `ft-${previewFile.file_type}`]">
            <el-icon :size="28">
              <component :is="getFileIcon(previewFile.file_type)" />
            </el-icon>
          </div>
          <div class="preview-meta">
            <h3>{{ getDisplayName(previewFile.filename) }}</h3>
            <div class="preview-meta-row">
              <span>{{ getFileTypeLabel(previewFile.file_type) }}</span>
              <span>{{ formatSize(previewFile.file_size) }}</span>
              <span>{{ formatDate(previewFile.created_at) }}</span>
            </div>
          </div>
          <el-button type="primary" @click="downloadFile(previewFile)">
            <el-icon><Download /></el-icon>
            下载文件
          </el-button>
        </div>

        <!-- 预览内容区域 -->
        <div class="preview-content">
          <!-- 图片预览 -->
          <div v-if="previewFile.file_type === 'image'" class="preview-image">
            <img
              :src="getPreviewUrl(previewFile.file_id)"
              :alt="previewFile.filename"
              @error="previewError = true"
            />
            <div v-if="previewError" class="preview-error">
              <el-icon :size="48" color="#c0c4cc"><Picture /></el-icon>
              <p>图片加载失败</p>
            </div>
          </div>

          <!-- PDF 预览 -->
          <div v-else-if="previewFile.file_type === 'pdf'" class="preview-pdf">
            <iframe
              :src="getPreviewUrl(previewFile.file_id)"
              frameborder="0"
            ></iframe>
          </div>

          <!-- 其他文件：显示文本摘要 -->
          <div v-else class="preview-text">
            <div class="preview-text-label">
              <el-icon><Document /></el-icon>
              搜索匹配内容
            </div>
            <div class="preview-text-content" v-html="previewFile.content_snippet"></div>
            <div class="preview-no-visual">
              <el-icon :size="40" color="#dcdfe6"><Document /></el-icon>
              <p>该文件类型暂不支持可视化预览</p>
              <el-button type="primary" plain @click="downloadFile(previewFile)">
                下载后查看完整内容
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { searchApi } from '@/api/search'
import { fileApi } from '@/api/files'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import type { SearchResult } from '@/types'
import {
  Search, Clock, Download, Document, Picture, Tickets, View, Folder,
} from '@element-plus/icons-vue'

const keyword = ref('')
const loading = ref(false)
const hasSearched = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const queryTime = ref(0)
const results = ref<SearchResult[]>([])
const suggestions = ref<any[]>([])
const showSuggestions = ref(false)
const hotKeywords = ref<any[]>([])

// 预览状态
const showPreview = ref(false)
const previewFile = ref<SearchResult | null>(null)
const previewError = ref(false)

const filters = reactive({
  file_type: '',
  sort_by: '',
})

// 搜索
const handleSearch = async () => {
  if (!keyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  loading.value = true
  hasSearched.value = true
  showSuggestions.value = false
  
  try {
    const response = await searchApi.search({
      q: keyword.value,
      page: page.value,
      page_size: pageSize.value,
      file_type: filters.file_type || undefined,
      sort_by: filters.sort_by || undefined,
    })
    
    results.value = response.results
    total.value = response.total
    queryTime.value = response.query_time_ms
  } catch (error) {
    ElMessage.error('搜索失败')
  } finally {
    loading.value = false
  }
}

// 输入变化
const handleInputChange = async () => {
  if (keyword.value.length >= 2) {
    try {
      const response = await searchApi.suggest(keyword.value)
      suggestions.value = response.suggestions || []
      showSuggestions.value = true
    } catch {
      suggestions.value = []
    }
  } else {
    showSuggestions.value = false
  }
}

// 选择建议
const selectSuggestion = (item: any) => {
  keyword.value = item.keyword
  showSuggestions.value = false
  handleSearch()
}

// 选择热门关键词
const selectHotKeyword = (kw: string) => {
  keyword.value = kw
  handleSearch()
}

// 翻页
const handlePageChange = () => {
  handleSearch()
}

// 打开预览
const openPreview = (result: SearchResult) => {
  if (!supportsPreview(result.file_type)) return
  previewFile.value = result
  previewError.value = false
  showPreview.value = true
}

// 获取预览 URL
const getPreviewUrl = (fileId: number): string => {
  return fileApi.getPreviewUrl(fileId)
}

// 下载文件
const downloadFile = (result: SearchResult) => {
  const url = fileApi.getDownloadUrl(result.file_id)
  window.open(url, '_blank')
}

// 获取纯文件名
const getDisplayName = (filename: string): string => {
  if (filename.includes('/')) {
    return filename.split('/').pop() || filename
  }
  return filename
}

// 高亮关键词
const highlightKeyword = (text: string): string => {
  if (!keyword.value) return text
  const escaped = keyword.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

// 获取文件图标
const getFileIcon = (type: string) => {
  const icons: Record<string, any> = {
    pdf: Document,
    word: Document,
    excel: Tickets,
    powerpoint: Document,
    image: Picture,
    archive: Folder,
  }
  return icons[type] || Document
}

const getFileTypeLabel = (type: string): string => {
  const labels: Record<string, string> = {
    image: '图片',
    pdf: 'PDF',
    word: 'Word',
    excel: 'Excel',
    powerpoint: 'PPT',
    text: '文本',
    archive: '压缩包',
  }
  return labels[type] || type
}

const supportsPreview = (type: string) => ['image', 'pdf'].includes(type)

// 格式化大小
const formatSize = (bytes: number): string => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

// 格式化日期
const formatDate = (date: string | null): string => {
  if (!date) return '-'
  return dayjs(date).format('YYYY-MM-DD')
}

// 加载热门关键词
onMounted(async () => {
  try {
    const response = await searchApi.getPopularKeywords(8)
    hotKeywords.value = response.data || []
  } catch {
    // 忽略错误
  }
})
</script>

<style lang="scss" scoped>
.search-page {
  padding: var(--ds-spacing-lg);
}

.search-area {
  max-width: 800px;
  margin: 0 auto 32px;
}

.search-box {
  position: relative;
  
  .search-input {
    :deep(.el-input__wrapper) {
      padding: 8px 16px;
      border-radius: 8px;
    }
    
    :deep(.el-input-group__append) {
      padding: 0;
      
      .el-button {
        height: 100%;
        padding: 0 24px;
        border-radius: 0 8px 8px 0;
      }
    }
  }
}

.suggestions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border-radius: 8px;
  box-shadow: var(--ds-shadow-light);
  margin-top: 4px;
  z-index: 100;
  overflow: hidden;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  cursor: pointer;
  
  &:hover {
    background: var(--ds-bg-base);
  }
}

.filters {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  
  .results-count {
    color: var(--ds-text-primary);
    
    strong {
      color: var(--ds-primary);
    }
  }
  
  .results-time {
    color: var(--ds-text-secondary);
    font-size: 13px;
  }
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-item {
  transition: all 0.2s;
  
  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  }
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.file-info {
  display: flex;
  gap: 12px;
  cursor: pointer;
  flex: 1;
  min-width: 0;

  &:hover .filename {
    color: #409eff;
  }
}

/* 搜索结果中的文件类型小图标 */
.file-type-icon-sm {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  flex-shrink: 0;

  &.ft-image { background: #f3e8ff; color: #9333ea; }
  &.ft-pdf { background: #fee2e2; color: #dc2626; }
  &.ft-word { background: #dbeafe; color: #2563eb; }
  &.ft-excel { background: #dcfce7; color: #16a34a; }
  &.ft-powerpoint { background: #ffedd5; color: #ea580c; }
  &.ft-text { background: #f3f4f6; color: #6b7280; }
  &.ft-archive { background: #fff7ed; color: #c2410c; }
}

/* 预览面板中的大图标 */
.file-type-icon-lg {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 50px;
  border-radius: 12px;
  flex-shrink: 0;

  &.ft-image { background: #f3e8ff; color: #9333ea; }
  &.ft-pdf { background: #fee2e2; color: #dc2626; }
  &.ft-word { background: #dbeafe; color: #2563eb; }
  &.ft-excel { background: #dcfce7; color: #16a34a; }
  &.ft-powerpoint { background: #ffedd5; color: #ea580c; }
  &.ft-text { background: #f3f4f6; color: #6b7280; }
  &.ft-archive { background: #fff7ed; color: #c2410c; }
}

.file-meta {
  min-width: 0;
  
  .filename {
    font-size: 16px;
    font-weight: 500;
    margin-bottom: 4px;
    transition: color 0.2s;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    
    :deep(mark) {
      background: #ffd54f;
      padding: 0 2px;
      border-radius: 2px;
    }
  }
  
  .meta-row {
    display: flex;
    align-items: center;
    gap: 12px;
    color: var(--ds-text-secondary);
    font-size: 13px;
  }

  .file-type-label {
    padding: 1px 8px;
    background: #f4f4f5;
    border-radius: 4px;
    font-size: 12px;
    color: #909399;
  }
}

.file-info.clickable {
  cursor: pointer;
}

.result-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.result-content {
  color: var(--ds-text-regular);
  font-size: 14px;
  line-height: 1.8;
  
  :deep(mark) {
    background: #ffd54f;
    padding: 0 2px;
    border-radius: 2px;
  }
}

/* 图片缩略图 */
.result-thumbnail {
  margin-top: 12px;
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #ebeef5;
  display: inline-block;
  transition: all 0.25s ease;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }

  img {
    display: block;
    max-width: 100%;
    max-height: 200px;
    object-fit: contain;
    background: #fafafa;
  }
}

.pagination {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

.welcome-area {
  text-align: center;
  padding: 60px 20px;
  
  h2 {
    margin: 24px 0 8px;
    color: var(--ds-text-primary);
  }
  
  p {
    color: var(--ds-text-secondary);
    margin-bottom: 40px;
  }
}

.hot-keywords {
  h4 {
    color: var(--ds-text-secondary);
    font-weight: normal;
    margin-bottom: 16px;
  }
}

.keyword-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.keyword-tag {
  cursor: pointer;
  
  &:hover {
    background: var(--ds-primary);
    color: #fff;
  }
}

/* ========= 预览面板样式 ========= */
.preview-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.preview-file-info {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f8f9ff, #f0f7ff);
  border-radius: 12px;
  margin-bottom: 20px;
  border: 1px solid #e8edf5;

  .preview-meta {
    flex: 1;
    min-width: 0;

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .preview-meta-row {
      display: flex;
      gap: 12px;
      font-size: 13px;
      color: #909399;
    }
  }
}

.preview-content {
  flex: 1;
  overflow: auto;
}

.preview-image {
  text-align: center;
  padding: 16px;
  background: #fafafa;
  border-radius: 10px;
  border: 1px solid #ebeef5;

  img {
    max-width: 100%;
    max-height: 70vh;
    object-fit: contain;
    border-radius: 6px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  }
}

.preview-error {
  padding: 60px 20px;
  text-align: center;
  color: #c0c4cc;

  p {
    margin-top: 12px;
    font-size: 14px;
  }
}

.preview-pdf {
  height: 70vh;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #ebeef5;

  iframe {
    width: 100%;
    height: 100%;
  }
}

.preview-text {
  .preview-text-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 14px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 12px;
  }

  .preview-text-content {
    padding: 16px 20px;
    background: #fafafa;
    border-radius: 8px;
    border: 1px solid #ebeef5;
    font-size: 14px;
    line-height: 1.8;
    color: #606266;
    margin-bottom: 24px;

    :deep(mark) {
      background: #ffd54f;
      padding: 0 2px;
      border-radius: 2px;
    }
  }

  .preview-no-visual {
    text-align: center;
    padding: 40px 20px;
    color: #c0c4cc;

    p {
      margin: 12px 0 16px;
      font-size: 14px;
      color: #909399;
    }
  }
}
</style>
