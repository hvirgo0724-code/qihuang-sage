<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { http } from '@/api/http'

const props = defineProps<{ sessionId?: number }>()
type Entry = { memory_key: string; value: { content: string }; expires_at?: string }
type Suggestion = { key: string; content: string; source: string; previous?: string }
const entries = ref<Entry[]>([])
const suggestions = ref<Suggestion[]>([])
const loading = ref(false)
const error = ref(false)
const busy = ref(false)
const editing = ref(false)
const key = ref('')
const content = ref('')
const consent = ref(false)

async function load() {
  loading.value = true
  error.value = false
  try {
    const [saved, proposed] = await Promise.all([
      http.get<Entry[]>('/memory'),
      http.get<Suggestion[]>('/memory/suggestions', { params: { session_id: props.sessionId } }),
    ])
    entries.value = saved.data
    suggestions.value = proposed.data
  } catch { error.value = true }
  finally { loading.value = false }
}
function edit(k = '', text = '') {
  key.value = k || `note_${crypto.randomUUID().replaceAll('-', '')}`
  content.value = text
  consent.value = false
  editing.value = true
}
async function save() {
  if (!consent.value || !content.value.trim() || busy.value) return
  busy.value = true
  try {
    await http.put('/memory', { key: key.value, content: content.value.trim(), consent: true })
    editing.value = false
    ElMessage.success('长期记忆已保存，将用于后续问诊')
    await load()
  } catch { /* HTTP interceptor displays error */ }
  finally { busy.value = false }
}
async function remove(entry: Entry) {
  try { await ElMessageBox.confirm('删除后，后续问诊将不再读取这条长期记忆。原始问诊记录和健康画像仍保留。', '删除长期记忆', { type: 'warning' }) }
  catch { return }
  busy.value = true
  try { await http.delete(`/memory/${entry.memory_key}`); await load() }
  catch { /* HTTP interceptor displays error */ }
  finally { busy.value = false }
}
onMounted(load)
defineExpose({ refresh: load })
</script>

<template>
  <section class="tcm-card memory-panel" v-loading="loading" aria-label="长期健康记忆">
    <div class="memory-heading">
      <h2>长期健康记忆</h2>
      <div><el-button :disabled="loading || busy" @click="load">刷新整理</el-button><el-button type="primary" @click="edit()">添加记忆</el-button></div>
    </div>
    <p>仅在您逐条确认后保存，供后续问诊参考。历史资料需要结合当前情况核实，您可以随时修改或删除。</p>
    <el-alert v-if="error" title="记忆加载失败，请点击刷新整理重试" type="error" :closable="false" />
    <template v-else>
      <div v-if="suggestions.length" class="proposals">
        <h3>待确认的信息</h3>
        <p>从健康画像及问诊信息自动整理，尚未保存为长期记忆。</p>
        <article v-for="item in suggestions" :key="item.key">
          <small>{{ item.source }}</small>
          <p>{{ item.content }}</p>
          <p v-if="item.previous">当前记忆：{{ item.previous }}（确认后将替换）</p>
          <el-button type="primary" plain @click="edit(item.key, item.content)">核实并保存</el-button>
          <el-button @click="suggestions = suggestions.filter(s => s.key !== item.key)">暂不保存</el-button>
        </article>
      </div>
      <h3>已保存 · {{ entries.length }} 条</h3>
      <el-empty v-if="!entries.length" description="还没有长期记忆，可手动添加或确认上方信息" :image-size="60" />
      <article v-for="entry in entries" :key="entry.memory_key">
        <p>{{ entry.value.content }}</p>
        <small v-if="entry.expires_at">有效至 {{ new Date(entry.expires_at).toLocaleDateString() }}</small>
        <div><el-button text type="primary" @click="edit(entry.memory_key, entry.value.content)">修改</el-button><el-button text type="danger" :disabled="busy" @click="remove(entry)">删除</el-button></div>
      </article>
    </template>
    <el-dialog v-model="editing" title="确认长期记忆" width="min(560px, 94vw)" :close-on-click-modal="false">
      <el-input v-model="content" aria-label="记忆内容" type="textarea" :rows="5" maxlength="2000" show-word-limit />
      <el-checkbox v-model="consent" class="consent">我已核实内容，同意保存并用于后续问诊</el-checkbox>
      <template #footer><el-button :disabled="busy" @click="editing = false">取消</el-button><el-button type="primary" :loading="busy" :disabled="!consent || !content.trim()" @click="save">确认保存</el-button></template>
    </el-dialog>
  </section>
</template>

<style scoped>
.memory-panel { margin-top: 24px; }
.memory-heading { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; align-items: center; }
h2 { font-size: 18px; margin: 0; } h3 { font-size: 15px; }
p { line-height: 1.7; white-space: pre-wrap; overflow-wrap: anywhere; }
small { color: var(--tcm-text-dim); }
article { padding: 14px 0; border-bottom: 1px solid var(--el-border-color-light); }
.proposals { background: var(--el-fill-color-light); padding: 16px; border-radius: 10px; }
.consent { margin-top: 20px; height: auto; white-space: normal; }
</style>
