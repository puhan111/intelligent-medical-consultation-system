<template>
  <div class="reports">
    <div class="page-head">
      <h2>我的检查报告</h2>
      <el-button :loading="loading" @click="loadReports">刷新</el-button>
    </div>

    <el-alert type="info" :closable="false" class="tip">
      AI 解读用于帮助您理解报告内容，不构成诊断结论。指标异常请及时就医咨询医生。
    </el-alert>

    <el-empty v-if="!loading && !reports.length" description="暂无检查报告">
      <div class="empty-hint">报告由检验科出结果后录入系统</div>
    </el-empty>

    <div v-loading="loading" class="list">
      <el-card v-for="report in reports" :key="report.id" shadow="never" class="card">
        <div class="card-head">
          <div class="head-left">
            <span class="type">{{ report.type }}</span>
            <el-tag :type="statusTagType(report.interpretation_status)" size="small">
              {{ statusLabel(report.interpretation_status) }}
            </el-tag>
          </div>
          <div class="head-right">
            <el-button
              v-if="report.interpretation_status === 'completed'"
              type="primary"
              link
              @click="openChat(report)"
            >
              追问
            </el-button>
            <span class="time">{{ formatTime(report.created_at) }}</span>
          </div>
        </div>

        <el-table v-if="report.content?.items?.length" :data="report.content.items" size="small" border>
          <el-table-column prop="name" label="项目" min-width="130" />
          <el-table-column label="结果" width="110">
            <template #default="{ row }">
              <span :class="{ abnormal: isAbnormal(row.status) }">
                {{ row.value }} {{ row.unit }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="reference_range" label="参考范围" width="120" />
          <el-table-column label="提示" width="110">
            <template #default="{ row }">
              <el-tag v-if="row.status" :type="isAbnormal(row.status) ? 'danger' : 'success'" size="small" effect="plain">
                {{ row.status }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>

        <!-- content 结构不符合约定时兜底展示原始 JSON -->
        <pre v-else class="raw-content">{{ JSON.stringify(report.content, null, 2) }}</pre>

        <div class="interpret">
          <div class="interpret-head">
            <span class="interpret-title">AI 解读</span>
            <span v-if="report.interpretation_at" class="interpret-time">
              {{ formatTime(report.interpretation_at) }}
            </span>
          </div>

          <div v-if="report.interpretation_status === 'completed'" class="markdown" v-html="renderMarkdown(report.ai_interpretation || '')" />

          <div v-else-if="report.interpretation_status === 'pending'" class="state-box pending">
            <el-icon class="spin"><Loading /></el-icon>
            <span>解读生成中，通常需要十几秒，稍后可刷新查看</span>
          </div>

          <div v-else class="state-box failed">
            <el-icon><WarningFilled /></el-icon>
            <span>本次解读生成失败，请咨询医生了解报告内容</span>
          </div>
        </div>
      </el-card>
    </div>

    <el-pagination
      v-if="total > perPage"
      class="pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="perPage"
      :current-page="currentPage"
      @current-change="handlePageChange"
    />

    <ReportChatDrawer v-model:visible="chatVisible" :report="chatReport" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { Loading, WarningFilled } from '@element-plus/icons-vue'
import { listMyReports, type InterpretationStatus, type Report } from '../../api/report'
import { renderMarkdown } from '../../utils/markdown'
import ReportChatDrawer from '../../components/ReportChatDrawer.vue'

const chatVisible = ref(false)
const chatReport = ref<Report | null>(null)

function openChat(report: Report) {
  chatReport.value = report
  chatVisible.value = true
}

const reports = ref<Report[]>([])
const loading = ref(false)
const total = ref(0)
const perPage = ref(10)
const currentPage = ref(1)

// 有报告处于解读中时自动轮询，避免用户手动刷新
let pollTimer: ReturnType<typeof setTimeout> | null = null
const POLL_INTERVAL = 5000

const STATUS_LABEL: Record<InterpretationStatus, string> = {
  pending: '解读中',
  completed: '解读完成',
  failed: '解读失败',
}

function statusLabel(status: InterpretationStatus) {
  return STATUS_LABEL[status] ?? status
}

function statusTagType(status: InterpretationStatus) {
  return ({ pending: 'warning', completed: 'success', failed: 'danger' } as Record<string, any>)[status] ?? 'info'
}

/** 兼容英文状态与中文正常标签；精确匹配，避免将「不正常」判为正常 */
function isAbnormal(status?: string) {
  const value = status?.trim().toLowerCase()
  return !!value && value !== 'normal' && value !== '正常'
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function schedulePoll() {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
  // 仅在存在解读中的报告时才继续轮询
  if (!reports.value.some((r) => r.interpretation_status === 'pending')) return

  pollTimer = setTimeout(() => loadReports(true), POLL_INTERVAL)
}

async function loadReports(silent = false) {
  if (!silent) loading.value = true
  try {
    const result = await listMyReports(currentPage.value, perPage.value)
    reports.value = result.items
    total.value = result.total
    perPage.value = result.per_page
    schedulePoll()
  } finally {
    if (!silent) loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadReports()
}

onMounted(() => loadReports())

onUnmounted(() => {
  if (pollTimer) clearTimeout(pollTimer)
})
</script>

<style scoped>
.reports {
  max-width: 900px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.page-head h2 {
  margin: 0;
  color: #303133;
}
.tip {
  margin: 16px 0;
}
.empty-hint {
  color: #909399;
  font-size: 12px;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.head-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.type {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}
.time {
  font-size: 12px;
  color: #909399;
}
.abnormal {
  color: #f56c6c;
  font-weight: 600;
}
.raw-content {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
  margin: 0;
}
.interpret {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed #dcdfe6;
}
.interpret-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.interpret-title {
  font-size: 14px;
  font-weight: 600;
  color: #1976d2;
}
.interpret-time {
  font-size: 12px;
  color: #c0c4cc;
}
.state-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px;
  border-radius: 6px;
  font-size: 13px;
}
.state-box.pending {
  background: #fdf6ec;
  color: #b88230;
}
.state-box.failed {
  background: #fef0f0;
  color: #c45656;
}
.spin {
  animation: rotate 1s linear infinite;
}
@keyframes rotate {
  to {
    transform: rotate(360deg);
  }
}
.markdown {
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
}
.markdown :deep(h3),
.markdown :deep(h4) {
  margin: 14px 0 8px;
  font-size: 14px;
  color: #303133;
}
.markdown :deep(p) {
  margin: 0 0 10px;
}
.markdown :deep(ul) {
  margin: 8px 0;
  padding-left: 22px;
}
.markdown :deep(li) {
  margin-bottom: 4px;
}
.pager {
  margin-top: 20px;
  justify-content: center;
}
</style>
