<script setup lang="ts">
import { computed } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{
    text?: string
    compact?: boolean
  }>(),
  {
    text: '本结果由 AI 生成，仅供参考，不构成医疗诊断、治疗方案或处方建议，不能替代执业医师的当面诊断。若身体不适，请及时前往正规医疗机构就诊，切勿自行用药。',
    compact: false,
  },
)

const cls = computed(() => (props.compact ? 'disclaimer compact' : 'disclaimer'))
</script>

<template>
  <div :class="cls">
    <el-icon class="disclaimer-icon"><WarningFilled /></el-icon>
    <span class="disclaimer-text">{{ text }}</span>
  </div>
</template>

<style scoped>
.disclaimer {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: rgba(212, 162, 59, 0.1);
  border: 1px solid rgba(212, 162, 59, 0.35);
  border-radius: 10px;
  padding: 12px 14px;
  color: var(--tcm-text-dim);
  font-size: 13px;
  line-height: 1.6;
}

.disclaimer.compact {
  padding: 8px 12px;
  font-size: 12px;
}

.disclaimer-icon {
  color: var(--tcm-gold);
  margin-top: 2px;
  flex-shrink: 0;
}

.disclaimer-text {
  flex: 1;
}
</style>