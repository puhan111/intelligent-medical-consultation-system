<template>
  <div class="booking">
    <h2>预约挂号</h2>

    <el-steps :active="step" align-center class="steps">
      <el-step title="选择科室" />
      <el-step title="选择医生" />
      <el-step title="确认时间" />
    </el-steps>

    <!-- 第一步：选科室 -->
    <div v-if="step === 0" class="panel">
      <div v-loading="loadingDepartments" class="dept-grid">
        <div
          v-for="dept in departments"
          :key="dept.id"
          class="dept-card"
          @click="selectDepartment(dept)"
        >
          <div class="dept-name">{{ dept.name }}</div>
          <div class="dept-desc">{{ dept.description || '暂无简介' }}</div>
        </div>
      </div>
    </div>

    <!-- 第二步：选医生 -->
    <div v-if="step === 1" class="panel">
      <div class="panel-head">
        <span>已选科室：<strong>{{ selectedDepartment?.name }}</strong></span>
        <el-button link type="primary" @click="backToStep(0)">重新选择</el-button>
      </div>

      <el-empty v-if="!loadingDoctors && !doctors.length" description="该科室暂无出诊医生，请选择其它科室" />

      <div v-loading="loadingDoctors" class="doctor-list">
        <div
          v-for="doc in doctors"
          :key="doc.id"
          class="doctor-card"
          @click="selectDoctor(doc)"
        >
          <div class="doctor-avatar">{{ (doc.last_name || '医')[0] }}</div>
          <div class="doctor-info">
            <div class="doctor-name">
              {{ doc.last_name }}{{ doc.first_name }}
              <el-tag v-if="doc.title" size="small" effect="plain">{{ doc.title }}</el-tag>
            </div>
            <div class="doctor-intro">{{ doc.introduction || '暂无简介' }}</div>
          </div>
          <el-button type="primary" size="small">选择</el-button>
        </div>
      </div>
    </div>

    <!-- 第三步：确认时间 -->
    <div v-if="step === 2" class="panel">
      <el-descriptions :column="1" border class="confirm-info">
        <el-descriptions-item label="科室">{{ selectedDepartment?.name }}</el-descriptions-item>
        <el-descriptions-item label="医生">
          {{ selectedDoctor?.last_name }}{{ selectedDoctor?.first_name }}
          {{ selectedDoctor?.title ? `（${selectedDoctor.title}）` : '' }}
        </el-descriptions-item>
      </el-descriptions>

      <el-form label-width="90px" class="time-form">
        <el-form-item label="就诊时间">
          <el-date-picker
            v-model="appointmentTime"
            type="datetime"
            placeholder="请选择就诊时间"
            format="YYYY-MM-DD HH:mm"
            :disabled-date="disabledDate"
          />
        </el-form-item>
      </el-form>

      <div class="actions">
        <el-button @click="backToStep(1)">上一步</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">提交预约</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listDepartments, type Department } from '../../api/department'
import { listDoctors, type Doctor } from '../../api/doctor'
import { createAppointment } from '../../api/appointment'

const route = useRoute()
const router = useRouter()

const step = ref(0)
const departments = ref<Department[]>([])
const doctors = ref<Doctor[]>([])
const loadingDepartments = ref(false)
const loadingDoctors = ref(false)
const submitting = ref(false)

const selectedDepartment = ref<Department | null>(null)
const selectedDoctor = ref<Doctor | null>(null)
const appointmentTime = ref<Date | null>(null)

/** 只允许预约今天及以后 */
function disabledDate(date: Date) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return date < today
}

async function loadDepartments() {
  loadingDepartments.value = true
  try {
    const result = await listDepartments()
    departments.value = result.items
  } finally {
    loadingDepartments.value = false
  }
}

async function selectDepartment(dept: Department) {
  selectedDepartment.value = dept
  selectedDoctor.value = null
  step.value = 1
  loadingDoctors.value = true
  try {
    doctors.value = await listDoctors(dept.id)
  } finally {
    loadingDoctors.value = false
  }
}

function selectDoctor(doc: Doctor) {
  selectedDoctor.value = doc
  step.value = 2
}

function backToStep(target: number) {
  step.value = target
}

async function handleSubmit() {
  if (!selectedDoctor.value || !selectedDepartment.value) return
  if (!appointmentTime.value) {
    ElMessage.warning('请选择就诊时间')
    return
  }
  submitting.value = true
  try {
    await createAppointment({
      doctor_id: selectedDoctor.value.id,
      department_id: selectedDepartment.value.id,
      appointment_time: appointmentTime.value.toISOString(),
    })
    ElMessage.success('预约成功')
    router.push('/appointments')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  await loadDepartments()
  // 支持从分诊页带 department_id 直接进入选医生步骤
  const preset = Number(route.query.department_id)
  if (preset) {
    const dept = departments.value.find((d) => d.id === preset)
    if (dept) await selectDepartment(dept)
  }
})
</script>

<style scoped>
.booking {
  max-width: 860px;
  margin: 0 auto;
}
.booking h2 {
  margin: 0 0 20px;
  color: #303133;
}
.steps {
  margin-bottom: 24px;
}
.panel {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 24px;
  min-height: 220px;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
  color: #606266;
  font-size: 14px;
}
.dept-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.dept-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}
.dept-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
}
.dept-name {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}
.dept-desc {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}
.doctor-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.doctor-card {
  display: flex;
  align-items: center;
  gap: 14px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s;
}
.doctor-card:hover {
  border-color: #409eff;
  background: #f8fbff;
}
.doctor-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #1976d2;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  flex-shrink: 0;
}
.doctor-info {
  flex: 1;
  min-width: 0;
}
.doctor-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}
.doctor-intro {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.confirm-info {
  margin-bottom: 20px;
}
.time-form {
  max-width: 420px;
}
.actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 8px;
}
</style>
