<template>
  <div id="root" ref="refRoot" class="accompanying-mode">
    <div class="header">
      <h2>陪伴模式</h2>
      <p>使用录音与AI助手进行对话</p>
    </div>
    
    <div class="content">
      <!-- 录音控制组件 -->
      <div class="voice-recorder">
        <div class="recorder-controls">
          <button 
            @click="toggleListening"
            :disabled="isConnecting"
            :class="{ 
              'active': isListening,
              'connecting': isConnecting,
              'recording': isRecording
            }"
            class="chat-button"
          >
            <span v-if="isConnecting">准备中...</span>
            <span v-else-if="isRecording">🎤 录音中</span>
            <span v-else-if="isListening">👂 聊天中</span>
            <span v-else>🎤 开始聊天</span>
          </button>
        </div>
        
        <div v-if="currentStatus" class="status-display">
          <span class="status-text">{{ currentStatus }}</span>
        </div>
        
        <div v-if="audioLevel > 0" class="audio-level">
          <div class="level-bar">
            <div 
              class="level-fill" 
              :style="{ width: audioLevel + '%' }"
            ></div>
          </div>
          <span class="level-text">音量: {{ Math.round(audioLevel) }}%</span>
        </div>
      </div>
      
      <!-- 对话历史 -->
      <div v-if="conversations.length > 0" class="conversation-history">
        <h3>对话记录</h3>
        <div class="messages">
          <div 
            v-for="(msg, index) in conversations" 
            :key="index"
            :class="['message', msg.type]"
          >
            <div class="message-content">
              <strong>{{ msg.type === 'user' ? '用户' : 'AI助手' }}：</strong>
              {{ msg.content }}
            </div>
            <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
          </div>
        </div>
      </div>
      

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { chat } from '@/services/AIService'
import type { Message } from '@/datasource/types'

interface Conversation {
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
}



// 状态管理
const conversations = ref<Conversation[]>([])
const currentStatus = ref('')
const isProcessing = ref(false)
const isRecording = ref(false)
const isConnecting = ref(false)
const isListening = ref(false)
const audioLevel = ref(0)

// 媒体相关
let mediaRecorder: MediaRecorder | null = null
let audioStream: MediaStream | null = null
let audioContext: AudioContext | null = null
let analyser: AnalyserNode | null = null
let dataArray: Uint8Array | null = null
let animationFrame: number | null = null
let recordingStartTime: number = 0
let silenceTimeout: number | null = null
let isCurrentlyRecording = false

// 音频监听阈值
const SILENCE_THRESHOLD = 30 // 静音阈值
const VOICE_THRESHOLD = 50 // 说话阈值
const SILENCE_DURATION = 2000 // 静音持续时间(ms)后停止录音
const MIN_RECORDING_DURATION = 1000 // 最小录音时长(ms)

// 获取麦克风权限并初始化音频上下文
const initializeAudio = async (): Promise<void> => {
  try {
    audioStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 44100,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true
      }
    })
    
    audioContext = new AudioContext()
    analyser = audioContext.createAnalyser()
    const source = audioContext.createMediaStreamSource(audioStream)
    source.connect(analyser)
    
    analyser.fftSize = 256
    const bufferLength = analyser.frequencyBinCount
    dataArray = new Uint8Array(bufferLength)
    
    console.log('音频初始化成功')
  } catch (error) {
    console.error('获取麦克风权限失败:', error)
    currentStatus.value = '无法访问麦克风，请检查权限设置'
    throw error
  }
}

// 计算音频音量
const getAudioLevel = (): number => {
  if (!analyser || !dataArray) return 0
  
  analyser.getByteFrequencyData(dataArray)
  let sum = 0
  for (let i = 0; i < dataArray.length; i++) {
    sum += dataArray[i]
  }
  const average = sum / dataArray.length
  return (average / 255) * 100
}

// 监听音频音量变化
const monitorAudioLevel = () => {
  if (!isListening.value && !isRecording.value) return
  
  const level = getAudioLevel()
  audioLevel.value = level
  
  // 如果正在监听模式且检测到说话
  if (isListening.value && !isCurrentlyRecording && level > VOICE_THRESHOLD) {
    console.log('检测到说话，开始录音')
    startRecordingFromListening()
  }
  
  // 如果正在录音且检测到静音
  if (isCurrentlyRecording && level < SILENCE_THRESHOLD) {
    if (!silenceTimeout) {
      silenceTimeout = setTimeout(() => {
        console.log('检测到静音，停止录音')
        stopRecording()
      }, SILENCE_DURATION)
    }
  } else if (silenceTimeout) {
    clearTimeout(silenceTimeout)
    silenceTimeout = null
  }
  
  animationFrame = requestAnimationFrame(monitorAudioLevel)
}

// 发送录音到语音转文字API
const sendRecordingToSTT = async (audioBlob: Blob): Promise<string> => {
  try {
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')
    
    const response = await fetch('/api/cpny', {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`语音转文字失败: ${response.statusText}`)
    }
    
    const result = await response.json()
    return result.text || ''
  } catch (error) {
    console.error('语音转文字失败:', error)
    throw error
  }
}

// 开始录音
const startRecording = async () => {
  if (!audioStream) return
  
  try {
    mediaRecorder = new MediaRecorder(audioStream, {
      mimeType: 'audio/webm;codecs=opus'
    })
    
    const chunks: Blob[] = []
    
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data)
      }
    }
    
    mediaRecorder.onstop = async () => {
      const blob = new Blob(chunks, { type: 'audio/webm' })
      const duration = Date.now() - recordingStartTime
      
      // 只处理超过最小时长的录音
      if (duration >= MIN_RECORDING_DURATION) {
        try {
          currentStatus.value = '正在转换语音...'
          
          // 发送到语音转文字API
          const transcribedText = await sendRecordingToSTT(blob)
          
          if (transcribedText.trim()) {
            // 添加用户消息到对话历史
            conversations.value.push({
              type: 'user',
              content: transcribedText,
              timestamp: new Date()
            })
            
            // 发送给AI处理
            await sendToAI(transcribedText)
          } else {
            currentStatus.value = '未识别到语音内容'
            setTimeout(() => {
              currentStatus.value = ''
            }, 2000)
          }
        } catch (error) {
          console.error('处理录音失败:', error)
          currentStatus.value = '语音处理失败，请重试'
          setTimeout(() => {
            currentStatus.value = ''
          }, 3000)
        }
      } else {
        currentStatus.value = '录音时间太短，已丢弃'
        setTimeout(() => {
          currentStatus.value = ''
        }, 2000)
      }
    }
    
    recordingStartTime = Date.now()
    mediaRecorder.start()
    isRecording.value = true
    isCurrentlyRecording = true
    currentStatus.value = '正在录音...'
    
    // 开始监听音频
    monitorAudioLevel()
    
  } catch (error) {
    console.error('录音失败:', error)
    currentStatus.value = '录音失败'
  }
}

// 从监听模式开始录音
const startRecordingFromListening = async () => {
  if (isCurrentlyRecording) return
  
  // 停止当前AI输出（如果有的话）
  if (isProcessing.value) {
    // 这里可以添加停止AI输出的逻辑
    console.log('检测到用户说话，中断AI输出')
  }
  
  await startRecording()
}

// 停止录音
const stopRecording = () => {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop()
  }
  
  isRecording.value = false
  isCurrentlyRecording = false
  
  if (silenceTimeout) {
    clearTimeout(silenceTimeout)
    silenceTimeout = null
  }
  
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
    animationFrame = null
  }
  
  audioLevel.value = 0
}

// 开始/停止监听
const toggleListening = async () => {
  if (isListening.value) {
    stopListening()
  } else {
    await startListening()
  }
}

// 开始监听
const startListening = async () => {
  try {
    if (!audioStream) {
      await initializeAudio()
    }
    
    isListening.value = true
    currentStatus.value = '正在监听麦克风...'
    monitorAudioLevel()
    
  } catch (error) {
    console.error('启动监听失败:', error)
    currentStatus.value = '启动监听失败'
  }
}

// 停止监听
const stopListening = () => {
  isListening.value = false
  
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
    animationFrame = null
  }
  
  audioLevel.value = 0
  currentStatus.value = ''
}



// 发送消息到AI服务
const sendToAI = async (userMessage: string) => {
  if (isProcessing.value) return
  
  try {
    isProcessing.value = true
    currentStatus.value = '正在思考...'
    
    // 构建消息历史
    const messages: Message[] = conversations.value.map(conv => ({
      role: conv.type === 'user' ? 'user' : 'assistant',
      content: conv.content
    }))
    
    // 添加当前用户消息（如果还没添加）
    const lastMessage = messages[messages.length - 1]
    if (!lastMessage || lastMessage.content !== userMessage) {
      messages.push({
        role: 'user',
        content: userMessage
      })
    }
    
    // 调用AI服务
    let aiResponse = ''
    await chat(messages, (chunk: string) => {
      aiResponse += chunk
      // 实时更新AI回复（可选）
      currentStatus.value = `AI回复中: ${aiResponse.substring(0, 50)}...`
    })
    
    // 添加AI回复到对话历史
    conversations.value.push({
      type: 'assistant',
      content: aiResponse,
      timestamp: new Date()
    })
    
    currentStatus.value = 'AI回复完成'
    
    // 清除状态
    setTimeout(() => {
      currentStatus.value = ''
    }, 2000)
    
  } catch (error) {
    console.error('AI服务调用失败:', error)
    currentStatus.value = 'AI服务调用失败，请重试'
    
    setTimeout(() => {
      currentStatus.value = ''
    }, 3000)
  } finally {
    isProcessing.value = false
  }
}

// 格式化时间
const formatTime = (date: Date): string => {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 格式化时长
const formatDuration = (duration: number): string => {
  const seconds = Math.floor(duration / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  
  if (minutes > 0) {
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }
  return `${remainingSeconds}秒`
}

// 清理资源
const cleanup = () => {
  stopRecording()
  stopListening()
  
  if (audioStream) {
    audioStream.getTracks().forEach(track => track.stop())
    audioStream = null
  }
  
  if (audioContext) {
    audioContext.close()
    audioContext = null
  }
}

// 组件挂载时初始化
onMounted(() => {
  console.log('陪伴模式组件已挂载')
})

// 组件卸载时清理
onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.accompanying-mode {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
  background: #f8f9fa;
  min-height: 100vh;
}

.header {
  text-align: center;
  margin-bottom: 30px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header h2 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 28px;
}

.header p {
  margin: 0;
  color: #666;
  font-size: 16px;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.conversation-history {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.conversation-history h3 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 20px;
}

.messages {
  max-height: 400px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  padding: 12px 16px;
  border-radius: 8px;
  max-width: 80%;
}

.message.user {
  background: #007bff;
  color: white;
  align-self: flex-end;
  margin-left: auto;
}

.message.assistant {
  background: #e9ecef;
  color: #333;
  align-self: flex-start;
}

.message-content {
  margin-bottom: 4px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.message-time {
  font-size: 12px;
  opacity: 0.7;
}

.status-display {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 8px;
  padding: 12px 16px;
  text-align: center;
}

.status-text {
  color: #856404;
  font-weight: 500;
}

.config-error {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  color: #721c24;
}

.config-error h3 {
  margin: 0 0 15px 0;
  color: #721c24;
  font-size: 18px;
}

.config-error ul {
  margin: 10px 0;
  padding-left: 20px;
}

.config-error li {
  margin: 5px 0;
}

.config-help {
  margin-top: 15px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 8px;
}

.config-help ol {
  margin: 10px 0;
  padding-left: 20px;
}

.config-help li {
  margin: 8px 0;
  line-height: 1.4;
}

.config-help a {
  color: #0056b3;
  text-decoration: none;
}

.config-help a:hover {
  text-decoration: underline;
}

.config-help code {
  background: #e9ecef;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.test-tool-section {
  margin-top: 20px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.toggle-test-button,
.quick-test-button {
  background: #17a2b8;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.2s;
  margin-top: 10px;
}

.toggle-test-button:hover,
.quick-test-button:hover {
  background: #138496;
}

.test-tool-container {
  margin-top: 20px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.quick-test {
  margin-top: 20px;
  padding: 15px;
  background: #e9ecef;
  border-radius: 8px;
  text-align: center;
}

.voice-recorder {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.recorder-controls {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.chat-button {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  background: #007bff;
  color: white;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.3s ease;
  min-width: 120px;
}

.chat-button:hover:not(:disabled) {
  background: #0056b3;
  transform: translateY(-1px);
}

.chat-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chat-button.recording {
  background: #dc3545;
  animation: pulse 1.5s infinite;
}

.chat-button.connecting {
  background: #ffc107;
  color: #000;
}

.chat-button.active {
  background: #28a745;
  animation: listening-pulse 2s infinite;
}

.audio-level {
  margin-top: 15px;
}

.level-bar {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.level-fill {
  height: 100%;
  background: linear-gradient(90deg, #28a745, #ffc107, #dc3545);
  transition: width 0.1s ease;
  border-radius: 4px;
}

.level-text {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}



@keyframes pulse {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 10px rgba(220, 53, 69, 0);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(220, 53, 69, 0);
  }
}

@keyframes listening-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7);
  }
  50% {
    box-shadow: 0 0 0 10px rgba(40, 167, 69, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(40, 167, 69, 0);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .accompanying-mode {
    padding: 15px;
  }
  
  .header {
    padding: 15px;
  }
  
  .header h2 {
    font-size: 24px;
  }
  
  .message {
    max-width: 90%;
  }
  
  .recorder-controls {
    flex-direction: column;
    align-items: stretch;
  }
  
  .chat-button {
    width: 100%;
  }
}

/* 滚动条样式 */
.messages::-webkit-scrollbar {
  width: 6px;
}

.messages::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.messages::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>