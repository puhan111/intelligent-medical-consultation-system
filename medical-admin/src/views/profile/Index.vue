<template>
  <div class="profile-page">
    <div class="page-header">
      <div>
        <h2>个人中心</h2>
        <p>维护当前工作账号的基本资料和登录密码</p>
      </div>
      <el-tag effect="plain">{{ roleLabel }}</el-tag>
    </div>

    <div class="profile-grid">
      <section class="profile-section">
        <h3>基本资料</h3>
        <el-form :model="profileForm" label-position="top">
          <el-form-item label="登录邮箱">
            <el-input :model-value="currentAdmin?.email" disabled />
          </el-form-item>
          <div class="name-row">
            <el-form-item label="姓">
              <el-input v-model="profileForm.last_name" maxlength="100" />
            </el-form-item>
            <el-form-item label="名">
              <el-input v-model="profileForm.first_name" maxlength="100" />
            </el-form-item>
          </div>
          <el-button type="primary" :loading="savingProfile" @click="saveProfile">保存资料</el-button>
        </el-form>
      </section>

      <section class="profile-section">
        <h3>修改密码</h3>
        <el-form :model="passwordForm" label-position="top">
          <el-form-item label="当前密码">
            <el-input v-model="passwordForm.current" type="password" show-password autocomplete="current-password" />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="passwordForm.next" type="password" show-password autocomplete="new-password" />
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input v-model="passwordForm.confirm" type="password" show-password autocomplete="new-password" />
          </el-form-item>
          <el-button type="primary" :loading="savingPassword" @click="savePassword">修改密码</el-button>
        </el-form>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { changeAdminPassword, updateAdmin } from '../../api/admin'
import { currentAdmin, loadCurrentAdmin } from '../../stores/auth'
import { getRoleLabel } from '../../utils/roleAccess'

const savingProfile = ref(false)
const savingPassword = ref(false)
const roleLabel = computed(() => getRoleLabel(currentAdmin.value?.role))
const profileForm = reactive({ first_name: '', last_name: '' })
const passwordForm = reactive({ current: '', next: '', confirm: '' })

watch(
  currentAdmin,
  (admin) => {
    profileForm.first_name = admin?.first_name ?? ''
    profileForm.last_name = admin?.last_name ?? ''
  },
  { immediate: true },
)

async function saveProfile() {
  if (!currentAdmin.value) return
  savingProfile.value = true
  try {
    await updateAdmin(currentAdmin.value.id, {
      first_name: profileForm.first_name.trim() || undefined,
      last_name: profileForm.last_name.trim() || undefined,
    })
    await loadCurrentAdmin()
    ElMessage.success('资料已保存')
  } finally {
    savingProfile.value = false
  }
}

async function savePassword() {
  if (!currentAdmin.value) return
  if (!passwordForm.current || !passwordForm.next) {
    ElMessage.warning('请填写当前密码和新密码')
    return
  }
  if (passwordForm.next.length < 8) {
    ElMessage.warning('新密码至少需要 8 位')
    return
  }
  if (passwordForm.next !== passwordForm.confirm) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  savingPassword.value = true
  try {
    await changeAdminPassword(currentAdmin.value.id, passwordForm.current, passwordForm.next)
    passwordForm.current = ''
    passwordForm.next = ''
    passwordForm.confirm = ''
    ElMessage.success('密码修改成功')
  } finally {
    savingPassword.value = false
  }
}
</script>

<style scoped>
.profile-page { max-width: 920px; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.page-header h2 { margin: 0 0 6px; font-size: 22px; }
.page-header p { color: #909399; font-size: 14px; }
.profile-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 32px; }
.profile-section { border-top: 2px solid #409eff; padding-top: 18px; }
.profile-section h3 { margin: 0 0 18px; font-size: 16px; }
.name-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
@media (max-width: 760px) { .profile-grid { grid-template-columns: 1fr; } }
</style>
