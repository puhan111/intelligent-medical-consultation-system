<template>
  <div class="appointment-container">
    <div class="toolbar">
      <el-select v-model="statusFilter" placeholder="全部状态" clearable @change="loadAppointments">
        <el-option label="待确认" value="pending" />
        <el-option label="已确认" value="confirmed" />
        <el-option label="待检查结果" value="waiting_exam" />
        <el-option label="已完成" value="completed" />
      </el-select>
      <el-button @click="loadAppointments">刷新</el-button>
    </div>

    <el-table :data="appointments" v-loading="loading" border>
      <el-table-column prop="padded_id" label="ID" width="90" />
      <el-table-column prop="patient_name" label="患者" />
      <el-table-column prop="department_name" label="科室" />
      <el-table-column label="预约时间（本地）">
        <template #default="{ row }">
          {{ formatTime(row.appointment_time) }}
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="检查报告" min-width="150">
        <template #default="{ row }">
          <span v-if="!row.report_count" class="muted">暂无</span>
          <div v-else class="report-status">
            <el-tag size="small" type="success">{{ row.report_count }} 份</el-tag>
            <span>{{ reportStatusText(row) }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="300">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'pending'"
            size="small"
            type="primary"
            @click="handleUpdateStatus(row, 'confirmed')"
          >
            确认接诊
          </el-button>
          <el-button
            v-if="row.status === 'confirmed'"
            size="small"
            type="warning"
            @click="handleUpdateStatus(row, 'waiting_exam')"
          >
            等待检查结果
          </el-button>
          <el-button
            v-if="row.status === 'confirmed'"
            size="small"
            type="success"
            @click="openCompleteDialog(row)"
          >
            录病历并完成
          </el-button>
          <el-button
            v-if="row.status === 'waiting_exam'"
            size="small"
            type="success"
            :disabled="row.report_count === 0"
            @click="openCompleteDialog(row)"
          >
            {{ row.report_count ? '查看报告并继续接诊' : '等待报告录入' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="completeDialogVisible" title="录入病历并完成接诊" width="min(860px, 92vw)">
      <section v-if="selectedAppointment?.reports.length" class="report-panel">
        <h3>本次就诊检查报告</h3>
        <el-collapse>
          <el-collapse-item
            v-for="report in selectedAppointment.reports"
            :key="report.id"
            :title="`${report.type} · ${interpretationLabel(report.interpretation_status)}`"
            :name="report.id"
          >
            <div class="report-block">
              <strong>原始结果</strong>
              <div class="report-items">
                <div v-for="(item, index) in reportItems(report.content)" :key="`${report.id}-${index}`" class="report-item">
                  <span class="report-item-name">{{ item.name || '检验项目' }}</span>
                  <span class="report-item-value" :class="reportStatusClass(item.status)">{{ item.value || '-' }}</span>
                  <span class="report-item-unit">{{ item.unit || '' }}</span>
                  <span class="report-item-range">参考范围：{{ item.reference_range || '-' }}</span>
                  <el-tag v-if="item.status" size="small" :type="reportStatusTagType(item.status)">{{ reportStatusLabel(item.status) }}</el-tag>
                </div>
              </div>
            </div>
            <div class="report-block">
              <strong>AI 辅助解读</strong>
              <div
                class="report-markdown"
                v-html="renderMarkdown(report.ai_interpretation || interpretationHint(report.interpretation_status))"
              />
            </div>
          </el-collapse-item>
        </el-collapse>
      </section>
      <el-form :model="completeForm" label-width="90px">
        <el-form-item label="诊断">
          <el-input v-model="completeForm.diagnosis" placeholder="诊断结论" />
        </el-form-item>
        <el-form-item label="病历内容">
          <el-input v-model="completeForm.content" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="处方">
          <div v-for="(item, idx) in completeForm.items" :key="idx" class="prescription-item">
            <el-select
              v-model="item.drug_id"
              filterable
              placeholder="选择药品"
              class="drug-select"
              @change="() => onDrugChange(item)"
            >
              <el-option
                v-for="drug in drugs"
                :key="drug.id"
                :label="drug.name"
                :value="drug.id"
              >
                <span>{{ drug.name }}</span>
                <span class="option-meta">{{ drug.spec }} ¥{{ drug.unit_price.toFixed(2) }}/{{ drug.unit }}</span>
              </el-option>
            </el-select>
            <el-input v-model="item.dosage" class="dosage-input" placeholder="用法用量" />
            <el-input-number v-model="item.quantity" class="quantity-input" :min="1" />
            <span class="item-subtotal">{{ itemSubtotal(item) }}</span>
            <el-button class="remove-button" text type="danger" @click="completeForm.items.splice(idx, 1)">移除</el-button>
          </div>
          <div class="prescription-footer">
            <el-button size="small" @click="addPrescriptionItem">+ 添加药品</el-button>
            <span v-if="completeForm.items.length" class="total">
              药费合计 ¥{{ prescriptionTotal.toFixed(2) }}
            </span>
          </div>
          <span class="field-hint">
            药费由患者在「我的处方」中确认选购后单独支付，患者可取消不需要的药品。
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="completeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="completing" @click="handleComplete">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listMyAppointments,
  updateAppointmentStatus,
  type Appointment,
} from '../../api/appointment'
import { createMedicalRecord } from '../../api/medicalRecord'
import { createPrescription } from '../../api/prescription'
import { listDrugs, type Drug } from '../../api/drug'
import { renderMarkdown } from '../../utils/markdown'

interface PrescriptionFormItem {
  drug_id: number | undefined
  dosage: string
  quantity: number
}

const appointments = ref<Appointment[]>([])
const loading = ref(false)
const statusFilter = ref<string | undefined>(undefined)
const drugs = ref<Drug[]>([])

const completeDialogVisible = ref(false)
const completing = ref(false)
const selectedAppointment = ref<Appointment | null>(null)
const completeForm = reactive({
  appointment_id: 0,
  diagnosis: '',
  content: '',
  items: [] as PrescriptionFormItem[],
})

/** 只加载启用中的药品，停用药不应再被开出 */
async function loadDrugs() {
  const result = await listDrugs(1, 200, undefined, true)
  drugs.value = result.items
}

function findDrug(drugId?: number) {
  return drugs.value.find((d) => d.id === drugId)
}

function addPrescriptionItem() {
  completeForm.items.push({ drug_id: undefined, dosage: '', quantity: 1 })
}

function onDrugChange(item: PrescriptionFormItem) {
  // 选药后带出规格作为用法参考，医生可改写
  const drug = findDrug(item.drug_id)
  if (drug && !item.dosage) {
    item.dosage = ''
  }
}

function itemSubtotal(item: PrescriptionFormItem): string {
  const drug = findDrug(item.drug_id)
  if (!drug) return ''
  return `¥${(drug.unit_price * item.quantity).toFixed(2)}`
}

const prescriptionTotal = computed(() =>
  completeForm.items.reduce((sum, item) => {
    const drug = findDrug(item.drug_id)
    return sum + (drug ? drug.unit_price * item.quantity : 0)
  }, 0)
)

async function loadAppointments() {
  loading.value = true
  try {
    const result = await listMyAppointments(1, 20, statusFilter.value)
    appointments.value = result.items
  } finally {
    loading.value = false
  }
}

function formatTime(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function statusLabel(status: string) {
  return { pending: '待确认', confirmed: '已确认', waiting_exam: '待检查结果', completed: '已完成', cancelled: '已取消' }[status] ?? status
}

function statusTagType(status: string) {
  return (
    ({ pending: 'warning', confirmed: 'primary', waiting_exam: 'warning', completed: 'success' } as Record<string, string>)[status] ?? 'info'
  )
}

function reportStatusText(row: Appointment) {
  if (row.reports.some((report) => report.interpretation_status === 'pending')) return 'AI 解读中'
  if (row.reports.some((report) => report.interpretation_status === 'failed')) return '部分解读失败'
  return '报告已出'
}

function interpretationLabel(status: string) {
  return ({ pending: 'AI 解读中', completed: 'AI 解读完成', failed: 'AI 解读失败' } as Record<string, string>)[status] ?? status
}

function interpretationHint(status: string) {
  return status === 'failed' ? 'AI 解读失败，请以原始报告和专业判断为准。' : 'AI 解读正在生成，请以原始报告为准。'
}

interface ReportItemView {
  name?: string
  code?: string
  value?: string | number
  unit?: string
  reference_range?: string
  status?: string
}

function reportItems(content: Record<string, unknown> | unknown): ReportItemView[] {
  if (Array.isArray(content)) return content as ReportItemView[]
  if (!content || typeof content !== 'object') return []
  const data = content as Record<string, unknown>
  const items = data.items ?? data.results ?? data.indicators
  return Array.isArray(items) ? items as ReportItemView[] : []
}

function reportStatusClass(status?: string) {
  return status === 'high' || status === 'low' ? 'report-abnormal' : ''
}

function reportStatusLabel(status?: string) {
  return ({ high: '偏高', low: '偏低', normal: '正常', abnormal: '异常' } as Record<string, string>)[status ?? ''] ?? status
}

function reportStatusTagType(status?: string) {
  return status === 'high' || status === 'low' || status === 'abnormal' ? 'warning' : 'success'
}

async function handleUpdateStatus(row: Appointment, status: string) {
  await updateAppointmentStatus(row.id, status)
  ElMessage.success(status === 'waiting_exam' ? '已转为等待检查结果，检验科现在可以录入报告' : '操作成功')
  await loadAppointments()
}

function openCompleteDialog(row: Appointment) {
  selectedAppointment.value = row
  completeForm.appointment_id = row.id
  completeForm.diagnosis = ''
  completeForm.content = ''
  completeForm.items = []
  completeDialogVisible.value = true
}

async function handleComplete() {
  if (!completeForm.diagnosis.trim()) {
    ElMessage.warning('请填写诊断')
    return
  }
  if (completeForm.items.some((i) => !i.drug_id)) {
    ElMessage.warning('请为每一行选择药品，或移除多余的空行')
    return
  }
  if (completeForm.items.some((i) => !i.dosage.trim())) {
    ElMessage.warning('请填写每种药品的用法用量')
    return
  }
  completing.value = true
  try {
    await createMedicalRecord({
      appointment_id: completeForm.appointment_id,
      diagnosis: completeForm.diagnosis,
      content: completeForm.content || undefined,
    })
    if (completeForm.items.length > 0) {
      await createPrescription({
        appointment_id: completeForm.appointment_id,
        items: completeForm.items.map((i) => ({
          drug_id: i.drug_id,
          dosage: i.dosage,
          quantity: i.quantity,
        })),
      })
    }
    await updateAppointmentStatus(completeForm.appointment_id, 'completed')
    ElMessage.success('接诊已完成')
    completeDialogVisible.value = false
    await loadAppointments()
  } finally {
    completing.value = false
  }
}

onMounted(() => {
  loadAppointments()
  loadDrugs()
})
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
}
.prescription-item {
  display: grid;
  grid-template-columns: minmax(190px, 1.5fr) minmax(130px, 1fr) 110px 72px 48px;
  gap: 8px;
  margin-bottom: 8px;
  align-items: center;
  width: 100%;
  min-width: 0;
}
.drug-select,
.dosage-input,
.quantity-input {
  width: 100%;
  min-width: 0;
}
.option-meta {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}
.item-subtotal {
  color: #67c23a;
  font-weight: 600;
  font-size: 14px;
  width: 72px;
  white-space: nowrap;
  text-align: right;
}
.remove-button {
  width: 48px;
  margin: 0;
  padding-inline: 0;
}
.prescription-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
.prescription-footer .total {
  color: #e6a23c;
  font-weight: 600;
  font-size: 15px;
}
.field-hint {
  display: block;
  margin-top: 6px;
  color: #909399;
  font-size: 12px;
  line-height: 1.4;
}
.muted { color: #909399; }
.report-status { display: flex; align-items: center; gap: 8px; color: #606266; font-size: 13px; }
.report-panel { margin-bottom: 20px; padding: 14px; border: 1px solid #dcdfe6; border-radius: 6px; background: #f8f9fb; }
.report-panel h3 { margin: 0 0 10px; font-size: 15px; }
.report-block { text-align: left; }
.report-block strong { display: block; margin-bottom: 6px; }
.report-items { display: grid; gap: 8px; max-height: 260px; overflow: auto; margin-bottom: 12px; padding: 10px; background: #fff; }
.report-item { display: grid; grid-template-columns: minmax(150px, 1.5fr) minmax(80px, .7fr) 48px minmax(130px, 1fr) auto; align-items: center; gap: 10px; padding: 8px 4px; border-bottom: 1px solid #ebeef5; font-size: 13px; }
.report-item:last-child { border-bottom: 0; }
.report-item-name { color: #303133; font-weight: 500; }
.report-item-value { color: #303133; font-weight: 600; }
.report-abnormal { color: #e6a23c; }
.report-item-unit, .report-item-range { color: #909399; }
.report-markdown { line-height: 1.7; }
.report-markdown :deep(p) { margin: 0 0 8px; }
.report-markdown :deep(p:last-child) { margin-bottom: 0; }
.report-markdown :deep(h2),
.report-markdown :deep(h3),
.report-markdown :deep(h4) { margin: 12px 0 6px; font-size: 15px; }
.report-markdown :deep(ul),
.report-markdown :deep(ol) { margin: 6px 0; padding-left: 22px; }
.report-markdown :deep(hr) { margin: 12px 0; border: 0; border-top: 1px solid #dcdfe6; }
@media (max-width: 680px) {
  .report-item { grid-template-columns: 1fr auto auto; gap: 5px 8px; }
  .report-item-range { grid-column: 1 / -1; }
}
@media (max-width: 760px) {
  .prescription-item {
    grid-template-columns: minmax(0, 1fr) 110px 64px 48px;
  }
  .drug-select {
    grid-column: 1 / -1;
  }
}
@media (max-width: 520px) {
  .prescription-item {
    grid-template-columns: minmax(0, 1fr) 96px;
    padding-bottom: 10px;
    border-bottom: 1px solid #ebeef5;
  }
  .dosage-input {
    grid-column: 1 / -1;
  }
  .item-subtotal {
    justify-self: start;
    width: auto;
    text-align: left;
  }
  .remove-button {
    justify-self: end;
  }
}
</style>
