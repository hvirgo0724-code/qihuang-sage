<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import JobProgress from '@/components/JobProgress.vue'
import {
  getGraphStats,
  importGraph,
  getAuditLogs,
  getOperationLogs,
  getPrompts,
  createPrompt,
  activatePrompt,
  getEvalDatasets,
  runEval,
  getEvalRuns,
} from '@/api/modules'
import type {
  KnowledgeStats,
  AuditLogItem,
  OperationLogItem,
  PromptVersion,
  EvalDataset,
  EvalRun,
} from '@/types'

const activeTab = ref('graph')

const graphStats = ref<KnowledgeStats | null>(null)
const importJobId = ref<string | null>(null)
const importing = ref(false)

const auditLogs = ref<AuditLogItem[]>([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditLoading = ref(false)
const auditPageSize = 20

const opLogs = ref<OperationLogItem[]>([])
const opTotal = ref(0)
const opPage = ref(1)
const opLoading = ref(false)
const opPageSize = 20

const prompts = ref<PromptVersion[]>([])
const promptLoading = ref(false)
const promptDialog = ref(false)
const promptSaving = ref(false)
const promptForm = reactive({
  scene: '' as string,
  content: '',
  changelog: '',
})

const datasets = ref<EvalDataset[]>([])
const evalRuns = ref<EvalRun[]>([])
const evalLoading = ref(false)
const evalRunningId = ref<number | null>(null)

const sceneOptions = ['inspection', 'inquiry', 'syndrome', 'treatment', 'safety']

function formatTime(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

async function loadStats() {
  try {
    graphStats.value = await getGraphStats()
  } catch {
    // 错误提示已由拦截器统一处理
  }
}

async function doImport() {
  importing.value = true
  try {
    const resp = await importGraph()
    importJobId.value = resp.job_id
    ElMessage.success('图谱/向量导入任务已创建')
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    importing.value = false
  }
}

async function loadAuditLogs() {
  auditLoading.value = true
  try {
    const resp = await getAuditLogs(auditPage.value, auditPageSize)
    auditLogs.value = resp.items
    auditTotal.value = resp.total
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    auditLoading.value = false
  }
}

async function loadOpLogs() {
  opLoading.value = true
  try {
    const resp = await getOperationLogs(opPage.value, opPageSize)
    opLogs.value = resp.items
    opTotal.value = resp.total
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    opLoading.value = false
  }
}

async function loadPrompts() {
  promptLoading.value = true
  try {
    prompts.value = await getPrompts()
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    promptLoading.value = false
  }
}

async function submitPrompt() {
  if (!promptForm.scene || !promptForm.content.trim()) {
    ElMessage.warning('请填写场景与提示词内容')
    return
  }
  promptSaving.value = true
  try {
    await createPrompt({
      scene: promptForm.scene,
      content: promptForm.content.trim(),
      changelog: promptForm.changelog.trim() || undefined,
    })
    ElMessage.success('提示词版本已创建')
    promptDialog.value = false
    promptForm.scene = ''
    promptForm.content = ''
    promptForm.changelog = ''
    loadPrompts()
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    promptSaving.value = false
  }
}

async function doActivate(versionId: number) {
  try {
    await activatePrompt(versionId)
    ElMessage.success('已启用该版本')
    loadPrompts()
  } catch {
    // 错误提示已由拦截器统一处理
  }
}

async function loadEvals() {
  evalLoading.value = true
  try {
    const [ds, runs] = await Promise.all([getEvalDatasets(), getEvalRuns()])
    datasets.value = ds
    evalRuns.value = runs
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    evalLoading.value = false
  }
}

async function doRunEval(datasetId: number) {
  evalRunningId.value = datasetId
  try {
    const resp = await runEval(datasetId)
    ElMessage.success(`评测已启动 (run #${resp.run_id})`)
    loadEvals()
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    evalRunningId.value = null
  }
}

function onTabChange(name: string | number) {
  const tab = String(name)
  if (tab === 'audit' && auditLogs.value.length === 0) loadAuditLogs()
  if (tab === 'operation' && opLogs.value.length === 0) loadOpLogs()
  if (tab === 'prompt' && prompts.value.length === 0) loadPrompts()
  if (tab === 'eval' && datasets.value.length === 0) loadEvals()
}

function onAuditPage(p: number) {
  auditPage.value = p
  loadAuditLogs()
}

function onOpPage(p: number) {
  opPage.value = p
  loadOpLogs()
}

onMounted(() => {
  loadStats()
})
</script>

<template>
  <div class="admin-view">
    <h1 class="page-title">管理后台</h1>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- 图谱与数据 -->
      <el-tab-pane label="图谱与数据" name="graph">
        <div class="stats-row">
          <el-card class="stat-card"><div class="stat-num">{{ graphStats?.formulas ?? '—' }}</div><div class="stat-label">方剂</div></el-card>
          <el-card class="stat-card"><div class="stat-num">{{ graphStats?.herbs ?? '—' }}</div><div class="stat-label">中药</div></el-card>
          <el-card class="stat-card"><div class="stat-num">{{ graphStats?.syndromes ?? '—' }}</div><div class="stat-label">证型</div></el-card>
          <el-card class="stat-card"><div class="stat-num">{{ graphStats?.symptoms ?? '—' }}</div><div class="stat-label">症状</div></el-card>
        </div>

        <div class="tcm-card import-card">
          <div class="import-head">
            <div>
              <h3 class="import-title">知识图谱 / 向量数据导入</h3>
              <p class="import-desc">触发图谱种子数据与向量索引的重新导入（异步任务）。</p>
            </div>
            <el-button type="primary" :loading="importing" @click="doImport">触发导入</el-button>
          </div>
          <JobProgress v-if="importJobId" :job-id="importJobId" />
        </div>
      </el-tab-pane>

      <!-- 审计日志 -->
      <el-tab-pane label="安全审计日志" name="audit">
        <el-table :data="auditLogs" v-loading="auditLoading" border stripe>
          <el-table-column prop="log_id" label="ID" width="70" />
          <el-table-column prop="session_id" label="会话" width="80" />
          <el-table-column prop="stage" label="阶段" width="90" />
          <el-table-column prop="check_result" label="判定" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.check_result === 'pass' ? 'success' : row.check_result === 'block' ? 'danger' : 'warning'" effect="dark">
                {{ row.check_result }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="hit_rule" label="命中规则" show-overflow-tooltip />
          <el-table-column prop="raw_text" label="文本(脱敏)" show-overflow-tooltip />
          <el-table-column prop="action" label="处理" width="100" />
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
          </el-table-column>
        </el-table>
        <div class="pagination">
          <el-pagination
            :current-page="auditPage"
            :page-size="auditPageSize"
            :total="auditTotal"
            layout="prev, pager, next, total"
            background
            @current-change="onAuditPage"
          />
        </div>
      </el-tab-pane>

      <!-- 操作日志 -->
      <el-tab-pane label="操作审计日志" name="operation">
        <el-table :data="opLogs" v-loading="opLoading" border stripe>
          <el-table-column prop="op_id" label="ID" width="70" />
          <el-table-column prop="user_id" label="用户" width="80" />
          <el-table-column prop="action" label="动作" width="100" />
          <el-table-column prop="resource_type" label="资源类型" width="120" />
          <el-table-column prop="resource_id" label="资源ID" width="90" />
          <el-table-column prop="result" label="结果" width="100" />
          <el-table-column prop="ip" label="IP" width="130" />
          <el-table-column prop="trace_id" label="Trace" show-overflow-tooltip />
          <el-table-column label="时间" width="170">
            <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
          </el-table-column>
        </el-table>
        <div class="pagination">
          <el-pagination
            :current-page="opPage"
            :page-size="opPageSize"
            :total="opTotal"
            layout="prev, pager, next, total"
            background
            @current-change="onOpPage"
          />
        </div>
      </el-tab-pane>

      <!-- 提示词管理 -->
      <el-tab-pane label="提示词版本" name="prompt">
        <div class="prompt-head">
          <el-button type="primary" @click="promptDialog = true">新建提示词版本</el-button>
        </div>
        <el-table :data="prompts" v-loading="promptLoading" border stripe>
          <el-table-column prop="version_id" label="ID" width="70" />
          <el-table-column prop="scene" label="场景" width="120" />
          <el-table-column prop="version" label="版本" width="120" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'active' ? 'success' : row.status === 'retired' ? 'info' : 'warning'" effect="dark">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="changelog" label="变更说明" show-overflow-tooltip />
          <el-table-column label="创建时间" width="170">
            <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.status !== 'active'"
                size="small"
                type="primary"
                link
                @click="doActivate(row.version_id)"
              >
                启用
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 评测中心 -->
      <el-tab-pane label="评测中心" name="eval">
        <div v-loading="evalLoading">
          <h3 class="section-title">评测集</h3>
          <el-table :data="datasets" border stripe>
            <el-table-column prop="dataset_id" label="ID" width="70" />
            <el-table-column prop="name" label="名称" />
            <el-table-column prop="scene" label="场景" width="140" />
            <el-table-column prop="sample_count" label="样本数" width="100" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button size="small" type="primary" :loading="evalRunningId === row.dataset_id" @click="doRunEval(row.dataset_id)">
                  运行评测
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <h3 class="section-title">评测记录</h3>
          <el-table :data="evalRuns" border stripe>
            <el-table-column prop="run_id" label="Run ID" width="90" />
            <el-table-column prop="dataset_id" label="数据集" width="90" />
            <el-table-column prop="prompt_version" label="提示词版本" width="140" />
            <el-table-column prop="metrics" label="指标" show-overflow-tooltip>
              <template #default="{ row }">{{ JSON.stringify(row.metrics) }}</template>
            </el-table-column>
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="promptDialog" title="新建提示词版本" width="560px">
      <el-form label-position="top">
        <el-form-item label="场景" required>
          <el-select v-model="promptForm.scene" placeholder="选择场景">
            <el-option v-for="s in sceneOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="提示词内容" required>
          <el-input v-model="promptForm.content" type="textarea" :rows="8" placeholder="输入提示词模板内容" />
        </el-form-item>
        <el-form-item label="变更说明">
          <el-input v-model="promptForm.changelog" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="promptDialog = false">取消</el-button>
        <el-button type="primary" :loading="promptSaving" @click="submitPrompt">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 24px;
  margin: 0 0 20px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-num {
  font-size: 26px;
  font-weight: 700;
  color: var(--tcm-gold);
}

.stat-label {
  color: var(--tcm-text-dim);
  font-size: 13px;
  margin-top: 4px;
}

.import-card {
  margin-bottom: 20px;
}

.import-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.import-title {
  margin: 0 0 6px;
  font-size: 15px;
}

.import-desc {
  margin: 0;
  color: var(--tcm-text-faint);
  font-size: 13px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.prompt-head {
  margin-bottom: 14px;
}

.section-title {
  font-size: 15px;
  margin: 20px 0 10px;
  color: var(--tcm-primary);
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>