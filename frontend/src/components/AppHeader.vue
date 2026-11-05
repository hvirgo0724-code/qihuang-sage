<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { Menu, ArrowDown, UserFilled, SwitchButton } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const { user, isAdmin, isLoggedIn } = storeToRefs(auth)

const menuOpen = ref(false)

interface NavItem {
  path: string
  label: string
  requiresAuth?: boolean
  admin?: boolean
}

const navItems = computed<NavItem[]>(() => {
  if (user.value?.role === 'DOCTOR') return [{ path: '/doctor', label: '医生工作台' }, { path: '/knowledge', label: '知识库' }]
  const items: NavItem[] = [
    { path: '/patient', label: '患者中心' },
    { path: '/consult/start', label: '开始问诊', requiresAuth: true },
    { path: '/history', label: '历史问诊', requiresAuth: true },
    { path: '/knowledge', label: '知识库' },
  ]
  if (isAdmin.value) items.push({ path: '/admin', label: '管理后台', admin: true })
  return items
})

function isActive(path: string): boolean {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function onSelect(path: string) {
  menuOpen.value = false
  router.push(path)
}

function logout() {
  auth.logout()
  router.push('/')
}

function goLogin() {
  router.push('/login')
}

const displayName = computed(() => user.value?.nickname || user.value?.username || '未登录')
</script>

<template>
  <header class="app-header">
    <div class="header-inner">
      <a class="brand" href="/" @click.prevent="router.push('/')">
        <div class="brand-mark">岐</div>
        <div class="brand-text">
          <span class="brand-name">岐黄智诊</span>
          <span class="brand-sub">Qihuang Sage</span>
        </div>
      </a>

      <nav class="nav desktop">
        <a
          v-for="item in navItems"
          :key="item.path"
          :href="item.path"
          :aria-current="isActive(item.path) ? 'page' : undefined"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          @click.prevent="onSelect(item.path)"
        >
          {{ item.label }}
        </a>
      </nav>

      <div class="header-right">
        <template v-if="isLoggedIn">
          <el-dropdown trigger="click">
            <span class="user-chip">
              <el-icon><UserFilled /></el-icon>
              <el-tag size="small" effect="plain">{{ user?.role === 'DOCTOR' ? '医生' : user?.role === 'ADMIN' ? '管理员' : '患者' }}</el-tag>
              <span class="user-name">{{ displayName }}</span>
              <el-icon class="arrow"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="onSelect('/profile')">个人中心</el-dropdown-item>
                <el-dropdown-item divided @click="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button size="small" text @click="onSelect('/login')">登录</el-button>
          <el-button size="small" type="primary" @click="onSelect('/register')">注册</el-button>
        </template>

        <el-dropdown class="mobile-menu" trigger="click" @command="onSelect">
          <el-button size="small" :icon="Menu" circle />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="item in navItems"
                :key="item.path"
                :command="item.path"
              >
                {{ item.label }}
              </el-dropdown-item>
              <el-dropdown-item v-if="isLoggedIn" command="/profile">个人中心</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--tcm-border-soft);
}

.header-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 20px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex-shrink: 0;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--tcm-primary), var(--tcm-primary-deep));
  color: #ffffff;
  font-weight: 700;
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(8, 127, 117, 0.15);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.1;
}

.brand-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--tcm-text);
  letter-spacing: 1px;
}

.brand-sub {
  font-size: 11px;
  color: var(--tcm-gold);
  letter-spacing: 1px;
}

.nav {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  justify-content: center;
}

.nav-item {
  padding: 8px 16px;
  border-radius: 8px;
  color: var(--tcm-text-dim);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.nav-item:hover {
  color: var(--tcm-text);
  background: var(--tcm-panel);
}

.nav-item.active {
  color: var(--tcm-primary);
  background: rgba(43, 179, 163, 0.12);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--tcm-text);
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--tcm-border-soft);
  outline: none;
}

.user-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.arrow {
  color: var(--tcm-text-faint);
  font-size: 12px;
}

.mobile-menu {
  display: none;
}

@media (max-width: 900px) {
  .nav.desktop {
    display: none;
  }
  .mobile-menu {
    display: inline-flex;
  }
}
</style>