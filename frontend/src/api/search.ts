/**
 * 搜索 API
 * 版本: v1.0
 */

import http from './http'
import type { SearchResponse, SearchHistoryResponse, PaginationParams } from '@/types'

export interface SearchParams extends PaginationParams {
    q: string
    file_type?: string
    sort_by?: string
    sort_order?: 'asc' | 'desc'
}

export const searchApi = {
    /**
     * 全文搜索
     */
    async search(params: SearchParams): Promise<SearchResponse> {
        return http.get('/search', { params })
    },

    /**
     * 获取搜索建议
     */
    async suggest(q: string, limit = 5): Promise<{ suggestions: string[] }> {
        return http.post('/search/suggest', null, { params: { q, limit } })
    },

    /**
     * 获取文档详情
     */
    async getDocument(docId: string): Promise<any> {
        return http.get(`/search/${docId}`)
    },

    /**
     * 获取搜索历史
     */
    async getHistory(params?: PaginationParams): Promise<SearchHistoryResponse> {
        return http.get('/history', { params })
    },

    /**
     * 获取最近搜索
     */
    async getRecentHistory(limit = 10): Promise<{ data: any[] }> {
        return http.get('/history/recent', { params: { limit } })
    },

    /**
     * 获取热门关键词
     */
    async getPopularKeywords(limit = 10): Promise<{ data: any[] }> {
        return http.get('/history/popular', { params: { limit } })
    },

    /**
     * 删除搜索历史
     */
    async deleteHistory(id: number): Promise<void> {
        return http.delete(`/history/${id}`)
    },

    /**
     * 清空搜索历史
     */
    async clearHistory(): Promise<void> {
        return http.delete('/history/')
    },
}
