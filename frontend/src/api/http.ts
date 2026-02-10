/**
 * Axios HTTP 客户端封装
 * 版本: v1.0
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

// 创建 axios 实例
const http = axios.create({
    baseURL: '/api/v1',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// 请求拦截器
http.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error: AxiosError) => {
        return Promise.reject(error)
    }
)

// 响应拦截器
http.interceptors.response.use(
    (response) => {
        return response.data
    },
    async (error: AxiosError<{ detail?: string; message?: string }>) => {
        const { response } = error

        if (!response) {
            ElMessage.error('网络连接失败，请检查网络')
            return Promise.reject(error)
        }

        const { status, data } = response
        const message = data?.detail || data?.message || '请求失败'

        switch (status) {
            case 401:
                // 尝试刷新令牌
                const authStore = useAuthStore()
                const refreshed = await authStore.refreshAccessToken()

                if (refreshed && error.config) {
                    // 重试请求
                    return http(error.config)
                } else {
                    authStore.clearAuth()
                    router.push({ name: 'login' })
                    ElMessage.error('登录已过期，请重新登录')
                }
                break

            case 403:
                ElMessage.error('没有权限执行此操作')
                break

            case 404:
                ElMessage.error('请求的资源不存在')
                break

            case 422:
                ElMessage.error(message || '请求参数错误')
                break

            case 500:
                ElMessage.error('服务器内部错误')
                break

            default:
                ElMessage.error(message)
        }

        return Promise.reject(error)
    }
)

export default http
