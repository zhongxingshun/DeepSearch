/**
 * DeepSearch 路由配置
 * 版本: v1.0
 */

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 路由配置
const routes: RouteRecordRaw[] = [
    {
        path: '/',
        component: () => import('@/layouts/MainLayout.vue'),
        meta: { requiresAuth: true },
        children: [
            {
                path: '',
                name: 'home',
                redirect: '/search',
            },
            {
                path: 'search',
                name: 'search',
                component: () => import('@/views/SearchPage.vue'),
                meta: { title: '搜索' },
            },
            {
                path: 'files',
                name: 'files',
                component: () => import('@/views/FilesPage.vue'),
                meta: { title: '文件管理' },
            },
            {
                path: 'history',
                name: 'history',
                component: () => import('@/views/HistoryPage.vue'),
                meta: { title: '搜索历史' },
            },
            {
                path: 'admin',
                name: 'admin',
                component: () => import('@/views/AdminPage.vue'),
                meta: { title: '系统管理', requiresAdmin: true },
                children: [
                    {
                        path: '',
                        redirect: '/admin/users',
                    },
                    {
                        path: 'users',
                        name: 'admin-users',
                        component: () => import('@/views/admin/UsersPage.vue'),
                        meta: { title: '用户管理' },
                    },
                    {
                        path: 'stats',
                        name: 'admin-stats',
                        component: () => import('@/views/admin/StatsPage.vue'),
                        meta: { title: '系统统计' },
                    },
                    {
                        path: 'logs',
                        name: 'admin-logs',
                        component: () => import('@/views/admin/LogsPage.vue'),
                        meta: { title: '审计日志' },
                    },
                    {
                        path: 'settings',
                        name: 'admin-settings',
                        component: () => import('@/views/admin/SettingsPage.vue'),
                        meta: { title: '系统设置' },
                    },
                ],
            },
            {
                path: 'profile',
                name: 'profile',
                component: () => import('@/views/ProfilePage.vue'),
                meta: { title: '个人中心' },
            },
        ],
    },
    {
        path: '/login',
        name: 'login',
        component: () => import('@/views/LoginPage.vue'),
        meta: { title: '登录' },
    },
    {
        path: '/:pathMatch(.*)*',
        name: 'not-found',
        component: () => import('@/views/NotFoundPage.vue'),
        meta: { title: '页面未找到' },
    },
]

// 创建路由
const router = createRouter({
    history: createWebHistory(),
    routes,
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
    // 设置页面标题
    const title = to.meta.title as string
    document.title = title ? `${title} - DeepSearch` : 'DeepSearch'

    const authStore = useAuthStore()

    // 检查是否需要认证
    if (to.meta.requiresAuth) {
        if (!authStore.isAuthenticated) {
            // 尝试从 localStorage 恢复登录状态
            const token = localStorage.getItem('token')
            if (token) {
                try {
                    await authStore.fetchUser()
                } catch {
                    return next({ name: 'login', query: { redirect: to.fullPath } })
                }
            } else {
                return next({ name: 'login', query: { redirect: to.fullPath } })
            }
        }

        // 检查是否需要管理员权限
        if (to.meta.requiresAdmin && !['admin', 'super_admin'].includes(authStore.user?.role || '')) {
            return next({ name: 'home' })
        }
    }

    // 已登录用户访问登录页，重定向到首页
    if (to.name === 'login' && authStore.isAuthenticated) {
        return next({ name: 'home' })
    }

    next()
})

export default router
