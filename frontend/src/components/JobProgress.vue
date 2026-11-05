<script setup lang="ts">
import { ref, watch, onBeforeUnmount, computed } from 'vue'
import { getJob } from '@/api/modules'
import type { JobStatus } from '@/types'

const props = defineProps<{
  jobId: string | null
}>()

const emit = defineEmits<{
  (e: 'result', payload: Record<string, unknown>): void
  (e: 'finished', payload: Record<string, unknown> | null): void
  (e: 'error', message: string): void
}>()

const status = ref<JobStatus | ''>('')
const progress = ref(0)
const jobType = ref('')
const error = ref('')
let timer: number | undefined

const polling = computed(() => status.value === 'pending' || status.value === 'running')

const statusText: Record<string, string> = {
  pending: '排队等待中…',
  running: '模型识别中…',
  success: '识别完成',
  failed: '识别失败',
}

const jobTypeText: Record<string, string> = {
  image_analysis: '舌面图像识别',
  graph_import: '图谱导入',
  vector_rebuild: '向量重建',
  export: '批量导出',
}

async function poll() {
  if (!props.jobId) return
  try {
    const job = await getJob(props.jobId)
    status.value = job.status
    progress.value = job.progress
    jobType.value = job.job_type
    error.value = job.error ?? ''
    if (job.status === 'success') {
      stop()
      emit('result', (job.result ?? {}) as Record<string, unknown>)
      emit('finished', (job.result ?? {}) as Record<string, unknown>)
    } else if (job.status === 'failed') {
      stop()
      emit('error', job.error ?? '识别失败')
      emit('finished', null)
    }
  } catch {
    stop()
    emit('error', '任务状态查询失败，请重试')
    emit('finished', null)
  }
}

function start() {
  stop()
  if (!props.jobId) return
  status.value = 'pending'
  progress.value = 0
  error.value = ''
  poll()
  timer = window.setInterval(poll, 1500)
}

function stop() {
  if (timer) {
    window.clearInterval(timer)
    timer = undefined
  }
}

watch(() => props.jobId, start, { immediate: true })

onBeforeUnmount(stop)
</script>

<template>
  <div v-if="jobId" class="job-progress">
    <div class="job-head">
      <span class="job-type">{{ jobTypeText[jobType] || jobType || '异步任务' }}</span>
      <el-tag
        v-if="status"
        size="small"
        :type="status === 'success' ? 'success' : status === 'failed' ? 'danger' : 'warning'"
        effect="dark"
      >
        {{ statusText[status] || status }}
      </el-tag>
    </div>
    <el-progress
      :percentage="progress ?? 0"
      :status="status === 'success' ? 'success' : status === 'failed' ? 'exception' : undefined"
      :stroke-width="10"
      :indeterminate="polling && progress === 0"
    />
    <p v-if="error && status === 'failed'" class="job-error">{{ error }}</p>
  </div>
</template>

<style scoped>
.job-progress {
  padding: 8px 0;
}

.job-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.job-type {
  font-size: 13px;
  color: var(--tcm-text-dim);
}

.job-error {
  color: var(--tcm-danger);
  font-size: 12px;
  margin: 8px 0 0;
}
</style>