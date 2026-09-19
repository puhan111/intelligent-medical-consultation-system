<template>
  <div class="home">
    <div class="hero">
      <h1>不知道挂哪个科？</h1>
      <p>描述症状，AI 助手帮您推荐合适的科室</p>
      <el-button type="primary" size="large" @click="router.push('/triage')">
        开始智能分诊
      </el-button>
    </div>

    <div class="quick-entries">
      <div class="entry" @click="router.push('/booking')">
        <div class="entry-title">预约挂号</div>
        <div class="entry-desc">已经知道科室，直接选医生下单</div>
      </div>
      <div class="entry" @click="router.push('/appointments')">
        <div class="entry-title">我的预约</div>
        <div class="entry-desc">查看预约状态、取消预约</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.home {
  max-width: 860px;
  margin: 0 auto;
}
.hero {
  background: #fff;
  border-radius: 8px;
  padding: 56px 40px;
  text-align: center;
  border: 1px solid #ebeef5;
}
.hero h1 {
  margin: 0;
  font-size: 28px;
  color: #303133;
}
.hero p {
  color: #909399;
  margin: 12px 0 28px;
}
.quick-entries {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 16px;
}
.entry {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}
.entry:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
}
.entry-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}
.entry-desc {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}
</style>
