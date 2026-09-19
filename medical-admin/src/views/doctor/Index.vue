<template>
  <div class="doctor-container">
    <div class="toolbar">
      <el-button type="primary" @click="openCreateDialog">新建医生</el-button>
      <el-button @click="loadDoctors">刷新</el-button>
    </div>

    <el-table :data="doctors" v-loading="loading" border>
      <el-table-column prop="padded_id" label="ID" width="90" />
      <el-table-column label="姓名">
        <template #default="{ row }">{{ row.last_name }}{{ row.first_name }}</template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" />
      <el-table-column prop="department_name" label="科室" />
      <el-table-column prop="title" label="职称" />
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="createDialogVisible" title="新建医生" width="500px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="科室">
          <el-select v-model="createForm.department_id" placeholder="请选择科室">
            <el-option
              v-for="dept in departments"
              :key="dept.id"
              :label="dept.name"
              :value="dept.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="职称">
          <el-input v-model="createForm.title" placeholder="例如：主治医师" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="createForm.email" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="createForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓">
          <el-input v-model="createForm.last_name" />
        </el-form-item>
        <el-form-item label="名">
          <el-input v-model="createForm.first_name" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="createForm.introduction" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="编辑医生" width="500px">
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="姓名">
          <span>{{ editingDoctor?.last_name }}{{ editingDoctor?.first_name }}</span>
        </el-form-item>
        <el-form-item label="邮箱">
          <span>{{ editingDoctor?.email }}</span>
        </el-form-item>
        <el-form-item label="科室">
          <el-select v-model="editForm.department_id" placeholder="请选择科室">
            <el-option
              v-for="dept in departments"
              :key="dept.id"
              :label="dept.name"
              :value="dept.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="职称">
          <el-input v-model="editForm.title" placeholder="例如：主治医师" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="editForm.introduction" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="updating" @click="handleUpdate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createDoctor,
  deleteDoctor,
  listDoctors,
  updateDoctor,
  type Doctor,
  type DoctorCreate,
  type DoctorUpdate,
} from '../../api/doctor'
import { listDepartments } from '../../api/department'
import type { Department } from '../../types/api'

const doctors = ref<Doctor[]>([])
const departments = ref<Department[]>([])
const loading = ref(false)

const createDialogVisible = ref(false)
const creating = ref(false)
const createForm = reactive<DoctorCreate>({
  department_id: 0,
  title: '',
  introduction: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
})

const editDialogVisible = ref(false)
const updating = ref(false)
const editingDoctor = ref<Doctor | null>(null)
const editForm = reactive<DoctorUpdate>({
  department_id: 0,
  title: '',
  introduction: '',
})

async function loadDoctors() {
  loading.value = true
  try {
    const result = await listDoctors()
    doctors.value = result.items
  } finally {
    loading.value = false
  }
}

async function loadDepartments() {
  const result = await listDepartments()
  departments.value = result.items
}

function openCreateDialog() {
  createForm.department_id = departments.value[0]?.id ?? 0
  createForm.title = ''
  createForm.introduction = ''
  createForm.email = ''
  createForm.password = ''
  createForm.first_name = ''
  createForm.last_name = ''
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!createForm.department_id || !createForm.email.trim() || !createForm.password.trim()) {
    ElMessage.warning('请填写科室、邮箱和密码')
    return
  }
  creating.value = true
  try {
    await createDoctor({ ...createForm })
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    await loadDoctors()
  } finally {
    creating.value = false
  }
}

function openEditDialog(row: Doctor) {
  editingDoctor.value = row
  editForm.department_id = row.department_id
  editForm.title = row.title ?? ''
  editForm.introduction = row.introduction ?? ''
  editDialogVisible.value = true
}

async function handleUpdate() {
  if (!editingDoctor.value) return
  if (!editForm.department_id) {
    ElMessage.warning('请选择科室')
    return
  }
  updating.value = true
  try {
    await updateDoctor(editingDoctor.value.id, {
      department_id: editForm.department_id,
      title: editForm.title,
      introduction: editForm.introduction,
    })
    ElMessage.success('保存成功')
    editDialogVisible.value = false
    await loadDoctors()
  } finally {
    updating.value = false
  }
}

async function handleDelete(row: Doctor) {
  await ElMessageBox.confirm(`确定删除医生 ${row.email} 吗？`, '提示', { type: 'warning' })
  await deleteDoctor(row.id)
  ElMessage.success('删除成功')
  await loadDoctors()
}

onMounted(() => {
  loadDoctors()
  loadDepartments()
})
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
}
</style>

