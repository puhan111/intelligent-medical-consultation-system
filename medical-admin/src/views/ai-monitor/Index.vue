<template>
  <div class="monitor-page">
    <div class="page-toolbar">
      <h2>AI 运行监控</h2>
      <div class="filters">
        <el-radio-group v-model="days" size="small" @change="loadOverview">
          <el-radio-button :value="7">7 天</el-radio-button>
          <el-radio-button :value="14">14 天</el-radio-button>
          <el-radio-button :value="30">30 天</el-radio-button>
        </el-radio-group>
        <el-select
          v-model="agentType"
          class="agent-select"
          size="small"
          placeholder="全部 Agent"
          @change="loadOverview"
        >
          <el-option label="全部 Agent" value="" />
          <el-option v-for="item in agentOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-tooltip content="刷新监控数据" placement="top">
          <el-button :icon="Refresh" circle size="small" :loading="loading" aria-label="刷新监控数据" @click="loadOverview" />
        </el-tooltip>
      </div>
    </div>

    <div class="metric-grid" v-loading="loading">
      <div v-for="metric in metricCards" :key="metric.label" class="metric-card">
        <span class="metric-label">{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <span class="metric-note">{{ metric.note }}</span>
      </div>
    </div>

    <section class="budget-band">
      <div class="section-head">
        <div>
          <h3>今日 Token 预算</h3>
          <span v-if="overview.budget.available">
            {{ formatNumber(overview.budget.used ?? 0) }} / {{ formatNumber(overview.budget.limit) }}
          </span>
          <span v-else>Redis 预算数据暂不可用</span>
        </div>
        <strong v-if="overview.budget.usage_rate !== null">
          {{ overview.budget.usage_rate.toFixed(1) }}%
        </strong>
      </div>
      <el-progress
        :percentage="budgetPercentage"
        :status="budgetStatus"
        :stroke-width="10"
        :show-text="false"
      />
      <div class="budget-scale"><span>0%</span><span>80% 告警</span><span>100% 熔断</span></div>
    </section>

    <section class="trend-section">
      <div class="section-head">
        <div>
          <h3>运行趋势</h3>
          <span>{{ overview.period.start_date }} 至 {{ overview.period.end_date }}</span>
        </div>
        <el-radio-group v-model="trendMetric" size="small">
          <el-radio-button value="calls">调用</el-radio-button>
          <el-radio-button value="tokens">Token</el-radio-button>
          <el-radio-button value="rag_queries">RAG</el-radio-button>
        </el-radio-group>
      </div>
      <div class="chart-scroll">
        <div class="bar-chart" :style="{ minWidth: `${Math.max(overview.trend.length * 52, 620)}px` }">
          <div v-for="(item, index) in overview.trend" :key="item.date" class="bar-column">
            <span class="bar-value">{{ compactNumber(item[trendMetric]) }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ height: `${barHeight(item[trendMetric])}%` }" />
            </div>
            <span class="bar-date">{{ showDateLabel(index) ? item.date.slice(5) : '' }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="breakdown-section">
      <div class="section-head">
        <div>
          <h3>Agent 调用分布</h3>
          <span>所选周期内各类模型调用</span>
        </div>
      </div>
      <div v-if="overview.agent_breakdown.length" class="breakdown-list">
        <div v-for="item in overview.agent_breakdown" :key="item.agent_type" class="breakdown-row">
          <span>{{ agentLabel(item.agent_type) }}</span>
          <el-progress :percentage="breakdownPercentage(item.count)" :show-text="false" />
          <strong>{{ item.count }}</strong>
        </div>
      </div>
      <el-empty v-else description="所选周期暂无调用记录" :image-size="64" />
    </section>

    <section class="logs-section">
      <el-tabs v-model="activeLogTab">
        <el-tab-pane label="LLM 调用" name="llm">
          <el-table :data="overview.recent_llm_calls" border stripe empty-text="暂无 LLM 调用记录">
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="Agent" width="140">
              <template #default="{ row }">{{ agentLabel(row.agent_type) }}</template>
            </el-table-column>
            <el-table-column label="Token" width="120" align="right">
              <template #default="{ row }">{{ formatNumber(row.input_tokens + row.output_tokens) }}</template>
            </el-table-column>
            <el-table-column prop="latency_ms" label="延迟(ms)" width="110" align="right" />
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small" effect="plain">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="error_message" label="错误信息" min-width="220" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="RAG 检索" name="rag">
          <el-table :data="overview.recent_rag_queries" border stripe empty-text="暂无 RAG 检索记录">
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="Agent" width="140">
              <template #default="{ row }">{{ agentLabel(row.agent_type) }}</template>
            </el-table-column>
            <el-table-column prop="query" label="查询内容" min-width="260" show-overflow-tooltip />
            <el-table-column prop="top_k" label="Top K" width="90" align="center" />
            <el-table-column prop="result_count" label="召回数" width="90" align="center" />
            <el-table-column prop="latency_ms" label="延迟(ms)" width="110" align="right" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import {
  getAiMonitorOverview,
  type AgentType,
  type AiMonitorOverview,
} from '../../api/aiMonitor'

type TrendMetric = 'calls' | 'tokens' | 'rag_queries'

const emptyOverview = (): AiMonitorOverview => ({
  period: { days: 7, start_date: '', end_date: '', agent_type: null },
  metrics: {
    call_count: 0,
    token_count: 0,
    average_latency_ms: 0,
    success_count: 0,
    error_count: 0,
    timeout_count: 0,
    success_rate: 0,
    rag_query_count: 0,
    rag_average_latency_ms: 0,
  },
  budget: { available: false, used: null, limit: 0, usage_rate: null },
  trend: [],
  agent_breakdown: [],
  recent_llm_calls: [],
  recent_rag_queries: [],
})

const overview = reactive<AiMonitorOverview>(emptyOverview())
const loading = ref(false)
const days = ref<7 | 14 | 30>(7)
const agentType = ref<AgentType | ''>('')
const trendMetric = ref<TrendMetric>('calls')
const activeLogTab = ref('llm')

const agentOptions: Array<{ value: AgentType; label: string }> = [
  { value: 'triage', label: '智能分诊' },
  { value: 'report_interpret', label: '报告解读' },
  { value: 'report_followup', label: '报告追问' },
  { value: 'eval_judge', label: '评测裁判' },
]

const metricCards = computed(() => [
  { label: '模型调用', value: formatNumber(overview.metrics.call_count), note: `${days.value} 天累计` },
  { label: 'Token 消耗', value: formatNumber(overview.metrics.token_count), note: '输入与输出合计' },
  { label: '平均延迟', value: `${formatNumber(overview.metrics.average_latency_ms)} ms`, note: '模型响应耗时' },
  { label: '调用成功率', value: `${overview.metrics.success_rate.toFixed(1)}%`, note: `${overview.metrics.error_count} 错误 / ${overview.metrics.timeout_count} 超时` },
  { label: 'RAG 检索', value: formatNumber(overview.metrics.rag_query_count), note: `平均 ${formatNumber(overview.metrics.rag_average_latency_ms)} ms` },
])

const budgetPercentage = computed(() => Math.min(Math.max(overview.budget.usage_rate ?? 0, 0), 100))
const budgetStatus = computed(() => {
  const rate = overview.budget.usage_rate ?? 0
  if (rate >= 100) return 'exception'
  if (rate >= 80) return 'warning'
  return 'success'
})
const trendMax = computed(() => Math.max(...overview.trend.map((item) => item[trendMetric.value]), 0))
const breakdownMax = computed(() => Math.max(...overview.agent_breakdown.map((item) => item.count), 0))

function formatNumber(value: number) {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 1 }).format(value)
}

function compactNumber(value: number) {
  return new Intl.NumberFormat('zh-CN', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(new Date(value))
}

function agentLabel(value?: string | null) {
  return {
    triage: '智能分诊',
    report_interpret: '报告解读',
    report_followup: '报告追问',
    eval_judge: '评测裁判',
  }[value ?? ''] ?? '未标记'
}

function statusLabel(value: string) {
  return { success: '成功', error: '错误', timeout: '超时' }[value] ?? value
}

function statusType(value: string) {
  return ({ success: 'success', error: 'danger', timeout: 'warning' } as Record<string, any>)[value] ?? 'info'
}

function barHeight(value: number) {
  if (!value || !trendMax.value) return 0
  return Math.max((value / trendMax.value) * 100, 5)
}

function showDateLabel(index: number) {
  if (overview.trend.length <= 14) return true
  return index === 0 || index === overview.trend.length - 1 || index % 5 === 0
}

function breakdownPercentage(value: number) {
  return breakdownMax.value ? Math.round((value / breakdownMax.value) * 100) : 0
}

async function loadOverview() {
  loading.value = true
  try {
    const result = await getAiMonitorOverview({
      days: days.value,
      ...(agentType.value ? { agent_type: agentType.value } : {}),
    })
    Object.assign(overview, result)
  } finally {
    loading.value = false
  }
}

onMounted(loadOverview)
</script>

<style scoped>
.monitor-page { width: 100%; color: #303133; }
.page-toolbar, .filters, .section-head, .budget-scale, .breakdown-row { display: flex; align-items: center; }
.page-toolbar { justify-content: space-between; gap: 20px; margin-bottom: 18px; }
.page-toolbar h2 { margin: 0; font-size: 20px; }
.filters { gap: 10px; flex-wrap: wrap; }
.agent-select { width: 150px; }
.metric-grid { display: grid; grid-template-columns: repeat(5, minmax(145px, 1fr)); gap: 12px; min-height: 112px; }
.metric-card { border: 1px solid #e4e7ed; border-radius: 6px; padding: 16px; background: #fff; display: flex; flex-direction: column; min-width: 0; }
.metric-label, .metric-note, .section-head span { color: #909399; font-size: 12px; }
.metric-card strong { margin: 9px 0 7px; font-size: 24px; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
section { margin-top: 24px; }
.budget-band { padding: 18px 0; border-top: 1px solid #ebeef5; border-bottom: 1px solid #ebeef5; }
.section-head { justify-content: space-between; gap: 16px; margin-bottom: 14px; }
.section-head h3 { margin: 0 0 4px; font-size: 16px; }
.section-head > strong { font-size: 18px; }
.budget-scale { justify-content: space-between; margin-top: 7px; color: #a8abb2; font-size: 11px; }
.chart-scroll { overflow-x: auto; padding-bottom: 4px; }
.bar-chart { height: 230px; display: flex; align-items: flex-end; gap: 8px; border-bottom: 1px solid #dcdfe6; padding: 8px 6px 0; }
.bar-column { flex: 1; min-width: 38px; height: 100%; display: grid; grid-template-rows: 22px 1fr 24px; align-items: end; text-align: center; }
.bar-value { font-size: 11px; color: #606266; align-self: center; }
.bar-track { height: 100%; display: flex; align-items: flex-end; justify-content: center; }
.bar-fill { width: 18px; min-height: 0; background: #409eff; border-radius: 3px 3px 0 0; transition: height .2s ease; }
.bar-date { min-height: 20px; padding-top: 5px; color: #909399; font-size: 11px; }
.breakdown-list { max-width: 760px; }
.breakdown-row { display: grid; grid-template-columns: 120px minmax(180px, 1fr) 50px; gap: 16px; min-height: 38px; }
.breakdown-row strong { text-align: right; }
.logs-section { min-width: 0; }
@media (max-width: 1100px) { .metric-grid { grid-template-columns: repeat(3, minmax(160px, 1fr)); } }
@media (max-width: 760px) {
  .page-toolbar { align-items: flex-start; flex-direction: column; }
  .filters { width: 100%; }
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .metric-card strong { font-size: 20px; }
  .breakdown-row { grid-template-columns: 100px minmax(120px, 1fr) 36px; gap: 10px; }
}
@media (max-width: 480px) { .metric-grid { grid-template-columns: 1fr; } }
</style>
