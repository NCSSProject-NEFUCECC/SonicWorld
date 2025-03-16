<template>
    <el-menu
      default-active="1"
      class="el-menu-vertical-demo"
      :collapse="isCollapse"
      style="height: 100%">
      <div @mouseenter="isCollapse = false" @mouseleave="isCollapse = true">
        <!--logo-->
        <el-menu-item index="1" @click="handleOpen('1', [])">
          <img
            src="https://element.eleme.io/favicon.ico"
            alt="Element logo"
            style="width: 45px; height: 45px; margin: 10px -10px" />
          <template #title>
            <span style="margin-left: 10px">无障碍助手</span>
          </template>
        </el-menu-item>
        <el-menu-item index="1" @click="handleOpen('1', [])">
          <el-icon><Search /></el-icon>
          <template #title>开始对话</template>
        </el-menu-item>
        <el-menu-item index="2" @click="handleOpen('2', [])">
          <el-icon><Compass /></el-icon>          
          <template #title>领航模式</template>
        </el-menu-item>
      </div>
      <el-divider></el-divider>
  
      <!-- 用户头像和弹出菜单 -->
      <div class="user-section">
        <div class="login-wrapper" @click="handleLoginClick">
          <div
            class="avatar-container"
            @mouseenter="showLoginCard = true"
            @mouseleave="showLoginCard = false">
            <el-avatar :size="40" :icon="UserFilled" />
  
            <!-- 悬浮显示的登录卡片 -->
            <div class="login-card" v-show="showLoginCard">
              <div class="login-header">
                <el-avatar :size="40" :icon="UserFilled" class="login-avatar" />
                <div class="login-title">账户登录</div>
              </div>
              <div class="login-menu">
                <div class="menu-item">
                  <span>个人中心</span>
                </div>
                <div class="menu-item">
                  <span>使用记录</span>
                </div>
                <div class="menu-item">
                  <span>辅助设置</span>
                </div>
                
              </div>
            </div>
          </div>
        </div>
      </div>
  
      <!-- 登录模态框 -->
      <el-dialog
        v-model="loginDialogVisible"
        title="用户登录"
        width="400px"
        :close-on-click-modal="false">
        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          label-width="80px"
          status-icon>
          <el-form-item label="用户名" prop="username">
            <el-input v-model="loginForm.username" placeholder="请输入用户名" :prefix-icon="User" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password />
          </el-form-item>
          <el-form-item class="form-buttons">
            <el-button type="primary" @click="handleSubmit" :loading="loading">登录</el-button>
            <el-button @click="loginDialogVisible = false">取消</el-button>
          </el-form-item>
        </el-form>
      </el-dialog>
    </el-menu>
  </template>
  
  <script lang="ts" setup>
  import router from '@/router'
  import {
    DataAnalysis,
    Document,
    Lock,
    Compass,
    Reading,
    Search,
    User,
    UserFilled
  } from '@element-plus/icons-vue'
  import type { FormInstance, FormRules } from 'element-plus'
  import { reactive, ref } from 'vue'
  
  const isCollapse = ref(true)
  const isLoggedIn = ref(false)
  const menus = ref([
    { name: '开始对话', path: '/ai/chat' },
    { name: '领航模式', path: '/navigation' },
    { name: '政策跟踪', path: '/websitetrack' },
    {
      name: '政策分析',
      path: '/policyanalysis'
    },
    { name: '个人账号', path: '/profile' },
    { name: '我的关注', path: '/favorites' },
    { name: '论文收藏', path: '/papers' },
    { name: '浏览历史', path: '/history' }
  ])
  
  const handleOpen = (key: string, keyPath: string[]) => {
    console.log('key', key, 'keyPath', keyPath)
  
    router.push(menus.value[parseInt(key) - 1].path)
  }
  
  const loginDialogVisible = ref(false)
  const loading = ref(false)
  const loginFormRef = ref<FormInstance>()
  
  const loginForm = reactive({
    username: '',
    password: ''
  })
  
  const loginRules = reactive<FormRules>({
    username: [
      { required: true, message: '请输入用户名', trigger: 'blur' },
      { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
    ],
    password: [
      { required: true, message: '请输入密码', trigger: 'blur' },
      { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' }
    ]
  })
  
  const handleLoginClick = () => {
    loginDialogVisible.value = true
  }
  
  const handleSubmit = async () => {
    if (!loginFormRef.value) return
  
    try {
      loading.value = true
      await loginFormRef.value.validate()
      // TODO: 添加登录API调用
      console.log('登录表单提交:', loginForm)
      loginDialogVisible.value = false
    } catch (error) {
      console.error('表单验证失败', error)
    } finally {
      loading.value = false
    }
  }
  
  const showLoginCard = ref(false)
  </script>
  
  <style>
  .el-menu-vertical-demo:not(.el-menu--collapse) {
    width: 200px;
  }
  .el-menu-vertical-demo {
    width: 60px;
    height: 100%;
    position: relative;
  }
  
  .user-section {
    position: absolute;
    bottom: 20px;
    width: 100%;
    display: flex;
    justify-content: center;
  }
  
  .avatar-container {
    cursor: pointer;
    padding: 5px;
    position: relative;
  }
  
  .el-dropdown-menu__item .el-icon {
    margin-right: 8px;
  }
  
  .login-wrapper {
    position: absolute;
    bottom: 20px;
    width: 100%;
  }
  
  .login-card {
    position: absolute;
    bottom: 0;
    left: 50px; /* 调整卡片位置 */
    background: white;
    border-radius: 8px;
    padding: 20px;
    width: 200px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    z-index: 1000;
  }
  
  .login-header {
    text-align: center;
    margin-bottom: 15px;
  }
  
  .login-avatar {
    background: #4285f4;
    margin-bottom: 10px;
  }
  
  .login-title {
    font-size: 16px;
    color: #333;
  }
  
  .login-menu {
    border-top: 1px solid #f0f0f0;
    padding-top: 10px;
  }
  
  .menu-item {
    padding: 8px 0;
    cursor: pointer;
    color: #666;
    font-size: 14px;
  }
  
  .menu-item:hover {
    color: #4285f4;
  }
  
  .form-buttons {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0;
  }
  
  :deep(.el-form-item:last-child) {
    margin-bottom: 0;
  }
  </style>
  