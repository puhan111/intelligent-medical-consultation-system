<template>
  <el-drawer
    :model-value="visible"
    :title="`追问 · ${report?.type ?? ''}`"
    size="520px"
    @update:model-value="$emit('update:visible', $event)"
    @closed="handleClosed"
  >
    <div class="chat">
      <el-alert type="info" :closable="false" class="tip">
        可就本份报告的指标继续提问。回答不构成诊断，异常指标请及时就医。
      </el-alert>

      <div ref="scrollRef" class="messages">
        <div v-if="!messages.length" class="empty">
          <p class="empty-title">您可以这样问：</p>
          <div class="suggestions">
            <el-tag
              v-for="s in suggestions"
              :key="s"
              class="suggestion"
              effect="plain"
              @click="draft = s"
            >
              {{ s }}
            </el-tag>
          </div>
        </div>

        <div v-for="(msg, idx) in messages" :key="idx" :class="['row', msg.role]">
          <div class="avatar">{{ msg.role === 'user' ? '我' : 'AI' }}</div>
          <div class="bubble">
            <div v-if="msg.role === 'user'" class="text">{{ msg.content }}</div>
            <div v-else class="text markdown" v-html="renderMarkdown(msg.content)" />
          </div>
        </div>

      </div>

      <div class="input-area">
        <el-input
          v-model="draft"
          type="textarea"
          :rows="3"
          maxlength="500"
          show-word-limit
          resize="none"
          placeholder="输入您的问题（Enter 发送，Shift+Enter 换行）"
          @keydown.enter.exact.prevent="handleSend"
        />
        <el-button type="primary" :loading="sending" class="send-btn" @click="handleSend">
          发送
        </el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { chatAboutReportStream, type Report } from '../api/report'
import { renderMarkdown } from '../utils/markdown'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

const props = defineProps<{
  visible: boolean
  report: Report | null
}>()

defineEmits<{ 'update:visible': [boolean] }>()

const messages = ref<ChatMessage[]>([])
const draft = ref('')
const sending = ref(false)
const sessionId = ref<string | undefined>(undefined)
const scrollRef = ref<HTMLElement | null>(null)

const suggestions = [
  '这些指标说明什么问题？',
  '异常的指标严重吗？',
  '我需要注意什么？',
  '需要复查吗？',
]

// 切换到另一份报告时重置会话，避免上下文串台
watch(
  () => props.report?.id,
  () => {
    messages.value = []
    sessionId.value = undefined
    draft.value = ''
  }
)

async function scrollToBottom() {
  await nextTick()
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight
  }
}

function createStreamRenderer(message: ChatMessage) {
  const queue: string[] = []
  let timer: number | undefined
  let sourceFinished = false
  let settled = false
  let resolveDrain: () => void
  const drained = new Promise<void>((resolve) => {
    resolveDrain = resolve
  })

  const settle = () => {
    if (!settled) {
      settled = true
      resolveDrain()
    }
  }
  const pump = () => {
    timer = undefined
    const character = queue.shift()
    if (character !== undefined) {
      message.content += character
      void scrollToBottom()
    }
    if (queue.length) timer = window.setTimeout(pump, 24)
    else if (sourceFinished) settle()
  }

  return {
    append(content: string) {
      queue.push(...Array.from(content))
      if (timer === undefined) pump()
    },
    async finish() {
      sourceFinished = true
      if (!queue.length && timer === undefined) settle()
      await drained
    },
    replace(content: string) {
      queue.length = 0
      if (timer !== undefined) window.clearTimeout(timer)
      timer = undefined
      sourceFinished = true
      message.content = content
      settle()
    },
    cancel() {
      queue.length = 0
      if (timer !== undefined) window.clearTimeout(timer)
      timer = undefined
      sourceFinished = true
      settle()
    },
  }
}

async function handleSend() {
  const text = draft.value.trim()
  if (!text) {
    ElMessage.warning('请输入您的问题')
    return
  }
  if (sending.value || !props.report) return

  messages.value.push({ role: 'user', content: text })
  draft.value = ''
  sending.value = true
  await scrollToBottom()

  let renderer: ReturnType<typeof createStreamRenderer> | undefined
  try {
    const assistantMessage = reactive<ChatMessage>({ role: 'assistant', content: '' })
    renderer = createStreamRenderer(assistantMessage)
    messages.value.push(assistantMessage)
    await scrollToBottom()

    await chatAboutReportStream(
      props.report.id,
      text,
      sessionId.value,
      (event) => {
        if (event.type === 'start' || event.type === 'done') {
          sessionId.value = event.session_id
        } else if (event.type === 'delta') {
          renderer?.append(event.content)
        } else if (event.type === 'replace') {
          renderer?.replace(event.content)
        } else if (event.type === 'error') {
          throw new Error(event.message)
        }
      },
    )
    await renderer.finish()
    await scrollToBottom()
  } catch {
    renderer?.cancel()
    // 失败时移除本轮用户消息和未完成的 AI 消息，方便直接重发
    messages.value.splice(-2, 2)
    draft.value = text
    ElMessage.error('报告追问暂时不可用，请稍后重试')
  } finally {
    sending.value = false
  }
}

function handleClosed() {
  // 抽屉关闭保留会话，重新打开同一份报告可继续之前的对话
  draft.value = ''
}
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.tip {
  margin-bottom: 14px;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}
.empty {
  padding: 30px 0;
  text-align: center;
}
.empty-title {
  color: #909399;
  font-size: 13px;
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 12px;
}
.suggestion {
  cursor: pointer;
}
.row {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}
.row.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #fff;
  flex-shrink: 0;
  background: #1976d2;
}
.row.assistant .avatar {
  background: #67c23a;
}
.bubble {
  max-width: 80%;
  padding: 10px 13px;
  border-radius: 8px;
  background: #f4f4f5;
  font-size: 13px;
  line-height: 1.75;
}
.row.user .bubble {
  background: #ecf5ff;
}
.thinking {
  color: #909399;
}
.markdown :deep(p) {
  margin: 0 0 8px;
}
.markdown :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown :deep(ul),
.markdown :deep(ol) {
  margin: 6px 0;
  padding-left: 20px;
}
.markdown :deep(li) {
  margin-bottom: 4px;
}
.markdown :deep(h3),
.markdown :deep(h4) {
  margin: 10px 0 6px;
  font-size: 13px;
}
.markdown :deep(hr) {
  border: none;
  border-top: 1px solid #e4e7ed;
  margin: 12px 0;
}
.input-area {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding-top: 14px;
  border-top: 1px solid #ebeef5;
}
.send-btn {
  height: 38px;
  flex-shrink: 0;
}
</style>
