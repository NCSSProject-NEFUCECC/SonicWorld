<template>
  <div
    style="
      width: 85%;
      height: 90%;
      margin: auto;
      padding: 10px;
      border: 1px solid #ccc;
      border-radius: 5px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    ">
    <div class="greeting">
      <img src="@/assets/xiaozhi.png" alt="小智AI" class="xiaozhi-image" />
      <p>{{ greetingMessage || '正在获取天气和时间信息。。。' }}</p>
    </div>
    <div class="chat-container"  style="flex: 1;"  ref="chatContainer">
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
      
    </div>
    <div class="chat-input">
        <el-input
          v-model="userInput"
          placeholder="请输入你的问题"
          :disabled="filled"
          @keyup.enter="sendMessage"></el-input>
        <el-button @click="sendMessage" :disabled="filled">发送</el-button>
      </div>
    <!-- 隐藏的视频元素用于拍照 -->
    <video ref="videoElement" style="display: none;" autoplay playsinline></video>
  </div>
</template>

<script setup lang="ts">
import type { Message } from '@/datasource/types'
import { chat } from '@/services/AIService'
import { ElMessage } from 'element-plus'
import { ref, onMounted, onUnmounted, watch, nextTick, inject } from 'vue'
import { useRouter } from 'vue-router'
import { CookieUtils } from '@/utils/cookieUtils'

const router = useRouter()
const chatContainer = ref<HTMLElement | null>(null)
// 小智AI对话相关
const chatMessages = ref<Message[]>([])
const userInput = ref('')
const loading = ref(false)
const filled=ref(false)
const limitNum=20
const resetF=()=>{
  chatMessages.value=[];
  filled.value=false;
}

// 导入音频文件
import generalErrorAudio from '@/assets/audio/general/general_error.mp3'
import limitWrongAudio from '@/assets/audio/chat/his_msg_limit.mp3'

const general_errora = new Audio(generalErrorAudio)
const limit_wronga = new Audio(limitWrongAudio)

// 视频和拍照相关
const videoElement = ref<HTMLVideoElement | null>(null)
let mediaStream: MediaStream | null = null
const canvas = document.createElement('canvas')
const context = canvas.getContext('2d')
const greetingMessage = ref('')
// 新增音频相关状态和函数
const audioContext = ref<AudioContext | null>(null)
const audioQueue = ref<Uint8Array[]>([])
const isPlayingAudio = ref(false)
const activeAudioSource = ref<AudioBufferSourceNode | null>(null)

// 初始化音频上下文
onMounted(() => {
  audioContext.value = new (window.AudioContext || (window as any).webkitAudioContext)()
  initCamera()
  getWeatherInfo()
})

// 播放音频函数
const playAudio = (audioData: Uint8Array): Promise<void> => {
  return new Promise((resolve) => {
    if (!audioContext.value) {
      console.error('AudioContext not initialized')
      return resolve()
    }

    const wavBuffer = encodeWav(audioData, 22050)
    audioContext.value.decodeAudioData(wavBuffer).then(audioBuffer => {
      const source = audioContext.value!.createBufferSource()
      activeAudioSource.value = source
      source.buffer = audioBuffer
      source.connect(audioContext.value!.destination)
      
      source.onended = () => {
        source.disconnect()
        activeAudioSource.value = null
        isPlayingAudio.value = false
        processAudioQueue()
        resolve()
      }
      
      isPlayingAudio.value = true
      source.start()
    }).catch(error => {
      console.error('Error decoding audio:', error)
      resolve()
    })
  })
}

// 处理音频队列
const processAudioQueue = async () => {
  if (isPlayingAudio.value || audioQueue.value.length === 0) return
  const nextAudio = audioQueue.value.shift()!
  await playAudio(nextAudio)
}

// WAV编码器
const encodeWav = (pcmData: Uint8Array, sampleRate: number): ArrayBuffer => {
  const numChannels = 1
  const bytesPerSample = 2
  const dataSize = pcmData.length
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  // RIFF头部
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(view, 8, 'WAVE')

  // fmt子块
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true) // PCM格式
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * numChannels * bytesPerSample, true)
  view.setUint16(32, numChannels * bytesPerSample, true)
  view.setUint16(34, 16, true)

  // data子块
  writeString(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  // 填充PCM数据
  new Uint8Array(buffer).set(pcmData, 44)

  return buffer
}

const writeString = (view: DataView, offset: number, str: string) => {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}

// 初始化相机
const initCamera = async () => {
  try {
    // 请求相机权限并获取视频流
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1440 },
        height: { ideal: 2560 },
        facingMode: "environment" // 指定使用后置摄像头
      }
    })
    
    // 将视频流设置到video元素
    if (videoElement.value) {
      videoElement.value.srcObject = mediaStream;
      
      canvas.width = 480;
      canvas.height = Math.round(480 * (16/9));
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

const isWeatherRequested = ref(false)

const getWeatherInfo = async () => {
  try {
    if (isWeatherRequested.value) return
    isWeatherRequested.value = true
    // 获取地理位置
    const position: GeolocationPosition = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0
      })
    })

    // 发送位置信息到后端获取天气
    const response = await fetch('http://101.42.16.55:5000/api/weather', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        location: {
          longitude: (position as GeolocationPosition).coords.longitude,
          latitude: (position as GeolocationPosition).coords.latitude
        }
      })
    })

    const data = await response.json()
    if (data.status === 'success') {
      greetingMessage.value = `${data.data.message}`
      console.log('获取天气信息成功，天气信息：', data.data.message)
      
      // 处理音频数据
      if (data.data.audio) {
        console.log('天气音频数据已收到')
        // 获取音频数据的十六进制字符串
        const audioHexString = data.data.audio
        // 将十六进制字符串转换为Uint8Array
        const audioData = new Uint8Array(
          audioHexString.match(/.{1,2}/g)?.map((byte: string) => parseInt(byte, 16)) || []
        )
        // 将音频数据添加到队列并播放
        audioQueue.value.push(audioData)
        processAudioQueue()
        console.log('天气音频数据已添加到播放队列')
      }
    }
  } catch (error) {
    console.error('获取天气信息失败，错误信息：', error)
  }
}

// 组件挂载时初始化相机
onMounted(() => {
  initCamera();
  getWeatherInfo();
})

// 组件卸载时清理资源
onUnmounted(() => {
  // 清理相机资源
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
  }
  activeAudioSource.value?.disconnect()
  audioContext.value?.close()
})

const sendMessage = async () => {
  if (!userInput.value.trim()) return
  const currentUserInput = userInput.value
  const user_token = ref(CookieUtils.getCookie('user_token') || '')
  
  chatMessages.value.push({role:'user', content: currentUserInput})
  try {
    loading.value = true
    userInput.value = ''
    
    const imageData = await captureAndSendImage('默认意图')
    
    const position: GeolocationPosition = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0
      })
    })
    console.log('经度:', position.coords.longitude)
    console.log('纬度:', position.coords.latitude)
    const response = await fetch('http://101.42.16.55:5000/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: chatMessages.value,
        image: imageData,
        longitude: position.coords.longitude,
        latitude: position.coords.latitude,
        user_token: CookieUtils.getCookie('user_token'),
      })
    })
    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`)
    if (!response.body) throw new Error('无法获取响应流')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let receivedText = ''
    const assistantMessageIndex = chatMessages.value.push({role:'assistant', content: ''}) - 1

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const content = line.substring(6)
          if (content === '[完成]') {
            console.log('对话完成')
          } else {
            receivedText += content
            chatMessages.value[assistantMessageIndex].content = receivedText
            
            if (receivedText === '领航模式') {
              router.push({
                path: '/navigation',
                query: { lastInput: currentUserInput }
              })
            }
            if (receivedText === '陪伴模式') {
              router.push({
                path: '/accompany',
              })
            }
          }
        } else if (line.startsWith('data:audio,')) {
          console.log('收到音频数据')
          const hexString = line.substring(11)
          const audioData = new Uint8Array(
            hexString.match(/.{1,2}/g)?.map(byte => parseInt(byte, 16)) || []
          )
          audioQueue.value.push(audioData)
          processAudioQueue()
        }
      }
      
      await nextTick()
      if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight
      }
    }

    if (chatMessages.value.length >= 2 * limitNum) {
      ElMessage.error('消息数量超过限制')
      limit_wronga.play()
      filled.value = true
    }
  } catch (error) {
    ElMessage.error('请求失败: ' + (error as Error).message)
    general_errora.play()
    console.error(error)
  } finally {
    loading.value = false
  }
}

</script>

<style scoped >
.greeting {
display: flex;
align-items: center;
}

.xiaozhi-image {
width: 30px;
height: 30px;
margin-right: 10px;
}

.chat-messages {
max-height: 300px;
height: 100%;
display: flex;
flex-direction: column;

}

.chat-container {
flex: 1;
height: 100%;
display: flex;
flex-direction: column;
max-height: 100;
overflow-y: auto;
}

.message-wrapper {
display: flex;
align-items: flex-start;
margin-bottom: 10px;
}

.avatar {
width: 25px;
height: 25px;
margin-right: 10px;
}

.message-content {
background-color: #f0f0f0;
padding: 8px;
border-radius: 5px;
}

.user-message .message-content {
background-color: #e0f7fa;
/* 用户说的话在右边 */
margin-left: auto;
}

.loading-indicator {
text-align: center;
margin-top: 10px;
}

.chat-input {
display: flex;

}

.el-input {
flex: 1;
margin-right: 10px;
}
</style>