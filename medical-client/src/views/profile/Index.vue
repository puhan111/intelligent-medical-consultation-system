<template>
  <div class="profile">
    <div class="page-head">
      <h2>个人中心</h2>
    </div>

    <el-card v-loading="loading" shadow="never" class="profile-card">
      <div class="section">
        <div class="section-title">基本信息</div>
        <el-form :model="form" label-width="80px">
          <el-form-item label="姓">
            <el-input v-model="form.last_name" placeholder="如：张" />
          </el-form-item>
          <el-form-item label="名">
            <el-input v-model="form.first_name" placeholder="如：三" />
          </el-form-item>
          <el-form-item label="性别">
            <el-radio-group v-model="form.gender">
              <el-radio label="male">男</el-radio>
              <el-radio label="female">女</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
          </el-form-item>
        </el-form>
      </div>

      <div class="section readonly">
        <div class="section-title">账户信息</div>
        <div class="info-list">
          <div class="info-item">
            <span class="info-label">邮箱</span>
            <span class="info-value">{{ profile?.email }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">账户 ID</span>
            <span class="info-value">{{ profile?.padded_id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">注册时间</span>
            <span class="info-value">{{ formatTime(profile?.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">账户状态</span>
            <el-tag :type="profile?.is_active ? 'success' : 'info'" size="small">
              {{ profile?.is_active ? '正常' : '已停用' }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getMyProfile, updateMyProfile, type UserProfile } from '../../api/user'

const profile = ref<UserProfile | null>(null)
const loading = ref(false)
const submitting = ref(false)
const form = reactive({
  first_name: '',
  last_name: '',
  gender: 'male' as 'male' | 'female',
})

function formatTime(iso?: string) {
  if (!iso) return '—'
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadProfile() {
  loading.value = true
  try {
    profile.value = await getMyProfile()
    form.first_name = profile.value.first_name || ''
    form.last_name = profile.value.last_name || ''
    form.gender = (profile.value.gender as 'male' | 'female') || 'male'
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!form.first_name.trim() || !form.last_name.trim()) {
    ElMessage.warning('请填写姓名')
    return
  }
  submitting.value = true
  try {
    profile.value = await updateMyProfile({
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      gender: form.gender,
    })
    ElMessage.success('保存成功')
  } finally {
    submitting.value = false
  }
}

onMounted(loadProfile)
</script>

<style scoped>
.profile {
  max-width: 640px;
  margin: 0 auto;
}
.page-head h2 {
  margin: 0 0 20px;
  color: #303133;
}
.section + .section {
  margin-top: 8px;
  padding-top: 20px;
  border-top: 1px solid #ebeef5;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 18px;
}
.info-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.info-item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.info-label {
  width: 68px;
  flex-shrink: 0;
  font-size: 13px;
  color: #909399;
}
.info-value {
  font-size: 14px;
  color: #303133;
}
</style>
