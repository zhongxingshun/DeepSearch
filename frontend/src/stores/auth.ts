/**
 * 认证状态管理
 * 版本: v1.0
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User, LoginRequest, LoginResponse } from '@/types'

export const useAuthStore = defineStore('auth', () => {
    // 状态
    const user = ref<User | null>(null)
    const token = ref<string | null>(localStorage.getItem('token'))
    const refreshToken = ref<string | null>(localStorage.getItem('refreshToken'))
    const loading = ref(false)

    // 计算属性
    const isAuthenticated = computed(() => !!token.value && !!user.value)
    const isAdmin = computed(() => ['admin', 'super_admin'].includes(user.value?.role || ''))
    const isSuperAdmin = computed(() => user.value?.role === 'super_admin')
    const username = computed(() => user.value?.username || '')

    // 登录
    async function login(credentials: LoginRequest): Promise<void> {
        loading.value = true
        try {
            const response = await authApi.login(credentials)
            setTokens(response)
            await fetchUser()
        } finally {
            loading.value = false
        }
    }

    // 登出
    async function logout(): Promise<void> {
        try {
            await authApi.logout()
        } catch {
            // 忽略登出错误
        } finally {
            clearAuth()
        }
    }

    // 获取用户信息
    async function fetchUser(): Promise<void> {
        if (!token.value) return

        try {
            const userData = await authApi.getMe()
            user.value = userData
        } catch (error) {
            clearAuth()
            throw error
        }
    }

    // 刷新令牌
    async function refreshAccessToken(): Promise<boolean> {
        if (!refreshToken.value) return false

        try {
            const response = await authApi.refresh(refreshToken.value)
            setTokens(response)
            return true
        } catch {
            clearAuth()
            return false
        }
    }

    // 修改密码
    async function changePassword(
        currentPassword: string,
        newPassword: string
    ): Promise<void> {
        await authApi.changePassword(currentPassword, newPassword)
    }

    // 设置令牌
    function setTokens(response: LoginResponse): void {
        token.value = response.access_token
        refreshToken.value = response.refresh_token
        localStorage.setItem('token', response.access_token)
        localStorage.setItem('refreshToken', response.refresh_token)
    }

    // 清除认证状态
    function clearAuth(): void {
        user.value = null
        token.value = null
        refreshToken.value = null
        localStorage.removeItem('token')
        localStorage.removeItem('refreshToken')
    }

    return {
        // 状态
        user,
        token,
        loading,
        // 计算属性
        isAuthenticated,
        isAdmin,
        isSuperAdmin,
        username,
        // 方法
        login,
        logout,
        fetchUser,
        refreshAccessToken,
        changePassword,
        clearAuth,
    }
})
