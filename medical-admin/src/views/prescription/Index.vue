<template>
  <div class="prescription-container">
    <div class="toolbar">
      <el-button @click="loadPrescriptions">刷新</el-button>
    </div>

    <el-table :data="prescriptions" v-loading="loading" border>
      <el-table-column prop="padded_id" label="ID" width="90" />
      <el-table-column prop="patient_name" label="患者" />
      <el-table-column prop="doctor_name" label="医生" />
      <el-table-column label="药品明细" min-width="280">
        <template #default="{ row }">
          <div
            v-for="item in row.items"
            :key="item.id"
            :class="{ declined: !item.is_selected }"
          >
            {{ item.drug_name }} · {{ item.dosage }} · x{{ item.quantity }}
            <span v-if="item.unit_price" class="price">¥{{ item.subtotal?.toFixed(2) }}</span>
            <el-tag v-if="!item.is_selected" size="small" type="info" effect="plain">
              患者已取消
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="应收药费" width="110">
        <template #default="{ row }">
          <span v-if="row.total_amount" class="total">¥{{ row.total_amount.toFixed(2) }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'dispensed' ? 'success' : 'warning'">
            {{ row.status === 'dispensed' ? '已发药' : '待发药' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button
            v-if="row.status !== 'dispensed'"
            size="small"
            type="primary"
            @click="handleDispense(row)"
          >
            发药
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dispensePrescription, listPendingPrescriptions, type Prescription } from '../../api/prescription'

const prescriptions = ref<Prescription[]>([])
const loading = ref(false)

async function loadPrescriptions() {
  loading.value = true
  try {
    const result = await listPendingPrescriptions()
    prescriptions.value = result.items
  } finally {
    loading.value = false
  }
}

async function handleDispense(row: Prescription) {
  const selected = row.items.filter((i) => i.is_selected)
  await ElMessageBox.confirm(
    `确认发放以下 ${selected.length} 种药品？\n${selected.map((i) => `${i.drug_name} x${i.quantity}`).join('\n')}`,
    '发药确认',
    { type: 'warning' }
  )
  await dispensePrescription(row.id)
  ElMessage.success('发药成功')
  await loadPrescriptions()
}

onMounted(loadPrescriptions)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
}
.declined {
  color: #c0c4cc;
  text-decoration: line-through;
}
.price {
  margin-left: 6px;
  color: #67c23a;
}
.total {
  color: #e6a23c;
  font-weight: 600;
}
.muted {
  color: #c0c4cc;
}
</style>
