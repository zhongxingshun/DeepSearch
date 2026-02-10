/**
 * 文件 API
 * 版本: v1.0
 */

import http from './http'
import type { FileListResponse, FileResponse, PaginationParams } from '@/types'

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
     * 移动文件到指定文件夹
     */
    async moveFile(id: number, targetFolder: string): Promise<any> {
        return http.put(`/files/${id}/move`, { target_folder: targetFolder })
    },
}
