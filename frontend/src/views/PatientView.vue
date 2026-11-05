<script setup lang="ts">
import HistoryView from './HistoryView.vue'
</script>
<template>
  <div>
    <section class="patient-welcome workspace-panel">
      <div><span class="eyebrow">PATIENT WORKSPACE</span><h1>您的健康咨询工作台</h1><p>从一次交流开始，逐步了解身体状况。报告由医生审核确认后向您发布。</p></div>
      <el-button type="primary" size="large" @click="$router.push('/consult/start')">开始新问诊 →</el-button>
    </section>
    <div class="care-path"><span>01 · 完善基本信息</span><span>02 · 四诊交流与影像</span><span>03 · 医生审核报告</span><span>04 · 查看调养建议</span></div>
    <HistoryView />
  </div>
</template>
<style scoped>
.patient-welcome { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 24px; border-left: 4px solid var(--tcm-primary); padding: 32px; }
.patient-welcome h1 { margin: 8px 0 12px; }
.patient-welcome p { color: var(--tcm-text-dim); margin: 0; line-height: 1.8; max-width: 640px; }
.care-path { display: flex; flex-wrap: wrap; gap: 12px 32px; padding: 22px 0 32px; color: var(--tcm-text-dim); font-size: 13px; }
</style>
