<template>
  <div class="triage">
    <div class="page-head">
      <div>
        <h2>AI 智能分诊</h2>
        <p class="sub">描述您的症状，助手会帮您推荐合适的挂号科室</p>
      </div>
      <el-button v-if="messages.length" plain :disabled="sending" @click="handleReset">
        重新开始
      </el-button>
    </div>

    <el-alert type="info" :closable="false" class="tip">
      本功能仅推荐科室，不提供诊断和用药建议。如遇紧急情况请立即就医或呼叫急救。
    </el-alert>

    <div ref="scrollRef" class="chat-box">
      <div v-if="!messages.length" class="empty">
        <p class="empty-title">您可以这样描述：</p>
        <div class="examples">
          <el-tag
            v-for="example in examples"
            :key="example"
            class="example"
            effect="plain"
            @click="useExample(example)"
          >
            {{ example }}
          </el-tag>
        </div>
      </div>

      <div v-for="(msg, idx) in messages" :key="idx" :class="['row', msg.role]">
        <div class="avatar">{{ msg.role === 'user' ? '我' : 'AI' }}</div>
        <div class="bubble">
          <div v-if="msg.role === 'user'" class="text">{{ msg.content }}</div>
          <div
            v-else-if="msg.content"
            class="text markdown"
            v-html="renderMarkdown(msg.content)"
          />
          <div v-else class="text thinking">
            正在分析您的症状<span class="typing-dots">...</span>
          </div>

          <div v-if="msg.recommendations?.length" class="recommend">
            <div class="recommend-title">推荐科室</div>
            <div class="recommend-list">
              <div v-for="rec in msg.recommendations" :key="rec.department_id" class="recommend-item">
                <span class="dept-name">{{ rec.department_name }}</span>
                <el-tag size="small" :type="confidenceType(rec.confidence)">
                  {{ confidenceLabel(rec.confidence) }}
                </el-tag>
                <el-button size="small" type="primary" link @click="goBooking(rec)">
                  去挂号
                </el-button>
              </div>
            </div>
          </div>
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
        placeholder="请描述症状，例如：位置、持续时间、伴随症状（Enter 发送，Shift+Enter 换行）"
        @keydown.enter.exact.prevent="handleSend"
      />
      <el-button type="primary" :loading="sending" class="send-btn" @click="handleSend">
        发送
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { triageChatStream, type DepartmentRecommendation } from '../../api/triage'
import { renderMarkdown } from '../../utils/markdown'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  recommendations?: DepartmentRecommendation[]
}

const router = useRouter()
const messages = ref<ChatMessage[]>([])
const draft = ref('')
const sending = ref(false)
const sessionId = ref<string | undefined>(undefined)
const scrollRef = ref<HTMLElement | null>(null)

const examples = [
  '最近三天咳嗽，有黄痰，还有点发烧',
  '胃疼了一周，饭后加重，有点反酸',
  '经常头晕，早上起床时特别明显',
  '膝盖上下楼梯疼，已经一个多月了',
]

function useExample(text: string) {
  draft.value = text
}

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

    if (queue.length) {
      timer = window.setTimeout(pump, 24)
    } else if (sourceFinished) {
      settle()
    }
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
    ElMessage.warning('请先描述您的症状')
    return
  }
  if (sending.value) return

  messages.value.push({ role: 'user', content: text })
  draft.value = ''
  sending.value = true
  await scrollToBottom()

  let renderer: ReturnType<typeof createStreamRenderer> | undefined
  try {
    const assistantMessage = reactive<ChatMessage>({
      role: 'assistant',
      content: '',
      recommendations: [],
    })
    renderer = createStreamRenderer(assistantMessage)
    let finalRecommendations: DepartmentRecommendation[] = []
    messages.value.push(assistantMessage)
    await scrollToBottom()

    await triageChatStream(
      { message: text, session_id: sessionId.value },
      (event) => {
        if (event.type === 'start') {
          sessionId.value = event.session_id
        } else if (event.type === 'delta') {
          renderer?.append(event.content)
        } else if (event.type === 'replace') {
          renderer?.replace(event.content)
        } else if (event.type === 'done') {
          sessionId.value = event.session_id
          finalRecommendations = event.recommendations
        } else if (event.type === 'error') {
          throw new Error(event.message)
        }
      },
    )
    await renderer.finish()
    assistantMessage.recommendations = finalRecommendations
    await scrollToBottom()
  } catch {
    renderer?.cancel()
    // 移除本轮用户消息和未完成的 AI 消息，方便直接重发
    messages.value.splice(-2, 2)
    draft.value = text
    ElMessage.error('智能分诊暂时不可用，请稍后重试')
  } finally {
    sending.value = false
  }
}

function handleReset() {
  messages.value = []
  sessionId.value = undefined
  draft.value = ''
}

function confidenceLabel(level: string) {
  return { high: '最匹配', medium: '可考虑', low: '备选' }[level] ?? level
}

function confidenceType(level: string) {
  return ({ high: 'success', medium: 'warning', low: 'info' } as Record<string, any>)[level] ?? 'info'
}

function goBooking(rec: DepartmentRecommendation) {
  router.push({ path: '/booking', query: { department_id: rec.department_id } })
}
</script>

<style scoped>
.triage {
  max-width: 860px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.page-head h2 {
  margin: 0;
  color: #303133;
}
.sub {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}
.tip {
  margin: 16px 0;
}
.chat-box {
  height: 460px;
  overflow-y: auto;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ebeef5;
}
.empty {
  padding: 40px 0;
  text-align: center;
}
.empty-title {
  color: #909399;
  font-size: 14px;
}
.examples {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-top: 12px;
}
.example {
  cursor: pointer;
}
.row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}
.row.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #fff;
  flex-shrink: 0;
  background: #1976d2;
}
.row.assistant .avatar {
  background: #67c23a;
}
.bubble {
  max-width: 78%;
  padding: 10px 14px;
  border-radius: 8px;
  background: #f4f4f5;
  font-size: 14px;
  line-height: 1.7;
}
.row.user .bubble {
  background: #ecf5ff;
}
.thinking {
  color: #909399;
}
.typing-dots {
  display: inline-block;
  width: 1.5em;
  overflow: hidden;
  vertical-align: bottom;
  animation: typing-dots 1.2s steps(4, end) infinite;
}
@keyframes typing-dots {
  from { width: 0; }
  to { width: 1.5em; }
}
.markdown :deep(p) {
  margin: 0 0 8px;
}
.markdown :deep(p:last-child) {
  margin-bottom: 0;
}
.markdown :deep(ul) {
  margin: 6px 0;
  padding-left: 20px;
}
.recommend {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #dcdfe6;
}
.recommend-title {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}
.recommend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
}
.dept-name {
  font-weight: 500;
  color: #303133;
}
.input-area {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}
.send-btn {
  height: 40px;
  flex-shrink: 0;
}
</style>
