<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import HumanConsultation from '@/components/HumanConsultation.vue'
import MemoryPanel from '@/components/MemoryPanel.vue'
import axios from 'axios'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import SyndromeReport from '@/components/SyndromeReport.vue'
import { getSessionResult, submitFeedback } from '@/api/modules'
import { ssePost } from '@/api/http'
import { useConsultStore } from '@/stores/consult'
import type { SyndromeReport as Report } from '@/types'

const route = useRoute()
const router = useRouter()
const consult = useConsultStore()

const sessionId = Number(route.params.id)

const report = ref<Report | null>(null)
const loading = ref(true)
const analysisId = ref<number | null>(null)
const missingReport = ref(false)
const errorMessage = ref('')
const generating = ref(false)
const generationStatus = ref('')
const pending = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined
let stopped = false

const rating = ref(0)
const comment = ref('')
const correct = ref(false)
const submitting = ref(false)

async function loadReport() {
  loading.value = true
  errorMessage.value = ''
  missingReport.value = false
  report.value = null
  try {
    const r = await getSessionResult(sessionId)
    pending.value = r.review_status === 'pending'
    if (r.review_status === 'pending') {
      errorMessage.value = r.message
      return
    }
    report.value = r
    analysisId.value = r.analysis_id ?? null
    if (consult.sessionId !== sessionId) consult.setSession(sessionId, null)
    consult.setReport(r)
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      missingReport.value = error.response.data?.detail === '暂无辨证报告'
      errorMessage.value = missingReport.value
        ? '本次问诊尚未生成报告，或上次生成未完成。可继续问诊，或根据已收集的信息生成报告。'
        : '会话不存在或无权访问，请返回问诊列表。'
    } else {
      errorMessage.value = '报告暂时无法加载，请检查网络后重试。'
    }
  } finally {
    loading.value = false
  }
}

async function pollReport() {
  await loadReport()
  if (!stopped && pending.value) timer = setTimeout(pollReport, 5000)
}
onMounted(pollReport)
onBeforeUnmount(() => { stopped = true; if (timer) clearTimeout(timer) })

async function generateReport() {
  if (generating.value) return
  generating.value = true
  errorMessage.value = ''
  generationStatus.value = '正在生成报告，请稍候…'
  try {
    await ssePost(`/consultation/${sessionId}/chat`, { message: '生成报告' }, {
      onPhase(phase) {
        generationStatus.value = phase === 'syndrome' ? '正在综合问诊与图像信息生成报告…' : '正在处理，请稍候…'
      },
      onResult(result) {
        report.value = result
        analysisId.value = result.analysis_id ?? null
        missingReport.value = false
        if (consult.sessionId !== sessionId) consult.setSession(sessionId, null)
        consult.setReport(result)
      },
      onError(message) { errorMessage.value = message },
      onReviewPending(data) {
        pending.value = true
        missingReport.value = false
        errorMessage.value = data.message
        if (!stopped && !timer) timer = setTimeout(pollReport, 5000)
      },
    })
    if (!report.value && !errorMessage.value && !pending.value) {
      errorMessage.value = '本次未生成报告，请返回问诊查看回复并补充信息。'
    }
  } finally {
    generating.value = false
  }
}

async function doFeedback() {
  if (!analysisId.value) {
    ElMessage.warning('当前报告暂无分析记录，无法提交反馈')
    return
  }
  if (!rating.value) {
    ElMessage.warning('请先评分')
    return
  }
  submitting.value = true
  try {
    await submitFeedback({
      analysis_id: analysisId.value,
      rating: rating.value,
      comment: comment.value.trim() || undefined,
      correct: correct.value || undefined,
    })
    ElMessage.success('感谢您的反馈')
    rating.value = 0
    comment.value = ''
    correct.value = false
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="result-view">
    <div class="page-heading">
      <div><span class="eyebrow">CONSULTATION REPORT</span><h1>辨证报告</h1><p>会话 #{{ sessionId }} · 医生确认后发布正式报告</p></div>
      <el-button text @click="router.push(`/consult/${sessionId}`)">← 返回问诊</el-button>
    </div>

    <div v-loading="loading" class="result-body">
      <SyndromeReport v-if="report" :report="report" />
      <el-alert v-if="report?.review_status === 'confirmed'" title="此报告已由医生修改并确认" type="success" :closable="false" />

      <section v-else-if="pending && !loading" class="review-wait workspace-panel">
        <div class="wait-symbol"><el-icon :size="28"><Clock /></el-icon></div>
        <el-tag type="warning" effect="plain">等待医生确认</el-tag>
        <h2>辨证分析已完成</h2><p>{{ errorMessage }}</p>
        <p class="tcm-subtitle">此页面会自动更新审核状态，您也可以返回问诊与医生交流。</p>
        <el-button type="primary" @click="router.push(`/consult/${sessionId}`)">返回问诊 / 联系医生</el-button>
        <el-button @click="loadReport">刷新状态</el-button>
      </section>
      <el-empty v-else-if="!loading" :description="generating ? generationStatus : errorMessage || '暂无辨证报告'">
        <el-button v-if="missingReport" type="primary" :loading="generating" @click="generateReport">生成报告</el-button>
        <el-button v-else :disabled="generating" @click="loadReport">重新加载</el-button>
        <el-button :disabled="generating" @click="router.push(`/consult/${sessionId}`)">继续问诊</el-button>
      </el-empty>
      <HumanConsultation v-if="pending" :session-id="sessionId" />
      <MemoryPanel v-if="pending || report" :session-id="sessionId" />

      <div v-if="report && !report.emergency_flag && report.risk_level !== 'emergency'" class="feedback-card tcm-card">
        <h3 class="feedback-title">本次结果反馈</h3>
        <p class="feedback-sub">您的反馈将用于改进辨证与调养建议的准确性</p>
        <div class="feedback-row">
          <span class="feedback-label">评分</span>
          <el-rate v-model="rating" />
        </div>
        <div class="feedback-row">
          <span class="feedback-label">辨证是否符合您的实际情况？</span>
          <el-switch
            v-model="correct"
            active-text="符合"
            inactive-text="不符合"
          />
        </div>
        <el-input
          v-model="comment"
          type="textarea"
          :rows="3"
          maxlength="500"
          show-word-limit
          placeholder="补充意见（选填）"
        />
        <el-button type="primary" class="feedback-btn" :loading="submitting" @click="doFeedback">
          提交反馈
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.review-wait { text-align: center; padding: 40px 24px; }
.review-wait p { line-height: 1.8; color: var(--tcm-text-dim); }
.wait-symbol { color: var(--tcm-primary); background: #edf8f5; border-radius: 50%; width: 64px; height: 64px; display: grid; place-items: center; margin: 0 auto 20px; }

.result-view {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-body {
  min-height: 200px;
}

.feedback-card {
  margin-top: 20px;
}

.feedback-title {
  margin: 0 0 6px;
  font-size: 16px;
}

.feedback-sub {
  color: var(--tcm-text-faint);
  font-size: 12px;
  margin: 0 0 18px;
}

.feedback-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.feedback-label {
  color: var(--tcm-text-dim);
  font-size: 13px;
  white-space: nowrap;
}

.feedback-btn {
  margin-top: 16px;
}
</style>
