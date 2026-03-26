<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { elementLocale } from '@/i18n'
</script>

<style>
#app {
  height: 100vh;
}
</style>
