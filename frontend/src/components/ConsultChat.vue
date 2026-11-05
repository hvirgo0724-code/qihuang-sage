<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { Promotion } from '@element-plus/icons-vue'
import { sendChatMessage } from '@/api/modules'
import { renderMarkdown } from '@/utils/markdown'
import type { ChatMessage, SyndromeReport, InquiryChoice } from '@/types'

const props = withDefaults(
  defineProps<{
    sessionId: number | null
    initialMessages?: ChatMessage[]
  }>(),
  {
    initialMessages: () => [],
  },
)

const emit = defineEmits<{
  (e: 'result', report: SyndromeReport): void
  (e: 'done', sessionId: number): void
  (e: 'busy', value: boolean): void
  (e: 'pending'): void
}>()

const router = useRouter()

interface UIMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  phase?: string
  isResult?: boolean
  pendingReview?: boolean
  choices?: InquiryChoice[]
}

const messages = ref<UIMessage[]>([])
const input = ref('')
const sending = ref(false)
const selections = ref<Record<string, string[]>>({})
const choicePage = ref(0)
const allQuestions = computed(() => {
  const last = messages.value[messages.value.length - 1]
  return !sending.value && last?.role === 'assistant' ? last.choices ?? [] : []
})
const activeQuestions = computed(() => {
  return allQuestions.value.slice(choicePage.value * 2, choicePage.value * 2 + 2)
})
watch(allQuestions, () => { choicePage.value = 0 })
watch(sending, value => emit('busy', value))
const streaming = ref(false)
const disclaimer = ref('')
const listRef = ref<HTMLElement | null>(null)

const phaseText: Record<string, string> = {
  inquiry: '四诊追问',
  syndrome: '辨证分析',
  treatment: '论治建议',
  emergency: '急危重症引导',
}

let uid = 0
function nextId(): string {
  uid += 1
  return `m-${Date.now()}-${uid}`
}

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

const exclusive = new Set(['不清楚', '其他（请补充）', '正常', '无明显异常', '平稳', '不适用', '已绝经'])
function toggleChoice(q: InquiryChoice, option: string) {
  const current = selections.value[q.id] ?? []
  if (current.includes(option)) {
    selections.value[q.id] = current.filter(v => v !== option)
  } else if (!q.multiple || exclusive.has(option)) {
    selections.value[q.id] = [option]
  } else {
    selections.value[q.id] = [...current.filter(v => !exclusive.has(v)), option]
  }
}
function setAge(value: string) {
  selections.value.age = /^\d{1,3}$/.test(value) && Number(value) <= 150 ? [value] : []
}

async function send() {
  const answers = allQuestions.value
    .filter(q => selections.value[q.id]?.length)
    .map(q => `${q.label}：${selections.value[q.id].join('、')}${q.input_type === 'age' ? '岁' : ''}`)
  const supplement = input.value.trim()
  const text = [...answers, ...(supplement ? [answers.length ? `补充：${supplement}` : supplement] : [])].join('\n')
  await sendText(text)
}

async function sendText(text: string) {
  if (!text || sending.value) return
  if (!props.sessionId) {
    ElMessage.warning('请先创建问诊会话')
    return
  }

  messages.value.push({ id: nextId(), role: 'user', content: text })
  const previousInput = input.value
  const previousSelections = { ...selections.value }
  input.value = ''
  selections.value = {}
  let failed = false
  sending.value = true
  streaming.value = true

  const assistant = reactive<UIMessage>({ id: nextId(), role: 'assistant', content: '' })
  messages.value.push(assistant)
  scrollToBottom()

  try {
    await sendChatMessage(props.sessionId, text, {
    onChoices: (data) => {
      assistant.choices = data.questions
    },
    onPhase: (phase) => {
      assistant.phase = phase
      scrollToBottom()
    },
    onChunk: (chunk) => {
      assistant.content += chunk
      scrollToBottom()
    },
    onResult: (report) => {
      emit('result', report)
      const hint: UIMessage = {
        id: nextId(),
        role: 'system',
        content: '辨证报告已生成，点击下方按钮即可查看详情。',
        isResult: true,
      }
      messages.value.push(hint)
      scrollToBottom()
    },
    onReviewPending: (data) => {
      emit('pending')
      messages.value.push({ id: nextId(), role: 'system', content: data.message, isResult: true, pendingReview: true })
      ElMessage.success({ message: data.message, duration: 6000 })
      scrollToBottom()
    },
    onDisclaimer: (text) => {
      disclaimer.value = text
    },
    onDone: (data) => {
      emit('done', data.session_id)
    },
    onError: (msg) => {
      failed = true
      ElMessage.error(msg)
    },
    })
  } finally {
    if (failed) {
      input.value = previousInput || text
      selections.value = previousSelections
    }
    sending.value = false
    streaming.value = false
    scrollToBottom()
  }
}

defineExpose({ generateReport: () => sendText('生成报告') })

function goResult() {
  if (props.sessionId) {
    router.push(`/consult/${props.sessionId}/result`)
  }
}

onMounted(() => {
  if (!props.initialMessages.some(m => m.type === 'text' || m.type === 'result')) {
    messages.value.push({
      id: nextId(), role: 'assistant', phase: 'inquiry',
      content: '我们先了解基本信息：本次咨询者的性别和年龄？您也可以在下方补充主要不适。',
      choices: [
        { id: 'sex', label: '性别', options: ['男', '女', '其他', '暂不提供'] },
        { id: 'age', label: '年龄', options: [], input_type: 'age' },
      ],
    })
  }
  if (props.initialMessages.length) {
    for (const m of props.initialMessages) {
      if (m.type === 'image') {
        if (props.initialMessages.some(item => item.type === 'text' || item.type === 'result')) {
          messages.value.push({ id: nextId(), role: 'system', content: '已上传影像资料' })
        } else {
          messages.value.unshift({ id: nextId(), role: 'system', content: '已上传影像资料' })
        }
      } else if (m.type === 'result') {
        messages.value.push({ id: nextId(), role: 'system', content: m.content, isResult: true })
      } else if (m.type === 'text') {
        messages.value.push({
          id: nextId(),
          role: m.role === 'user' ? 'user' : 'assistant',
          content: m.content,
          choices: (m.meta as { choices?: InquiryChoice[] } | null)?.choices,
        })
      }
    }
  }
  scrollToBottom()
})
</script>

<template>
  <div class="consult-chat">
    <div class="chat-list" ref="listRef">
      <div v-if="messages.length === 0" class="chat-empty">
        请描述您的主诉与不适感受，AI 将基于四诊信息进行辨证分析与调养建议。舌象/面色图片可先行上传以辅助辨证。
      </div>

      <div
        v-for="msg in messages"
        :key="msg.id"
        class="chat-row"
        :class="msg.role"
      >
        <div v-if="msg.role === 'system'" class="system-row">
          <el-alert
            :type="msg.pendingReview ? 'warning' : 'success'"
            :closable="false"
            show-icon
            :title="msg.pendingReview ? '辨证分析已完成 · 待医生确认' : msg.isResult ? '报告审核与发布' : '问诊资料'"
            :description="msg.content"
            class="system-alert"
          >
            <template #default>
              <p>{{ msg.content }}</p>
              <el-button v-if="msg.isResult" type="primary" size="small" @click="goResult">查看报告状态</el-button>
            </template>
          </el-alert>
        </div>

        <template v-else>
          <div class="bubble" :class="msg.role">
            <el-tag
              v-if="msg.phase"
              size="small"
              effect="dark"
              class="phase-tag"
              :type="msg.phase === 'emergency' ? 'danger' : 'info'"
            >
              {{ phaseText[msg.phase] || msg.phase }}
            </el-tag>
            <template v-if="msg.role === 'assistant' && (msg.choices?.length ?? 0) > 2">
              <p>我们分步了解您的情况，每次回答一两项即可，也可以随时补充描述。</p>
              <details><summary>查看完整问题（可选）</summary>
                <div class="markdown-body" v-html="renderMarkdown(msg.content)" />
              </details>
            </template>
            <div v-else-if="msg.role === 'assistant'" class="markdown-body" v-html="renderMarkdown(msg.content)" />
            <div v-else class="user-text">{{ msg.content }}</div>
            <div v-if="streaming && msg.role === 'assistant' && msg.id === messages[messages.length - 1]?.id" class="cursor" />
          </div>
        </template>
      </div>

      <div v-if="disclaimer" class="disclaimer-line">⚠ {{ disclaimer }}</div>
    </div>

    <div v-if="activeQuestions.length" class="answer-choices">
      <p>先回答眼前的一两项即可，点击“提交回答”后继续交流。不清楚可跳过，也可以补充文字。</p>
      <div v-for="q in activeQuestions" :key="q.id" class="choice-group">
        <strong>{{ q.label }} <small v-if="q.multiple">（可多选）</small></strong>
        <el-input v-if="q.input_type === 'age'" :model-value="selections[q.id]?.[0] ?? ''"
          @update:model-value="setAge" inputmode="numeric" maxlength="3" placeholder="填写实际年龄（岁，可跳过）" />
        <div v-else class="choice-buttons" role="group" :aria-label="q.label">
          <el-button v-for="option in q.options" :key="option"
            :type="selections[q.id]?.includes(option) ? 'primary' : 'default'"
            :aria-pressed="selections[q.id]?.includes(option) ?? false"
            @click="toggleChoice(q, option)">{{ option }}</el-button>
        </div>
      </div>
      <div v-if="allQuestions.length > 2" class="choice-buttons">
        <el-button size="small" :disabled="choicePage === 0" @click="choicePage--">上一组</el-button>
        <el-button size="small" :disabled="(choicePage + 1) * 2 >= allQuestions.length" @click="choicePage++">继续补充其他问题（可选）</el-button>
      </div>
      <el-button size="small" text @click="selections = {}">清空选择</el-button>
    </div>
    <div class="chat-input">
      <el-input
        v-model="input"
        type="textarea"
        :rows="2"
        resize="none"
        :placeholder="activeQuestions.length ? '补充描述（选填），也可以直接输入完整回答…' : '请输入您的主诉或症状，例如：最近睡眠不好，容易疲劳…'"
        @keydown.enter.exact.prevent="send"
      />
      <el-button
        type="primary"
        :icon="Promotion"
        :loading="sending"
        :disabled="streaming"
        class="send-btn"
        @click="send"
      >
        {{ activeQuestions.length ? '提交回答' : '发送' }}
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.answer-choices { padding: 12px; border-top: 1px solid var(--tcm-border-soft); }
.answer-choices p { color: var(--tcm-text-dim); font-size: 13px; }
.choice-group { display: flex; flex-direction: column; gap: 4px; margin-bottom: 10px; }
.choice-buttons { display: flex; flex-wrap: wrap; gap: 8px; }
.choice-buttons .el-button { margin-left: 0; white-space: normal; height: auto; min-height: 36px; }
.choice-group small { font-weight: normal; color: var(--tcm-text-dim); }
.answer-choices { max-height: 360px; overflow-y: auto; background: var(--tcm-bg-soft); border-radius: 10px; margin: 12px 0; }
.consult-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 4px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 280px;
  max-height: 480px;
}

.chat-empty {
  color: var(--tcm-text-faint);
  text-align: center;
  padding: 40px 20px;
  font-size: 13px;
  line-height: 1.7;
}

.chat-row {
  display: flex;
}

.chat-row.user {
  justify-content: flex-end;
}

.chat-row.assistant {
  justify-content: flex-start;
}

.bubble {
  max-width: 90%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.8;
}

.bubble.user {
  background: var(--tcm-primary-deep);
  color: #eaf7f5;
  border-bottom-right-radius: 4px;
}

.bubble.assistant {
  background: var(--tcm-panel);
  border: 1px solid var(--tcm-border-soft);
  color: var(--tcm-text);
  border-bottom-left-radius: 4px;
  width: fit-content;
}

.user-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.phase-tag {
  margin-bottom: 6px;
}

.system-row {
  width: 100%;
}

.system-alert {
  --el-alert-bg-color: rgba(63, 174, 122, 0.12);
  border-radius: 10px;
}

.cursor {
  display: inline-block;
  width: 6px;
  height: 15px;
  background: var(--tcm-primary);
  animation: blink 0.8s infinite;
  vertical-align: text-bottom;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.disclaimer-line {
  color: var(--tcm-gold);
  font-size: 12px;
  line-height: 1.6;
  padding: 8px 10px;
  background: rgba(212, 162, 59, 0.08);
  border-radius: 8px;
}

.chat-input {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--tcm-border-soft);
}

.send-btn {
  flex-shrink: 0;
}
</style>
