<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { healthz } from '@/api/modules'

const defaultUrl = import.meta.env.VITE_GRAFANA_URL || ''
const grafanaUrl = ref(defaultUrl)
const appliedUrl = ref('')
const healthStatus = ref<'loading' | 'ok' | 'error'>('loading')

const metricDescriptions = [
  { name: 'tcm_requests_total', desc: 'HTTP 请求总量（按方法/路径/状态码标签）' },
  { name: 'tcm_request_latency_seconds', desc: 'HTTP 请求延迟直方图（P50/P95/P99）' },
  { name: 'tcm_requests_total{status=~"5.."}', desc: '接口 5xx 错误计数与错误率' },
  { name: 'tcm_llm_latency_seconds / tcm_llm_tokens_total', desc: '大模型调用耗时与 token 数' },
  { name: 'tcm_llm_calls_total{outcome="fallback"}', desc: 'LLM 多模型降级触发次数' },
  { name: 'tcm_safety_checks_total', desc: '医疗安全护栏检查次数与命中率' },
  { name: 'tcm_graph_search_latency_seconds', desc: '知识图谱检索耗时与命中数' },
  { name: 'tcm_vector_search_latency_seconds', desc: '向量检索耗时' },
  { name: 'tcm_celery_queue_depth', desc: 'Celery 任务队列积压深度' },
]

function applyUrl() {
  const url = grafanaUrl.value.trim()
  if (!url) {
    ElMessage.warning('请先输入 Grafana 面板 URL')
    return
  }
  appliedUrl.value = url
}

async function checkHealth() {
  healthStatus.value = 'loading'
  try {
    const resp = await healthz()
    healthStatus.value = resp.status === 'ok' ? 'ok' : 'error'
  } catch {
    healthStatus.value = 'error'
  }
}

onMounted(() => {
  checkHealth()
  if (defaultUrl) appliedUrl.value = defaultUrl
})
</script>

<template>
  <div class="monitor-view">
    <h1 class="page-title">监控大盘</h1>

    <div class="monitor-control tcm-card">
      <div class="control-row">
        <el-input
          v-model="grafanaUrl"
          placeholder="输入 Grafana 面板 URL，例如 http://host:3000/d/dashboard"
          clearable
          @keyup.enter="applyUrl"
        />
        <el-button type="primary" @click="applyUrl">加载 Grafana</el-button>
      </div>
      <p class="control-hint">
        生产环境请在环境变量 VITE_GRAFANA_URL 中配置默认面板地址；需要开放跨域或同域反代以正常嵌入。
      </p>
    </div>

    <div v-if="appliedUrl" class="grafana-frame">
      <iframe :src="appliedUrl" frameborder="0" class="grafana-iframe" title="Grafana Dashboard" />
    </div>

    <div class="health-grid">
      <div class="tcm-card health-card">
        <div class="health-head">
          <span class="health-title">后端健康状态</span>
          <el-button size="small" @click="checkHealth">刷新</el-button>
        </div>
        <div class="health-body">
          <el-tag
            v-if="healthStatus === 'ok'"
            type="success"
            effect="dark"
            size="large"
          >
            服务正常 (/healthz ok)
          </el-tag>
          <el-tag v-else-if="healthStatus === 'error'" type="danger" effect="dark" size="large">
            服务不可用
          </el-tag>
          <el-tag v-else type="info" effect="dark" size="large">检测中…</el-tag>
          <p class="health-desc">
            后端暴露 <code>/healthz</code>（存活）与 <code>/readyz</code>（就绪，含 MySQL/Redis/Neo4j/Milvus 依赖探测）探针。
          </p>
        </div>
      </div>

      <div class="tcm-card metric-card">
        <h3 class="metric-title">/metrics 指标说明</h3>
        <div class="metric-list">
          <div v-for="m in metricDescriptions" :key="m.name" class="metric-item">
            <code class="metric-name">{{ m.name }}</code>
            <span class="metric-desc">{{ m.desc }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title {
  font-size: 24px;
  margin: 0 0 20px;
}

.monitor-control {
  margin-bottom: 20px;
}

.control-row {
  display: flex;
  gap: 10px;
}

.control-hint {
  margin: 10px 0 0;
  color: var(--tcm-text-faint);
  font-size: 12px;
}

.grafana-frame {
  margin-bottom: 20px;
  border: 1px solid var(--tcm-border-soft);
  border-radius: var(--tcm-radius);
  overflow: hidden;
}

.grafana-iframe {
  width: 100%;
  height: 560px;
  display: block;
  background: #111;
}

.health-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.health-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.health-title,
.metric-title {
  font-size: 16px;
  margin: 0;
}

.health-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
}

.health-desc {
  color: var(--tcm-text-dim);
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
}

.health-desc code,
.metric-name {
  background: var(--tcm-bg-soft);
  color: var(--tcm-primary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.metric-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
}

.metric-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.metric-name {
  white-space: nowrap;
  flex-shrink: 0;
}

.metric-desc {
  color: var(--tcm-text-dim);
  font-size: 13px;
}

@media (max-width: 900px) {
  .health-grid {
    grid-template-columns: 1fr;
  }
}
</style>