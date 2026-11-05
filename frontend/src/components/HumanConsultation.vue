<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { clinical, statusLabel, type Encounter, type Physician } from '@/api/clinical'
import { ElMessage } from 'element-plus'
import DoctorReportEditor from './DoctorReportEditor.vue'
const props = defineProps<{ sessionId: number; doctor?: boolean }>()
const emit = defineEmits<{ changed: [] }>()
const data = ref<Encounter | null>(null), doctors = ref<Physician[]>([])
const doctorId = ref<number>(), consent = ref(false), text = ref(''), review = ref('')
const busy = ref(false), loaded = ref(false), error = ref('')
const imageSrcs = ref<Record<number, string>>({})
let timer: ReturnType<typeof setTimeout> | undefined, stopped = false, loading = false
async function load() {
  if (loading) return
  loading = true
  try { data.value = await clinical.detail(props.sessionId); loaded.value = true; error.value = ''; await loadImages() }
  catch { error.value = '接诊信息加载失败，请刷新重试'; data.value = null; loaded.value = false }
  finally { loading = false }
}
async function loadImages() {
  if (!props.doctor) return
  const imgs = data.value?.images
  if (!imgs) return
  for (const img of imgs) {
    if (!img.image_id || imageSrcs.value[img.image_id]) continue
    try {
      const blob = await clinical.imageBlob(props.sessionId, img.image_id)
      imageSrcs.value[img.image_id] = URL.createObjectURL(blob)
    } catch { /* 图片拉取失败：保持空占位 */ }
  }
}
async function poll() { await load(); if (!stopped) timer = setTimeout(poll, 5000) }
async function run(action: () => Promise<unknown>) {
  busy.value = true
  try { await action(); await load(); emit('changed') } catch { ElMessage.error('操作失败，请检查当前接诊状态后重试') }
  finally { busy.value = false }
}
async function send() { await clinical.message(props.sessionId, text.value); text.value = '' }
onMounted(async () => {
  if (!props.doctor) try { doctors.value = await clinical.doctors() } catch { error.value = '医生列表加载失败' }
  if (!stopped) void poll()
})
onBeforeUnmount(() => { stopped = true; if (timer) clearTimeout(timer); Object.values(imageSrcs.value).forEach(URL.revokeObjectURL) })
</script>
<template>
  <el-card class="human">
    <h2>{{ doctor ? '人工接诊' : '联系医生' }}</h2>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <template v-if="loaded && (!data || data.status === 'cancelled') && !doctor">
      <p>选择医生后，将本次问诊记录、图像分析结果和 AI 报告授权给该医生查看。</p>
      <el-select v-model="doctorId" placeholder="选择接诊医生"><el-option v-for="d in doctors" :key="d.user_id" :label="d.nickname" :value="d.user_id" /></el-select>
      <p v-if="!doctors.length">暂无可接诊医生，请联系管理员开通医生账号。</p>
      <p><el-checkbox v-model="consent">我同意向所选医生提供本次问诊资料</el-checkbox></p>
      <el-button type="primary" :loading="busy" :disabled="!doctorId || !consent" @click="run(() => clinical.request(sessionId, doctorId!))">申请人工接诊</el-button>
    </template>
    <template v-if="data">
      <el-tag>{{ statusLabel[data.status] }}</el-tag>
      <el-button v-if="doctor && data.status === 'requested'" :loading="busy" @click="run(() => clinical.action(sessionId, 'accept'))">接受接诊</el-button>
      <el-button v-if="!doctor && data.status !== 'cancelled'" :loading="busy" @click="run(() => clinical.action(sessionId, 'cancel'))">撤回医生访问授权</el-button>
      <template v-if="doctor"><el-collapse>
        <el-collapse-item title="患者问诊记录" name="records"><p v-for="(r, i) in data.records" :key="i"><strong>{{ r.role === 'user' ? '患者' : 'AI 助手' }}：</strong>{{ r.content }}</p></el-collapse-item>
        <el-collapse-item :title="data.report_review?.status === 'confirmed' ? 'AI 辨证报告与图像分析（已确认发布）' : 'AI 辨证报告与图像分析（待医生审阅）'" name="report"><pre>{{ data.report ? JSON.stringify(data.report, null, 2) : '暂无 AI 报告' }}</pre><div v-for="(img, i) in data.images" :key="img.image_id ?? i" class="img-box"><p><strong>{{ img.image_type === 'tongue' ? '舌象' : '面色' }}</strong> <el-tag :type="img.quality_pass ? 'success' : 'warning'" size="small">{{ img.quality_pass ? '质检通过' : '质检未通过' }}</el-tag></p><img v-if="imageSrcs[img.image_id]" :src="imageSrcs[img.image_id]" alt="上传图像" /><pre>{{ JSON.stringify(img.analysis_result, null, 2) }}</pre></div></el-collapse-item>
      </el-collapse></template>
      <DoctorReportEditor v-if="doctor && data.report_review && ['active', 'closed'].includes(data.status)" :key="data.report_review.analysis_id" :session-id="sessionId" :value="data.report_review" @changed="load(); emit('changed')" />
      <h3>医患交流</h3><p v-if="!data.messages?.length">暂无人工消息</p>
      <article v-for="m in data.messages" :key="m.message_id"><strong>{{ m.author_role === 'DOCTOR' ? '医生回复' : '患者' }}</strong> <small>{{ m.created_at.replace('T', ' ') }}</small><p>{{ m.content }}</p></article>
      <template v-if="data.status === 'active'"><el-input v-model="text" type="textarea" :rows="3" maxlength="10000" placeholder="输入给对方的消息" /><el-button type="primary" :disabled="!text.trim()" :loading="busy" @click="run(send)">发送{{ doctor ? '医生回复' : '消息' }}</el-button></template>
      <h3>医生审阅意见</h3><p>{{ data.review || '尚未提交审阅意见' }}</p>
      <template v-if="doctor && data.status === 'active'">
        <el-input v-model="review" type="textarea" :rows="4" maxlength="10000" placeholder="填写完整审阅意见，保存后患者可见" />
        <el-button :loading="busy" :disabled="!review.trim()" @click="run(() => clinical.review(sessionId, review))">保存审阅意见</el-button>
        <el-button :loading="busy" :disabled="!data.review" @click="run(() => clinical.action(sessionId, 'close'))">结束接诊</el-button>
      </template>
    </template>
  </el-card>
</template>
<style scoped>
.human { margin: 16px 0; } h2 { margin-top: 0; } article { border-bottom: 1px solid var(--tcm-border-soft); padding: 12px 0; } p, pre { white-space: pre-wrap; overflow-wrap: anywhere; } pre { max-height: 420px; overflow: auto; } .el-button { margin-top: 12px; } small { opacity: .65; } .img-box { margin-top: 8px; } .img-box img { max-width: 100%; border-radius: 6px; }
</style>
