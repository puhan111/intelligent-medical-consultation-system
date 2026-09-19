<template>
  <div class="admin-container">
    <div class="toolbar">
      <el-button type="primary" @click="openCreateDialog">新建管理员</el-button>
      <el-button @click="loadAdmins">刷新</el-button>
    </div>

    <el-table :data="admins" v-loading="loading" border>
      <el-table-column prop="padded_id" label="ID" width="90" />
      <el-table-column prop="email" label="邮箱" />
      <el-table-column label="姓名">
        <template #default="{ row }">{{ row.last_name }}{{ row.first_name }}</template>
      </el-table-column>
      <el-table-column prop="role" label="角色" width="120" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button size="small" @click="openResetDialog(row)">重置密码</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="createDialogVisible" title="新建管理员" width="500px">
      <el-form :model="createForm" label-width="90px">
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
        <el-form-item label="角色">
          <el-select v-model="createForm.role">
            <el-option label="普通管理员" value="admin" />
            <el-option label="超级管理员" value="superadmin" />
            <el-option label="药师" value="pharmacist" />
            <el-option label="收费员" value="cashier" />
            <el-option label="检验科" value="lab" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetDialogVisible" title="重置密码" width="400px">
      <el-form :model="resetForm" label-width="90px">
        <el-form-item label="新密码">
          <el-input
            v-model="resetForm.password"
            type="password"
            show-password
            minlength="8"
            placeholder="请输入至少 8 位的新密码"
            @keyup.enter="handleReset"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="handleReset">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createAdmin, deleteAdmin, listAdmins, resetAdminPassword } from '../../api/admin'
import type { Admin } from '../../types/api'

const admins = ref<Admin[]>([])
const loading = ref(false)

const createDialogVisible = ref(false)
const creating = ref(false)
const createForm = reactive({
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  role: 'admin',
})

const resetDialogVisible = ref(false)
const resetting = ref(false)
const resetForm = reactive({ password: '' })
let resetTargetId: number | null = null

async function loadAdmins() {
  loading.value = true
  try {
    const result = await listAdmins()
    admins.value = result.items
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  createForm.email = ''
  createForm.password = ''
  createForm.first_name = ''
  createForm.last_name = ''
  createForm.role = 'admin'
  createDialogVisible.value = true
}

async function handleCreate() {
  if (!createForm.email.trim() || !createForm.password.trim()) {
    ElMessage.warning('请填写邮箱和密码')
    return
  }
  creating.value = true
  try {
    await createAdmin({ ...createForm })
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    await loadAdmins()
  } finally {
    creating.value = false
  }
}

function openResetDialog(row: Admin) {
  resetTargetId = row.id
  resetForm.password = ''
  resetDialogVisible.value = true
}

async function handleReset() {
  if (!resetForm.password || resetTargetId === null) {
    ElMessage.warning('请输入新密码')
    return
  }
  if (resetForm.password.length < 8) {
    ElMessage.warning('新密码至少需要 8 位')
    return
  }
  resetting.value = true
  try {
    await resetAdminPassword(resetTargetId, resetForm.password)
    ElMessage.success('密码已重置')
    resetDialogVisible.value = false
  } finally {
    resetting.value = false
  }
}

async function handleDelete(row: Admin) {
  await ElMessageBox.confirm(`确定删除管理员 ${row.email} 吗？`, '提示', { type: 'warning' })
  await deleteAdmin(row.id)
  ElMessage.success('删除成功')
  await loadAdmins()
}

onMounted(loadAdmins)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
}
</style>
