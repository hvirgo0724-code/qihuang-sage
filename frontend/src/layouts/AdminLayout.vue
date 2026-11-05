<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { DataAnalysis, Monitor } from '@element-plus/icons-vue'

const route = useRoute()

const active = computed(() => route.path)
</script>

<template>
  <div class="admin-layout">
    <aside class="admin-side">
      <div class="admin-side-title">管理控制台</div>
      <el-menu :default-active="active" router class="admin-menu">
        <el-menu-item index="/admin">
          <el-icon><DataAnalysis /></el-icon>
          <span>管理后台</span>
        </el-menu-item>
        <el-menu-item index="/admin/doctors">医生账号</el-menu-item>
        <el-menu-item index="/admin/monitor">
          <el-icon><Monitor /></el-icon>
          <span>监控大盘</span>
        </el-menu-item>
      </el-menu>
    </aside>
    <section class="admin-content">
      <router-view />
    </section>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.admin-side {
  width: 200px;
  flex-shrink: 0;
  background: var(--tcm-card);
  border: 1px solid var(--tcm-border-soft);
  border-radius: var(--tcm-radius);
  overflow: hidden;
  position: sticky;
  top: 84px;
}

.admin-side-title {
  padding: 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--tcm-text);
  border-bottom: 1px solid var(--tcm-border-soft);
}

.admin-menu {
  border-right: none;
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-hover-bg-color: rgba(43, 179, 163, 0.12);
  --el-menu-active-color: var(--tcm-primary);
}

.admin-content {
  flex: 1;
  min-width: 0;
}

@media (max-width: 900px) {
  .admin-layout {
    flex-direction: column;
  }
  .admin-side {
    width: 100%;
    position: static;
  }
}
</style>