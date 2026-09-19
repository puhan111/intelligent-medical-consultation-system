<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand">
        <h1>智慧医院</h1>
        <p>患者服务平台</p>
      </div>

      <el-tabs v-model="activeTab" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form :model="loginForm" label-position="top" @submit.prevent>
            <el-form-item label="邮箱">
              <el-input v-model="loginForm.email" placeholder="请输入邮箱" clearable />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入密码"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="submitting" @click="handleLogin">
              登录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form :model="registerForm" label-position="top" @submit.prevent>
            <el-form-item label="邮箱">
              <el-input v-model="registerForm.email" placeholder="请输入邮箱" clearable />
            </el-form-item>
            <div class="name-row">
              <el-form-item label="姓">
                <el-input v-model="registerForm.last_name" placeholder="张" />
              </el-form-item>
              <el-form-item label="名">
                <el-input v-model="registerForm.first_name" placeholder="三" />
              </el-form-item>
            </div>
            <el-form-item label="密码">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="至少8位，含字母和数字"
                show-password
              />
            </el-form-item>
            <el-button type="primary" class="submit-btn" :loading="submitting" @click="handleRegister">
              注册
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register } from '../../api/auth'
import { setToken, setRefreshToken } from '../../utils/request'
import { loadCurrentUser } from '../../stores/auth'

const router = useRouter()
const activeTab = ref('login')
const submitting = ref(false)

const loginForm = reactive({ email: '', password: '' })
const registerForm = reactive({ email: '', password: '', first_name: '', last_name: '' })

async function handleLogin() {
  if (!loginForm.email.trim() || !loginForm.password) {
    ElMessage.warning('请填写邮箱和密码')
    return
  }
  submitting.value = true
  try {
    const result = await login({ email: loginForm.email.trim(), password: loginForm.password })
    setToken(result.access_token)
    setRefreshToken(result.refresh_token)
    await loadCurrentUser()
    ElMessage.success('登录成功')
    router.push('/')
  } finally {
    submitting.value = false
  }
}

async function handleRegister() {
  const { email, password, first_name, last_name } = registerForm
  if (!email.trim() || !password || !first_name.trim() || !last_name.trim()) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (password.length < 8) {
    ElMessage.warning('密码至少 8 位')
    return
  }
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    ElMessage.warning('密码必须同时包含字母和数字')
    return
  }
  submitting.value = true
  try {
    await register({
      email: email.trim(),
      password,
      first_name: first_name.trim(),
      last_name: last_name.trim(),
    })
    ElMessage.success('注册成功，请登录')
    loginForm.email = email.trim()
    activeTab.value = 'login'
    registerForm.password = ''
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e3f2fd 0%, #f8fbff 100%);
}
.login-card {
  width: 420px;
  padding: 32px 40px 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
}
.brand {
  text-align: center;
  margin-bottom: 16px;
}
.brand h1 {
  margin: 0;
  font-size: 26px;
  color: #1976d2;
}
.brand p {
  margin: 6px 0 0;
  color: #909399;
  font-size: 13px;
}
.name-row {
  display: flex;
  gap: 12px;
}
.name-row .el-form-item {
  flex: 1;
}
.submit-btn {
  width: 100%;
  margin-top: 8px;
}
</style>
