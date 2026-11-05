<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const portal = computed(() => route.path === '/admin/login' ? 'ADMIN' : route.path === '/doctor/login' ? 'DOCTOR' : 'USER')
const portalName = computed(() => portal.value === 'ADMIN' ? '管理员' : portal.value === 'DOCTOR' ? '医生' : '患者')

const form = reactive({
  username: '',
  password: '',
})
const loading = ref(false)

async function submit() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.username.trim(), form.password)
    if (portal.value !== 'USER' && auth.user?.role !== portal.value) {
      auth.logout()
      ElMessage.error(`该账号没有${portalName.value}权限，请使用对应账号登录`)
      return
    }
    ElMessage.success('登录成功')
    const requested = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    const fallback = portal.value === 'ADMIN' ? '/admin/doctors' : portal.value === 'DOCTOR' ? '/doctor' : '/'
    const redirect = requested.startsWith('/') && !requested.startsWith('//') && !requested.split('?')[0].endsWith('/login') ? requested : fallback
    router.replace(redirect)
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card tcm-card">
      <h1 class="auth-title">{{ portalName }}登录</h1>
      <p class="auth-sub">岐黄智诊 · 中医智能诊疗协同平台</p>
      <p v-if="portal !== 'USER'" class="auth-sub">请使用{{ portalName }}账号登录，普通注册账号没有此权限。</p>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            :prefix-icon="Lock"
            @keydown.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" class="auth-btn" :loading="loading" @click="submit">
          登录
        </el-button>
      </el-form>

      <div v-if="portal === 'USER'" class="auth-footer">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
      </div>
      <div class="auth-footer">
        <router-link to="/login">患者登录</router-link> ·
        <router-link to="/doctor/login">医生登录</router-link> ·
        <router-link to="/admin/login">管理员登录</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 16px;
}

.auth-card {
  width: 100%;
  max-width: 400px;
}

.auth-title {
  font-size: 26px;
  margin: 0 0 6px;
  text-align: center;
}

.auth-sub {
  text-align: center;
  color: var(--tcm-text-faint);
  font-size: 13px;
  margin: 0 0 24px;
}

.auth-btn {
  width: 100%;
  margin-top: 8px;
}

.auth-footer {
  margin-top: 18px;
  text-align: center;
  color: var(--tcm-text-dim);
  font-size: 13px;
}
</style>
