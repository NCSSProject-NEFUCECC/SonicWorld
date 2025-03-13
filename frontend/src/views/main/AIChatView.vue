<template>
    <div
      style="
        width: 1200px;
        margin: auto;
        padding: 20px;
        border: 1px solid #ccc;
        border-radius: 5px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      ">
      <div class="greeting">
        <img src="@/assets/xiaozhi.png" alt="小智AI" class="xiaozhi-image" />
        <p>你好！我是智能导盲助手，有什么问题尽管问我吧。</p>
      </div>
      <div class="chat-container">
        <div class="chat-messages">
          <div
            v-for="(message, index) in chatMessages"
            :key="index"
            :class="{
              'user-message': message.role === 'user',
              'ai-message': message.role === 'assistant'
            }">
            <div class="message-wrapper">
              <img
                v-if="message.role === 'assistant'"
                src="@/assets/xiaozhi.png"
                alt="AI"
                class="avatar" />
              <div class="message-content">
                {{ message.content }}
              </div>
            </div>
          </div>
          <!-- 加载提示 -->
          <div v-if="loading" class="loading-indicator">
            <p class="loading-dots">导盲助手正在思考，请稍候...</p>
          </div>
          <div v-if="filled" class="loading-indicator">
            <p class="loading-dots">超出对话限制，请开始新的对话</p>
            <el-button @click="resetF()">开始新的对话</el-button>
          </div>
        </div>
        <div class="chat-input">
          <el-input
            v-model="userInput"
            placeholder="请输入你的问题"
            :disabled="filled"
            @keyup.enter="sendMessage"></el-input>
          <el-button @click="sendMessage" :disabled="filled">发送</el-button>
        </div>
      </div>
    </div>
  </template>
  
  <script setup lang="ts">
  import type { Message } from '@/datasource/types'
  import { chat } from '@/services/AIService'
  import { ElMessage } from 'element-plus'
  import { ref } from 'vue'
  
  // 小智AI对话相关
  const chatMessages = ref<Message[]>([])
  const userInput = ref('')
  const loading = ref(false)
  const filled=ref(false);
  const limitNum=20;
  const resetF=()=>{
    chatMessages.value=[];
    filled.value=false;
  }
  const sendMessage = async () => {
    if (!userInput.value.trim()) return
    chatMessages.value.push({role:'user',content: userInput.value})
    try {
      loading.value = true
  
      // 使用消息管理函数(历史记录处理)
      userInput.value = ''
      // 调用服务
      const response = await chat(chatMessages.value)
  
      // 更新消息记录
      chatMessages.value.push({role:'assistant',content: response});
      if(chatMessages.value.length >= 2*limitNum) {
      ElMessage.error('消息数量超过限制')
      filled.value=true;
    }
    } catch (error) {
      ElMessage.error('请求失败: ' + (error as Error).message)
    } finally {
      loading.value = false
    }
  }
  </script>
  
  <style scoped src="@/assets/XiaoZhiComponent.css"></style>
  