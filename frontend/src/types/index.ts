/**
 * TypeScript 类型定义
 * 版本: v1.0
 */

// ============================================
// 用户相关
// ============================================

export interface User {
    id: number
    username: string
    email: string
    role: 'super_admin' | 'admin' | 'user'
    is_active: boolean
    created_at: string
    updated_at: string
}

export interface LoginRequest {
    username: string
    password: string
}

export interface LoginResponse {
    access_token: string
    refresh_token: string
    token_type: string
}

// ============================================
// 文件相关
// ============================================

export interface FileItem {
    id: number
    filename: string
    file_path: string
    folder_path?: string
    display_name?: string
    uploaded_by: number | null
    file_size: number
    file_size_human: string
    file_type: 'pdf' | 'word' | 'excel' | 'powerpoint' | 'text' | 'image' | 'archive' | 'other' | string
    source_url?: string | null
    md5_hash: string | null
    index_status: 'pending' | 'processing' | 'completed' | 'failed'
    created_at: string
    updated_at: string
}

export interface FileResponse extends FileItem { }

export interface FileListResponse {
    success: boolean
    data: FileItem[]
    total: number
    page: number
    page_size: number
}

export interface FileUploadResponse {
    success: boolean
    message: string
    file_id: number
    filename: string
    md5_hash: string
    is_duplicate: boolean
    task_id: string | null
}

// ============================================
// 搜索相关
// ============================================

export interface SearchHighlight {
    field: string
    snippet: string
}

export interface SearchResult {
    id: string
    file_id: number
    filename: string
    file_type: 'pdf' | 'word' | 'excel' | 'powerpoint' | 'text' | 'image' | 'archive' | 'other' | string
    file_size: number
    file_path: string
    content_snippet: string
    score: number
    highlights: SearchHighlight[]
    created_at: string | null
}

export interface SearchResponse {
    success: boolean
    keyword: string
    results: SearchResult[]
    total: number
    page: number
    page_size: number
    total_pages: number
    query_time_ms: number
}

export interface SearchHistoryItem {
    id: number
    keyword: string
    result_count: number
    created_at: string
}

export interface SearchHistoryResponse {
    success: boolean
    data: SearchHistoryItem[]
    total: number
}

// ============================================
// 通用
// ============================================

export interface PaginationParams {
    page?: number
    page_size?: number
}

export interface ApiResponse<T = any> {
    success: boolean
    message?: string
    data?: T
}

// ============================================
// 管理后台
// ============================================

export interface AuditLog {
    id: number
    user_id: number
    action: string
    resource_type: string
    resource_id: number | null
    details: Record<string, any>
    ip_address: string
    created_at: string
}

export interface SystemStats {
    total_files: number
    total_size: number
    total_size_human: string
    by_status: Record<string, number>
    by_type: Record<string, number>
}
