/**
 * 认证 API
 * 版本: v1.0
 */

import http from './http'
import type { User, LoginRequest, LoginResponse } from '@/types'

export const authApi = {
    /**
     * 用户登录
     */
    async login(data: LoginRequest): Promise<LoginResponse> {
        return http.post('/auth/login', data)
    },

    /**
     * 用户登出
     */
    async logout(): Promise<void> {
        return http.post('/auth/logout')
    },

    /**
     * 获取当前用户信息
     */
    async getMe(): Promise<User> {
        return http.get('/auth/me')
    },

    /**
     * 刷新令牌
     */
    async refresh(refreshToken: string): Promise<LoginResponse> {
        return http.post('/auth/refresh', { refresh_token: refreshToken })
    },

    /**
     * 修改密码
     */
    async changePassword(
        currentPassword: string,
        newPassword: string
    ): Promise<void> {
        return http.put('/auth/password', {
            current_password: currentPassword,
            new_password: newPassword,
        })
    },
}
