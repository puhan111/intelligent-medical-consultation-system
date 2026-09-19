<template>
  <div class="appointments">
    <div class="page-head">
      <h2>我的预约</h2>
      <el-button type="primary" @click="router.push('/booking')">新增预约</el-button>
    </div>

    <el-empty v-if="!loading && !appointments.length" description="还没有预约记录">
      <el-button type="primary" @click="router.push('/booking')">去挂号</el-button>
    </el-empty>

    <div v-loading="loading" class="list">
      <div v-for="item in appointments" :key="item.id" class="card">
        <div class="card-main">
          <div class="line-1">
            <span class="dept">{{ item.department_name }}</span>
            <el-tag :type="statusType(item.status)" size="small">
              {{ statusLabel(item.status) }}
            </el-tag>
          </div>
          <div class="line-2">
            <span>医生：{{ item.doctor_name || '—' }}</span>
            <span>就诊时间：{{ formatTime(item.appointment_time) }}</span>
          </div>
          <div class="line-3">预约号：{{ item.padded_id }}</div>
          <div v-if="item.status === 'waiting_exam'" class="exam-hint">
            医生正在等待检查报告，报告录入后将继续完成本次诊疗。
          </div>
        </div>
        <el-button
          v-if="canCancel(item.status)"
          type="danger"
          plain
          size="small"
          @click="handleCancel(item)"
        >
          取消预约
        </el-button>
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  cancelAppointment,
  listMyAppointments,
  type Appointment,
  type AppointmentStatus,
} from '../../api/appointment'

const router = useRouter()
const appointments = ref<Appointment[]>([])
const loading = ref(false)
const total = ref(0)
const perPage = ref(10)
const currentPage = ref(1)

const STATUS_LABEL: Record<AppointmentStatus, string> = {
  pending: '待确认',
  confirmed: '已确认',
  waiting_exam: '等待检查结果',
  completed: '已完成',
  cancelled: '已取消',
}

const STATUS_TYPE: Record<AppointmentStatus, string> = {
  pending: 'warning',
  confirmed: 'primary',
  waiting_exam: 'warning',
  completed: 'success',
  cancelled: 'info',
}

function statusLabel(status: AppointmentStatus) {
  return STATUS_LABEL[status] ?? status
}

function statusType(status: AppointmentStatus) {
  return (STATUS_TYPE[status] ?? 'info') as any
}

/** 医生确认接诊后流程已开始，患者不能再从前台取消。 */
function canCancel(status: AppointmentStatus) {
  return status === 'pending'
}

function formatTime(iso: string) {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadAppointments() {
  loading.value = true
  try {
    const result = await listMyAppointments(currentPage.value, perPage.value)
    appointments.value = result.items
    total.value = result.total
    perPage.value = result.per_page
  } finally {
    loading.value = false
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadAppointments()
}

async function handleCancel(item: Appointment) {
  await ElMessageBox.confirm(
    `确定取消 ${item.department_name} 的预约吗？`,
    '提示',
    { type: 'warning' }
  )
  await cancelAppointment(item.id)
  ElMessage.success('已取消预约')
  await loadAppointments()
}

onMounted(loadAppointments)
</script>

<style scoped>
.appointments {
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
.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px 20px;
}
.card-main {
  flex: 1;
  min-width: 0;
}
.line-1 {
  display: flex;
  align-items: center;
  gap: 10px;
}
.dept {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}
.line-2 {
  display: flex;
  gap: 20px;
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
}
.line-3 {
  margin-top: 6px;
  font-size: 12px;
  color: #c0c4cc;
}
.exam-hint {
  margin-top: 10px;
  padding: 8px 10px;
  border-left: 3px solid #e6a23c;
  background: #fdf6ec;
  color: #7d5b22;
  font-size: 13px;
  line-height: 1.5;
}
.pager {
  margin-top: 20px;
  justify-content: center;
}
</style>
