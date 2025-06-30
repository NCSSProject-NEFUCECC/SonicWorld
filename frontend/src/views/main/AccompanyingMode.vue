<template>
  <div class="accompanying-mode">
    <div class="header">
      <h2>陪伴模式</h2>
      <p>使用语音与AI助手进行对话</p>
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
let analyser: AnalyserNode | null = null
let dataArray: Uint8Array | null = null
let animationFrame: number | null = null
let recordingStartTime: number = 0
let silenceTimeout: number | null = null
let isCurrentlyRecording = false

// 音频监听阈值
const SILENCE_THRESHOLD = 3 // 静音阈值 - 当音量小于3%时认为用户已经说完话
const VOICE_THRESHOLD = 10 // 说话阈值 - 当音量大于10%时开始录音
const SILENCE_DURATION = 500 // 静音持续时间(ms)后停止录音 - 0.5秒
const MIN_RECORDING_DURATION = 100 // 最小录音时长(ms) - 降低最小时长以适应更敏感的检测

// 获取麦克风权限并初始化音频上下文
const initializeAudio = async (): Promise<void> => {
  try {
    console.log('开始请求麦克风权限...')
    audioStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 44100,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true
      }
    })
    console.log('麦克风权限获取成功，音频流已创建')
    
    audioContext.value = new AudioContext()
    analyser = audioContext.value.createAnalyser()
    const source = audioContext.value.createMediaStreamSource(audioStream)
    source.connect(analyser)
    
    analyser.fftSize = 256
    const bufferLength = analyser.frequencyBinCount
    dataArray = new Uint8Array(bufferLength)
    
    console.log('音频初始化成功，分析器已设置，缓冲区长度:', bufferLength)
    
    // 测试音频数据获取
    const testLevel = getAudioLevel()
    console.log('初始音频测试，当前音量:', testLevel.toFixed(1), '%')
    
  } catch (error) {
    console.error('获取麦克风权限失败:', error)
    currentStatus.value = '无法访问麦克风，请检查权限设置'
    throw error
  }
}

// 计算音频音量
const getAudioLevel = (): number => {
  if (!analyser || !dataArray) return 0
  
  // 使用时域数据来计算音量，更准确地反映实际音量
  analyser.getByteTimeDomainData(dataArray)
  let sum = 0
  for (let i = 0; i < dataArray.length; i++) {
    // 计算与中心值(128)的偏差
    const deviation = Math.abs(dataArray[i] - 128)
    sum += deviation
  }
  const average = sum / dataArray.length
  // 将偏差转换为百分比 (最大偏差为127)
  return ((average / 127) * 100)+1
}

// 监听音频音量变化
const monitorAudioLevel = () => {
  if (!isListening.value && !isRecording.value) {
    console.log('音频监控停止：isListening=', isListening.value, 'isRecording=', isRecording.value)
    return
  }
  
  const level = getAudioLevel()
  audioLevel.value = level
  
  // 每隔一段时间输出音量信息（避免过多日志）
  // if (Math.random() < 0.05) { // 约5%的概率输出，增加频率以便验证修复
  //   console.log(`[音量调试] 计算音量: ${level.toFixed(1)}%, 前端显示: ${audioLevel.value.toFixed(1)}%, 监听: ${isListening.value}, 录音: ${isCurrentlyRecording}`)
  // }
  
  // 如果正在监听模式且检测到说话
  if (isListening.value && !isCurrentlyRecording && level > VOICE_THRESHOLD) {
    console.log(`检测到说话 (${level.toFixed(1)}% > ${VOICE_THRESHOLD}%)，开始录音`)
    startRecordingFromListening()
  }
  
  // 如果正在录音且检测到静音
  if (isCurrentlyRecording && level < SILENCE_THRESHOLD) {
    if (!silenceTimeout) {
      console.log(`检测到静音 (${level.toFixed(1)}% < ${SILENCE_THRESHOLD}%)，开始静音计时器`)
      silenceTimeout = setTimeout(() => {
        console.log('静音持续2秒，停止录音并发送到后端')
        stopRecording()
      }, SILENCE_DURATION)
    }
  } else if (isCurrentlyRecording && silenceTimeout) {
    // 正在录音且音量重新超过静音阈值，清除静音定时器
    console.log(`音量恢复 (${level.toFixed(1)}% >= ${SILENCE_THRESHOLD}%)，清除静音计时器`)
    clearTimeout(silenceTimeout)
    silenceTimeout = null
  }
  
  animationFrame = requestAnimationFrame(monitorAudioLevel)
}

// 发送录音到陪伴模式API并处理流式响应
const sendRecordingToCompanion = async (audioBlob: Blob): Promise<void> => {
  try {
    console.log(`[前端] 准备发送录音数据，大小: ${audioBlob.size} 字节，类型: ${audioBlob.type}`)
    const formData = new FormData()
    formData.append('audio', audioBlob, 'recording.webm')
    
    console.log('[前端] 开始发送请求到 /api/cpny')
    const response = await fetch('/api/cpny', {
      method: 'POST',
      body: formData
    })
    
    console.log(`[前端] 收到响应，状态码: ${response.status}, 状态文本: ${response.statusText}`)
    
    if (!response.ok) {
      throw new Error(`陪伴模式请求失败: ${response.statusText}`)
    }
    
    // 处理流式响应
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
    }
    
    const decoder = new TextDecoder()
    let aiResponse = ''
    let userText = ''
    let hasAddedUserMessage = false
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          
          if (data === '[完成]') {
            // AI回复完成
            if (aiResponse.trim()) {
              conversations.value.push({
                type: 'assistant',
                content: aiResponse,
                timestamp: new Date()
              })
            }
            currentStatus.value = 'AI回复完成'
            setTimeout(() => {
              currentStatus.value = ''
            }, 2000)
            return
          } else if (data.startsWith('audio,')) {
            // 处理音频数据
            const audioHex = data.slice(6)
            console.log('接收到音频数据，原始长度:', data.length, '十六进制长度:', audioHex.length)
            console.log('音频数据前100字符:', audioHex.substring(0, 100))
            try {
              playAudioFromHex(audioHex)
            } catch (audioError) {
              console.error('音频播放失败:', audioError)
            }
          } else if (data.startsWith('STT:')) {
            // 处理STT识别结果
            userText = data.slice(4).trim()
            if (userText && !hasAddedUserMessage) {
              conversations.value.push({
                type: 'user',
                content: userText,
                timestamp: new Date()
              })
              hasAddedUserMessage = true
              currentStatus.value = '语音识别完成，AI思考中...'
            }
          } else if (data.trim() && !data.startsWith('STT:')) {
            // 处理AI回复文本数据
            aiResponse += data
            currentStatus.value = `AI回复中: ${aiResponse.substring(0, 50)}...`
          }
        }
      }
    }
    
  } catch (error: unknown) {
    const err = error as Error
    console.error('[前端] 陪伴模式请求失败:', err)
    console.error('[前端] 错误详情:', {
      message: err.message,
      stack: err.stack,
      name: err.name
    })
    throw err
  }
}

// 音频相关状态
const audioContext = ref<AudioContext | null>(null)
const audioQueue = ref<Uint8Array[]>([])
const isPlayingAudio = ref(false)
const activeAudioSource = ref<AudioBufferSourceNode | null>(null)

// 初始化音频上下文
const initAudioContext = () => {
  if (!audioContext.value) {
    audioContext.value = new (window.AudioContext || (window as any).webkitAudioContext)()
    console.log('AudioContext initialized, state:', audioContext.value.state)
  }
}

// WAV编码器 - 处理16位PCM数据
const encodeWav = (pcmData: Uint8Array, sampleRate: number): ArrayBuffer => {
  const numChannels = 1
  const bytesPerSample = 2
  const dataSize = pcmData.length
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  console.log('编码WAV - PCM数据长度:', dataSize, '字节')
  console.log('编码WAV - 预期音频时长:', (dataSize / (sampleRate * bytesPerSample)).toFixed(2), '秒')

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
  view.setUint16(34, 16, true) // 16位深度

  // data子块
  writeString(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  // 填充PCM数据
  new Uint8Array(buffer).set(pcmData, 44)
  
  return buffer
}

// 写入字符串到DataView
const writeString = (view: DataView, offset: number, str: string) => {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}

// 播放音频函数
const playAudio = (audioData: Uint8Array): Promise<void> => {
  return new Promise((resolve) => {
    if (!audioContext.value) {
      console.error('AudioContext not initialized')
      return resolve()
    }

    console.log('开始播放音频，数据长度:', audioData.length)
    
    // 确保AudioContext处于运行状态
    if (audioContext.value.state === 'suspended') {
      audioContext.value.resume().then(() => {
        playAudioInternal(audioData, resolve)
      }).catch((error: any) => {
        console.error('Error resuming AudioContext:', error)
        resolve()
      })
    } else {
      playAudioInternal(audioData, resolve)
    }
  })
}

// 内部音频播放函数
const playAudioInternal = (audioData: Uint8Array, resolve: () => void) => {
  try {
    const wavBuffer = encodeWav(audioData, 24000)
    console.log('WAV buffer created, size:', wavBuffer.byteLength)
    
    audioContext.value!.decodeAudioData(wavBuffer).then(audioBuffer => {
      console.log('音频解码成功，时长:', audioBuffer.duration, '秒')
      
      const source = audioContext.value!.createBufferSource()
      const gainNode = audioContext.value!.createGain()
      
      activeAudioSource.value = source
      source.buffer = audioBuffer
      
      // 设置音量
      gainNode.gain.value = 1.0
      console.log('音量设置为:', 1.0)
      
      // 连接音频节点
      source.connect(gainNode)
      gainNode.connect(audioContext.value!.destination)
      
      // 播放结束处理
      source.onended = () => {
        console.log('音频播放结束')
        isPlayingAudio.value = false
        activeAudioSource.value = null
        resolve()
        // 继续处理队列中的下一个音频
        setTimeout(() => {
          processAudioQueue()
        }, 100)
      }
      
      // 开始播放
      isPlayingAudio.value = true
      source.start(0)
      console.log('音频开始播放')
      
    }).catch((error: any) => {
      console.error('Error decoding audio:', error)
      isPlayingAudio.value = false
      resolve()
    })
    
  } catch (error) {
    console.error('播放音频时出错:', error)
    isPlayingAudio.value = false
    resolve()
  }
}

// 处理音频队列
const processAudioQueue = async () => {
  if (isPlayingAudio.value) {
    console.log('音频正在播放中，等待队列处理')
    return
  }
  if (audioQueue.value.length === 0) {
    console.log('音频队列为空')
    return
  }
  
  console.log('开始处理音频队列，队列长度:', audioQueue.value.length)
  const nextAudio = audioQueue.value.shift()!
  await playAudio(nextAudio)
}

// 播放十六进制音频数据
const playAudioFromHex = (audioHex: string): void => {
  try {
    console.log('收到音频数据，长度:', audioHex.length)
    console.log('音频数据样本:', audioHex.substring(0, 50))
    
    // 确保AudioContext已初始化
    initAudioContext()
    
    // 将十六进制字符串转换为字节数组
    const audioData = new Uint8Array(
      audioHex.match(/.{1,2}/g)?.map((byte: string) => parseInt(byte, 16)) || []
    )
    
    if (audioData.length > 0) {
      console.log('音频数据转换完成，长度:', audioData.length)
      console.log('前10个字节:', Array.from(audioData.slice(0, 10)))
      // 将音频数据添加到队列并播放
      audioQueue.value.push(audioData)
      processAudioQueue()
    } else {
      console.warn('收到空的音频十六进制字符串')
    }
    
  } catch (error) {
    console.error('音频数据处理失败:', error)
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
          
          // 发送到陪伴模式API进行处理
        await sendRecordingToCompanion(blob)
        } catch (error) {
          console.error('陪伴模式处理失败:', error)
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
  
  // 如果还在监听模式，继续监控音频，否则停止
  if (isListening.value) {
    // 继续监听，不停止动画帧
    console.log('录音结束，继续监听模式')
  } else {
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
      animationFrame = null
    }
    audioLevel.value = 0
  }
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
    console.log('开始启动监听模式...')
    if (!audioStream) {
      console.log('音频流不存在，开始初始化音频...')
      await initializeAudio()
    }
    
    isListening.value = true
    currentStatus.value = '正在监听麦克风...'
    console.log('监听状态已设置，开始音频监控')
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
  
  if (audioContext.value) {
    audioContext.value.close()
    audioContext.value = null
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
  min-height: 100vh;
}

.header {
  text-align: center;
  margin-bottom: 30px;
  margin-left: 70px; /* 与录音控件左边距保持一致 */
  margin-right: 20px; /* 与录音控件右边距保持一致 */
  padding: 45px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.header h2 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 28px;
  display: block;
  width: 100%;
  text-align: center;
}

.header hr {
  margin: 15px 0;
  border: none;
  border-top: 1px solid #e9ecef;
  width: 100%;
  display: block;
}

.header p {
  margin: 15px 0 0 0;
  color: #666;
  font-size: 16px;
  display: block;
  width: 100%;
  text-align: center;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 120px; /* 为底部固定的录音组件留出空间 */
}

.conversation-history {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-left: 70px; /* 与录音控件左边距保持一致 */
  margin-right: 20px; /* 与录音控件右边距保持一致 */
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
  margin-left: 70px; /* 与录音控件左边距保持一致 */
  margin-right: 20px; /* 与录音控件右边距保持一致 */
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
  margin-left: 70px; /* 与录音控件左边距保持一致 */
  margin-right: 20px; /* 与录音控件右边距保持一致 */
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
  margin-left: 70px; /* 与录音控件左边距保持一致 */
  margin-right: 20px; /* 与录音控件右边距保持一致 */
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
  margin-left: 70px; /* 与录音控件左边距保持一致 */
  margin-right: 20px; /* 与录音控件右边距保持一致 */
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.quick-test {
  margin-top: 20px;
  margin-left: 70px; /* 与录音控件左边距保持一致 */
  margin-right: 20px; /* 与录音控件右边距保持一致 */
  padding: 15px;
  background: #e9ecef;
  border-radius: 8px;
  text-align: center;
}

.voice-recorder {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  position: fixed;
  bottom: 20px; /* 添加底部间距 */
  left: 70px; /* 避免覆盖导航栏，并留出边距 */
  right: 20px; /* 与其他控件右边距保持一致 */
  z-index: 999; /* 降低层级，确保不覆盖导航栏 */
  border: 1px solid #e9ecef;
}

.recorder-controls {
  display: flex;
  justify-content: center;
  align-items: center;
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
  text-align: center;
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
  
  /* 移动端统一边距设置 */
  .conversation-history,
  .config-error,
  .status-display,
  .test-tool-section,
  .test-tool-container,
  .quick-test,
  .header {
    margin-left: 10px; /* 移动端减少边距 */
    margin-right: 10px;
  }
  
  .voice-recorder {
    right: 10px;
    bottom: 10px;
  }
  
  .header {
    text-align: center;
    margin-bottom: 30px;
    padding: 45px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    display: flex;
    flex-direction: column;
    align-items: center;
  }

.header h2 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 28px;
  display: block;
  width: 100%;
  text-align: center;
}

.header hr {
  margin: 15px 0;
  border: none;
  border-top: 1px solid #e9ecef;
  width: 100%;
  display: block;
}

.header p {
  margin: 15px 0 0 0;
  color: #666;
  font-size: 16px;
  display: block;
  width: 100%;
  text-align: center;
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