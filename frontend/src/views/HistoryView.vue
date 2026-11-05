<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listSessions } from '@/api/modules'
import { http } from '@/api/http'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useConsultStore } from '@/stores/consult'
import type { SessionSummary } from '@/types'

const router = useRouter()

const sessions = ref<SessionSummary[]>([])
const loading = ref(true)
const failed = ref(false)
const query = ref('')
const filter = ref('all')
const page = ref(1)
const deleting = ref<number | null>(null)

async function removeSession(id: number) {
  if (deleting.value !== null) return
  try {
    await ElMessageBox.confirm(`确定删除问诊 #${id} 吗？该次问诊记录、关联报告及接诊记录将一并删除，无法恢复。账号、其他问诊和已确认的长期记忆保留。`,
      '删除问诊与报告', { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' })
  } catch { return }
  deleting.value = id
  try {
    await http.delete(`/consultation/${id}`)
    const consult = useConsultStore()
    if (consult.sessionId === id) consult.reset()
    ElMessage.success('本次问诊及关联报告已删除')
    await load()
  } catch { /* HTTP interceptor displays error */ }
  finally { deleting.value = null }
}
const filtered = computed(() => sessions.value.filter(s =>
  (!query.value.trim() || `${s.session_id} ${s.complaint || ''}`.includes(query.value.trim())) &&
  (filter.value === 'all' || (filter.value === 'none' ? !s.report_status : s.report_status === filter.value))))
const visible = computed(() => filtered.value.slice((page.value - 1) * 8, page.value * 8))
const pendingCount = computed(() => sessions.value.filter(s => s.report_status === 'pending').length)
const confirmedCount = computed(() => sessions.value.filter(s => s.report_status === 'confirmed').length)
watch([query, filter], () => { page.value = 1 })

const riskText: Record<string, string> = {
  low: '低风险',
  medium: '中等',
  high: '高风险',
  emergency: '急危重症',
}

const riskType: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
  low: 'success',
  medium: 'warning',
  high: 'danger',
  emergency: 'danger',
}

const statusText: Record<string, string> = {
  ongoing: '进行中',
  pending_review: '等待医生审核',
  completed: '已完成',
  aborted: '已中断',
}

function formatTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate(),
  ).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function openResult(sessionId: number) {
  router.push(`/consult/${sessionId}/result`)
}

async function load() {
  failed.value = false
  loading.value = true
  try {
    sessions.value = await listSessions()
    page.value = Math.min(page.value, Math.max(1, Math.ceil(filtered.value.length / 8)))
  } catch {
    failed.value = true
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <div class="history-view">
    <div class="page-heading"><div><span class="eyebrow">CONSULTATION RECORDS</span><h2>问诊记录与报告</h2><p>查看问诊进展、联系接诊医生，或阅读已确认的报告。</p></div><el-button :loading="loading" @click="load">刷新记录</el-button></div>
    <div class="metric-grid">
      <div class="metric-card"><span>已加载问诊</span><strong>{{ loading ? '—' : sessions.length }}</strong></div>
      <div class="metric-card"><span>待医生审核</span><strong>{{ loading ? '—' : pendingCount }}</strong></div>
      <div class="metric-card"><span>报告已发布</span><strong>{{ loading ? '—' : confirmedCount }}</strong></div>
    </div>
    <div class="workspace-toolbar">
      <el-input v-model="query" clearable placeholder="搜索问诊编号或主诉" aria-label="搜索问诊记录" />
      <el-select v-model="filter" aria-label="报告状态"><el-option label="全部报告状态" value="all" /><el-option label="待医生审核" value="pending" /><el-option label="已发布" value="confirmed" /><el-option label="尚未生成" value="none" /></el-select>
      <span class="tcm-subtitle">共 {{ filtered.length }} 条 · 最近 100 次问诊</span>
    </div>

    <div v-loading="loading">
      <el-empty v-if="failed" description="记录加载失败，请重试"><el-button @click="load">重新加载</el-button></el-empty>
      <el-empty v-else-if="!loading && filtered.length === 0" :description="sessions.length ? '没有匹配的问诊记录，请调整筛选条件' : '暂无问诊记录，开始一次新的健康咨询吧'" />

      <div v-else class="session-list">
        <el-card
          v-for="s in visible"
          :key="s.session_id"
          class="session-item"
          shadow="hover"
        >
          <div class="session-main">
            <div class="session-head">
              <span class="session-id">#{{ s.session_id }}</span>
              <el-tag
                v-if="s.risk_level"
                size="small"
                effect="dark"
                :type="riskType[s.risk_level] ?? 'info'"
              >
                {{ riskText[s.risk_level] ?? s.risk_level }}
              </el-tag>
              <el-tag size="small" effect="plain" type="info">
                {{ statusText[s.status] ?? s.status }}
              </el-tag>
            </div>
            <p class="session-complaint">{{ s.complaint || '（未填写主诉）' }}</p>
            <el-tag :type="s.report_status === 'confirmed' ? 'success' : 'info'">
              {{ s.report_status === 'confirmed' ? '报告已发布' : s.report_status === 'pending' ? '报告待医生审核' : '尚未生成报告' }}
            </el-tag>
          </div>
          <div class="session-time">{{ formatTime(s.start_time) }}</div>
          <div class="session-actions"><el-button @click.stop="router.push(`/consult/${s.session_id}`)">进入问诊 / 联系医生</el-button>
          <el-button v-if="s.report_status" type="primary" @click.stop="openResult(s.session_id)">
            {{ s.report_status === 'confirmed' ? '查看正式报告' : '查看审核状态 / 选择医生' }}
          </el-button>
          <el-button type="danger" plain :loading="deleting === s.session_id" :disabled="deleting !== null" @click.stop="removeSession(s.session_id)">删除</el-button></div>
        </el-card>
      </div>
      <el-pagination v-if="filtered.length > 8" v-model:current-page="page" :page-size="8" :total="filtered.length" layout="prev, pager, next" />
    </div>
  </div>
</template>

<style scoped>
.session-actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--tcm-border-soft); }
.session-actions .el-button { margin-left: 0; }
.session-head { flex-wrap: wrap; }
.page-title {
  font-size: 24px;
  margin: 0 0 20px;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.session-item {
  transition: border-color .2s;
}

.session-main {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.session-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.session-id {
  font-weight: 600;
  color: var(--tcm-primary);
}

.session-complaint {
  margin: 0;
  color: var(--tcm-text-dim);
  line-height: 1.6;
}

.session-time {
  margin-top: 10px;
  color: var(--tcm-text-faint);
  font-size: 12px;
}
</style>
