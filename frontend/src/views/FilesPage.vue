<template>
  <div class="files-page page-container">
    <div class="page-header">
      <h1>{{ t('files.title') }}</h1>
      <div class="header-actions">
        <el-button v-if="isAdmin" type="warning" :icon="FolderAdd" @click="openCreateFolderDialog">
          {{ t('files.newFolder') }}
        </el-button>
        <el-button
          v-if="isAdmin && currentFolder !== '/'"
          type="info"
          plain
          :icon="EditPen"
          @click="openRenameFolderDialog({ path: currentFolder, name: currentFolder.split('/').filter(Boolean).pop() || '' })"
        >
          {{ t('files.renameCurrentFolder') }}
        </el-button>
        <el-button type="primary" :icon="Upload" @click="showUpload = true">
          {{ t('files.uploadFile') }}
        </el-button>
        <el-button type="success" :icon="FolderOpened" @click="triggerFolderUpload">
          {{ t('files.uploadFolder') }}
        </el-button>
        <!-- 隐藏的文件夹选择 input -->
        <input
          ref="folderInputRef"
          type="file"
          webkitdirectory
          directory
          multiple
          style="display: none"
          @change="handleFolderSelected"
        />
      </div>
    </div>
    
    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon" style="background: #e3f2fd">
          <el-icon :size="24" color="#2196f3"><Folder /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_files || 0 }}</div>
          <div class="stat-label">{{ t('files.totalFiles') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #e8f5e9">
          <el-icon :size="24" color="#4caf50"><Upload /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.total_size_human || '0 B' }}</div>
          <div class="stat-label">{{ t('files.totalSize') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fff3e0">
          <el-icon :size="24" color="#ff9800"><Loading /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.by_status?.pending || 0 }}</div>
          <div class="stat-label">{{ t('files.pending') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #fce4ec">
          <el-icon :size="24" color="#f44336"><Warning /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.by_status?.failed || 0 }}</div>
          <div class="stat-label">{{ t('files.processingFailed') }}</div>
        </div>
      </div>
    </div>

    <!-- 面包屑导航 -->
    <div class="breadcrumb-bar card">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item>
          <span class="breadcrumb-link" @click="navigateToFolder('/')">
            <el-icon :size="16"><HomeFilled /></el-icon>
            {{ t('files.allFiles') }}
          </span>
        </el-breadcrumb-item>
        <el-breadcrumb-item v-for="(segment, idx) in breadcrumbSegments" :key="idx">
          <span
            :class="['breadcrumb-link', { active: idx === breadcrumbSegments.length - 1 }]"
            @click="navigateToFolder(segment.path)"
          >
            {{ segment.name }}
          </span>
        </el-breadcrumb-item>
      </el-breadcrumb>
      <span class="breadcrumb-count">
        {{ t('files.fileCount', { count: total }) }}
        <template v-if="subfolders.length > 0">，{{ t('files.folderCount', { count: subfolders.length }) }}</template>
      </span>
    </div>

    <!-- 子文件夹列表 -->
    <div v-if="subfolders.length > 0" class="subfolders-row">
      <div
        v-for="folder in subfolders"
        :key="folder.path"
        class="subfolder-card"
        @click="navigateToFolder(folder.path)"
      >
        <el-icon :size="32" color="#f5a623"><FolderOpened /></el-icon>
        <div class="subfolder-info">
          <div class="subfolder-name">{{ folder.name }}</div>
          <div class="subfolder-count">{{ folder.file_count }} 个文件</div>
        </div>
        <el-button
          v-if="isAdmin"
          class="subfolder-rename"
          link
          type="primary"
          :icon="EditPen"
          @click.stop="openRenameFolderDialog(folder)"
        >
          {{ t('files.renameFolder') }}
        </el-button>
        <el-button
          v-if="isAdmin"
          class="subfolder-delete"
          link
          type="danger"
          :icon="Delete"
          @click.stop="deleteFolder(folder)"
        >
          {{ t('files.deleteFolder') }}
        </el-button>
      </div>
    </div>
    
    <!-- 筛选栏 -->
    <div class="filter-bar card">
      <el-input
        v-model="filters.keyword"
        :placeholder="t('files.searchFilename')"
        clearable
        :prefix-icon="Search"
        style="width: 250px"
        @keyup.enter="loadFiles"
      />
      <el-select v-model="filters.file_type" :placeholder="t('searchPage.fileType')" clearable @change="loadFiles">
        <el-option label="PDF" value="pdf" />
        <el-option label="Word" value="word" />
        <el-option label="Excel" value="excel" />
        <el-option label="PowerPoint" value="powerpoint" />
        <el-option :label="t('files.typeLabel.image')" value="image" />
        <el-option :label="t('files.typeLabel.text')" value="text" />
        <el-option :label="t('files.typeLabel.archive')" value="archive" />
      </el-select>
      <el-select v-model="filters.status" :placeholder="t('files.indexStatus')" clearable @change="loadFiles">
        <el-option :label="t('files.status.pending')" value="pending" />
        <el-option :label="t('files.status.processing')" value="processing" />
        <el-option :label="t('files.status.completed')" value="completed" />
        <el-option :label="t('files.status.failed')" value="failed" />
      </el-select>
      <el-button :icon="Refresh" @click="loadFiles">{{ t('common.refresh') }}</el-button>
      <el-button v-if="isAdmin && stats.by_status?.failed > 0" type="warning" :icon="RefreshRight" @click="retryAllFailed">
        {{ t('files.retryAllFailed', { count: stats.by_status?.failed }) }}
      </el-button>
    </div>

    <div v-if="isAdmin && selectedFiles.length > 0" class="batch-bar card">
      <span class="batch-summary">{{ t('files.batchSelected', { count: selectedFiles.length }) }}</span>
      <div class="batch-actions">
        <el-button type="danger" :icon="Delete" @click="batchDeleteSelectedFiles">
          {{ t('files.batchDelete') }}
        </el-button>
        <el-button @click="clearSelection">{{ t('files.clearSelection') }}</el-button>
      </div>
    </div>
    
    <!-- 文件列表 -->
    <el-table
      ref="tableRef"
      v-loading="loading"
      :data="files"
      class="files-table"
      stripe
      @selection-change="handleSelectionChange"
    >
      <el-table-column v-if="isAdmin" type="selection" width="48" reserve-selection />
      <el-table-column :label="t('files.filename')" min-width="250">
        <template #default="{ row }">
          <div class="file-name-cell">
            <el-icon :size="20" :class="getFileTypeClass(row.file_type)">
              <component :is="getFileIcon(row.file_type)" />
            </el-icon>
            <span class="filename" :title="row.filename">{{ row.display_name || row.filename }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column :label="t('files.folder')" width="180" v-if="!currentFolder || currentFolder === '/'">
        <template #default="{ row }">
          <span
            v-if="row.folder_path && row.folder_path !== '/'"
            class="folder-tag"
            @click="navigateToFolder(row.folder_path)"
          >
            <el-icon :size="14"><FolderOpened /></el-icon>
            {{ row.folder_path }}
          </span>
          <span v-else class="folder-tag root">{{ t('files.rootFolder') }}</span>
        </template>
      </el-table-column>
      <el-table-column :label="t('files.type')" width="80" align="center">
        <template #default="{ row }">
          <el-tooltip :content="getFileTypeLabel(row.file_type)" placement="top" :show-after="300">
            <div :class="['file-type-icon', `file-type-${row.file_type}`]">
              <el-icon :size="20">
                <component :is="getFileIcon(row.file_type)" />
              </el-icon>
            </div>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column :label="t('files.size')" width="100" prop="file_size_human" />
      <el-table-column :label="t('files.statusLabel')" width="110">
        <template #default="{ row }">
          <el-tooltip
            v-if="shouldShowStatusDetail(row)"
            placement="top"
            :show-after="200"
            :content="getStatusDetail(row)"
          >
            <el-tag :type="getStatusType(row.index_status)" size="small" class="status-tag detail">
              {{ getStatusText(row.index_status) }}
            </el-tag>
          </el-tooltip>
          <el-tag v-else :type="getStatusType(row.index_status)" size="small" class="status-tag">
            {{ getStatusText(row.index_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column :label="t('files.uploadedAt')" width="160">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column :label="t('files.actions')" width="380" fixed="right">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button v-if="supportsPreview(row.file_type)" size="small" link type="primary" @click="openPreview(row)">
              {{ t('common.preview') }}
            </el-button>
            <el-button
              v-if="isAdmin"
              size="small"
              link
              type="primary"
              @click="openRenameFileDialog(row)"
            >
              {{ t('common.rename') }}
            </el-button>
            <el-button
              v-if="row.source_url"
              size="small"
              link
              type="primary"
              @click="copySourceUrl(row.source_url)"
            >
              {{ t('files.sourceLink') }}
            </el-button>
            <el-button
              v-if="isAdmin"
              size="small"
              link
              type="primary"
              @click="openSourceUrlDialog(row)"
            >
              {{ row.source_url ? t('files.editSourceLink') : t('files.setSourceLink') }}
            </el-button>
            <el-button size="small" link type="primary" @click="downloadFile(row)">
              {{ t('common.download') }}
            </el-button>
            <el-button v-if="isAdmin" size="small" link type="primary" @click="showMoveDialog(row)">
              {{ t('common.move') }}
            </el-button>
            <el-button
              v-if="isAdmin && (row.index_status === 'failed' || row.index_status === 'parsed')"
              size="small"
              link
              type="warning"
              @click="retryFile(row)"
            >
              {{ row.index_status === 'failed' ? t('files.retryUpload') : t('files.reprocess') }}
            </el-button>
            <el-button v-if="isAdmin" size="small" link type="danger" @click="deleteFile(row)">
              {{ t('common.delete') }}
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadFiles"
        @size-change="loadFiles"
      />
    </div>

    <el-drawer
      v-model="showPreview"
      :title="previewFile?.display_name || previewFile?.filename || t('files.previewTitle')"
      size="55%"
      direction="rtl"
      :close-on-click-modal="true"
    >
      <div v-if="previewFile" class="preview-container">
        <div class="preview-file-info">
          <div :class="['file-type-icon-lg', `file-type-${previewFile.file_type}`]">
            <el-icon :size="28">
              <component :is="getFileIcon(previewFile.file_type)" />
            </el-icon>
          </div>
          <div class="preview-meta">
            <h3>{{ previewFile.display_name || previewFile.filename }}</h3>
            <div class="preview-meta-row">
              <span>{{ getFileTypeLabel(previewFile.file_type) }}</span>
              <span>{{ previewFile.file_size_human }}</span>
              <span>{{ formatDate(previewFile.created_at) }}</span>
            </div>
          </div>
          <div class="preview-actions">
            <el-button
              v-if="isAdmin"
              @click="openRenameFileDialog(previewFile)"
            >
              {{ t('files.fileRenameTitle') }}
            </el-button>
            <el-button v-if="previewFile.source_url" @click="copySourceUrl(previewFile.source_url)">
              {{ t('files.sourceLink') }}
            </el-button>
            <el-button
              v-if="isAdmin"
              @click="openSourceUrlDialog(previewFile)"
            >
              {{ previewFile.source_url ? t('files.editSourceLink') : t('files.setSourceLink') }}
            </el-button>
            <el-button type="primary" @click="downloadFile(previewFile)">
              {{ t('files.downloadFile') }}
            </el-button>
          </div>
        </div>

        <div class="preview-content">
          <div v-if="previewFile.file_type === 'image'" class="preview-image">
            <img
              :src="getPreviewUrl(previewFile.id)"
              :alt="previewFile.filename"
              @error="previewError = true"
            />
            <div v-if="previewError" class="preview-error">
              <el-icon :size="48" color="#c0c4cc"><Picture /></el-icon>
              <p>{{ t('files.imageLoadFailed') }}</p>
            </div>
          </div>

          <div v-else-if="previewFile.file_type === 'pdf'" class="preview-pdf">
            <iframe :src="getPreviewUrl(previewFile.id)" frameborder="0"></iframe>
          </div>

          <div v-else class="preview-text">
            <div class="preview-text-label">
              <el-icon><Document /></el-icon>
              {{ t('files.previewDescription') }}
            </div>
            <div class="preview-no-visual">
              <el-icon :size="40" color="#dcdfe6"><Document /></el-icon>
              <p>{{ t('files.unsupportedPreview') }}</p>
              <el-button type="primary" plain @click="downloadFile(previewFile)">
                {{ t('files.downloadToView') }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>
    
    <!-- 上传对话框 -->
    <el-dialog v-model="showUpload" :title="t('files.uploadTo', { folder: currentFolder })" width="500px">
      <div class="upload-target-hint">
        <el-icon :size="14"><FolderOpened /></el-icon>
        {{ t('files.targetFolder') }}<strong>{{ currentFolder }}</strong>
      </div>
      <el-upload
        ref="uploadRef"
        v-model:file-list="uploadFileList"
        drag
        multiple
        :limit="10"
        :auto-upload="false"
        :accept="acceptTypes"
      >
        <el-icon :size="48" color="#409eff"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处，或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            {{ t('files.uploadTip') }}
          </div>
        </template>
      </el-upload>
      <div v-if="uploadFailedItems.length > 0" class="upload-failed-list">
        <div class="upload-failed-title">{{ t('files.uploadFailedFiles') }}</div>
        <div
          v-for="item in uploadFailedItems"
          :key="item.uid"
          class="upload-failed-item"
        >
          <span class="upload-failed-name">{{ item.name }}</span>
          <span class="upload-failed-reason">{{ item.errorMessage || t('files.sourceLinkSaveFailed') }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="showUpload = false">{{ t('common.cancel') }}</el-button>
        <el-button
          v-if="uploadFailedItems.length > 0"
          type="warning"
          :loading="uploading"
          @click="retryFailedUploadItems"
        >
          {{ t('files.retryFailedItems', { count: uploadFailedItems.length }) }}
        </el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">
          {{ t('files.startUpload') }}
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 文件夹上传对话框 -->
    <el-dialog v-model="showFolderUpload" :title="t('files.folderUploadTitle')" width="650px" :close-on-click-modal="!folderUploading">
      <div v-if="folderName" class="folder-info">
        <el-icon :size="20" color="#409eff"><FolderOpened /></el-icon>
        <span class="folder-name">{{ folderName }}</span>
        <el-tag size="small" type="info">{{ t('files.fileCount', { count: folderFiles.length }) }}</el-tag>
        <el-popover
          v-if="skippedCount > 0"
          placement="bottom"
          :width="260"
          trigger="click"
        >
          <template #reference>
            <el-tag size="small" type="warning" class="skipped-tag">
              {{ t('files.skippedCount', { count: skippedCount }) }}
            </el-tag>
          </template>
          <div class="skipped-details">
            <div class="skipped-title">{{ t('files.skippedReason') }}</div>
            <div class="skipped-item">
              <span>{{ t('files.skippedHidden') }}</span>
              <strong>{{ skippedStats.hidden }}</strong>
            </div>
            <div class="skipped-item">
              <span>{{ t('files.skippedEmpty') }}</span>
              <strong>{{ skippedStats.empty }}</strong>
            </div>
            <div class="skipped-item">
              <span>{{ t('files.skippedUnsupported') }}</span>
              <strong>{{ skippedStats.unsupported }}</strong>
            </div>
          </div>
        </el-popover>
      </div>
      
      <div class="folder-file-list">
        <el-table :data="folderFiles" max-height="400" size="small" stripe>
          <el-table-column :label="t('files.path')" min-width="280">
            <template #default="{ row }">
              <div class="folder-file-path">
                <el-icon :size="14"><Document /></el-icon>
                <span>{{ row.relativePath }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column :label="t('files.size')" width="100">
            <template #default="{ row }">
              {{ formatFileSize(row.file.size) }}
            </template>
          </el-table-column>
          <el-table-column :label="t('files.statusLabel')" width="80" align="center">
            <template #default="{ row }">
              <el-icon v-if="row.status === 'success'" color="#67c23a" :size="16"><CircleCheckFilled /></el-icon>
              <span v-else-if="row.status === 'duplicate'" class="status-duplicate">{{ t('files.status.duplicate') }}</span>
              <el-icon v-else-if="row.status === 'error'" color="#f56c6c" :size="16"><CircleCloseFilled /></el-icon>
              <el-icon v-else-if="row.status === 'uploading'" class="is-loading" color="#409eff" :size="16"><Loading /></el-icon>
              <span v-else class="status-pending">{{ t('files.pending') }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <!-- 上传进度 -->
      <div v-if="folderUploading || folderUploadedCount > 0" class="folder-progress">
        <el-progress :percentage="folderProgress" :stroke-width="10" />
        <span class="progress-text">
          {{ t('files.uploadProgress', { done: folderUploadedCount, total: folderFiles.length }) }}
          <span v-if="folderFailCount > 0" style="color: #f56c6c">{{ t('files.failedCountInline', { count: folderFailCount }) }}</span>
        </span>
      </div>
      
      <template #footer>
        <el-button @click="showFolderUpload = false" :disabled="folderUploading">{{ t('common.cancel') }}</el-button>
        <el-button
          v-if="failedFolderItems.length > 0"
          type="warning"
          :loading="folderUploading"
          @click="retryFailedFolderUploads"
        >
          {{ t('files.retryFailedFolderItems', { count: failedFolderItems.length }) }}
        </el-button>
        <el-button type="primary" :loading="folderUploading" @click="handleFolderUpload" :disabled="folderProgress === 100">
          {{ folderUploading ? t('files.uploading') : folderProgress === 100 ? t('files.uploadCompleted') : t('files.startUpload') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 移动文件对话框 -->
    <el-dialog v-model="showMove" :title="t('files.moveTo')" width="450px">
      <div class="move-current">
        {{ t('files.currentLocation') }}<el-tag>{{ moveFile?.folder_path || '/' }}</el-tag>
      </div>
      <div class="move-target">
        <el-select
          v-model="moveTargetFolder"
          filterable
          allow-create
          :placeholder="t('files.targetFolderPlaceholder')"
          style="width: 100%"
        >
          <el-option
            v-for="folder in allFolders"
            :key="folder.path"
            :label="`${folder.path} (${folder.file_count})`"
            :value="folder.path"
          />
        </el-select>
        <div class="move-hint">
          {{ t('files.moveHint') }}
        </div>
      </div>
      <template #footer>
        <el-button @click="showMove = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleMoveFile" :disabled="!moveTargetFolder">
          {{ t('common.move') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCreateFolder" :title="t('files.createFolderTitle')" width="420px">
      <el-form label-width="90px">
        <el-form-item :label="t('files.parentFolder')">
          <span>{{ currentFolder }}</span>
        </el-form-item>
        <el-form-item :label="t('files.folderName')">
          <el-input
            v-model="newFolderName"
            :placeholder="t('files.folderNamePlaceholder')"
            maxlength="100"
            @keyup.enter="handleCreateFolder"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateFolder = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleCreateFolder">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRenameFolderDialog" :title="t('files.folderRenameTitle')" width="440px">
      <el-form label-width="90px">
        <el-form-item :label="t('files.currentPath')">
          <span>{{ renameFolderTarget?.path || '-' }}</span>
        </el-form-item>
        <el-form-item :label="t('files.newName')">
          <el-input
            v-model="renameFolderForm.new_name"
            :placeholder="t('files.folderRenamePlaceholder')"
            maxlength="100"
            @keyup.enter="handleRenameFolder"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRenameFolderDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleRenameFolder">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showRenameFileDialog" :title="t('files.fileRenameTitle')" width="460px">
      <el-form label-width="80px">
        <el-form-item :label="t('files.currentFile')">
          <span>{{ renameFileTarget?.display_name || renameFileTarget?.filename || '-' }}</span>
        </el-form-item>
        <el-form-item :label="t('files.newFilename')">
          <el-input
            v-model="renameFileForm.filename"
            :placeholder="t('files.newFilenamePlaceholder')"
            maxlength="255"
            @keyup.enter="handleRenameFile"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRenameFileDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" @click="handleRenameFile">{{ t('common.save') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showSourceUrlDialog" :title="t('files.sourceLinkTitle')" width="520px">
      <el-form label-width="80px">
        <el-form-item :label="t('files.currentFile')">
          <span>{{ sourceUrlTargetFile?.display_name || sourceUrlTargetFile?.filename || '-' }}</span>
        </el-form-item>
        <el-form-item :label="t('files.sourceLinkField')">
          <el-input
            v-model="sourceUrlForm.source_url"
            :placeholder="t('files.sourceLinkPlaceholder')"
            clearable
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSourceUrlDialog = false">{{ t('common.cancel') }}</el-button>
        <el-button
          v-if="sourceUrlTargetFile?.source_url"
          type="danger"
          plain
          @click="saveSourceUrl(null)"
        >
          {{ t('files.clearSourceLink') }}
        </el-button>
        <el-button type="primary" @click="saveSourceUrl(sourceUrlForm.source_url)">
          {{ t('common.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { fileApi } from '@/api/files'
import { useAuthStore } from '@/stores/auth'
import { ElMessage, ElMessageBox, type UploadInstance, type TableInstance } from 'element-plus'
import dayjs from 'dayjs'
import type { FileItem } from '@/types'
import { useI18n } from '@/i18n'
import {
  Upload, Folder, Search, Refresh, Loading, Warning, Document,
  Picture, Tickets, UploadFilled, FolderOpened,
  CircleCheckFilled, CircleCloseFilled, RefreshRight, HomeFilled,
  FolderAdd, Delete, EditPen,
} from '@element-plus/icons-vue'

const loading = ref(false)
const uploading = ref(false)
const showUpload = ref(false)
const tableRef = ref<TableInstance>()
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const files = ref<FileItem[]>([])
const selectedFiles = ref<FileItem[]>([])
const stats = ref<any>({})
const uploadRef = ref<UploadInstance>()
const uploadFileList = ref<any[]>([])
const showPreview = ref(false)
const previewFile = ref<FileItem | null>(null)
const previewError = ref(false)
const showSourceUrlDialog = ref(false)
const sourceUrlTargetFile = ref<FileItem | null>(null)
const sourceUrlForm = reactive({
  source_url: '',
})
const fileStatusDetails = reactive<Record<number, { error_message?: string | null; task_status?: string | null; updated_at?: string }>>({})
let statusPollTimer: ReturnType<typeof setInterval> | null = null
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.isAdmin)
const { t } = useI18n()

// 文件夹导航
const currentFolder = ref<string>('/')
const subfolders = ref<any[]>([])
const allFolders = ref<any[]>([])
const showCreateFolder = ref(false)
const newFolderName = ref('')
const showRenameFolderDialog = ref(false)
const renameFolderTarget = ref<{ path: string; name: string } | null>(null)
const renameFolderForm = reactive({
  new_name: '',
})

// 面包屑
const breadcrumbSegments = computed(() => {
  if (!currentFolder.value || currentFolder.value === '/') return []
  const parts = currentFolder.value.split('/').filter(Boolean)
  return parts.map((part, idx) => ({
    name: part,
    path: '/' + parts.slice(0, idx + 1).join('/'),
  }))
})

// 文件夹上传相关
const folderInputRef = ref<HTMLInputElement>()
const showFolderUpload = ref(false)
const folderName = ref('')
const folderFiles = ref<any[]>([])
const skippedCount = ref(0)
const skippedStats = reactive({
  hidden: 0,
  empty: 0,
  unsupported: 0,
})
const folderUploading = ref(false)
const folderProgress = ref(0)
const folderUploadedCount = ref(0)
const folderFailCount = ref(0)
const uploadFailedItems = computed(() =>
  uploadFileList.value.filter((item) => item.uploadStatus === 'error')
)
const failedFolderItems = computed(() =>
  folderFiles.value.filter((item) => item.status === 'error')
)

// 移动文件
const showMove = ref(false)
const moveFile = ref<FileItem | null>(null)
const moveTargetFolder = ref('')
const showRenameFileDialog = ref(false)
const renameFileTarget = ref<FileItem | null>(null)
const renameFileForm = reactive({
  filename: '',
})

const filters = reactive({
  keyword: '',
  file_type: '',
  status: '',
})

const acceptTypes = '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.md,.csv,.jpg,.jpeg,.png,.gif,.bmp,.zip,.rar'

// 支持的文件扩展名
const allowedExtensions = new Set([
  'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
  'txt', 'md', 'csv', 'log',
  'zip', 'rar',
  'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg',
])

// ============== 文件夹导航 ==============

const navigateToFolder = (path: string) => {
  currentFolder.value = path
  page.value = 1
  loadFiles()
  loadSubfolders()
}

const loadSubfolders = async () => {
  try {
    const res = await fileApi.getFolders(currentFolder.value === '/' ? undefined : currentFolder.value)
    if (currentFolder.value === '/') {
      // 根目录：显示顶级文件夹
      // 从所有文件夹中提取顶级文件夹
      const topLevel: Record<string, { path: string; name: string; file_count: number }> = {}
      for (const f of res.folders) {
        if (f.path === '/') continue
        const parts = f.path.split('/').filter(Boolean)
        const topName = parts[0]
        const topPath = '/' + topName
        if (!topLevel[topPath]) {
          topLevel[topPath] = { path: topPath, name: topName, file_count: 0 }
        }
        topLevel[topPath].file_count += f.file_count
      }
      subfolders.value = Object.values(topLevel)
    } else {
      subfolders.value = res.folders || []
    }
  } catch {
    subfolders.value = []
  }
}

const loadAllFolders = async () => {
  try {
    const res = await fileApi.getFolders()
    allFolders.value = res.folders || []
  } catch {
    allFolders.value = []
  }
}

const openCreateFolderDialog = () => {
  newFolderName.value = ''
  showCreateFolder.value = true
}

const openSourceUrlDialog = (file: FileItem) => {
  sourceUrlTargetFile.value = file
  sourceUrlForm.source_url = file.source_url || ''
  showSourceUrlDialog.value = true
}

const openRenameFolderDialog = (folder: { path: string; name: string }) => {
  renameFolderTarget.value = folder
  renameFolderForm.new_name = folder.name
  showRenameFolderDialog.value = true
}

const openRenameFileDialog = (file: FileItem) => {
  renameFileTarget.value = file
  renameFileForm.filename = file.display_name || file.filename
  showRenameFileDialog.value = true
}

// 加载文件列表
const loadFiles = async () => {
  loading.value = true
  try {
    const params: any = {
      page: page.value,
      page_size: pageSize.value,
      ...filters,
    }
    // 只有在非根目录时传 folder 参数
    if (currentFolder.value && currentFolder.value !== '/') {
      params.folder = currentFolder.value
    }
    const response = await fileApi.getFiles(params)
    files.value = response.data
    total.value = response.total
    selectedFiles.value = []
    await refreshVisibleStatusDetails()
  } catch {
    ElMessage.error(t('files.loadFailed'))
  } finally {
    loading.value = false
  }
}

// 加载统计
const loadStats = async () => {
  try {
    const response = await fileApi.getStats()
    stats.value = response.data || {}
  } catch {
    // 忽略错误
  }
}

const refreshFilePageData = () => {
  loadFiles()
  loadStats()
  loadSubfolders()
}

const copySourceUrl = async (sourceUrl?: string | null) => {
  if (!sourceUrl) return

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(sourceUrl)
    } else {
      const input = document.createElement('textarea')
      input.value = sourceUrl
      input.style.position = 'fixed'
      input.style.opacity = '0'
      document.body.appendChild(input)
      input.focus()
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
    }
    ElMessage.success(t('files.sourceLinkCopied'))
  } catch {
    ElMessage.error(t('files.sourceLinkCopyFailed'))
  }
}

const joinFolderPath = (...segments: Array<string | undefined>) => {
  const parts = segments
    .filter((segment): segment is string => !!segment)
    .flatMap((segment) => segment.split('/'))
    .map((segment) => segment.trim())
    .filter(Boolean)

  return parts.length ? `/${parts.join('/')}` : '/'
}

const extractErrorMessage = (error: any, fallback = t('files.allUploadFailed')) =>
  error?.response?.data?.detail || error?.response?.data?.message || fallback

const resetUploadDialogState = () => {
  uploadFileList.value = []
  showUpload.value = false
}

const syncStatusPolling = () => {
  const needPolling = files.value.some((file) =>
    ['pending', 'processing', 'parsed'].includes(file.index_status)
  )

  if (!needPolling) {
    if (statusPollTimer) {
      clearInterval(statusPollTimer)
      statusPollTimer = null
    }
    return
  }

  if (statusPollTimer) return

  statusPollTimer = setInterval(() => {
    refreshVisibleStatusDetails()
  }, 5000)
}

const refreshVisibleStatusDetails = async () => {
  const currentIds = new Set(files.value.map((file) => file.id))
  for (const key of Object.keys(fileStatusDetails)) {
    if (!currentIds.has(Number(key))) {
      delete fileStatusDetails[Number(key)]
    }
  }

  const targetFiles = files.value.filter((file) =>
    ['pending', 'processing', 'failed', 'parsed'].includes(file.index_status)
  )

  if (!targetFiles.length) {
    syncStatusPolling()
    return
  }

  const statuses = await Promise.allSettled(
    targetFiles.map((file) => fileApi.getFileStatus(file.id))
  )

  let shouldRefreshStats = false

  statuses.forEach((result, index) => {
    const file = targetFiles[index]
    if (result.status !== 'fulfilled') return

    const payload = result.value
    fileStatusDetails[file.id] = {
      error_message: payload.error_message,
      updated_at: payload.updated_at,
    }

    if (payload.index_status && payload.index_status !== file.index_status) {
      file.index_status = payload.index_status
      shouldRefreshStats = true
    }
  })

  if (shouldRefreshStats) {
    loadStats()
  }

  syncStatusPolling()
}

// 上传文件（普通）
const handleUpload = async () => {
  if (!uploadFileList.value.length) {
    ElMessage.warning(t('files.selectFileWarning'))
    return
  }
  
  uploading.value = true
  let successCount = 0
  let duplicateCount = 0
  let failCount = 0
  const candidates = uploadFileList.value.filter((item) => item.raw)
  
  try {
    for (const item of candidates) {
      item.uploadStatus = 'uploading'
      item.errorMessage = ''

      try {
        const res = await fileApi.uploadFile(
          item.raw,
          undefined,
          currentFolder.value !== '/' ? currentFolder.value : undefined
        )

        if (res.is_duplicate) {
          item.uploadStatus = 'duplicate'
          duplicateCount++
        } else {
          item.uploadStatus = 'success'
          successCount++
        }
      } catch (error) {
        item.uploadStatus = 'error'
        item.errorMessage = extractErrorMessage(error)
        failCount++
      }
    }

    if (successCount > 0 || duplicateCount > 0) {
      refreshFilePageData()
    }

    if (failCount > 0) {
      uploadFileList.value = uploadFileList.value.filter((item) => item.uploadStatus === 'error')
    } else if (successCount > 0 || duplicateCount > 0) {
      resetUploadDialogState()
    }

    if (successCount > 0 && duplicateCount > 0) {
      ElMessage.warning(t('files.uploadSuccessAndDuplicate', { success: successCount, duplicate: duplicateCount }))
    } else if (successCount > 0) {
      ElMessage.success(t('files.uploadSuccessCount', { count: successCount }))
    } else if (duplicateCount > 0) {
      ElMessage.warning(t('files.duplicateSkippedOnly', { count: duplicateCount }))
    }

    if (failCount > 0) {
      ElMessage.warning(t('files.uploadFailedRetry', { count: failCount }))
    }
  } finally {
    uploading.value = false
  }
}

const retryFailedUploadItems = async () => {
  if (!uploadFailedItems.value.length) return
  await handleUpload()
}

// ============== 文件夹上传 ==============

// 触发文件夹选择
const triggerFolderUpload = () => {
  folderInputRef.value?.click()
}

// 处理文件夹选择结果
const handleFolderSelected = (event: Event) => {
  const input = event.target as HTMLInputElement
  const fileList = input.files
  if (!fileList || fileList.length === 0) return
  
  // 提取文件夹名称
  const firstPath = (fileList[0] as any).webkitRelativePath || ''
  folderName.value = firstPath.split('/')[0] || '未知文件夹'
  
  // 过滤支持的文件类型
  const validFiles: any[] = []
  let skipped = 0
  skippedStats.hidden = 0
  skippedStats.empty = 0
  skippedStats.unsupported = 0
  
  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i]
    const relativePath = (file as any).webkitRelativePath || file.name
    const ext = file.name.split('.').pop()?.toLowerCase() || ''
    
    // 跳过隐藏文件和系统文件
    if (file.name.startsWith('.') || file.name.startsWith('~')) {
      skipped++
      skippedStats.hidden++
      continue
    }
    
    // 跳过空文件
    if (file.size === 0) {
      skipped++
      skippedStats.empty++
      continue
    }
    
    // 检查文件扩展名
    if (allowedExtensions.has(ext)) {
      validFiles.push({
        file: file,
        relativePath: relativePath,
        status: 'pending',
      })
    } else {
      skipped++
      skippedStats.unsupported++
    }
  }
  
  folderFiles.value = validFiles
  skippedCount.value = skipped
  folderProgress.value = 0
  folderUploadedCount.value = 0
  folderFailCount.value = 0
  folderUploading.value = false
  
  if (validFiles.length === 0) {
    ElMessage.warning(t('files.noSupportedFiles'))
    return
  }
  
  showFolderUpload.value = true
  
  // 重置 input，允许重复选择同一文件夹
  input.value = ''
}

// 执行文件夹上传
const handleFolderUpload = async () => {
  const baseFolderPath = joinFolderPath(currentFolder.value, folderName.value)
  await fileApi.createFolder(baseFolderPath)

  await uploadFolderItems(
    folderFiles.value.filter((item) => item.status === 'pending'),
    true
  )
}

const uploadFolderItems = async (items: any[], resetCounters = false) => {
  if (items.length === 0) return

  folderUploading.value = true
  let duplicateCount = 0

  if (resetCounters) {
    folderUploadedCount.value = 0
    folderFailCount.value = 0
    folderProgress.value = 0
  } else {
    folderFailCount.value = failedFolderItems.value.length
  }

  for (const item of items) {
    item.status = 'uploading'
    item.errorMessage = ''
    
    try {
      const relativeParts = item.relativePath.split('/').filter(Boolean)
      const relativeDirectory = relativeParts.slice(0, -1).join('/')
      const targetFolderPath = joinFolderPath(currentFolder.value, relativeDirectory)

      const res = await fileApi.uploadFile(
        item.file,
        undefined,
        targetFolderPath !== '/' ? targetFolderPath : undefined
      )

      if (res.is_duplicate) {
        item.status = 'duplicate'
        duplicateCount++
      } else {
        item.status = 'success'
      }
    } catch (error) {
      item.status = 'error'
      item.errorMessage = extractErrorMessage(error)
    }

    folderUploadedCount.value = folderFiles.value.filter((file) => file.status === 'success').length
    folderFailCount.value = failedFolderItems.value.length
    const completedCount = folderFiles.value.filter((file) =>
      ['success', 'duplicate', 'error'].includes(file.status)
    ).length
    folderProgress.value = Math.round((completedCount / folderFiles.value.length) * 100)
  }
  
  folderUploading.value = false
  
  const successCount = folderUploadedCount.value
  const failCount = folderFailCount.value
  
  if (successCount > 0 || duplicateCount > 0) {
    refreshFilePageData()
  }

  if (successCount > 0 && duplicateCount > 0) {
    ElMessage.warning(t('files.folderUploadSummaryMixed', {
      success: successCount,
      duplicate: duplicateCount,
      failedPart: failCount > 0 ? t('files.failedCountInline', { count: failCount }) : '',
    }))
  } else if (successCount > 0) {
    ElMessage.success(t('files.folderUploadSummarySuccess', {
      success: successCount,
      failedPart: failCount > 0 ? t('files.failedCountInline', { count: failCount }) : '',
    }))
  } else if (duplicateCount > 0) {
    ElMessage.warning(t('files.folderUploadSummaryDuplicate', {
      duplicate: duplicateCount,
      failedPart: failCount > 0 ? t('files.failedCountInline', { count: failCount }) : '',
    }))
  } else {
    ElMessage.error(t('files.allUploadFailed'))
  }
}

const retryFailedFolderUploads = async () => {
  await uploadFolderItems(failedFolderItems.value, false)
}

// ============== 移动功能 ==============

const showMoveDialog = (file: FileItem) => {
  moveFile.value = file
  moveTargetFolder.value = ''
  loadAllFolders()
  showMove.value = true
}

const handleMoveFile = async () => {
  if (!moveFile.value || !moveTargetFolder.value) return
  
  try {
    await fileApi.moveFile(moveFile.value.id, moveTargetFolder.value)
    ElMessage.success(t('files.moveSuccess', { path: moveTargetFolder.value }))
    showMove.value = false
    loadFiles()
    loadSubfolders()
  } catch {
    ElMessage.error(t('files.moveFailed'))
  }
}

const handleCreateFolder = async () => {
  const trimmedName = newFolderName.value.trim().replace(/^\/+|\/+$/g, '')
  if (!trimmedName) {
    ElMessage.warning(t('files.folderNamePlaceholder'))
    return
  }
  if (trimmedName.includes('/')) {
    ElMessage.warning(t('files.folderRenameFailed'))
    return
  }

  const targetPath = currentFolder.value === '/'
    ? `/${trimmedName}`
    : `${currentFolder.value}/${trimmedName}`

  try {
    await fileApi.createFolder(targetPath)
    ElMessage.success(t('files.createSuccess', { path: targetPath }))
    showCreateFolder.value = false
    loadSubfolders()
    loadAllFolders()
  } catch {
    ElMessage.error(t('files.createFailed'))
  }
}

const handleRenameFolder = async () => {
  if (!renameFolderTarget.value) return

  const nextName = renameFolderForm.new_name.trim().replace(/^\/+|\/+$/g, '')
  if (!nextName) {
    ElMessage.warning(t('files.folderRenamePlaceholder'))
    return
  }
  if (nextName.includes('/')) {
    ElMessage.warning(t('files.folderRenameFailed'))
    return
  }

  try {
    const res = await fileApi.renameFolder(renameFolderTarget.value.path, nextName)
    const nextPath = res.data?.path || renameFolderTarget.value.path
    const prevPath = renameFolderTarget.value.path

    if (currentFolder.value === prevPath) {
      currentFolder.value = nextPath
    }

    showRenameFolderDialog.value = false
    renameFolderTarget.value = null
    renameFolderForm.new_name = ''
    ElMessage.success(t('files.folderRenameSuccess'))
    loadFiles()
    loadSubfolders()
    loadAllFolders()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || t('files.folderRenameFailed'))
  }
}

const deleteFolder = async (folder: { path: string; name: string }) => {
  try {
    const summaryRes = await fileApi.getFolderDeleteSummary(folder.path)
    const summary = summaryRes.data || { file_count: 0, subfolder_count: 0 }

    await ElMessageBox.confirm(
      t('files.confirmDeleteFolder', { name: folder.name }),
      t('files.confirmDeleteFolderTitle'),
      {
        confirmButtonText: t('common.ok'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      }
    )

    await ElMessageBox.confirm(
      t('files.confirmDeleteFolderSecond', {
        name: folder.name,
        files: summary.file_count,
        folders: summary.subfolder_count,
      }),
      t('files.secondConfirmTitle'),
      {
        confirmButtonText: t('files.confirmDelete'),
        cancelButtonText: t('common.cancel'),
        type: 'error',
      }
    )

    await fileApi.deleteFolder(folder.path)
    ElMessage.success(t('files.folderDeleteSuccess'))
    loadSubfolders()
    loadAllFolders()
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error(t('files.folderDeleteFailed'))
  }
}

const handleRenameFile = async () => {
  if (!renameFileTarget.value) return

  const nextFilename = renameFileForm.filename.trim()
  if (!nextFilename) {
    ElMessage.warning(t('files.newFilenamePlaceholder'))
    return
  }
  if (nextFilename.includes('/')) {
    ElMessage.warning(t('files.fileRenameFailed'))
    return
  }

  try {
    const res = await fileApi.renameFile(renameFileTarget.value.id, nextFilename)
    const updatedFilename = res.data?.filename || nextFilename
    const updatedDisplayName = res.data?.display_name || updatedFilename
    const targetId = renameFileTarget.value.id

    files.value = files.value.map((file) =>
      file.id === targetId
        ? { ...file, filename: updatedFilename, display_name: updatedDisplayName }
        : file
    )

    if (previewFile.value?.id === targetId) {
      previewFile.value = {
        ...previewFile.value,
        filename: updatedFilename,
        display_name: updatedDisplayName,
      }
    }

    showRenameFileDialog.value = false
    renameFileTarget.value = null
    renameFileForm.filename = ''
    ElMessage.success(t('files.fileRenameSuccess'))
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || t('files.fileRenameFailed'))
  }
}

const saveSourceUrl = async (value: string | null) => {
  if (!sourceUrlTargetFile.value) return

  try {
    const normalizedValue = typeof value === 'string' ? value.trim() : null
    const res = await fileApi.updateSourceUrl(
      sourceUrlTargetFile.value.id,
      normalizedValue || null
    )
    const nextSourceUrl = res.data?.source_url || null

    const targetId = sourceUrlTargetFile.value.id
    files.value = files.value.map((file) =>
      file.id === targetId ? { ...file, source_url: nextSourceUrl } : file
    )

    if (previewFile.value?.id === targetId) {
      previewFile.value = {
        ...previewFile.value,
        source_url: nextSourceUrl,
      }
    }

    sourceUrlTargetFile.value = null
    sourceUrlForm.source_url = ''
    showSourceUrlDialog.value = false
    ElMessage.success(nextSourceUrl ? t('files.sourceLinkUpdated') : t('files.sourceLinkCleared'))
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || t('files.sourceLinkSaveFailed'))
  }
}

// ============== 重试功能 ==============

// 重试单个文件
const retryFile = async (file: FileItem) => {
  try {
    const res = await fileApi.retryFile(file.id)
    ElMessage.success(res.message || t('files.retrySuccess', { name: file.filename }))
    refreshFilePageData()
  } catch {
    ElMessage.error(file.index_status === 'failed' ? t('files.retryUploadFailed') : t('files.retryProcessFailed'))
  }
}

// 重试所有失败文件
const retryAllFailed = async () => {
  await ElMessageBox.confirm(
    t('files.confirmRetryAllFailed'),
    t('files.retryAllTitle'),
    {
      confirmButtonText: t('common.ok'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    }
  )
  
  try {
    const res = await fileApi.retryAllFailed()
    ElMessage.success(res.message || t('files.retrySubmitted'))
    loadFiles()
    loadStats()
  } catch {
    ElMessage.error(t('files.retryAllFailedRequest'))
  }
}

// ============== 通用工具函数 ==============

const openPreview = (file: FileItem) => {
  previewFile.value = file
  previewError.value = false
  showPreview.value = true
}

const getPreviewUrl = (fileId: number): string => {
  return fileApi.getPreviewUrl(fileId)
}

// 下载文件
const downloadFile = (file: FileItem) => {
  const url = fileApi.getDownloadUrl(file.id)
  window.open(url, '_blank')
}

// 删除文件
const deleteFile = async (file: FileItem) => {
  await ElMessageBox.confirm(t('files.confirmDeleteFile', { name: file.filename }), t('files.actions'), {
    confirmButtonText: t('common.ok'),
    cancelButtonText: t('common.cancel'),
    type: 'warning',
  })
  
  try {
    await fileApi.deleteFile(file.id)
    ElMessage.success(t('files.fileDeleteSuccess'))
    loadFiles()
    loadStats()
    loadSubfolders()
  } catch {
    ElMessage.error(t('files.fileDeleteFailed'))
  }
}

const handleSelectionChange = (selection: FileItem[]) => {
  selectedFiles.value = selection
}

const clearSelection = () => {
  tableRef.value?.clearSelection()
  selectedFiles.value = []
}

const batchDeleteSelectedFiles = async () => {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning(t('files.batchSelected', { count: 0 }))
    return
  }

  await ElMessageBox.confirm(
    t('files.confirmBatchDelete', { count: selectedFiles.value.length }),
    t('files.batchDelete'),
    {
      confirmButtonText: t('common.ok'),
      cancelButtonText: t('common.cancel'),
      type: 'warning',
    }
  )

  try {
    const res = await fileApi.batchDeleteFiles(selectedFiles.value.map((file) => file.id))
    const deletedCount = res.data?.deleted_count || 0
    const missingCount = res.data?.missing_ids?.length || 0
    ElMessage.success(
      missingCount > 0
        ? t('files.batchDeleteSummary', { deleted: deletedCount, missing: missingCount })
        : t('files.batchDeleteSuccess', { deleted: deletedCount })
    )
    clearSelection()
    loadFiles()
    loadStats()
    loadSubfolders()
  } catch {
    ElMessage.error(t('files.batchDeleteFailed'))
  }
}

const getFileIcon = (type: string) => {
  const icons: Record<string, any> = {
    image: Picture,
    pdf: Document,
    word: Document,
    excel: Tickets,
    powerpoint: Document,
    text: Document,
    archive: Folder,
  }
  return icons[type] || Document
}

const getFileTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    image: t('files.typeLabel.image'),
    pdf: t('files.typeLabel.pdf'),
    word: t('files.typeLabel.word'),
    excel: t('files.typeLabel.excel'),
    powerpoint: t('files.typeLabel.powerpoint'),
    text: t('files.typeLabel.text'),
    archive: t('files.typeLabel.archive'),
  }
  return labels[type] || type
}

const supportsPreview = (type: string) => ['image', 'pdf'].includes(type)

const getFileTypeClass = (type: string) => `file-type-${type}`

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'warning',
    processing: '',
    completed: 'success',
    failed: 'danger',
    parsed: 'info',
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: t('files.status.pending'),
    processing: t('files.status.processing'),
    completed: t('files.status.completed'),
    failed: t('files.status.failed'),
    parsed: t('files.status.parsed'),
  }
  return texts[status] || status
}

const shouldShowStatusDetail = (file: FileItem) =>
  ['pending', 'processing', 'failed', 'parsed'].includes(file.index_status)

const getStatusDetail = (file: FileItem) => {
  const statusDetail = fileStatusDetails[file.id]

  if (file.index_status === 'failed') {
    return statusDetail?.error_message || t('files.failedHintFallback')
  }

  if (file.index_status === 'parsed') {
    return t('files.parsedHint')
  }

  if (file.index_status === 'processing') {
    return t('files.processingHint')
  }

  return t('files.pendingHint')
}

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm')

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i]
}

onMounted(() => {
  loadFiles()
  loadStats()
  loadSubfolders()
})

onBeforeUnmount(() => {
  if (statusPollTimer) {
    clearInterval(statusPollTimer)
    statusPollTimer = null
  }
})
</script>

<style lang="scss" scoped>
.header-actions {
  display: flex;
  gap: 8px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: var(--ds-shadow-base);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-info {
  .stat-value {
    font-size: 24px;
    font-weight: 600;
    color: var(--ds-text-primary);
  }
  
  .stat-label {
    font-size: 13px;
    color: var(--ds-text-secondary);
    margin-top: 4px;
  }
}

/* 面包屑 */
.breadcrumb-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 12px 20px;

  .breadcrumb-link {
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: #409eff;
    font-weight: 500;
    transition: color 0.2s;

    &:hover {
      color: #337ecc;
    }

    &.active {
      color: #303133;
      cursor: default;
      font-weight: 600;
    }
  }

  .breadcrumb-count {
    font-size: 13px;
    color: #909399;
  }
}

/* 子文件夹 */
.subfolders-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.subfolder-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid #f0f0f0;
  min-width: 180px;

  &:hover {
    box-shadow: 0 4px 12px rgba(64, 158, 255, 0.15);
    border-color: #b3d8ff;
    transform: translateY(-1px);
  }

  .subfolder-info {
    flex: 1;

    .subfolder-name {
      font-weight: 600;
      font-size: 14px;
      color: #303133;
    }

    .subfolder-count {
      font-size: 12px;
      color: #909399;
      margin-top: 2px;
    }
  }
}

.subfolder-delete {
  opacity: 0.8;
}

.subfolder-rename {
  opacity: 0.9;
}

.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.batch-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #fff7ed;
  border: 1px solid #fed7aa;

  .batch-summary {
    color: #9a3412;
    font-weight: 600;
  }

  .batch-actions {
    display: flex;
    gap: 8px;
  }
}

.files-table {
  background: #fff;
  border-radius: 8px;
}

.table-actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, max-content));
  align-items: center;
  gap: 4px 12px;
  justify-content: start;

  :deep(.el-button) {
    margin-left: 0;
    justify-self: start;
  }
}

.status-duplicate {
  color: #e6a23c;
  font-size: 12px;
  font-weight: 600;
}

.status-tag.detail {
  cursor: help;
}

.skipped-tag {
  cursor: pointer;
}

.skipped-details {
  display: flex;
  flex-direction: column;
  gap: 8px;

  .skipped-title {
    font-size: 13px;
    font-weight: 600;
    color: #303133;
  }

  .skipped-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 13px;
    color: #606266;
  }
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .filename {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

/* 文件类型图标 */
.file-type-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  transition: transform 0.2s ease;

  &:hover {
    transform: scale(1.15);
  }

  &.file-type-image {
    background: #f3e8ff;
    color: #9333ea;
  }

  &.file-type-pdf {
    background: #fee2e2;
    color: #dc2626;
  }

  &.file-type-word {
    background: #dbeafe;
    color: #2563eb;
  }

  &.file-type-excel {
    background: #dcfce7;
    color: #16a34a;
  }

  &.file-type-powerpoint {
    background: #ffedd5;
    color: #ea580c;
  }

  &.file-type-text {
    background: #f3f4f6;
    color: #6b7280;
  }

  &.file-type-archive {
    background: #fff7ed;
    color: #c2410c;
  }
}

.folder-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #409eff;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 4px;
  background: #ecf5ff;
  transition: all 0.2s;

  &:hover {
    background: #d9ecff;
  }

  &.root {
    color: #909399;
    background: #f4f4f5;
    cursor: default;
  }
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.preview-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.preview-file-info {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.preview-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.file-type-icon-lg {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 14px;
}

.preview-meta {
  flex: 1;
  min-width: 0;

  h3 {
    margin: 0 0 8px;
    font-size: 18px;
    color: #303133;
    word-break: break-all;
  }
}

.preview-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: #909399;
}

.preview-content {
  min-height: 420px;
}

.preview-image {
  position: relative;
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  border-radius: 12px;
  overflow: hidden;

  img {
    max-width: 100%;
    max-height: 72vh;
    object-fit: contain;
  }
}

.preview-pdf {
  height: 72vh;
  border-radius: 12px;
  overflow: hidden;
  background: #f8fafc;

  iframe {
    width: 100%;
    height: 100%;
  }
}

.preview-text-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 14px;
  font-weight: 600;
  color: #606266;
}

.preview-no-visual,
.preview-error {
  min-height: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  border-radius: 12px;
  background: #f8fafc;
  color: #909399;
  text-align: center;
}

/* 文件夹上传样式 */
.folder-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f0f7ff, #e8f4f8);
  border-radius: 8px;
  margin-bottom: 16px;
  border: 1px solid #d4e8ff;
  
  .folder-name {
    font-weight: 600;
    font-size: 15px;
    color: #303133;
  }
}

.folder-file-list {
  margin-bottom: 16px;
}

.folder-file-path {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  
  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.status-pending {
  font-size: 12px;
  color: #909399;
}

.folder-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 8px 0;
  
  .el-progress {
    flex: 1;
  }
  
  .progress-text {
    font-size: 13px;
    color: #606266;
    white-space: nowrap;
  }
}

/* 上传目标提示 */
.upload-target-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f0f9eb;
  border-radius: 6px;
  margin-bottom: 14px;
  font-size: 13px;
  color: #67c23a;
  border: 1px solid #e1f3d8;
}

.upload-failed-list {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid #fde2e2;
  border-radius: 8px;
  background: #fff7f7;
}

.upload-failed-title {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #f56c6c;
}

.upload-failed-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 0;
  font-size: 13px;
  border-top: 1px dashed #f8d7da;

  &:first-of-type {
    border-top: none;
  }
}

.upload-failed-name {
  color: #303133;
  word-break: break-all;
}

.upload-failed-reason {
  color: #909399;
  text-align: right;
}

/* 移动文件对话框 */
.move-current {
  margin-bottom: 16px;
  font-size: 14px;
  color: #606266;
}

.move-target {
  .move-hint {
    margin-top: 8px;
    font-size: 12px;
    color: #909399;
  }
}
</style>
