<script setup lang="ts">
import { ref, watch } from 'vue'
import { clinical, type Encounter } from '@/api/clinical'
import { ElMessage } from 'element-plus'
const props = defineProps<{ sessionId: number; value: NonNullable<Encounter['report_review']> }>()
const emit = defineEmits<{ changed: [] }>()
const fields = ref<Record<string, string>>({}), revision = ref(0), busy = ref(false), dirty = ref(false)
const labels: Record<string, string> = { syndrome: '辨证结论', treatment_principle: '调养原则', disclaimer: '说明', differential: '鉴别分析', diet_advice: '饮食建议', acupoint_advice: '穴位建议', lifestyle_advice: '生活建议' }
const structured: Record<string, string> = { evidence: '辨证依据', formula_suggestions: '方剂参考', graph_refs: '知识来源' }
const draft = ref<Record<string, unknown> & { risk_level: string; emergency_flag: boolean }>({ risk_level: 'low', emergency_flag: false })
function reset() {
  draft.value = { ...props.value.report, risk_level: String(props.value.report.risk_level || 'low'), emergency_flag: Boolean(props.value.report.emergency_flag) }
  revision.value = props.value.revision
  for (const key of Object.keys(labels)) {
    const value = draft.value[key]
    fields.value[key] = Array.isArray(value) ? value.join('\n') : String(value ?? '')
  }
  for (const key of Object.keys(structured)) fields.value[key] = JSON.stringify(draft.value[key] ?? [], null, 2)
  dirty.value = false
}
watch(() => props.value.analysis_id, reset, { immediate: true })
async function save() {
  busy.value = true
  try {
    const report = { ...draft.value }
    for (const key of Object.keys(labels)) report[key] = ['syndrome', 'treatment_principle', 'disclaimer'].includes(key) ? fields.value[key] : fields.value[key].split('\n').map(x => x.trim()).filter(Boolean)
    for (const key of Object.keys(structured)) report[key] = JSON.parse(fields.value[key])
    const response = await clinical.saveReport(props.sessionId, props.value.analysis_id, revision.value, report)
    revision.value = response.data.revision
    draft.value = { ...report, risk_level: String(report.risk_level), emergency_flag: Boolean(report.emergency_flag) }
    dirty.value = false
    ElMessage.success('草稿已保存，患者暂不可见')
    emit('changed')
  } catch { ElMessage.error('保存失败，请检查内容格式；版本冲突时请重新载入') }
  finally { busy.value = false }
}
async function confirm() {
  busy.value = true
  try { await clinical.confirmReport(props.sessionId, props.value.analysis_id, revision.value); ElMessage.success('报告已确认并发布给患者'); emit('changed') }
  catch { ElMessage.error('确认失败，请检查报告内容及版本') }
  finally { busy.value = false }
}
</script>
<template>
  <section>
    <h3>报告审核：{{ value.status === 'confirmed' ? '已确认发布' : '待审核' }}</h3>
    <p v-if="value.status !== 'confirmed'">修改并保存草稿后，点击确认发布，患者才能查看正式报告。列表内容每行一条。</p>
    <el-form label-position="top" :disabled="busy || value.status === 'confirmed'">
      <el-form-item v-for="(label, key) in labels" :key="key" :label="label"><el-input v-model="fields[key]" type="textarea" :rows="3" @input="dirty = true" /></el-form-item>
      <el-form-item label="风险等级"><el-select v-model="draft.risk_level" @change="dirty = true"><el-option v-for="level in ['low', 'medium', 'high', 'emergency']" :key="level" :value="level" :label="level" /></el-select></el-form-item>
      <el-checkbox v-model="draft.emergency_flag" @change="dirty = true">急危重症标记</el-checkbox>
      <el-collapse><el-collapse-item title="结构化依据、方剂与来源（JSON 数组）"><el-form-item v-for="(label, key) in structured" :key="key" :label="label"><el-input v-model="fields[key]" type="textarea" :rows="8" @input="dirty = true" /></el-form-item></el-collapse-item></el-collapse>
    </el-form>
    <template v-if="value.status !== 'confirmed'">
      <el-button :loading="busy" @click="save">保存草稿</el-button>
      <el-button :disabled="busy || dirty || revision < 1" type="primary" @click="confirm">确认并发布给患者</el-button>
      <el-button :disabled="busy" @click="reset">重新载入服务器草稿</el-button>
    </template>
  </section>
</template>
