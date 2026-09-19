<template>
  <div class="department-page">
    <div class="toolbar">
      <el-button type="primary" @click="openCreateDialog">新建科室</el-button>
      <el-button type="primary" @click="importDialogVisible = true">
        导入科室（Markdown）
      </el-button>
      <el-button @click="loadDepartments">刷新</el-button>
    </div>

    <el-table :data="departments" v-loading="loading" border style="width: 100%">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="科室名称" width="180" />
      <el-table-column prop="description" label="描述" />
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="importDialogVisible" title="导入科室" width="600px">
      <p class="hint">
        格式：使用二级标题 <code>## 科室名</code>，标题下方文字为描述，可一次导入多个科室。
      </p>
      <el-upload
        drag
        accept=".md"
        :auto-upload="false"
        :limit="1"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        :file-list="fileList"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽 .md 文件到此处，或<em>点击选择文件</em></div>
      </el-upload>
      <el-input
        v-if="mdContent"
        v-model="mdContent"
        type="textarea"
        :rows="10"
        class="preview-box"
      />
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="handleImport">导入</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" :title="editingId ? '编辑科室' : '新建科室'" width="500px">
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="科室名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import type { UploadFile, UploadFiles } from 'element-plus'
import {
  createDepartment,
  deleteDepartment,
  importDepartmentsFromMarkdown,
  listDepartments,
  updateDepartment,
} from '../../api/department'
import type { Department } from '../../types/api'

const departments = ref<Department[]>([])
const loading = ref(false)
const importDialogVisible = ref(false)
const importing = ref(false)
const mdContent = ref('')
const fileList = ref<UploadFiles>([])

const editDialogVisible = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const editForm = reactive({ name: '', description: '' })

async function loadDepartments() {
  loading.value = true
  try {
    const result = await listDepartments()
    departments.value = result.items
  } finally {
    loading.value = false
  }
}

function handleFileChange(file: UploadFile) {
  fileList.value = [file]
  const raw = file.raw
  if (!raw) return
  const reader = new FileReader()
  reader.onload = () => {
    mdContent.value = (reader.result as string) ?? ''
  }
  reader.readAsText(raw, 'utf-8')
}

function handleFileRemove() {
  fileList.value = []
  mdContent.value = ''
}

async function handleImport() {
  if (!mdContent.value.trim()) {
    ElMessage.warning('请先选择一个 .md 文件')
    return
  }
  importing.value = true
  try {
    const result = await importDepartmentsFromMarkdown(mdContent.value)
    ElMessage.success(`导入成功：新增 ${result.created.length} 个，跳过 ${result.skipped.length} 个（已存在）`)
    importDialogVisible.value = false
    mdContent.value = ''
    fileList.value = []
    await loadDepartments()
  } finally {
    importing.value = false
  }
}

function openCreateDialog() {
  editingId.value = null
  editForm.name = ''
  editForm.description = ''
  editDialogVisible.value = true
}

function openEditDialog(row: Department) {
  editingId.value = row.id
  editForm.name = row.name
  editForm.description = row.description ?? ''
  editDialogVisible.value = true
}

async function handleSave() {
  if (!editForm.name.trim()) {
    ElMessage.warning('请输入科室名称')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateDepartment(editingId.value, { ...editForm })
      ElMessage.success('修改成功')
    } else {
      await createDepartment({ ...editForm })
      ElMessage.success('创建成功')
    }
    editDialogVisible.value = false
    await loadDepartments()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: Department) {
  await ElMessageBox.confirm(`确定删除科室「${row.name}」吗？`, '提示', { type: 'warning' })
  await deleteDepartment(row.id)
  ElMessage.success('删除成功')
  await loadDepartments()
}

onMounted(loadDepartments)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 8px;
}
.hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 12px;
}
.hint code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
}
.preview-box {
  margin-top: 12px;
}
</style>
