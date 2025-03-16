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
      <!-- 隐藏的视频元素用于拍照 -->
      <video ref="videoElement" style="display: none;" autoplay playsinline></video>
    </div>
  </template>
  
  <script setup lang="ts">
  import type { Message } from '@/datasource/types'
  import { chat } from '@/services/AIService'
  import { ElMessage } from 'element-plus'
  import { ref, onMounted, onUnmounted } from 'vue'
  import { useRouter } from 'vue-router'
  
  const router = useRouter()
  
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

  // 视频和拍照相关
  const videoElement = ref<HTMLVideoElement | null>(null)
  let mediaStream: MediaStream | null = null
  const canvas = document.createElement('canvas')
  const context = canvas.getContext('2d')

  // 初始化相机
  const initCamera = async () => {
    try {
      // 请求相机权限并获取视频流
      mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: "environment" // 指定使用后置摄像头
        }
      })
      
      // 将视频流设置到video元素
      if (videoElement.value) {
        videoElement.value.srcObject = mediaStream;
        
        // 设置canvas尺寸 - 高度固定为480，宽度按比例缩放
        canvas.height = 480;
        // 假设原始比例是16:9，保持这个比例
        canvas.width = Math.round(480 * (16/9));
      }
    } catch (error) {
      console.error('相机访问失败:', error);
    }
  }

  // 捕获图像并发送到后端
  const captureAndSendImage = async (intent: string) => {
    try {
      if (!videoElement.value || !context) {
        console.error('视频元素或Canvas上下文不可用');
        return null;
      }
      
      // 在canvas上绘制当前视频帧，并按照指定尺寸压缩
      context.drawImage(videoElement.value, 0, 0, canvas.width, canvas.height);
      
      // 将canvas内容转换为base64编码的图像，压缩质量为0.7
      const imageData = canvas.toDataURL('image/jpeg', 0.7);
      console.log('成功捕获图像，准备发送到后端');
      
      return imageData;
    } catch (error) {
      console.error('拍照过程中出错:', error);
      return null;
    }
  }

  // 组件挂载时初始化相机
  onMounted(() => {
    initCamera();
  })

  // 组件卸载时清理资源
  onUnmounted(() => {
    // 清理相机资源
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
    }
  })

const sendMessage = async () => {
  if (!userInput.value.trim()) return
  const currentUserInput = userInput.value // 保存当前用户输入
  chatMessages.value.push({role:'user',content: currentUserInput})
  try {
    loading.value = true

    // 使用消息管理函数(历史记录处理)
    userInput.value = ''
    
    // 先捕获图像
    const imageData = await captureAndSendImage('默认意图');
    
    // 使用fetch API发送请求并处理流式响应
    fetch('http://101.42.16.55:5000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          messages: chatMessages.value,
          image: imageData // 每次请求都发送图像数据
        })
      }).then(async response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        const reader = response.body?.getReader()
        if (!reader) {
          throw new Error('无法获取响应流');
        }
        const handleStream=async()=>{
          let receivedText = '';
          // 创建一个初始的空消息
          const assistantMessageIndex = chatMessages.value.push({role:'assistant',content: ''}) - 1;
            
            while (true) {
              const { done, value } = await reader.read();
              
              if (done) {
                console.log('流式响应接收完成');
                break;
              }
              
              // 将接收到的数据块转换为文本
              const chunk = new TextDecoder().decode(value);
              console.log('接收到数据块:', chunk);
              
              // 处理SSE格式的数据
              const lines = chunk.split('\n\n');
              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  const content = line.substring(6);
                  if (content === '[完成]') {
                    console.log('导航指引完成');
                  } else {
                    // 累积接收到的文本
                    receivedText += content;
                    // 更新最后一条消息的内容，而不是添加新消息
                    chatMessages.value[assistantMessageIndex].content = receivedText;
                  }
                }
              }
            }
            
            // 移除原有的图像处理逻辑，因为每次请求都已经包含图像
        }
        
        // 调用处理流的函数
        handleStream();
             
      })
    // if(response==='领航模式'){
    //   // alert(currentUserInput)
    //   //跳转页面并传递用户最后一次输入
    //   router.push({
    //     path: '/navigation',
    //     query: { lastInput: currentUserInput }
    //   })
    // }
    // // 更新消息记录
    // chatMessages.value.push({role:'assistant',content: response});
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
  