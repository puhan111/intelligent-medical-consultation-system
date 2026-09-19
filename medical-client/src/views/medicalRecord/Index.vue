<template>
  <div class="records">
    <div class="page-head">
      <h2>我的病历</h2>
      <el-button :loading="loading" @click="loadRecords">刷新</el-button>
    </div>

    <el-empty v-if="!loading && !records.length" description="暂无病历记录">
      <div class="empty-hint">病历由医生在接诊完成时录入</div>
    </el-empty>

    <div v-loading="loading" class="list">
      <el-card v-for="record in records" :key="record.id" shadow="never" class="card">
        <div class="card-head">
          <div class="head-left">
            <span class="label">诊断</span>
            <span class="diagnosis">{{ record.diagnosis }}</span>
          </div>
          <span class="meta">{{ formatTime(record.created_at) }}</span>
        </div>

        <div class="info-row">
          <span>接诊医生：{{ record.doctor_name || '—' }}</span>
          <span>病历号：{{ record.padded_id }}</span>
        </div>

        <div v-if="record.content" class="content">
          <div class="content-label">病历详情</div>
          <div class="content-body">{{ record.content }}</div>
        </div>
        <div v-else class="no-content">医生未填写详细病历内容</div>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listMyMedicalRecords, type MedicalRecord } from '../../api/medicalRecord'

const records = ref<MedicalRecord[]>([])
const loading = ref(false)
const total = ref(0)
const perPage = ref(10)
const currentPage = ref(1)

function formatTime(iso: string) {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadRecords() {
  loading.value = true
  try {
    const result = await listMyMedicalRecords(currentPage.value, perPage.value)
    records.value = result.items
    total.value = result.total
    perPage.value = result.per_page
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadRecords()
}

onMounted(loadRecords)
</script>

<style scoped>
.records {
  max-width: 860px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-head h2 {
  margin: 0;
  color: #303133;
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
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.head-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}
.label {
  flex-shrink: 0;
  font-size: 12px;
  color: #909399;
  background: #f4f4f5;
  padding: 2px 8px;
  border-radius: 3px;
}
.diagnosis {
  font-size: 17px;
  font-weight: 600;
  color: #303133;
}
.meta {
  flex-shrink: 0;
  font-size: 12px;
  color: #909399;
}
.info-row {
  display: flex;
  gap: 24px;
  margin-top: 12px;
  font-size: 13px;
  color: #606266;
}
.content {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed #dcdfe6;
}
.content-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}
.content-body {
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
  /* 医生可能分行填写，保留换行 */
  white-space: pre-wrap;
}
.no-content {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed #dcdfe6;
  font-size: 13px;
  color: #c0c4cc;
}
.pager {
  margin-top: 20px;
  justify-content: center;
}
</style>
