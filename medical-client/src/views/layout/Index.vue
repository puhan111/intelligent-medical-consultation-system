<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="logo" @click="router.push('/')">智慧医院</div>
      <el-menu :default-active="activePath" mode="horizontal" router class="nav">
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/triage">AI 智能分诊</el-menu-item>
        <el-menu-item index="/booking">预约挂号</el-menu-item>
        <el-menu-item index="/appointments">我的预约</el-menu-item>
        <el-menu-item index="/prescriptions">我的处方</el-menu-item>
        <el-menu-item index="/bills">我的账单</el-menu-item>
        <el-menu-item index="/reports">我的报告</el-menu-item>
        <el-menu-item index="/medical-records">我的病历</el-menu-item>
      </el-menu>
      <div class="user-area">
        <el-dropdown @command="handleCommand">
          <span class="user-name">
            {{ displayName }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { currentUser, clearCurrentUser } from '../../stores/auth'
import { getRefreshToken } from '../../utils/request'
import { logout } from '../../api/auth'

const route = useRoute()
const router = useRouter()
const activePath = computed(() => route.path)
const displayName = computed(() => {
  if (!currentUser.value) return ''
  const { last_name, first_name, email } = currentUser.value
  return last_name && first_name ? `${last_name}${first_name}` : email
})

function handleCommand(command: string) {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'logout') {
    handleLogout()
  }
}

async function handleLogout() {
  const refreshToken = getRefreshToken()
  if (refreshToken) {
    // 登出接口失败不阻塞本地清理
    await logout(refreshToken).catch(() => {})
  }
  clearCurrentUser()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped>
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  align-items: center;
  gap: 24px;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  padding: 0 32px;
}
.logo {
  font-size: 19px;
  font-weight: bold;
  color: #1976d2;
  cursor: pointer;
  white-space: nowrap;
}
.nav {
  flex: 1;
  border-bottom: none;
}
.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-name {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
  font-size: 13px;
  cursor: pointer;
  outline: none;
}
.main {
  background: #f5f7fa;
  padding: 24px 32px;
}
</style>
