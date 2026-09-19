<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2>医疗咨询系统 - 后台管理</h2>
      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.email" placeholder="管理员邮箱" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" style="width: 100%" @click="handleLogin">
            登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../../api/auth'
import { setToken } from '../../utils/request'
import { loadCurrentAdmin } from '../../stores/auth'
import { getRoleHomePath } from '../../utils/roleAccess'

const router = useRouter()
const loading = ref(false)
const form = reactive({
  email: '',
  password: '',
})

async function handleLogin() {
  if (!form.email || !form.password) {
    ElMessage.warning('请输入邮箱和密码')
    return
  }
  loading.value = true
  try {
    const result = await login({ email: form.email, password: form.password })
    setToken(result.access_token)
    const admin = await loadCurrentAdmin()
    ElMessage.success('登录成功')
    await router.push(getRoleHomePath(admin?.role))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: #f0f2f5;
}
.login-card {
  width: 400px;
}
.login-card h2 {
  text-align: center;
  margin-bottom: 24px;
  font-size: 18px;
}
</style>
