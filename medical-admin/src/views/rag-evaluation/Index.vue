<template>
  <div class="page">
    <div class="header">
      <div><h2>RAG 质量评测</h2><p>使用内置合成数据集检查混合检索，不写入线上查询日志。</p></div>
      <div class="actions">
        <el-select v-model="topK" style="width:100px"><el-option v-for="n in [1,3,5]" :key="n" :label="`Top ${n}`" :value="n" /></el-select>
        <el-switch v-model="rerank" active-text="启用精排" />
        <el-button type="primary" :loading="loading" @click="run">运行评测</el-button>
      </div>
    </div>
    <el-alert v-if="result && !result.ready" type="warning" :closable="false" title="评测数据尚未导入" :description="`缺少：${result.missing_sources?.join('、')}`" />
    <template v-if="result?.ready">
      <div class="metrics">
        <el-card v-for="(value,key) in result.summary" :key="key" shadow="never"><div class="label">{{ metricLabel(key) }}</div><strong>{{ formatMetric(key, value) }}</strong></el-card>
      </div>
      <el-collapse>
        <el-collapse-item v-for="item in result.cases" :key="item.case_id" :title="`${caseLabels[item.case_id] ?? item.case_id} · ${statusLabels[item.status] ?? item.status}`">
          <p v-if="item.reason">{{ item.reason }}</p>
          <template v-if="item.diagnostics">
            <p>总延迟：{{ item.diagnostics.latency_ms }} ms；Embedding：{{ item.diagnostics.embedding_latency_ms }} ms；向量：{{ item.diagnostics.vector_search_latency_ms }} ms；全文：{{ item.diagnostics.fulltext_search_latency_ms }} ms</p>
            <el-table :data="item.diagnostics.results" border>
              <el-table-column prop="source" label="召回来源" min-width="220" /><el-table-column prop="score" label="RRF分数" width="110" /><el-table-column prop="preview" label="片段预览" min-width="360" />
            </el-table>
          </template>
        </el-collapse-item>
      </el-collapse>
    </template>
    <el-empty v-else-if="!loading && !result" description="点击运行评测查看结果" />
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { runRagEvaluation, type RagEvaluationResult } from '../../api/aiMonitor'
const topK = ref(3); const rerank = ref(false); const loading = ref(false); const result = ref<RagEvaluationResult|null>(null)
const metricLabels: Record<string, string> = {
  case_count: '案例总数',
  evaluated_case_count: '参与评测',
  skipped_case_count: '跳过案例',
}
const caseLabels: Record<string, string> = {
  'known-night-clinic-code': '已知事实：夜间门诊代号',
  'distinguish-adult-xq9': '区分成人组资料',
  'distinguish-pregnancy-xq9': '区分孕期组资料',
  'prefer-current-protocol': '优先当前版本流程',
  'missing-moonlight-cycle': '缺失事实：月光周期',
}
const statusLabels: Record<string, string> = { evaluated: '已评测', skipped: '已跳过' }
function metricLabel(key: string) {
  const match = key.match(/^(hit_rate_at_|mean_recall_at_|mrr_at_)(\d+)$/)
  if (!match) return metricLabels[key] ?? key
  const prefix: Record<string, string> = {
    hit_rate_at_: '命中率', mean_recall_at_: '平均召回率', mrr_at_: '平均倒数排名',
  }
  return `${prefix[match[1]]}@${match[2]}`
}
function formatMetric(key: string, value: number) { return key.endsWith('_count') ? value : value.toFixed(3) }
async function run() { loading.value=true; try { result.value=await runRagEvaluation({top_k:topK.value,rerank:rerank.value}) } catch { ElMessage.error('评测运行失败，请检查模型与数据库状态') } finally { loading.value=false } }
</script>
<style scoped>
.page{display:grid;gap:18px}.header{display:flex;justify-content:space-between;align-items:center;gap:20px}.header h2{margin:0}.header p,.label{color:#909399}.actions{display:flex;align-items:center;gap:12px}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}.metrics strong{font-size:24px}
</style>
