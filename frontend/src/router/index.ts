/**
 * DeepSearch 路由配置
 * 版本: v1.0
 */

import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { t } from '@/i18n'

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
                meta: { titleKey: 'route.search' },
            },
            {
                path: 'files',
                name: 'files',
                component: () => import('@/views/FilesPage.vue'),
                meta: { titleKey: 'route.files' },
            },
            {
                path: 'history',
                name: 'history',
                component: () => import('@/views/HistoryPage.vue'),
                meta: { titleKey: 'route.history' },
            },
            {
                path: 'admin',
                name: 'admin',
                component: () => import('@/views/AdminPage.vue'),
                meta: { titleKey: 'route.admin', requiresAdmin: true },
                children: [
                    {
                        path: '',
                        redirect: '/admin/users',
                    },
                    {
                        path: 'users',
                        name: 'admin-users',
                        component: () => import('@/views/admin/UsersPage.vue'),
                        meta: { titleKey: 'route.adminUsers' },
                    },
                    {
                        path: 'stats',
                        name: 'admin-stats',
                        component: () => import('@/views/admin/StatsPage.vue'),
                        meta: { titleKey: 'route.adminStats' },
                    },
                    {
                        path: 'logs',
                        name: 'admin-logs',
                        component: () => import('@/views/admin/LogsPage.vue'),
                        meta: { titleKey: 'route.adminLogs' },
                    },
                    {
                        path: 'settings',
                        name: 'admin-settings',
                        component: () => import('@/views/admin/SettingsPage.vue'),
                        meta: { titleKey: 'route.adminSettings' },
                    },
                ],
            },
            {
                path: 'profile',
                name: 'profile',
                component: () => import('@/views/ProfilePage.vue'),
                meta: { titleKey: 'route.profile' },
            },
        ],
    },
    {
        path: '/login',
        name: 'login',
        component: () => import('@/views/LoginPage.vue'),
        meta: { titleKey: 'route.login' },
    },
    {
        path: '/:pathMatch(.*)*',
        name: 'not-found',
        component: () => import('@/views/NotFoundPage.vue'),
        meta: { titleKey: 'route.notFound' },
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
    const titleKey = to.meta.titleKey as string | undefined
    const title = titleKey ? t(titleKey) : ''
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
