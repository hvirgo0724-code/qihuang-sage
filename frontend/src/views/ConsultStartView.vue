<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { createSession } from '@/api/modules'
import { useConsultStore } from '@/stores/consult'
import DisclaimerBar from '@/components/DisclaimerBar.vue'

const router = useRouter()
const consult = useConsultStore()

const complaint = ref('')
const loading = ref(false)

async function start() {
  loading.value = true
  try {
    const resp = await createSession(complaint.value.trim())
    consult.setSession(resp.session_id, resp.trace_id, complaint.value.trim())
    router.push(`/consult/${resp.session_id}`)
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="consult-start">
    <div class="start-card tcm-card">
      <h1 class="start-title">开始问诊</h1>
      <p class="start-sub">
        请先简要描述您的不适主诉（可选），随后进入四诊问诊界面：上传舌象/面色图片并进行智能对话。
      </p>

      <el-input
        v-model="complaint"
        type="textarea"
        :rows="5"
        maxlength="500"
        show-word-limit
        placeholder="例如：最近两周睡眠不好、容易疲劳、口干…"
      />

      <div class="start-actions">
        <el-button type="primary" size="large" :loading="loading" @click="start">
          开始问诊
        </el-button>
        <span class="start-hint">可稍后在对话中补充主诉</span>
      </div>

      <div class="start-disclaimer">
        <DisclaimerBar compact />
      </div>
    </div>
  </div>
</template>

<style scoped>
.consult-start {
  max-width: 680px;
  margin: 40px auto;
}

.start-card {
  padding: 32px;
}

.start-title {
  font-size: 24px;
  margin: 0 0 12px;
}

.start-sub {
  color: var(--tcm-text-dim);
  line-height: 1.7;
  margin: 0 0 22px;
}

.start-actions {
  margin-top: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.start-hint {
  color: var(--tcm-text-faint);
  font-size: 12px;
}

.start-disclaimer {
  margin-top: 24px;
}
</style>