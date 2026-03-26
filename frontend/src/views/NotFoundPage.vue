<template>
  <div class="not-found-page">
    <div class="content">
      <h1>404</h1>
      <p>{{ t('notFound.title') }}</p>
      <el-button type="primary" @click="$router.push('/')">{{ t('notFound.backHome') }}</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '@/i18n'

const { t } = useI18n()
</script>

<style scoped>
.not-found-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ds-bg-base);
}

.content {
  text-align: center;
}

.content h1 {
  font-size: 120px;
  color: var(--ds-primary);
  margin: 0;
  line-height: 1;
}

.content p {
  font-size: 24px;
  color: var(--ds-text-secondary);
  margin: 24px 0;
}
</style>
