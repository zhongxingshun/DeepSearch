/**
 * 文件 API
 * 版本: v1.0
 */

import http from './http'
import type {
    FileListResponse,
    FileResponse,
    FileShareLinkResponse,
    PaginationParams,
} from '@/types'

export interface FileListParams extends PaginationParams {
    file_type?: string
    status?: string
    keyword?: string
    folder?: string
}

export const fileApi = {
    /**
     * 获取文件列表
     */
    async getFiles(params?: FileListParams): Promise<FileListResponse> {
        return http.get('/files/', { params })
    },

    /**
     * 获取文件详情
     */
    async getFile(id: number): Promise<FileResponse> {
        return http.get(`/files/${id}`)
    },

    /**
     * 获取文件分享短链接
     */
    async getShareLink(id: number, ensure = false): Promise<FileShareLinkResponse> {
        return http.get(`/files/${id}/share-link`, { params: { ensure } })
    },

    /**
     * 创建或刷新文件分享短链接
     */
    async createShareLink(
        id: number,
        payload?: { expires_in_hours?: number; max_downloads?: number | null },
    ): Promise<FileShareLinkResponse> {
        return http.post(`/files/${id}/share-link`, payload || {})
    },

    /**
     * 更新文件源链接
     */
    async updateSourceUrl(id: number, sourceUrl: string | null): Promise<any> {
        return http.put(`/files/${id}/source-url`, { source_url: sourceUrl })
    },

    /**
     * 上传单个文件
     */
    async uploadFile(file: File, onProgress?: (percent: number) => void, folderPath?: string): Promise<any> {
        const formData = new FormData()
        formData.append('file', file)
        if (folderPath) {
            formData.append('folder_path', folderPath)
        }

        return http.post('/files/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            onUploadProgress: (event) => {
                if (event.total && onProgress) {
                    onProgress(Math.round((event.loaded * 100) / event.total))
                }
            },
        })
    },

    /**
     * 批量上传文件
     */
    async uploadFiles(files: File[]): Promise<any> {
        const formData = new FormData()
        files.forEach((file) => {
            formData.append('files', file)
        })

        return http.post('/files/upload/batch', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
        })
    },

    /**
     * 获取文件下载链接
     */
    getDownloadUrl(id: number): string {
        const token = localStorage.getItem('token')
        return `/api/v1/files/${id}/download?token=${token}`
    },

    /**
     * 获取文件预览链接（内联显示）
     */
    getPreviewUrl(id: number): string {
        const token = localStorage.getItem('token')
        return `/api/v1/files/${id}/preview?token=${token}`
    },

    /**
     * 获取文件状态
     */
    async getFileStatus(id: number): Promise<any> {
        return http.get(`/files/${id}/status`)
    },

    /**
     * 删除文件
     */
    async deleteFile(id: number): Promise<void> {
        return http.delete(`/files/${id}`)
    },

    /**
     * 批量删除文件
     */
    async batchDeleteFiles(fileIds: number[]): Promise<any> {
        return http.post('/files/batch-delete', { file_ids: fileIds })
    },

    /**
     * 获取文件统计
     */
    async getStats(): Promise<any> {
        return http.get('/files/stats/overview')
    },

    /**
     * 重试解析失败的文件
     */
    async retryFile(id: number): Promise<any> {
        return http.post(`/files/${id}/retry`)
    },

    /**
     * 重试所有失败的文件
     */
    async retryAllFailed(): Promise<any> {
        return http.post('/files/retry-all-failed')
    },

    /**
     * 获取文件夹列表
     */
    async getFolders(parent?: string): Promise<any> {
        return http.get('/files/folders/tree', { params: parent ? { parent } : {} })
    },

    /**
     * 创建文件夹
     */
    async createFolder(path: string): Promise<any> {
        return http.post('/files/folders', { path })
    },

    /**
     * 重命名文件夹
     */
    async renameFolder(path: string, newName: string): Promise<any> {
        return http.put('/files/folders/rename', { path, new_name: newName })
    },

    /**
     * 删除文件夹
     */
    async deleteFolder(path: string): Promise<any> {
        return http.delete('/files/folders', { params: { path } })
    },

    /**
     * 获取删除文件夹影响范围
     */
    async getFolderDeleteSummary(path: string): Promise<any> {
        return http.get('/files/folders/delete-summary', { params: { path } })
    },

    /**
     * 移动文件到指定文件夹
     */
    async moveFile(id: number, targetFolder: string): Promise<any> {
        return http.put(`/files/${id}/move`, { target_folder: targetFolder })
    },

    /**
     * 重命名文件
     */
    async renameFile(id: number, filename: string): Promise<any> {
        return http.put(`/files/${id}/rename`, { filename })
    },
}
