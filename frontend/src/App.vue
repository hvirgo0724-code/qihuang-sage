<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'

const route = useRoute()
const showHeader = computed(() => !route.meta.hideHeader)
</script>

<template>
  <div class="app-shell">
    <AppHeader v-if="showHeader" />
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-main {
  min-height: calc(100vh - 64px);
}
</style>