<template>
  <div class="drug-container">
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="搜索药品名称"
        clearable
        style="width: 240px"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      />
      <el-radio-group v-model="activeFilter" @change="handleSearch">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="true">已启用</el-radio-button>
        <el-radio-button label="false">已停用</el-radio-button>
      </el-radio-group>
      <el-button type="primary" @click="openCreateDialog">新增药品</el-button>
      <el-button @click="loadDrugs">刷新</el-button>
    </div>

    <el-table :data="drugs" v-loading="loading" border>
      <el-table-column prop="padded_id" label="ID" width="90" />
      <el-table-column prop="name" label="药品名称" min-width="180" />
      <el-table-column prop="spec" label="规格" width="150">
        <template #default="{ row }">{{ row.spec || '—' }}</template>
      </el-table-column>
      <el-table-column label="单价" width="120">
        <template #default="{ row }">¥{{ row.unit_price.toFixed(2) }} / {{ row.unit }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button
            v-if="row.is_active"
            size="small"
            type="danger"
            plain
            @click="handleDeactivate(row)"
          >
            停用
          </el-button>
          <el-button v-else size="small" type="success" plain @click="handleReactivate(row)">
            启用
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

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑药品' : '新增药品'" width="480px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="药品名称" required>
          <el-input v-model="form.name" placeholder="如：阿莫西林胶囊" />
        </el-form-item>
        <el-form-item label="规格">
          <el-input v-model="form.spec" placeholder="如：0.25g×24粒" />
        </el-form-item>
        <el-form-item label="计价单位" required>
          <el-select v-model="form.unit" style="width: 120px">
            <el-option label="盒" value="盒" />
            <el-option label="瓶" value="瓶" />
            <el-option label="粒" value="粒" />
            <el-option label="支" value="支" />
            <el-option label="袋" value="袋" />
          </el-select>
        </el-form-item>
        <el-form-item label="单价" required>
          <el-input-number v-model="form.unit_price" :min="0.01" :precision="2" :step="1" />
          <span class="unit-hint">元 / {{ form.unit }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createDrug,
  deactivateDrug,
  listDrugs,
  updateDrug,
  type Drug,
} from '../../api/drug'

const drugs = ref<Drug[]>([])
const loading = ref(false)
const keyword = ref('')
const activeFilter = ref<'' | 'true' | 'false'>('')
const total = ref(0)
const perPage = ref(20)
const currentPage = ref(1)

const dialogVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({ name: '', spec: '', unit: '盒', unit_price: 10 })

async function loadDrugs() {
  loading.value = true
  try {
    const isActive = activeFilter.value === '' ? undefined : activeFilter.value === 'true'
    const result = await listDrugs(currentPage.value, perPage.value, keyword.value.trim(), isActive)
    drugs.value = result.items
    total.value = result.total
    perPage.value = result.per_page
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  loadDrugs()
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadDrugs()
}

function openCreateDialog() {
  editingId.value = null
  form.name = ''
  form.spec = ''
  form.unit = '盒'
  form.unit_price = 10
  dialogVisible.value = true
}

function openEditDialog(row: Drug) {
  editingId.value = row.id
  form.name = row.name
  form.spec = row.spec ?? ''
  form.unit = row.unit
  form.unit_price = row.unit_price
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写药品名称')
    return
  }
  if (!form.unit_price || form.unit_price <= 0) {
    ElMessage.warning('单价必须大于 0')
    return
  }
  submitting.value = true
  try {
    const payload = {
      name: form.name.trim(),
      spec: form.spec.trim() || undefined,
      unit: form.unit,
      unit_price: form.unit_price,
    }
    if (editingId.value) {
      await updateDrug(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await createDrug(payload)
      ElMessage.success('已新增')
    }
    dialogVisible.value = false
    await loadDrugs()
  } finally {
    submitting.value = false
  }
}

async function handleDeactivate(row: Drug) {
  await ElMessageBox.confirm(
    `停用「${row.name}」后医生将无法再选用该药，已开出的历史处方不受影响。确定停用？`,
    '提示',
    { type: 'warning' }
  )
  await deactivateDrug(row.id)
  ElMessage.success('已停用')
  await loadDrugs()
}

async function handleReactivate(row: Drug) {
  await updateDrug(row.id, { is_active: true })
  ElMessage.success('已启用')
  await loadDrugs()
}

onMounted(loadDrugs)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}
.unit-hint {
  margin-left: 10px;
  color: #909399;
  font-size: 13px;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
