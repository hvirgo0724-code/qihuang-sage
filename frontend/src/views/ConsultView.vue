<script setup lang="ts">
import HumanConsultation from '@/components/HumanConsultation.vue'
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import TongueUploader from '@/components/TongueUploader.vue'
import FaceUploader from '@/components/FaceUploader.vue'
import ConsultChat from '@/components/ConsultChat.vue'
import JobProgress from '@/components/JobProgress.vue'
import AnalysisFeatureTag from '@/components/AnalysisFeatureTag.vue'
import DisclaimerBar from '@/components/DisclaimerBar.vue'
import { getSessionMessages } from '@/api/modules'
import { useConsultStore } from '@/stores/consult'
import type { ChatMessage, SyndromeReport } from '@/types'

const route = useRoute()
const router = useRouter()
const consult = useConsultStore()

const sessionId = Number(route.params.id)

const tongueJob = ref<string | null>(null)
const faceJob = ref<string | null>(null)
const tongueResult = ref<Record<string, unknown> | null>(null)
const faceResult = ref<Record<string, unknown> | null>(null)
const reportReady = ref(false)
const history = ref<ChatMessage[]>([])
const historyLoading = ref(true)
const historyError = ref(false)
const chatRef = ref<InstanceType<typeof ConsultChat> | null>(null)
const chatBusy = ref(false)

function onTongueUploaded(jobId: string) {
  tongueJob.value = jobId
  tongueResult.value = null
  ElMessage.info('舌象图片已上传，识别任务已创建')
}

function onFaceUploaded(jobId: string) {
  faceJob.value = jobId
  faceResult.value = null
  ElMessage.info('面色图片已上传，识别任务已创建')
}

function onTongueResult(result: Record<string, unknown>) {
  tongueResult.value = result
}

function onFaceResult(result: Record<string, unknown>) {
  faceResult.value = result
}

function onJobError(msg: string) {
  ElMessage.error(msg)
}

function onReport(report: SyndromeReport) {
  consult.setReport(report)
  reportReady.value = true
}

function goResult() {
  router.push(`/consult/${sessionId}/result`)
}

function handleReport() {
  if (chatBusy.value || historyLoading.value || historyError.value) return
  if (reportReady.value) goResult()
  else void chatRef.value?.generateReport()
}

function restoreImageResults(messages: ChatMessage[]) {
  for (let i = messages.length - 1; i >= 0; i--) {
    const meta = messages[i].meta as { slots?: { 图像识别?: Record<string, unknown> } } | null
    const result = meta?.slots?.图像识别
    if (!result) continue
    if (result.image_type === 'tongue' && !tongueResult.value) tongueResult.value = result
    if (result.image_type === 'face' && !faceResult.value) faceResult.value = result
  }
}

async function loadHistory() {
  historyLoading.value = true
  historyError.value = false
  try {
    history.value = await getSessionMessages(sessionId)
    reportReady.value = history.value.some(message => message.type === 'result')
    restoreImageResults(history.value)
  } catch {
    historyError.value = true
  } finally {
    historyLoading.value = false
  }
}

onMounted(() => {
  consult.setSession(sessionId, null, consult.complaint)
  void loadHistory()
})
</script>

<template>
  <div class="consult-view">
    <div class="consult-top">
      <div>
        <span class="eyebrow">GUIDED CONSULTATION</span><h1 class="consult-title">四诊问诊</h1>
        <p class="consult-sub">会话 #{{ sessionId }} · 每次回答一两项，按您的节奏继续</p>
      </div>
      <el-button
        type="primary"
        size="large"
        :disabled="historyLoading || historyError || chatBusy"
        :loading="chatBusy"
        @click="handleReport"
      >
        {{ chatBusy ? '正在处理…' : reportReady ? '查看报告状态' : '生成报告并提交审核' }}
      </el-button>
    </div>

    <div class="consult-stage"><span class="stage-active">01 · 四诊信息采集</span><span :class="{ 'stage-active': reportReady }">02 · 报告审核与发布</span><span>03 · 查看正式报告</span></div>
    <div class="consult-grid">
      <div class="panel left">
        <div><h2 class="tcm-title">影像资料</h2><p class="tcm-subtitle">选填 · 上传清晰舌象或面色照片，辅助本次问诊。</p></div>
        <div class="upload-section">
          <TongueUploader :session-id="sessionId" @uploaded="onTongueUploaded" @error="onJobError" />
          <JobProgress
            v-if="tongueJob"
            :job-id="tongueJob"
            @result="onTongueResult"
            @error="onJobError"
          />
          <AnalysisFeatureTag :result="tongueResult" />
        </div>

        <div class="upload-section">
          <FaceUploader :session-id="sessionId" @uploaded="onFaceUploaded" @error="onJobError" />
          <JobProgress
            v-if="faceJob"
            :job-id="faceJob"
            @result="onFaceResult"
            @error="onJobError"
          />
          <AnalysisFeatureTag :result="faceResult" />
        </div>

        <div class="consult-disclaimer">
          <DisclaimerBar compact />
        </div>
      </div>

      <div class="panel right">
        <div class="chat-panel-heading"><h2>问诊交流</h2><span>选择回答 · 随时补充</span></div>
        <el-skeleton v-if="historyLoading" :rows="6" animated />
        <el-empty v-else-if="historyError" description="历史问诊记录加载失败，请重试">
          <el-button type="primary" @click="loadHistory">重新加载</el-button>
        </el-empty>
        <ConsultChat
          v-else
          ref="chatRef"
          :session-id="sessionId"
          :initial-messages="history"
          @result="onReport"
          @pending="reportReady = true"
          @busy="chatBusy = $event"
        />
      </div>
    </div>
    <section><div class="page-heading"><div><h2>医生接诊与报告审核</h2><p>选择并授权医生后，可进行人工交流和报告审核。</p></div></div><HumanConsultation :session-id="sessionId" /></section>
  </div>
</template>

<style scoped>
.chat-panel-heading { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; border-bottom: 1px solid var(--tcm-border-soft); padding-bottom: 16px; margin-bottom: 16px; }
.chat-panel-heading h2 { margin: 0; font-size: 17px; }
.chat-panel-heading span { color: var(--tcm-text-faint); font-size: 12px; }
.consult-stage { display: flex; flex-wrap: wrap; gap: 12px 24px; padding: 16px 20px; border-radius: 10px; background: white; border: 1px solid var(--tcm-border-soft); color: var(--tcm-text-faint); font-size: 13px; }
.stage-active { color: var(--tcm-primary); font-weight: 600; }
@media (max-width: 1000px) { .right { order: -1; } }

.consult-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.consult-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 14px;
}

.consult-title {
  font-size: 24px;
  margin: 0;
}

.consult-sub {
  color: var(--tcm-text-faint);
  font-size: 13px;
  margin: 4px 0 0;
}

.consult-grid {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

.panel {
  background: var(--tcm-card);
  border: 1px solid var(--tcm-border-soft);
  border-radius: var(--tcm-radius);
  padding: 20px;
  box-shadow: var(--tcm-shadow);
}

.left {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.upload-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.consult-disclaimer {
  margin-top: auto;
}

@media (max-width: 1000px) {
  .consult-grid {
    grid-template-columns: 1fr;
  }
}
</style>
