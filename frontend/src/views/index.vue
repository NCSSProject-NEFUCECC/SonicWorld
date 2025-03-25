<script setup lang="ts">
import HeaderView from '@/views/header/index.vue'
</script>

<template>
  <div class="app-container">
    <!-- 左侧导航栏 -->
    <nav class="side-nav">
      <HeaderView />
    </nav>

    <!-- 主内容区域 -->
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8f9ff 0%, #fff1f1 100%);
}

.side-nav {
  position: fixed;
  left: 0;
  top: 0;
  width: 40px;
  height: 100vh;
  background-color: #fff;
  box-shadow: 0 2px 6px 0 rgba(0, 0, 0, 0.05);
  z-index: 1000;
}

.main-content {
  
  margin-left: 50px;
  align-content: center;
  width: calc(100% - 50px);
  height: 100vh;
}
</style>    