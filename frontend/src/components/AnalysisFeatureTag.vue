<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  result: Record<string, unknown> | null | undefined
}>()

interface TagItem {
  key: string
  label: string
  value: string
  warning?: boolean
}

const FIELD_LABELS: Record<string, string> = {
  tongue_color: '舌色',
  tongue_shape: '舌形',
  coating: '舌苔',
  moisture: '润燥',
  sublingual: '舌下络脉',
  complexion: '面色',
  sheen: '光泽',
  abnormal_regions: '异常区域',
  quality_flags: '质控提示',
  confidence: '置信度',
}

function flattenValue(value: unknown): string[] {
  if (value == null || value === '') return []
  if (Array.isArray(value)) {
    return value.map((v) => String(v)).filter((s) => s.trim() !== '')
  }
  return [String(value)]
}

const tags = computed<TagItem[]>(() => {
  if (!props.result) return []
  const items: TagItem[] = []
  for (const [key, value] of Object.entries(props.result)) {
    if (key === 'confidence') continue
    const values = flattenValue(value)
    if (values.length === 0) continue
    const label = FIELD_LABELS[key] ?? key
    for (const v of values) {
      items.push({ key, label, value: v, warning: key === 'quality_flags' })
    }
  }
  return items
})
</script>

<template>
  <div v-if="tags.length" class="feature-tags">
    <el-tag
      v-for="(t, i) in tags"
      :key="`${t.key}-${i}`"
      :type="t.warning ? 'warning' : 'success'"
      effect="dark"
      round
      class="feature-tag"
    >
      <span class="label">{{ t.label }}</span>
      <span class="value">{{ t.value }}</span>
    </el-tag>
  </div>
  <div v-else class="feature-empty">暂无识别特征</div>
</template>

<style scoped>
.feature-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feature-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.feature-tag .label {
  color: var(--tcm-text-dim);
}

.feature-tag .value {
  font-weight: 600;
}

.feature-empty {
  color: var(--tcm-text-faint);
  font-size: 13px;
}
</style>