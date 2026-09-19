<template>
  <div class="bills">
    <div class="page-head">
      <h2>我的账单</h2>
      <el-button @click="loadBills">刷新</el-button>
    </div>

    <el-empty v-if="!loading && !bills.length" description="暂无账单">
      <div class="empty-hint">账单在医生完成接诊后自动生成</div>
    </el-empty>

    <div v-loading="loading" class="list">
      <div v-for="bill in bills" :key="bill.id" class="card">
        <div class="card-row">
          <div class="card-main">
            <div class="line-1">
              <span class="amount">¥{{ bill.amount.toFixed(2) }}</span>
              <el-tag :type="bill.bill_type === 'prescription' ? 'primary' : 'info'" size="small" effect="plain">
                {{ bill.bill_type === 'prescription' ? '药费' : '问诊费' }}
              </el-tag>
              <el-tag :type="bill.status === 'paid' ? 'success' : 'warning'" size="small">
                {{ bill.status === 'paid' ? '已支付' : '待支付' }}
              </el-tag>
            </div>
            <div class="line-2">账单号：{{ bill.padded_id }}</div>
            <div v-if="bill.status === 'paid'" class="line-3">
              <span>{{ payMethodLabel(bill) }}</span>
              <span v-if="bill.paid_at">{{ formatTime(bill.paid_at) }}</span>
            </div>
          </div>

          <div class="card-actions">
            <el-button
              v-if="bill.items.length"
              link
              type="primary"
              @click="toggleDetail(bill.id)"
            >
              {{ expanded.has(bill.id) ? '收起明细' : '收费明细' }}
            </el-button>
            <el-button
              v-if="bill.status === 'unpaid'"
              type="primary"
              :loading="payingId === bill.id"
              @click="handlePay(bill)"
            >
              {{ payingId === bill.id ? '支付中' : '立即支付' }}
            </el-button>
          </div>
        </div>

        <el-table
          v-if="expanded.has(bill.id) && bill.items.length"
          :data="bill.items"
          size="small"
          border
          class="detail-table"
        >
          <el-table-column label="收费项目" min-width="160">
            <template #default="{ row }">
              {{ row.name }}
              <el-tag size="small" effect="plain" class="type-tag">
                {{ row.item_type === 'consultation' ? '问诊' : '药品' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="单价" width="100">
            <template #default="{ row }">¥{{ row.unit_price.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量" width="70" align="center" />
          <el-table-column label="小计" width="100">
            <template #default="{ row }">
              <span class="subtotal">¥{{ row.subtotal.toFixed(2) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
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

    <el-dialog v-model="payDialogVisible" title="支付处理中" width="400px" :close-on-click-modal="false" :show-close="false">
      <div class="pay-progress">
        <el-icon v-if="payState === 'pending'" class="spin" :size="38"><Loading /></el-icon>
        <el-icon v-else-if="payState === 'success'" :size="38" color="#67c23a"><CircleCheck /></el-icon>
        <el-icon v-else :size="38" color="#f56c6c"><CircleClose /></el-icon>

        <div class="pay-text">{{ payMessage }}</div>
        <div v-if="payOrderNo" class="pay-order-no">流水号：{{ payOrderNo }}</div>
      </div>
      <template #footer>
        <el-button v-if="payState !== 'pending'" type="primary" @click="closePayDialog">
          知道了
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, CircleClose, Loading } from '@element-plus/icons-vue'
import {
  getPaymentStatus,
  listMyBills,
  payBill,
  type Bill,
  type PaymentOrderStatus,
} from '../../api/bill'

const bills = ref<Bill[]>([])
const loading = ref(false)
const total = ref(0)
const perPage = ref(10)
const currentPage = ref(1)

const payingId = ref<number | null>(null)
const expanded = ref<Set<number>>(new Set())
const payDialogVisible = ref(false)
const payState = ref<PaymentOrderStatus>('pending')
const payMessage = ref('')
const payOrderNo = ref('')

// 轮询相关：支付发起后需等待后端回调确认，最多轮询 20 次（约 20 秒）
let pollTimer: ReturnType<typeof setTimeout> | null = null
const MAX_POLL = 20

function toggleDetail(billId: number) {
  // Set 原地增删不触发 Vue 响应，需替换引用
  const next = new Set(expanded.value)
  if (next.has(billId)) {
    next.delete(billId)
  } else {
    next.add(billId)
  }
  expanded.value = next
}

function payMethodLabel(bill: Bill) {
  if (bill.paid_by_type === 'cashier') {
    const method = bill.payment_method === 'card' ? '刷卡' : '现金'
    return `窗口缴费（${method}）`
  }
  if (bill.paid_by_type === 'patient') {
    return '线上支付'
  }
  // 本次改动前已支付的历史账单没有渠道信息
  return '支付方式未记录'
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadBills() {
  loading.value = true
  try {
    const result = await listMyBills(currentPage.value, perPage.value)
    bills.value = result.items
    total.value = result.total
    perPage.value = result.per_page
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadBills()
}

async function handlePay(bill: Bill) {
  payingId.value = bill.id
  payState.value = 'pending'
  payMessage.value = '正在等待支付结果，请稍候...'
  payOrderNo.value = ''

  try {
    const order = await payBill(bill.id)
    payOrderNo.value = order.order_no
    payDialogVisible.value = true

    // 后端可能直接返回终态（如复用了已完成的流水），无需轮询
    if (order.status !== 'pending') {
      applyFinalState(order.status, order.fail_reason)
      return
    }
    pollPaymentStatus(bill.id, 0)
  } catch {
    payingId.value = null
    // 失败提示由请求拦截器统一弹出，这里只需刷新看最新状态
    await loadBills()
  }
}

function pollPaymentStatus(billId: number, attempt: number) {
  if (attempt >= MAX_POLL) {
    payState.value = 'failed'
    payMessage.value = '支付结果确认超时，请稍后刷新查看'
    payingId.value = null
    return
  }

  pollTimer = setTimeout(async () => {
    try {
      const order = await getPaymentStatus(billId)
      if (order.status === 'pending') {
        pollPaymentStatus(billId, attempt + 1)
        return
      }
      applyFinalState(order.status, order.fail_reason)
    } catch {
      payState.value = 'failed'
      payMessage.value = '无法获取支付结果，请稍后刷新查看'
      payingId.value = null
    }
  }, 1000)
}

function applyFinalState(status: PaymentOrderStatus, failReason?: string) {
  payState.value = status
  payMessage.value =
    status === 'success' ? '支付成功' : failReason || '支付失败，请重试'
  payingId.value = null
}

async function closePayDialog() {
  payDialogVisible.value = false
  if (payState.value === 'success') {
    ElMessage.success('支付成功')
  }
  await loadBills()
}

onMounted(loadBills)

onUnmounted(() => {
  if (pollTimer) clearTimeout(pollTimer)
})
</script>

<style scoped>
.bills {
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
  gap: 12px;
}
.card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px 20px;
}
.card-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.card-main {
  flex: 1;
  min-width: 0;
}
.card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.detail-table {
  margin-top: 14px;
}
.type-tag {
  margin-left: 6px;
}
.subtotal {
  color: #67c23a;
  font-weight: 600;
}
.line-1 {
  display: flex;
  align-items: center;
  gap: 10px;
}
.amount {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}
.line-2 {
  margin-top: 6px;
  font-size: 12px;
  color: #c0c4cc;
}
.line-3 {
  display: flex;
  gap: 16px;
  margin-top: 6px;
  font-size: 13px;
  color: #606266;
}
.pager {
  margin-top: 20px;
  justify-content: center;
}
.pay-progress {
  padding: 12px 0 4px;
  text-align: center;
}
.pay-text {
  margin-top: 14px;
  font-size: 15px;
  color: #303133;
}
.pay-order-no {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}
.spin {
  animation: rotate 1s linear infinite;
  color: #409eff;
}
@keyframes rotate {
  to {
    transform: rotate(360deg);
  }
}
</style>
