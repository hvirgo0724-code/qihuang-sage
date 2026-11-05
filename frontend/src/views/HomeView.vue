<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Camera, ChatDotRound, DocumentChecked, Share } from '@element-plus/icons-vue'
import DisclaimerBar from '@/components/DisclaimerBar.vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const { isLoggedIn } = storeToRefs(auth)

const abilities = [
  {
    icon: Camera,
    title: '舌面影像识别',
    desc: '上传舌象 / 面色照片，多模态模型智能识别特征，辅助整体辨证。',
  },
  {
    icon: ChatDotRound,
    title: '四诊智能对话',
    desc: '沿「十问歌」思路逐层追问，结构化收集主诉、寒热、饮食、睡眠等信息。',
  },
  {
    icon: DocumentChecked,
    title: '辨证报告与调养',
    desc: '报告草稿由医生审核确认后发布，包含辨证依据与饮食、生活调养建议。',
  },
  {
    icon: Share,
    title: '方剂知识图谱',
    desc: '查看相关中医方剂知识与来源，了解报告使用的参考依据。',
  },
]

function startConsult() {
  router.push('/consult/start')
}
</script>

<template>
  <div class="home">
    <section class="hero">
      <div class="hero-badge">四诊合参 · 辨证论治</div>
      <h1 class="hero-title">岐黄智诊</h1>
      <p class="hero-sub">Qihuang Sage · 中医智能诊疗协同平台</p>
      <p class="hero-desc">
        以望、闻、问、切为纲，融合舌面影像识别与中医方剂知识图谱，为您提供参考性的辨证分析与调养建议。
      </p>
      <div class="hero-actions">
        <el-button type="primary" size="large" @click="startConsult">
          {{ isLoggedIn ? '开始问诊' : '立即体验' }}
        </el-button>
        <el-button size="large" @click="router.push('/knowledge')">浏览知识库</el-button>
      </div>
    </section>

    <section class="abilities">
      <el-card v-for="a in abilities" :key="a.title" class="ability-card" shadow="hover">
        <div class="ability-icon">
          <el-icon :size="26"><component :is="a.icon" /></el-icon>
        </div>
        <h3 class="ability-title">{{ a.title }}</h3>
        <p class="ability-desc">{{ a.desc }}</p>
      </el-card>
    </section>

    <section class="home-disclaimer">
      <DisclaimerBar />
    </section>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.hero {
  text-align: center;
  padding: 56px 24px 48px;
  background: #ffffff; border: 1px solid var(--tcm-border-soft); border-radius: 16px;
}

.hero-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 20px;
  background: rgba(43, 179, 163, 0.12);
  color: var(--tcm-primary);
  font-size: 13px;
  letter-spacing: 1px;
  margin-bottom: 20px;
}

.hero-title {
  font-size: clamp(32px, 5vw, 48px);
  font-weight: 800;
  margin: 0 0 8px;
  letter-spacing: 2px;
  background: linear-gradient(120deg, var(--tcm-primary), var(--tcm-gold));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-sub {
  font-size: 15px;
  color: var(--tcm-gold);
  letter-spacing: 2px;
  margin: 0 0 20px;
}

.hero-desc {
  max-width: 560px;
  margin: 0 auto 28px;
  color: var(--tcm-text-dim);
  line-height: 1.8;
}

.abilities {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 18px;
}

.ability-card {
  text-align: center;
  padding: 10px;
}

.ability-icon {
  width: 56px;
  height: 56px;
  margin: 10px auto 14px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(43, 179, 163, 0.14);
  color: var(--tcm-primary);
}

.ability-title {
  margin: 0 0 8px;
  font-size: 16px;
  color: var(--tcm-text);
}

.ability-desc {
  margin: 0;
  color: var(--tcm-text-dim);
  font-size: 13px;
  line-height: 1.7;
}

.home-disclaimer {
  max-width: 760px;
  margin: 0 auto;
  width: 100%;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 38px;
  }
}
</style>