<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { clinical, statusLabel, type Encounter } from '@/api/clinical'
import HumanConsultation from '@/components/HumanConsultation.vue'
import { ElMessage } from 'element-plus'
const cases = ref<Encounter[]>([]), selected = ref<number>(), loading = ref(false)
const query = ref(''), filter = ref('all'), failed = ref(false)
const visible = computed(() => cases.value.filter(c =>
  `${c.session_id} ${c.patient_name || ''} ${c.complaint || ''}`.includes(query.value.trim()) &&
  (filter.value === 'all' || (filter.value === 'pending' ? c.report_status === 'pending' : c.status === filter.value))))
const requested = computed(() => cases.value.filter(c => c.status === 'requested').length)
const pending = computed(() => cases.value.filter(c => c.report_status === 'pending').length)
async function load(silent = false) {
  if (!silent) loading.value = true
  try { cases.value = await clinical.cases(); failed.value = false }
  catch { failed.value = true; if (!silent) ElMessage.error('病例列表加载失败') }
  finally { loading.value = false }
}
let timer: ReturnType<typeof setTimeout> | undefined, stopped = false
async function poll() { await load(cases.value.length > 0); if (!stopped) timer = setTimeout(poll, 10000) }
onMounted(poll)
onBeforeUnmount(() => { stopped = true; if (timer) clearTimeout(timer) })
</script>
<template>
  <div>
    <div class="page-heading"><div><span class="eyebrow">CLINICAL WORKSPACE</span><h1>医生工作台</h1><p>处理接诊申请、回复患者，并审核发布辨证报告。</p></div><el-button :loading="loading" @click="load()">刷新列表</el-button></div>
    <div class="metric-grid">
      <div class="metric-card"><span>已加载病例</span><strong>{{ cases.length }}</strong></div>
      <div class="metric-card"><span>待接诊申请</span><strong>{{ requested }}</strong></div>
      <div class="metric-card"><span>待审核报告</span><strong>{{ pending }}</strong></div>
    </div>
    <section class="workspace-panel">
      <div class="page-heading"><div><h2>接诊队列</h2><p>仅展示授权给您的病例 · 每 10 秒自动更新 · 最多 200 条</p></div></div>
      <el-alert v-if="failed" title="列表更新失败，当前内容可能不是最新状态，请重试刷新。" type="warning" :closable="false" />
      <div class="workspace-toolbar">
        <el-input v-model="query" clearable placeholder="搜索患者、主诉或问诊编号" aria-label="搜索病例" />
        <el-select v-model="filter" aria-label="筛选接诊队列"><el-option label="全部病例" value="all" /><el-option label="待接诊" value="requested" /><el-option label="接诊中" value="active" /><el-option label="待审核报告" value="pending" /></el-select>
      </div>
      <el-table :data="visible" v-loading="loading" empty-text="暂无匹配的授权病例" @row-click="(row: Encounter) => selected = row.session_id">
        <el-table-column prop="session_id" label="编号" width="80" />
        <el-table-column prop="patient_name" label="患者" min-width="110" />
        <el-table-column prop="complaint" label="主诉" min-width="180" show-overflow-tooltip />
        <el-table-column label="接诊状态" min-width="120"><template #default="{ row }"><el-tag effect="plain">{{ statusLabel[row.status] }}</el-tag></template></el-table-column>
        <el-table-column label="报告审核" min-width="130"><template #default="{ row }"><el-tag v-if="row.report_status" :type="row.report_status === 'confirmed' ? 'success' : 'warning'">{{ row.report_status === 'confirmed' ? '已确认发布' : '待审核' }}</el-tag><span v-else class="tcm-subtitle">尚未生成</span></template></el-table-column>
        <el-table-column label="操作" width="110" fixed="right"><template #default="{ row }"><el-button type="primary" plain size="small" @click.stop="selected = row.session_id">查看病例</el-button></template></el-table-column>
      </el-table>
    </section>
    <section v-if="selected" class="case-detail"><div class="page-heading"><h2>病例详情 · #{{ selected }}</h2><el-button text @click="selected = undefined">收起详情</el-button></div><HumanConsultation :key="selected" :session-id="selected" doctor @changed="load()" /></section>
  </div>
</template>
<style scoped>.case-detail { margin-top: 28px; } h2 { font-size: 18px; margin: 0; }</style>
