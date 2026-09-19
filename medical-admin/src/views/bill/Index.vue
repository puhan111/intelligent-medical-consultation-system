<template>
  <div class="bill-container">
    <div class="toolbar">
      <el-radio-group v-model="statusFilter" @change="handleFilterChange">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="unpaid">待结算</el-radio-button>
        <el-radio-button label="paid">已结算</el-radio-button>
      </el-radio-group>
      <el-button @click="loadBills">刷新</el-button>
    </div>

    <el-table :data="bills" v-loading="loading" border>
      <el-table-column prop="padded_id" label="账单号" width="90" />
      <el-table-column prop="patient_name" label="患者" width="110" />
      <el-table-column label="金额" width="100">
        <template #default="{ row }">¥{{ row.amount.toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'paid' ? 'success' : 'warning'">
            {{ row.status === 'paid' ? '已结算' : '待结算' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="支付渠道" width="130">
        <template #default="{ row }">
          <span v-if="row.status !== 'paid'" class="muted">—</span>
          <el-tag v-else :type="row.paid_by_type === 'patient' ? 'primary' : 'info'" size="small" effect="plain">
            {{ channelLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="经办人" width="110">
        <template #default="{ row }">
          <span v-if="row.paid_by_type === 'cashier'">{{ row.cashier_name || '—' }}</span>
          <span v-else-if="row.paid_by_type === 'patient'" class="muted">患者自助</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="支付时间" min-width="150">
        <template #default="{ row }">
          <span v-if="row.paid_at">{{ formatTime(row.paid_at) }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status !== 'paid'"
            size="small"
            type="primary"
            @click="handleSettle(row)"
          >
            结算
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > perPage"
      class="pager"
      layout="prev, pager, next, total"
      :total="total"
      :page-size="perPage"
      :current-page="currentPage"
      @current-change="handlePageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listBills, settleBill, type Bill } from '../../api/bill'

const bills = ref<Bill[]>([])
const loading = ref(false)
const statusFilter = ref<'' | 'unpaid' | 'paid'>('')
const total = ref(0)
const perPage = ref(20)
const currentPage = ref(1)

function channelLabel(row: Bill) {
  if (row.paid_by_type === 'patient') return '线上支付'
  if (row.paid_by_type === 'cashier') {
    return row.payment_method === 'card' ? '窗口刷卡' : '窗口现金'
  }
  // 本次改动前已支付的历史账单没有渠道信息
  return '未记录'
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadBills() {
  loading.value = true
  try {
    const result = await listBills(
      currentPage.value,
      perPage.value,
      statusFilter.value || undefined
    )
    bills.value = result.items
    total.value = result.total
    perPage.value = result.per_page
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  currentPage.value = 1
  loadBills()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadBills()
}

async function handleSettle(row: Bill) {
  await ElMessageBox.confirm(
    `确认已收到患者 ${row.patient_name || ''} 的 ¥${row.amount.toFixed(2)} 款项？`,
    '窗口收款确认',
    { type: 'warning' }
  )
  await settleBill(row.id)
  ElMessage.success('结算成功')
  await loadBills()
}

onMounted(loadBills)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
  align-items: center;
}
.muted {
  color: #c0c4cc;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
