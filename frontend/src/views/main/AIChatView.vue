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
      <!-- <img src="@/assets/xiaozhi.png" alt="小智AI" class="xiaozhi-image" style="transform: scaleX(-1)"/> -->
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
              class="avatar" style="transform: scaleX(-1)"/>
            <div class="message-content">
              {{ message.content }}
            </div>
          </div>
        </div>
        <!-- 加载提示 -->
        <div v-if="loading" class="loading-indicator">
          <p class="loading-dots">正在生成回应，请稍候...</p>
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
let mediaStream: MediaStream | null = null;
const canvas = document.createElement('canvas')
const context = canvas.getContext('2d')
const greetingMessage = ref('')
// 新增音频相关状态和函数
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

onMounted(() => {
  // 延迟初始化AudioContext，等待用户交互
  initAudioContext()
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

    console.log('开始播放音频，数据长度:', audioData.length)
    
    // 确保AudioContext处于运行状态
    if (audioContext.value.state === 'suspended') {
      audioContext.value.resume().then(() => {
        playAudioInternal(audioData, resolve)
      }).catch(error => {
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
    // 分析PCM数据
    const nonZeroCount = Array.from(audioData).filter(byte => byte !== 0).length
    const zeroPercentage = ((audioData.length - nonZeroCount) / audioData.length) * 100
    console.log(`PCM数据分析 - 零字节占比: ${zeroPercentage.toFixed(2)}%, 非零字节: ${nonZeroCount}/${audioData.length}`)
    
    // 检查音频幅度和静音段
    let maxAmplitude = 0
    let minAmplitude = 0
    const samples = []
    for (let i = 0; i < audioData.length; i += 2) {
      if (i + 1 < audioData.length) {
        const sample = (audioData[i] | (audioData[i + 1] << 8)) << 16 >> 16
        samples.push(sample)
        maxAmplitude = Math.max(maxAmplitude, sample)
        minAmplitude = Math.min(minAmplitude, sample)
      }
    }
    console.log(`音频幅度范围: ${minAmplitude} 到 ${maxAmplitude}`)
    
    // 检查前置静音段
    let firstNonZeroIndex = -1
    for (let i = 0; i < samples.length; i++) {
      if (Math.abs(samples[i]) > 10) { // 阈值设为10，避免微小噪声
        firstNonZeroIndex = i
        break
      }
    }
    if (firstNonZeroIndex > 0) {
      const silentDuration = (firstNonZeroIndex / 24000).toFixed(3)
      console.log(`检测到前置静音段: ${firstNonZeroIndex} 样本 (${silentDuration}秒)`)
    }
    
    if (maxAmplitude === 0 && minAmplitude === 0) {
      console.warn('警告: 音频数据全为静音!')
    }
    
    // 检查是否需要跳过前置静音段
    let processedAudioData = audioData
    if (firstNonZeroIndex > 0) {
      // 跳过前置静音段，从第一个非零样本开始
      const skipBytes = firstNonZeroIndex * 2 // 每个样本2字节
      processedAudioData = audioData.slice(skipBytes)
      console.log(`跳过前置静音段，移除 ${skipBytes} 字节，剩余 ${processedAudioData.length} 字节`)
    }

    const wavBuffer = encodeWav(processedAudioData, 24000)
    console.log('WAV buffer created, size:', wavBuffer.byteLength)
    
    audioContext.value!.decodeAudioData(wavBuffer).then(audioBuffer => {
      console.log('音频解码成功，时长:', audioBuffer.duration, '秒')
      console.log('音频采样率:', audioBuffer.sampleRate, 'Hz')
      console.log('音频声道数:', audioBuffer.numberOfChannels)
      console.log('AudioContext采样率:', audioContext.value!.sampleRate, 'Hz')
      
      // 检查采样率是否匹配
      if (audioBuffer.sampleRate !== audioContext.value!.sampleRate) {
        console.warn(`采样率不匹配! 音频: ${audioBuffer.sampleRate}Hz, AudioContext: ${audioContext.value!.sampleRate}Hz`)
      }
      
      const source = audioContext.value!.createBufferSource()
      const gainNode = audioContext.value!.createGain()
      
      activeAudioSource.value = source
      source.buffer = audioBuffer
      
      // 设置更高的音量来确保可听见
      const playVolume = Math.max(1.0, 0.8) // 至少80%音量
      gainNode.gain.value = playVolume
      console.log('音量设置为:', playVolume)
      
      // 连接音频节点：source -> gainNode -> destination
      source.connect(gainNode)
      gainNode.connect(audioContext.value!.destination)
      
      // 检查连接状态
      console.log('音频节点连接完成')
      console.log('AudioContext destination:', audioContext.value!.destination)
      console.log('AudioContext state before play:', audioContext.value!.state)
      
      // 添加更多事件监听器
      source.onended = () => {
        console.log('音频播放结束')
        source.disconnect()
        gainNode.disconnect()
        activeAudioSource.value = null
        isPlayingAudio.value = false
        processAudioQueue()
        resolve()
      }
      isPlayingAudio.value = true
      source.start()
      console.log('音频开始播放，AudioContext状态:', audioContext.value!.state)
      console.log('音频缓冲区信息: 时长=', audioBuffer.duration.toFixed(2), 's, 采样率=', audioBuffer.sampleRate, 'Hz')
      
      // 添加播放监控
      const checkPlayback = () => {
        if (isPlayingAudio.value) {
          console.log('播放状态检查: 音频仍在播放中... AudioContext状态:', audioContext.value!.state)
          setTimeout(checkPlayback, 1000)
        }
      }
      setTimeout(checkPlayback, 1000)
      
    }).catch(error => {
      console.error('Error decoding audio:', error)
      console.error('Audio data length:', audioData.length)
      console.error('First few bytes:', Array.from(audioData.slice(0, 20)).map(b => b.toString(16).padStart(2, '0')).join(' '))
      
      console.error('WAV数据前44字节 (头部):')
      const headerView = new Uint8Array(wavBuffer, 0, Math.min(44, wavBuffer.byteLength))
      let headerHex = ''
      for (let i = 0; i < headerView.length; i++) {
        headerHex += headerView[i].toString(16).padStart(2, '0') + ' '
        if ((i + 1) % 8 === 0) headerHex += '\n'
      }
      console.error(headerHex)
      
      resolve()
    })
  } catch (error) {
    console.error('Error in playAudioInternal:', error)
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

// WAV编码器 - 处理16位PCM数据
const encodeWav = (pcmData: Uint8Array, sampleRate: number): ArrayBuffer => {
  const numChannels = 1
  const bytesPerSample = 2
  const dataSize = pcmData.length
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  console.log('编码WAV - PCM数据长度:', dataSize, '字节')
  console.log('编码WAV - 预期音频时长:', (dataSize / (sampleRate * bytesPerSample)).toFixed(2), '秒')
  console.log('编码WAV - 前20字节数据:', Array.from(pcmData.slice(0, 20)).map(b => b.toString(16).padStart(2, '0')).join(' '))

  // 检查PCM数据是否有效
  const nonZeroCount = Array.from(pcmData).filter(byte => byte !== 0).length
  const zeroPercentage = ((pcmData.length - nonZeroCount) / pcmData.length) * 100
  console.log(`编码WAV - 零字节占比: ${zeroPercentage.toFixed(2)}%, 非零字节: ${nonZeroCount}/${pcmData.length}`)
  
  // 检查PCM数据长度是否为偶数（16位PCM每个样本2字节）
  if (pcmData.length % 2 !== 0) {
    console.warn('警告: PCM数据长度不是偶数，可能不是16位数据')
  }
  
  // 检查PCM数据的字节序
  let littleEndianCount = 0
  let bigEndianCount = 0
  for (let i = 0; i < Math.min(1000, pcmData.length); i += 2) {
    if (i + 1 < pcmData.length) {
      // 如果低字节有值而高字节为0，可能是小端序
      if (pcmData[i] !== 0 && pcmData[i + 1] === 0) {
        littleEndianCount++
      }
      // 如果高字节有值而低字节为0，可能是大端序
      else if (pcmData[i] === 0 && pcmData[i + 1] !== 0) {
        bigEndianCount++
      }
    }
  }
  console.log(`编码WAV - 字节序分析: 小端序特征: ${littleEndianCount}, 大端序特征: ${bigEndianCount}`)

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

  // 填充PCM数据 - 直接复制16位PCM数据
  new Uint8Array(buffer).set(pcmData, 44)
  
  // 验证WAV头部
  console.log('WAV头部验证:')
  console.log(`- 文件格式: ${String.fromCharCode(view.getUint8(0), view.getUint8(1), view.getUint8(2), view.getUint8(3))}`)
  console.log(`- 文件大小: ${view.getUint32(4, true) + 8} 字节`)
  console.log(`- 文件类型: ${String.fromCharCode(view.getUint8(8), view.getUint8(9), view.getUint8(10), view.getUint8(11))}`)
  console.log(`- 格式块标识: ${String.fromCharCode(view.getUint8(12), view.getUint8(13), view.getUint8(14), view.getUint8(15))}`)
  console.log(`- 音频格式: ${view.getUint16(20, true)}`)
  console.log(`- 声道数: ${view.getUint16(22, true)}`)
  console.log(`- 采样率: ${view.getUint32(24, true)} Hz`)
  console.log(`- 位深度: ${view.getUint16(34, true)} 位`)
  console.log(`- 数据块标识: ${String.fromCharCode(view.getUint8(36), view.getUint8(37), view.getUint8(38), view.getUint8(39))}`)
  console.log(`- 数据大小: ${view.getUint32(40, true)} 字节`)

  return buffer
}

const writeString = (view: DataView, offset: number, str: string) => {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}

// 初始化相机
const initCamera = async () => {
  const _plus = (window as any).plus;
  if (_plus && _plus.os.name === "Android") {
    const permission = "android.permission.CAMERA";
    const mainActivity = _plus.android.runtimeMainActivity();
    const PackageManager = _plus.android.importClass("android.content.pm.PackageManager");
    
    // 检查权限
    if (mainActivity.checkSelfPermission(permission) !== PackageManager.PERMISSION_GRANTED) {
      // 申请权限
      mainActivity.requestPermissions([permission], {
        onGranted: async function () {
          console.log("Camera 权限已授权");
          await startCamera();
        },
        onDenied: function () {
          alert("相机权限被拒绝，请手动在系统设置中开启");
        }
      });
    } else {
      // 已经有权限，直接打开相机
      await startCamera();
    }
  } else {
    // 不是 Android 或者没有 plus 对象，直接调用
    await startCamera();
  }
};

// 实际的相机启动逻辑
const startCamera = async () => {
  try {
    const mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 3072 },
        height: { ideal: 4096 },
        facingMode: "environment" // 后置摄像头
      }
    });

    if (videoElement.value) {
      videoElement.value.srcObject = mediaStream;
      canvas.width = 540;
      canvas.height = 720;
    }
  } catch (error) {
    alert("相机访问失败:" + error);
  }
};

// 页面加载时检查 plus 是否已加载
onMounted(() => {
  if ((window as any).plus) {
    initCamera();
  } else {
    const checkPlusInterval = setInterval(() => {
      if ((window as any).plus) {
        clearInterval(checkPlusInterval);
        initCamera();
      }
    }, 500);
  }
});


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
    const response = await fetch('http://192.168.31.140:5000/api/weather', {
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
        // 确保AudioContext已初始化
        initAudioContext()
        // 获取音频数据的十六进制字符串
        const audioHexString = data.data.audio
        // 将十六进制字符串转换为Uint8Array
        const audioData = new Uint8Array(
          audioHexString.match(/.{1,2}/g)?.map((byte: string) => parseInt(byte, 16)) || []
        )
        console.log('天气音频数据转换完成，长度:', audioData.length)
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
  // if (mediaStream) {
  //   mediaStream.getTracks().forEach((track) => track.stop());
  // }
  // if (mediaStream) {
  //   mediaStream.getTracks().forEach(track => track.stop())
  // }
  activeAudioSource.value?.disconnect()
  audioContext.value?.close()
})

const sendMessage = async () => {
  if (!userInput.value.trim()) return
  
  // 确保AudioContext已初始化并处于运行状态
  initAudioContext()
  if (audioContext.value && audioContext.value.state === 'suspended') {
    try {
      await audioContext.value.resume()
      console.log('AudioContext resumed')
    } catch (error) {
      console.error('Failed to resume AudioContext:', error)
    }
  }
  
  const currentUserInput = userInput.value
  const user_token = ref(localStorage.getItem('user_token') || '')
  
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
    const response = await fetch('http://192.168.31.140:5000/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: chatMessages.value,
        image: imageData,
        longitude: position.coords.longitude,
        latitude: position.coords.latitude,
        user_token: localStorage.getItem('user_token'),
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
            
            // 处理API标签内容 - 考虑流式传输的情况
            let displayText = receivedText
            
            // 删除完整的API标签，保持换行格式
            displayText = displayText.replace(/<API>.*?<\/API>/gs, '')
            displayText = displayText.replace(/<APIs>.*?<\/APIs>/gs, '')
            
            // 处理未闭合的API标签
            const apiMatch = displayText.match(/(.*?)(<APIs?>(?!.*<\/APIs?>).*?)$/s)
            if (apiMatch) {
              displayText = apiMatch[1]
            }
            
            // 格式化特定文本，确保独立成行
            displayText = displayText.replace(/(我将去调用\[.*?\]，容我思考一下。。。)/g, '\n$1\n')
            displayText = displayText.replace(/\n{3,}/g, '\n\n') // 避免过多空行
            
            chatMessages.value[assistantMessageIndex].content = displayText
            
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
          // 确保AudioContext已初始化
          initAudioContext()
          const hexString = line.substring(11)
          if (hexString && hexString.length > 0) {
            const audioData = new Uint8Array(
              hexString.match(/.{1,2}/g)?.map((byte: string) => parseInt(byte, 16)) || []
            )
            console.log('SSE音频数据转换完成，长度:', audioData.length)
            
            // 验证音频数据
            if (audioData.length > 0) {
              const nonZeroCount = Array.from(audioData).filter(byte => byte !== 0).length
              const zeroPercentage = ((audioData.length - nonZeroCount) / audioData.length) * 100
              console.log(`音频数据验证 - 零字节占比: ${zeroPercentage.toFixed(2)}%, 非零字节: ${nonZeroCount}/${audioData.length}`)
              
              if (nonZeroCount > 0) {
                audioQueue.value.push(audioData)
                processAudioQueue()
              } else {
                console.warn('音频数据全为零，跳过播放')
              }
            } else {
              console.warn('音频数据为空，跳过播放')
            }
          } else {
            console.warn('收到空的音频十六进制字符串')
          }
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
text-align: center;
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
width: 42px;
height: 42px;
margin-right: 8px;
}

.message-content {
background-color: #f0f0f0;
padding: 8px;
border-radius: 5px;
white-space: pre-wrap;
word-wrap: break-word;
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