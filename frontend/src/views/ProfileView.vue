<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import { getProfile, updateProfile, deleteMyData } from '@/api/modules'
import type { UserProfile } from '@/types'
import MemoryPanel from '@/components/MemoryPanel.vue'

const router = useRouter()
const auth = useAuthStore()
const { user } = storeToRefs(auth)

const form = reactive({
  height: null as number | null,
  weight: null as number | null,
  allergies: '',
  chronic_diseases: '',
  medication_history: '',
  remark: '',
})
const profileLoading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const memoryPanel = ref<InstanceType<typeof MemoryPanel>>()

function fillForm(p: UserProfile) {
  form.height = p.height
  form.weight = p.weight
  form.allergies = p.allergies ?? ''
  form.chronic_diseases = p.chronic_diseases ?? ''
  form.medication_history = p.medication_history ?? ''
  form.remark = p.remark ?? ''
}

function currentPayload() {
  return {
    height: form.height,
    weight: form.weight,
    allergies: form.allergies.trim() || null,
    chronic_diseases: form.chronic_diseases.trim() || null,
    medication_history: form.medication_history.trim() || null,
    remark: form.remark.trim() || null,
  }
}

async function save() {
  saving.value = true
  try {
    const p = await updateProfile(currentPayload())
    fillForm(p)
    ElMessage.success('健康画像已保存')
    await memoryPanel.value?.refresh()
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    saving.value = false
  }
}

async function confirmDelete() {
  try {
    await ElMessageBox.confirm(
      '将清除健康画像、问诊记录、报告和长短期记忆，且不可恢复。账号、密码及登录能力保留。确定继续吗？',
      '清除我的健康数据',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  deleting.value = true
  try {
    await deleteMyData()
    ElMessage.success('健康数据已清除，账号保留')
    fillForm(await getProfile())
    await memoryPanel.value?.refresh()
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  profileLoading.value = true
  try {
    const p = await getProfile()
    fillForm(p)
  } catch {
    // 无画像记录时留空表单，不做额外提示
  } finally {
    profileLoading.value = false
  }
})
</script>

<template>
  <div class="profile-view">
    <h1 class="page-title">个人中心</h1>

    <div class="profile-grid">
      <div class="profile-left">
        <div class="tcm-card">
          <h2 class="card-title">账号信息</h2>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="用户名">{{ user?.username }}</el-descriptions-item>
            <el-descriptions-item label="昵称">{{ user?.nickname || '—' }}</el-descriptions-item>
            <el-descriptions-item label="角色">
              {{ user?.role === 'ADMIN' ? '管理员' : user?.role === 'DOCTOR' ? '医生' : '患者' }}
            </el-descriptions-item>
            <el-descriptions-item label="性别">{{ user?.gender || '—' }}</el-descriptions-item>
            <el-descriptions-item label="年龄">{{ user?.age ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="数据授权时间">
              {{ user?.data_consent_at ? new Date(user.data_consent_at).toLocaleString() : '未授权' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <div class="tcm-card danger-card">
          <h2 class="card-title danger">数据权利</h2>
          <p class="danger-desc">
            清除健康画像、问诊记录、报告及长短期记忆。保留账号、密码和登录状态。
          </p>
          <el-button type="danger" plain :loading="deleting" @click="confirmDelete">
            清除我的健康数据
          </el-button>
        </div>
      </div>

      <div class="tcm-card profile-right">
        <h2 class="card-title">健康画像</h2>
        <p class="card-sub">以下健康信息将用于辨证时检索个性化禁忌，字段将加密存储。</p>

        <el-form label-position="top" v-loading="profileLoading">
          <div class="form-row">
            <el-form-item label="身高 (cm)" class="form-half">
              <el-input-number v-model="form.height" :min="0" :max="260" controls-position="right" placeholder="选填" />
            </el-form-item>
            <el-form-item label="体重 (kg)" class="form-half">
              <el-input-number v-model="form.weight" :min="0" :max="400" controls-position="right" placeholder="选填" />
            </el-form-item>
          </div>
          <el-form-item label="过敏史">
            <el-input v-model="form.allergies" type="textarea" :rows="2" placeholder="药物、食物过敏等（选填）" />
          </el-form-item>
          <el-form-item label="慢性病史">
            <el-input v-model="form.chronic_diseases" type="textarea" :rows="2" placeholder="高血压、糖尿病等（选填）" />
          </el-form-item>
          <el-form-item label="用药史">
            <el-input v-model="form.medication_history" type="textarea" :rows="2" placeholder="长期服用的药物等（选填）" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="其他需要说明的健康情况（选填）" />
          </el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存健康画像</el-button>
        </el-form>
      </div>
    </div>
    <MemoryPanel ref="memoryPanel" />
  </div>
</template>

<style scoped>
.page-title {
  font-size: 24px;
  margin: 0 0 20px;
}

.profile-grid {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  align-items: start;
}

.profile-left {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-title {
  font-size: 16px;
  margin: 0 0 16px;
}

.card-title.danger {
  color: var(--tcm-danger);
}

.card-sub {
  color: var(--tcm-text-faint);
  font-size: 12px;
  margin: 0 0 18px;
}

.danger-card {
  border-color: rgba(200, 81, 63, 0.4);
}

.danger-desc {
  color: var(--tcm-text-dim);
  font-size: 13px;
  line-height: 1.7;
  margin: 0 0 16px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-half {
  flex: 1;
}

.form-half :deep(.el-input-number) {
  width: 100%;
}

@media (max-width: 900px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
}
</style>
