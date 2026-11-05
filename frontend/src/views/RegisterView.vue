<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Postcard } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({
  username: '',
  password: '',
  confirm: '',
  nickname: '',
  gender: '' as string,
  age: undefined as number | undefined,
  consent: false,
})
const loading = ref(false)

async function submit() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (form.password.length < 6) {
    ElMessage.warning('密码长度至少 6 位')
    return
  }
  if (form.password !== form.confirm) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  if (!form.consent) {
    ElMessage.warning('请先勾选并同意健康数据授权')
    return
  }
  loading.value = true
  try {
    await auth.registerAccount({
      username: form.username.trim(),
      password: form.password,
      nickname: form.nickname.trim() || undefined,
      gender: form.gender || undefined,
      age: form.age,
      consent: form.consent,
    })
    ElMessage.success('注册成功')
    router.push('/')
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
      <h1 class="auth-title">注册账号</h1>
      <p class="auth-sub">岐黄智诊 · 中医智能诊疗协同平台</p>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="至少 6 位密码"
            :prefix-icon="Lock"
          />
        </el-form-item>
        <el-form-item label="确认密码" required>
          <el-input
            v-model="form.confirm"
            type="password"
            show-password
            placeholder="再次输入密码"
            :prefix-icon="Lock"
            @keydown.enter="submit"
          />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="选填" :prefix-icon="Postcard" />
        </el-form-item>
        <div class="form-row">
          <el-form-item label="性别" class="form-half">
            <el-select v-model="form.gender" placeholder="选填" clearable>
              <el-option label="男" value="男" />
              <el-option label="女" value="女" />
              <el-option label="其他" value="其他" />
            </el-select>
          </el-form-item>
          <el-form-item label="年龄" class="form-half">
            <el-input-number v-model="form.age" :min="1" :max="120" placeholder="选填" controls-position="right" />
          </el-form-item>
        </div>

        <el-checkbox v-model="form.consent" class="consent">
          <span>
            我已阅读并<strong>同意</strong>收集我的健康相关数据（舌象/面色图片、健康画像），仅用于提供更准确的辨证与调养建议，并授权对其进行加密存储与数据权利管理。
          </span>
        </el-checkbox>

        <el-button type="primary" class="auth-btn" :loading="loading" :disabled="!form.consent" @click="submit">
          注册并登录
        </el-button>
      </el-form>

      <div class="auth-footer">
        已有账号？
        <router-link to="/login">去登录</router-link>
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
  max-width: 440px;
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

.form-row {
  display: flex;
  gap: 12px;
}

.form-half {
  flex: 1;
}

.form-half :deep(.el-select),
.form-half :deep(.el-input-number) {
  width: 100%;
}

.consent {
  margin: 8px 0 16px;
  align-items: flex-start;
  line-height: 1.6;
  font-size: 13px;
  color: var(--tcm-text-dim);
  white-space: normal;
}

.consent :deep(.el-checkbox__label) {
  white-space: normal;
}

.auth-btn {
  width: 100%;
}

.auth-footer {
  margin-top: 18px;
  text-align: center;
  color: var(--tcm-text-dim);
  font-size: 13px;
}
</style>