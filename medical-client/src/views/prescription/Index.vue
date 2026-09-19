<template>
  <div class="prescriptions">
    <div class="page-head">
      <h2>我的处方</h2>
      <el-button :loading="loading" @click="loadPrescriptions">刷新</el-button>
    </div>

    <el-alert type="info" :closable="false" class="tip">
      您可以取消不需要的药品，仅为勾选的药品付费。付费后药师才会配药，且不可再修改。
    </el-alert>

    <el-empty v-if="!loading && !prescriptions.length" description="暂无处方">
      <div class="empty-hint">处方由医生在接诊时开出</div>
    </el-empty>

    <div v-loading="loading" class="list">
      <el-card v-for="rx in prescriptions" :key="rx.id" shadow="never" class="card">
        <div class="card-head">
          <div class="head-left">
            <span class="rx-no">处方 {{ rx.padded_id }}</span>
            <el-tag :type="rx.status === 'dispensed' ? 'success' : 'warning'" size="small">
              {{ rx.status === 'dispensed' ? '已取药' : '待取药' }}
            </el-tag>
            <el-tag :type="billTagType(rx.bill_status)" size="small" effect="plain">
              {{ billLabel(rx.bill_status) }}
            </el-tag>
          </div>
          <span class="meta">
            {{ rx.department_name }} · {{ rx.doctor_name }} · {{ formatTime(rx.created_at) }}
          </span>
        </div>

        <el-table :data="rx.items" size="small" border>
          <el-table-column label="选购" width="70" align="center">
            <template #default="{ row }">
              <el-checkbox
                :model-value="row.is_selected"
                :disabled="!rx.can_modify_selection || rx.status === 'dispensed' || togglingId === row.id"
                @change="(v: any) => handleToggle(rx, row, !!v)"
              />
            </template>
          </el-table-column>
          <el-table-column label="药品" min-width="150">
            <template #default="{ row }">
              <span :class="{ declined: !row.is_selected }">{{ row.drug_name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="dosage" label="用法用量" min-width="140" />
          <el-table-column label="单价" width="100">
            <template #default="{ row }">
              <span v-if="row.unit_price">¥{{ row.unit_price.toFixed(2) }}</span>
              <span v-else class="muted">未计价</span>
            </template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量" width="70" align="center" />
          <el-table-column label="小计" width="100">
            <template #default="{ row }">
              <span v-if="row.subtotal" :class="row.is_selected ? 'subtotal' : 'muted'">
                ¥{{ row.subtotal.toFixed(2) }}
              </span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
        </el-table>

        <div class="card-foot">
          <div class="total-area">
            <span class="total-label">应付药费</span>
            <span class="total-value">¥{{ rx.selected_total.toFixed(2) }}</span>
          </div>

          <div class="actions">
            <el-tag v-if="rx.bill_status === 'paid'" type="success">药费已支付</el-tag>
            <template v-else-if="rx.selected_total > 0">
              <el-button
                v-if="rx.bill_status === 'none'"
                type="primary"
                :loading="billingId === rx.id"
                @click="handleCreateBill(rx)"
              >
                确认选购并生成账单
              </el-button>
              <el-button
                v-else
                type="primary"
                :loading="payingId === rx.id"
                @click="handlePay(rx)"
              >
                立即支付 ¥{{ rx.selected_total.toFixed(2) }}
              </el-button>
            </template>
            <span v-else class="muted">未选购任何药品</span>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createPrescriptionBill,
  listMyPrescriptions,
  updateItemSelection,
  type Prescription,
  type PrescriptionBillStatus,
  type PrescriptionItem,
} from '../../api/prescription'
import { getPaymentStatus, payBill } from '../../api/bill'

const prescriptions = ref<Prescription[]>([])
const loading = ref(false)
const total = ref(0)
const perPage = ref(10)
const currentPage = ref(1)

const togglingId = ref<number | null>(null)
const billingId = ref<number | null>(null)
const payingId = ref<number | null>(null)

let pollTimer: ReturnType<typeof setTimeout> | null = null

const BILL_LABEL: Record<PrescriptionBillStatus, string> = {
  none: '待选购',
  unpaid: '待支付',
  paid: '已支付',
}

function billLabel(s: PrescriptionBillStatus) {
  return BILL_LABEL[s] ?? s
}

function billTagType(s: PrescriptionBillStatus) {
  return ({ none: 'info', unpaid: 'warning', paid: 'success' } as Record<string, any>)[s] ?? 'info'
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadPrescriptions() {
  loading.value = true
  try {
    const result = await listMyPrescriptions(currentPage.value, perPage.value)
    prescriptions.value = result.items
    total.value = result.total
    perPage.value = result.per_page
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadPrescriptions()
}

async function handleToggle(rx: Prescription, item: PrescriptionItem, checked: boolean) {
  togglingId.value = item.id
  try {
    const updated = await updateItemSelection(rx.id, item.id, checked)
    // 取消勾选会作废未支付的旧账单，用后端返回的最新状态整体替换
    Object.assign(rx, updated)
  } catch {
    await loadPrescriptions()
  } finally {
    togglingId.value = null
  }
}

async function handleCreateBill(rx: Prescription) {
  const selected = rx.items.filter((i) => i.is_selected)
  await ElMessageBox.confirm(
    `将为以下 ${selected.length} 种药品生成账单，合计 ¥${rx.selected_total.toFixed(2)}。生成后仍可修改，支付后不可修改。`,
    '确认选购',
    { type: 'info' }
  )
  billingId.value = rx.id
  try {
    const updated = await createPrescriptionBill(rx.id)
    Object.assign(rx, updated)
    ElMessage.success('账单已生成，请支付')
  } finally {
    billingId.value = null
  }
}

async function handlePay(rx: Prescription) {
  if (!rx.bill_id) return
  payingId.value = rx.id
  try {
    const order = await payBill(rx.bill_id)
    if (order.status !== 'pending') {
      finishPay(order.status === 'success')
      return
    }
    pollPayment(rx.bill_id, 0)
  } catch {
    payingId.value = null
    await loadPrescriptions()
  }
}

/** 支付回调是异步的，轮询直到拿到终态（最多 20 次约 20 秒） */
function pollPayment(billId: number, attempt: number) {
  if (attempt >= 20) {
    payingId.value = null
    ElMessage.warning('支付结果确认超时，请稍后刷新查看')
    return
  }
  pollTimer = setTimeout(async () => {
    try {
      const order = await getPaymentStatus(billId)
      if (order.status === 'pending') {
        pollPayment(billId, attempt + 1)
        return
      }
      finishPay(order.status === 'success')
    } catch {
      payingId.value = null
      ElMessage.warning('无法获取支付结果，请稍后刷新查看')
    }
  }, 1000)
}

function finishPay(ok: boolean) {
  payingId.value = null
  if (ok) {
    ElMessage.success('支付成功，请到药房取药')
  } else {
    ElMessage.error('支付失败，请重试')
  }
  loadPrescriptions()
}

onMounted(loadPrescriptions)

onUnmounted(() => {
  if (pollTimer) clearTimeout(pollTimer)
})
</script>

<style scoped>
.prescriptions {
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
  flex-wrap: wrap;
  gap: 8px;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.rx-no {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.meta {
  font-size: 12px;
  color: #909399;
}
.declined {
  color: #c0c4cc;
  text-decoration: line-through;
}
.muted {
  color: #c0c4cc;
}
.subtotal {
  color: #67c23a;
  font-weight: 600;
}
.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed #dcdfe6;
  flex-wrap: wrap;
  gap: 12px;
}
.total-label {
  color: #606266;
  font-size: 13px;
  margin-right: 8px;
}
.total-value {
  font-size: 22px;
  font-weight: 600;
  color: #e6a23c;
}
.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.pager {
  margin-top: 20px;
  justify-content: center;
}
</style>

