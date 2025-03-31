<template>
    <el-menu
      default-active="1"
      class="el-menu-vertical-demo"
      :collapse="isCollapse"
      style="height: 100%">
      <div @mouseenter="isCollapse = false" @mouseleave="isCollapse = true" style="top: auto;">
        <!--logo-->
        <el-menu-item index="1" @click="handleOpen('1', [])">
          <img
            src="https://element.eleme.io/favicon.ico"
            alt="Element logo"
            style="width: 45px; height: 45px; margin: 10px -10px" />
          <template #title>
            <span style="margin-left: 20px">希声</span>
          </template>
        </el-menu-item>
        <el-menu-item index="1" @click="handleOpen('1', [])" aria-label="开始对话">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>开始对话</template>
        </el-menu-item>
        <el-menu-item index="2" @click="handleOpen('2', [])" aria-label="领航模式">
          <el-icon><Compass /></el-icon>          
          <template #title>领航模式</template>
        </el-menu-item>
        <el-menu-item index="3" @click="handleOpen('3', [])" aria-label="陪伴模式">
          <el-icon><Phone /></el-icon>        
          <template #title>陪伴模式</template>
        </el-menu-item>
      </div>
      <el-divider></el-divider>
  
      <!-- 用户头像和弹出菜单 -->
      <div class="user-section">
        <div class="login-wrapper" @click="handleLoginClick">
          <div
            class="avatar-container"
            @click="showLoginCard = !showLoginCard"
            role="button"
            aria-label="用户登录按钮"
            tabindex="0">
            <el-avatar :size="40" :icon="UserFilled" />
  
            <!-- 悬浮显示的登录卡片 -->
            <div class="login-card" v-show="showLoginCard">
              <div class="login-header">
                <el-avatar :size="40" :icon="UserFilled" class="login-avatar" />
                <!--未登录显示登入，已经登入显示haveLogin-->
                <div class="login-title">
                  <span v-if="haveLogin==null">点此登录</span>
                  <span v-else>{{haveLogin}}</span>
                </div>
              </div>
              <div class="login-menu">
                <div class="menu-item" role="menuitem" aria-label="点此输入陪伴模式令牌" @click="handleTokenInput">
                  <span>陪伴模式令牌</span>
                </div>
                <div class="menu-item" @click="handleLogout">
                  <span>退出登录</span>
                </div> 
              </div>
            </div>
          </div>
        </div>
      </div>
  
      <!-- 登录模态框 -->
      <el-dialog
        v-if="haveLogin==null"
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
  import { ElMessageBox } from 'element-plus'
  import type { FormInstance, FormRules } from 'element-plus'
  import { reactive, ref, provide } from 'vue'
  import axios from 'axios'
  import {CommonService} from '@/services/CommonService.ts'
  import { CookieUtils } from '@/utils/cookieUtils.ts'
  import { ElMessage } from 'element-plus'
  import wrongUsrpsdAudio from '@/assets/audio/login/wrong_usrpsd.mp3'
  import wrongServerAudio from '@/assets/audio/login/wrong_server.mp3'
  import otherWrongAudio from '@/assets/audio/login/other_wrong.mp3'
  import successLoginAudio from '@/assets/audio/login/success_login.mp3'
  import loginReminderAudio from '@/assets/audio/login/login_reminder.mp3'
  const haveLogin=ref<string|null>(null);
  haveLogin.value=localStorage.getItem('user_token')
  const isCollapse = ref(true)
  const isLoggedIn = ref(false)
  const menus = ref([
    { 
      name: '开始对话', 
      path: '/ai/chat' 
    },
    {
      name: '领航模式',
      path: '/navigation'
    },
    {
      name: '陪伴模式',
      path: '/accompany'
    },
  ])
  const loginRemindera = new Audio(loginReminderAudio)
   
  const handleOpen = (key: string, keyPath: string[]) => {
    console.log('key', key, 'keyPath', keyPath)
    console.log('user_token',CookieUtils.getCookie('user_token'))
    if(key!=='1' && localStorage.getItem('user_token')==null){
      ElMessage.error('请先登录')
      loginRemindera.play()
      router.push(menus.value[0].path)
      return
    }
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
  const handleLogout = () => {
    // 使用CookieUtils工具类删除cookie
    localStorage.removeItem('user_token')
    haveLogin.value=null;
    ElMessage.success('已退出登录')
  }

  const wrong_usrpsda = new Audio(wrongUsrpsdAudio)
  const wrong_servera = new Audio(wrongServerAudio)
  const other_wronga = new Audio(otherWrongAudio)
  const success_logina = new Audio(successLoginAudio)

  const handleSubmit = async () => {
    if (!loginFormRef.value) return
  
    try {
      loading.value = true
      await loginFormRef.value.validate()
      
      const response = await CommonService.loginService(loginForm.username,loginForm.password)
  
      if (response.data.status === 'success') {
        ElMessage.success(response.data.message)
        isLoggedIn.value = true
        loginDialogVisible.value = false
        showLoginCard.value = false
        haveLogin.value=localStorage.getItem('user_token')
        success_logina.play()
      } else {
        ElMessage.error(response.data.message || '登录失败')
        wrong_servera.play()
      }
    } catch (error: any) {
      console.error('登录失败:', error)
      if (error.response?.status === 401) {
        ElMessage.error('用户名或密码错误')
        wrong_usrpsda.play()
      } else {
        ElMessage.error(error.response?.data?.message || '登录失败，请稍后重试')
        other_wronga.play()
      }
    } finally {
      loading.value = false
    }
  }
  
  const showLoginCard = ref(false)
  
  const handleTokenInput = () => {
    ElMessageBox.prompt('请输入陪伴模式令牌', '令牌输入', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    }).then(({ value }) => {
      localStorage.setItem('accompany_token', value)
      ElMessage.success('令牌已保存')
    }).catch(() => {
      ElMessage.info('已取消输入')
    })
  }
  </script>
  
  <style scoped>
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
  