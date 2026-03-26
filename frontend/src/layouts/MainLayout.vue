<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo" @click="$router.push('/')">
        <el-icon :size="28"><Search /></el-icon>
        <span v-if="!isCollapsed" class="logo-text">DeepSearch</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :collapse-transition="false"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/search">
          <el-icon><Search /></el-icon>
          <template #title>{{ t('route.search') }}</template>
        </el-menu-item>
        
        <el-menu-item index="/files">
          <el-icon><Folder /></el-icon>
          <template #title>{{ t('route.files') }}</template>
        </el-menu-item>
        
        <el-menu-item index="/history">
          <el-icon><Clock /></el-icon>
          <template #title>{{ t('route.history') }}</template>
        </el-menu-item>
        
        <el-divider v-if="isAdmin" />
        
        <el-sub-menu v-if="isAdmin" index="/admin">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>{{ t('layout.systemManagement') }}</span>
          </template>
          <el-menu-item index="/admin/users">{{ t('layout.userManagement') }}</el-menu-item>
          <el-menu-item index="/admin/stats">{{ t('layout.systemStats') }}</el-menu-item>
          <el-menu-item index="/admin/logs">{{ t('layout.auditLogs') }}</el-menu-item>
          <el-menu-item index="/admin/settings">{{ t('layout.systemSettings') }}</el-menu-item>
        </el-sub-menu>
      </el-menu>
      
      <!-- 折叠按钮 -->
      <div class="collapse-btn" @click="isCollapsed = !isCollapsed">
        <el-icon :size="18">
          <component :is="isCollapsed ? 'Expand' : 'Fold'" />
        </el-icon>
      </div>
    </el-aside>
    
    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶部栏 -->
      <el-header class="header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">{{ t('route.home') }}</el-breadcrumb-item>
            <el-breadcrumb-item v-if="routeTitle">
              {{ routeTitle }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-select
            v-model="locale"
            class="language-switcher"
            size="small"
            @change="handleLocaleChange"
          >
            <el-option value="zh-CN" :label="t('common.chinese')" />
            <el-option value="en-US" :label="t('common.english')" />
          </el-select>
          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  {{ t('layout.profile') }}
                </el-dropdown-item>
                <el-dropdown-item command="password">
                  <el-icon><Key /></el-icon>
                  {{ t('layout.changePassword') }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  {{ t('layout.logout') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <!-- 主内容 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessageBox } from 'element-plus'
import { useI18n } from '@/i18n'
import {
  Search, Folder, Clock, Setting, UserFilled,
  ArrowDown, User, Key, SwitchButton, Expand, Fold,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { locale, setLocale, t } = useI18n()

const isCollapsed = ref(false)
const activeMenu = computed(() => route.path)
const username = computed(() => authStore.username)
const isAdmin = computed(() => authStore.isAdmin)
const routeTitle = computed(() => {
  const titleKey = route.meta.titleKey as string | undefined
  return titleKey ? t(titleKey) : ''
})

watch(
  () => [route.fullPath, locale.value],
  () => {
    document.title = routeTitle.value ? `${routeTitle.value} - DeepSearch` : 'DeepSearch'
  },
  { immediate: true }
)

const handleLocaleChange = (value: 'zh-CN' | 'en-US') => {
  setLocale(value)
}

const handleCommand = async (command: string) => {
  switch (command) {
    case 'profile':
      router.push('/profile')
      break
    case 'password':
      router.push('/profile?tab=password')
      break
    case 'logout':
      await ElMessageBox.confirm(t('layout.confirmLogout'), t('layout.confirmTitle'), {
        confirmButtonText: t('common.ok'),
        cancelButtonText: t('common.cancel'),
        type: 'warning',
      })
      await authStore.logout()
      router.push('/login')
      break
  }
}
</script>

<style lang="scss" scoped>
.main-layout {
  height: 100vh;
}

.sidebar {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  transition: width 0.3s;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  cursor: pointer;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  
  .logo-text {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 1px;
  }
}

.sidebar-menu {
  flex: 1;
  border: none;
  background: transparent;
  
  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    color: rgba(255, 255, 255, 0.75);
    
    &:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }
  }
  
  :deep(.el-menu-item.is-active) {
    background: rgba(64, 158, 255, 0.2);
    color: #409eff;
    border-right: 3px solid #409eff;
  }

  // 子菜单展开区域
  :deep(.el-sub-menu .el-menu) {
    background: rgba(0, 0, 0, 0.2) !important;
  }

  :deep(.el-sub-menu .el-menu .el-menu-item) {
    color: rgba(255, 255, 255, 0.65);
    background: transparent;
    padding-left: 54px !important;

    &:hover {
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
    }

    &.is-active {
      background: rgba(64, 158, 255, 0.2);
      color: #409eff;
    }
  }
}

.collapse-btn {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  
  &:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.05);
  }
}

.main-container {
  background: var(--ds-bg-base);
}

.header {
  height: 60px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.language-switcher {
  width: 120px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  
  &:hover {
    background: var(--ds-bg-base);
  }
  
  .username {
    color: var(--ds-text-primary);
    font-weight: 500;
  }
}

.main-content {
  padding: 0;
  overflow: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
