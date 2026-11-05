<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { GraphRef } from '@/types'

const props = defineProps<{
  graphRef: GraphRef
}>()

const router = useRouter()

const typeText: Record<string, string> = {
  Formula: '方剂',
  Herb: '中药',
  Syndrome: '证型',
  Symptom: '症状',
}

const typeTarget: Record<string, string> = {
  Formula: 'formula',
  Herb: 'herb',
  Syndrome: 'syndrome',
  Symptom: 'symptom',
}

function navigate() {
  const target = typeTarget[props.graphRef.label]
  if (target) {
    router.push({ path: '/knowledge', query: { q: props.graphRef.name, type: target } })
  }
}
</script>

<template>
  <el-card shadow="hover" class="graph-ref" @click="navigate">
    <div class="ref-head">
      <el-tag size="small" effect="dark" class="ref-type">{{ typeText[graphRef.label] }}</el-tag>
      <span class="ref-name">{{ graphRef.name }}</span>
    </div>
    <p class="ref-desc">{{ graphRef.description }}</p>
    <div class="ref-source">出处：{{ graphRef.source || '—' }}</div>
  </el-card>
</template>

<style scoped>
.graph-ref {
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.graph-ref:hover {
  transform: translateY(-2px);
  border-color: var(--tcm-primary) !important;
}

.ref-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.ref-type {
  --el-tag-bg-color: var(--tcm-primary-deep);
  --el-tag-border-color: var(--tcm-primary-deep);
  flex-shrink: 0;
}

.ref-name {
  font-weight: 600;
  color: var(--tcm-text);
  font-size: 15px;
}

.ref-desc {
  color: var(--tcm-text-dim);
  font-size: 13px;
  line-height: 1.6;
  margin: 0 0 8px;
}

.ref-source {
  color: var(--tcm-text-faint);
  font-size: 12px;
}
</style>