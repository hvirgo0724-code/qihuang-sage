<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import {
  searchKnowledge,
  getFormulaDetail,
  getHerbDetail,
  getSyndromeDetail,
  getSymptomDetail,
  getKnowledgeStats,
} from '@/api/modules'
import type { KnowledgeItem, KnowledgeNodeDetail, KnowledgeStats, KnowledgeType } from '@/types'

const route = useRoute()

const tabs: Array<{ label: string; value: KnowledgeType }> = [
  { label: '全部', value: 'all' },
  { label: '方剂', value: 'formula' },
  { label: '中药', value: 'herb' },
  { label: '证型', value: 'syndrome' },
  { label: '症状', value: 'symptom' },
]

const activeType = ref<KnowledgeType>('all')
const keyword = ref('')
const items = ref<KnowledgeItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const stats = ref<KnowledgeStats | null>(null)

const drawerVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<KnowledgeNodeDetail | null>(null)
const detailFields = computed(() => {
  const node = detail.value?.node
  if (!node) return {}
  const props = node.properties
  return { name: node.name, ...(props && typeof props === 'object' ? props : {}) }
})

const typeText: Record<string, string> = {
  formula: '方剂',
  herb: '中药',
  syndrome: '证型',
  symptom: '症状',
}

const typeTag: Record<string, 'primary' | 'success' | 'warning' | 'info'> = {
  formula: 'primary',
  herb: 'success',
  syndrome: 'warning',
  symptom: 'info',
}

const FIELD_LABELS: Record<string, string> = {
  name: '名称',
  description: '描述',
  category: '分类',
  title: '标题',
  source: '出处',
  pinyin: '拼音',
  nature: '性',
  flavors: '味',
  meridians: '归经',
  effects: '功效',
  toxicity: '毒性',
  daily_dose_range: '常用剂量',
  contraindications: '禁忌',
  aliases: '别名',
  composition: '组成',
  indications: '主治',
  usage: '用法',
  dosage_note: '剂量说明',
  definition: '定义',
  main_symptoms: '主症',
  accompanying_symptoms: '兼症',
  tongue: '舌象',
  pulse: '脉象',
  treatment_principle: '治法',
  formulas: '代表方',
  location: '部位',
  updated_at: '更新时间',
}

function formatValue(v: unknown): string {
  if (v == null) return '—'
  if (Array.isArray(v)) return v.map((x) => String(x)).join('、')
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

async function load() {
  loading.value = true
  try {
    const resp = await searchKnowledge(keyword.value.trim(), activeType.value, page.value, pageSize)
    items.value = resp.items
    total.value = resp.total
  } catch {
    // 错误提示已由拦截器统一处理
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  load()
}

function onTabChange() {
  page.value = 1
  load()
}

watch(page, load)

async function openDetail(item: KnowledgeItem) {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    if (item.type === 'formula') {
      detail.value = await getFormulaDetail(item.name)
    } else if (item.type === 'herb') {
      detail.value = await getHerbDetail(item.name)
    } else if (item.type === 'syndrome') {
      detail.value = await getSyndromeDetail(item.name)
    } else if (item.type === 'symptom') {
      detail.value = await getSymptomDetail(item.name)
    }
  } catch {
    ElMessage.error('详情加载失败，请稍后重试')
  } finally {
    detailLoading.value = false
  }
}

function fieldLabel(key: string): string {
  return FIELD_LABELS[key] ?? key
}

onMounted(async () => {
  const q = typeof route.query.q === 'string' ? route.query.q : ''
  const t = typeof route.query.type === 'string' ? route.query.type : ''
  if (q) keyword.value = q
  if (t && ['formula', 'herb', 'syndrome', 'symptom'].includes(t)) {
    activeType.value = t as KnowledgeType
  }
  load()
  try {
    stats.value = await getKnowledgeStats()
  } catch {
    // 统计加载失败不阻塞
  }
})
</script>

<template>
  <div class="knowledge-view">
    <h1 class="page-title">中医知识库</h1>

    <div v-if="stats" class="stats-row">
      <el-card class="stat-card"><div class="stat-num">{{ stats.formulas }}</div><div class="stat-label">方剂</div></el-card>
      <el-card class="stat-card"><div class="stat-num">{{ stats.herbs }}</div><div class="stat-label">中药</div></el-card>
      <el-card class="stat-card"><div class="stat-num">{{ stats.syndromes }}</div><div class="stat-label">证型</div></el-card>
      <el-card class="stat-card"><div class="stat-num">{{ stats.symptoms }}</div><div class="stat-label">症状</div></el-card>
    </div>

    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索方剂 / 中药 / 证型 / 症状"
        :prefix-icon="Search"
        clearable
        @keyup.enter="onSearch"
        @clear="onSearch"
      />
      <el-button type="primary" @click="onSearch">搜索</el-button>
    </div>

    <el-tabs v-model="activeType" class="type-tabs" @tab-change="onTabChange">
      <el-tab-pane v-for="t in tabs" :key="t.value" :label="t.label" :name="t.value" />
    </el-tabs>

    <div v-loading="loading">
      <el-empty v-if="!loading && items.length === 0" description="未查询到相关知识条目" />

      <div v-else class="knowledge-list">
        <el-card
          v-for="item in items"
          :key="`${item.type}-${item.name}`"
          class="knowledge-item"
          shadow="hover"
          @click="openDetail(item)"
        >
          <div class="item-head">
            <el-tag size="small" effect="dark" :type="typeTag[item.type] ?? 'info'">
              {{ typeText[item.type] ?? item.type }}
            </el-tag>
            <span class="item-name">{{ item.name }}</span>
            <span v-if="item.title" class="item-title">{{ item.title }}</span>
          </div>
          <p class="item-desc">{{ item.description }}</p>
          <div class="item-source">出处：{{ item.source || '—' }}</div>
        </el-card>
      </div>
    </div>

    <div v-if="total > pageSize" class="pagination">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        background
      />
    </div>

    <el-drawer v-model="drawerVisible" size="480px" title="知识节点详情">
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail && detail.node">
          <div class="detail-section">
            <div v-for="(value, key) in detailFields" :key="key" class="detail-row">
              <span class="detail-label">{{ fieldLabel(String(key)) }}</span>
              <span class="detail-value">{{ formatValue(value) }}</span>
            </div>
          </div>

          <h3 v-if="detail.neighbors?.length" class="neighbor-title">关联节点</h3>
          <div v-for="(n, i) in detail.neighbors" :key="i" class="neighbor-item">
            <el-tag size="small" effect="plain">{{ n.relation }}</el-tag>
            <span class="neighbor-name">{{ formatValue(n.related?.name ?? n.related?.title ?? '—') }}</span>
          </div>
        </template>
        <el-empty v-else-if="!detailLoading" description="暂无详情数据" />
      </div>
    </el-drawer>
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

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.type-tabs {
  margin-bottom: 8px;
}

.knowledge-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.knowledge-item {
  cursor: pointer;
}

.item-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.item-name {
  font-weight: 600;
  font-size: 16px;
  color: var(--tcm-text);
}

.item-title {
  color: var(--tcm-text-faint);
  font-size: 13px;
}

.item-desc {
  margin: 10px 0 8px;
  color: var(--tcm-text-dim);
  font-size: 13px;
  line-height: 1.7;
}

.item-source {
  color: var(--tcm-text-faint);
  font-size: 12px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.detail-body {
  min-height: 120px;
}

.detail-row {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--tcm-border-soft);
  line-height: 1.6;
}

.detail-label {
  width: 84px;
  flex-shrink: 0;
  color: var(--tcm-text-faint);
  font-size: 13px;
}

.detail-value {
  flex: 1;
  color: var(--tcm-text);
  font-size: 13px;
  word-break: break-word;
}

.neighbor-title {
  margin: 20px 0 10px;
  font-size: 15px;
  color: var(--tcm-primary);
}

.neighbor-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}

.neighbor-name {
  color: var(--tcm-text);
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
