<template>
  <div class="report-page">
    <div class="page-header">
      <div>
        <h2>最终检验报告录入</h2>
        <p>处理医生接诊中发起的检查任务，录入最终报告后将自动回流到本次就诊并生成 AI 辅助解读。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadAppointments">刷新</el-button>
    </div>

    <div class="toolbar">
      <el-input v-model="keyword" clearable :prefix-icon="Search" placeholder="搜索待检查患者姓名或邮箱"
        @keyup.enter="handleSearch" @clear="handleSearch" />
      <el-button type="primary" @click="handleSearch">搜索</el-button>
    </div>

    <el-table :data="appointments" v-loading="loading" border empty-text="暂无等待检查结果的就诊">
      <el-table-column label="预约号" width="110">
        <template #default="{ row }">{{ String(row.id).padStart(4, '0') }}</template>
      </el-table-column>
      <el-table-column label="患者姓名" min-width="150">
        <template #default="{ row }">{{ row.patient_name || '未填写姓名' }}</template>
      </el-table-column>
      <el-table-column prop="patient_email" label="邮箱" min-width="200" />
      <el-table-column prop="department_name" label="科室" min-width="130" />
      <el-table-column prop="doctor_name" label="接诊医生" min-width="130" />
      <el-table-column label="就诊时间" min-width="180">
        <template #default="{ row }">{{ formatTime(row.appointment_time) }}</template>
      </el-table-column>
      <el-table-column label="已录报告" width="100">
        <template #default="{ row }">{{ row.report_count }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" size="small" :icon="Upload" @click="openReportDialog(row)">录入报告</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-row" v-if="total > 0">
      <span>共 {{ total }} 条待检查就诊</span>
      <el-pagination v-model:current-page="page" v-model:page-size="perPage" :page-sizes="[10, 20, 50]"
        :total="total" layout="sizes, prev, pager, next" @current-change="loadAppointments"
        @size-change="handlePageSizeChange" />
    </div>

    <el-dialog v-model="dialogVisible" title="最终检验报告录入" width="min(980px, 94vw)" destroy-on-close>
      <div class="selected-patient" v-if="selectedAppointment">
        <div>
          <strong>{{ selectedAppointment.patient_name || '未填写姓名' }}</strong>
          <span>{{ selectedAppointment.department_name }} · {{ selectedAppointment.doctor_name }} · {{ formatTime(selectedAppointment.appointment_time) }}</span>
        </div>
        <el-tag effect="plain">预约号 {{ String(selectedAppointment.id).padStart(4, '0') }}</el-tag>
      </div>

      <el-form :model="form" label-position="top">
        <el-form-item label="报告类型" required>
          <el-input v-model="form.type" maxlength="50" placeholder="例如：血常规、尿常规、X 光" />
        </el-form-item>

        <el-form-item label="录入方式">
          <el-radio-group v-model="entryMode">
            <el-radio-button value="manual">结构化录入</el-radio-button>
            <el-radio-button value="csv">上传 CSV</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="entryMode === 'manual'">
          <el-form-item label="检查指标" required>
            <div class="items-table">
              <div class="items-head">
                <span>项目名称 *</span><span>缩写</span><span>结果 *</span><span>单位</span><span>参考范围</span><span>状态</span><span></span>
              </div>
              <div v-for="(item, index) in form.items" :key="index" class="items-row">
                <el-input v-model="item.name" placeholder="白细胞计数" />
                <el-input v-model="item.code" placeholder="WBC" />
                <el-input v-model="item.value" placeholder="13.8" />
                <el-input v-model="item.unit" placeholder="×10^9/L" />
                <el-input v-model="item.reference_range" placeholder="5.0-12.0" />
                <el-select v-model="item.status" clearable placeholder="状态">
                  <el-option label="正常" value="normal" />
                  <el-option label="偏高" value="high" />
                  <el-option label="偏低" value="low" />
                  <el-option label="危急" value="critical" />
                  <el-option label="异常" value="abnormal" />
                </el-select>
                <el-button text type="danger" :disabled="form.items.length === 1" @click="removeItem(index)">移除</el-button>
              </div>
              <el-button size="small" @click="addItem">添加指标</el-button>
            </div>
          </el-form-item>
          <el-form-item label="检验结论">
            <el-input v-model="form.conclusion" type="textarea" :rows="3" maxlength="2000"
              placeholder="例如：炎症指标升高，建议结合临床表现综合判断。" />
          </el-form-item>
        </template>

        <el-form-item v-else label="CSV 报告文件" required>
          <div class="csv-panel">
            <el-upload
              :auto-upload="false"
              :limit="1"
              accept=".csv,text/csv"
              :on-change="handleCsvChange"
              :on-remove="handleCsvRemove"
            >
              <el-button :icon="Upload">选择 CSV 文件</el-button>
            </el-upload>
            <el-button link type="primary" @click="downloadCsvTemplate">下载 CSV 模板</el-button>
            <span class="field-hint">支持 UTF-8 CSV，最大 1 MB、200 行。AI 可按模板生成测试数据后直接上传。</span>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ entryMode === 'csv' ? '上传并生成 AI 解读' : '录入并生成 AI 解读' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { Refresh, Search, Upload } from '@element-plus/icons-vue'
import {
  createReport,
  listExamPendingAppointments,
  uploadReportCsv,
  type ExamPendingAppointment,
  type ReportItem,
} from '../../api/report'

const appointments = ref<ExamPendingAppointment[]>([])
const loading = ref(false)
const keyword = ref('')
const page = ref(1)
const perPage = ref(10)
const total = ref(0)
const dialogVisible = ref(false)
const submitting = ref(false)
const selectedAppointment = ref<ExamPendingAppointment | null>(null)
const entryMode = ref<'manual' | 'csv'>('manual')
const csvFile = ref<File | null>(null)
const emptyItem = (): ReportItem => ({ name: '', code: '', value: '', unit: '', reference_range: '', status: undefined })
const form = reactive({ type: '', items: [emptyItem()], conclusion: '' })

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

async function loadAppointments() {
  loading.value = true
  try {
    const result = await listExamPendingAppointments(page.value, perPage.value, keyword.value.trim())
    appointments.value = result.items
    total.value = result.total
  } finally {
    loading.value = false
  }
}

function handleSearch() { page.value = 1; loadAppointments() }
function handlePageSizeChange() { page.value = 1; loadAppointments() }

function openReportDialog(appointment: ExamPendingAppointment) {
  selectedAppointment.value = appointment
  form.type = ''
  form.items = [emptyItem()]
  form.conclusion = ''
  entryMode.value = 'manual'
  csvFile.value = null
  dialogVisible.value = true
}

function addItem() { form.items.push(emptyItem()) }
function removeItem(index: number) { if (form.items.length > 1) form.items.splice(index, 1) }

function handleCsvChange(uploadFile: UploadFile) {
  csvFile.value = uploadFile.raw ?? null
}

function handleCsvRemove() { csvFile.value = null }

function downloadCsvTemplate() {
  const csv = '\ufeff项目名称,缩写,结果,单位,参考范围,状态,检验结论\n白细胞计数,WBC,13.8,×10^9/L,5.0-12.0,偏高,炎症指标升高，建议结合临床表现综合判断。\n中性粒细胞百分比,NEUT%,78.2,%,40.0-70.0,偏高,\nC反应蛋白,CRP,32.6,mg/L,0-10,偏高,\n'
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = '检验报告模板.csv'
  link.click()
  URL.revokeObjectURL(url)
}

async function handleSubmit() {
  if (!selectedAppointment.value) return
  if (!form.type.trim()) {
    ElMessage.warning('请填写报告类型')
    return
  }
  if (entryMode.value === 'manual' && form.items.some((item) => !item.name.trim() || !item.value.trim())) {
    ElMessage.warning('请填写每项指标的项目名称和结果')
    return
  }
  if (entryMode.value === 'csv' && !csvFile.value) {
    ElMessage.warning('请选择 CSV 报告文件')
    return
  }
  submitting.value = true
  try {
    if (entryMode.value === 'csv') {
      const data = new FormData()
      data.append('patient_id', String(selectedAppointment.value.patient_id))
      data.append('appointment_id', String(selectedAppointment.value.id))
      data.append('report_type', form.type.trim())
      data.append('file', csvFile.value!)
      await uploadReportCsv(data)
    } else {
      await createReport({
        patient_id: selectedAppointment.value.patient_id,
        appointment_id: selectedAppointment.value.id,
        type: form.type.trim(),
        content: {
          items: form.items.map((item) => ({
            name: item.name.trim(), code: item.code?.trim() || undefined,
            value: item.value.trim(), unit: item.unit?.trim() || undefined,
            reference_range: item.reference_range?.trim() || undefined, status: item.status,
          })),
          conclusion: form.conclusion.trim() || undefined,
        },
      })
    }
    ElMessage.success('报告已录入，AI 解读任务正在处理中')
    dialogVisible.value = false
    await loadAppointments()
  } finally {
    submitting.value = false
  }
}

onMounted(loadAppointments)
</script>

<style scoped>
.page-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 20px; text-align: left; }
.page-header h2 { margin: 0 0 6px; font-size: 22px; }
.page-header p { color: #909399; font-size: 14px; }
.toolbar { display: flex; gap: 10px; width: min(520px, 100%); margin-bottom: 16px; }
.pagination-row { display: flex; align-items: center; justify-content: space-between; margin-top: 18px; color: #909399; font-size: 14px; }
.selected-patient { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px 0; margin-bottom: 16px; border-bottom: 1px solid #ebeef5; }
.selected-patient div { display: flex; flex-direction: column; gap: 4px; text-align: left; }
.selected-patient span { color: #909399; font-size: 13px; }
.field-hint { display: block; margin-top: 6px; color: #909399; font-size: 12px; line-height: 1.5; }
.items-table { width: 100%; overflow-x: auto; }
.items-head, .items-row { display: grid; grid-template-columns: minmax(145px, 1.3fr) 90px 100px minmax(110px, 1fr) minmax(120px, 1fr) 100px 48px; gap: 8px; align-items: center; min-width: 820px; }
.items-head { padding: 0 0 7px; color: #606266; font-size: 12px; }
.items-row { margin-bottom: 8px; }
.items-row :deep(.el-button) { margin: 0; padding-inline: 0; }
.csv-panel { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 12px; width: 100%; }
.csv-panel .field-hint { flex-basis: 100%; margin-top: 0; }
@media (max-width: 680px) {
  .page-header, .pagination-row { align-items: stretch; flex-direction: column; }
  .toolbar { width: 100%; }
  .selected-patient { align-items: flex-start; flex-direction: column; }
}
</style>
