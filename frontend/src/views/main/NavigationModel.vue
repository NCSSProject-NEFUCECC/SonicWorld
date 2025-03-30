<template>
  <div class="navigation-layout">
    <div class="camera-container">
      <video ref="videoElement" autoplay playsinline @loadedmetadata="handleVideoLoaded"></video>
      <div v-if="locationInfo" class="location-info">
        <p v-if="compassHeading !== null">朝向: {{ compassHeading.toFixed(0) }}°</p>
      </div>
    </div>
    <div class="navigation-response">
      <p>{{ navigationResponse }}</p>
    </div>
    <div v-if="!cameraReady" class="status-message">
      <p>{{ cameraStatusMessage }}</p>
    </div>
    <div v-if="cameraError" class="error-message">
      <p>{{ cameraError }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import axios from 'axios'
import { chat } from '@/services/AIService'
// 导入音频文件
import mediaWrongAudio from '@/assets/audio/navigator/media_wrong.mp3'

// 定义类型接口
interface LocationInfo {
  latitude: number;
  longitude: number;
}

interface MediaError {
  name: string;
  message?: string;
}

// 添加指南针相关变量
const compassHeading = ref<number | null>(null)
const hasDeviceOrientation = ref(false)

const videoElement = ref<HTMLVideoElement | null>(null)
let mediaStream: MediaStream | null = null
const locationInfo = ref<LocationInfo | null>(null)
let locationWatchId: number | null = null
const canvas = document.createElement('canvas')
const context = canvas.getContext('2d')
const navigationResponse = ref<string | null>(null)

// 状态标志
const cameraReady = ref(false)
const locationReady = ref(false)
const videoLoaded = ref(false)
const navigationStarted = ref(false)
const cameraError = ref<string | null>(null)
const cameraStatusMessage = ref('正在初始化摄像头...')
// 新增音频相关状态和函数
const audioContext = ref<AudioContext | null>(null)
const audioQueue = ref<Uint8Array[]>([])
const isPlayingAudio = ref(false)
const activeAudioSource = ref<AudioBufferSourceNode | null>(null)


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
// 视频加载完成事件处理
const handleVideoLoaded = () => {
  console.log('视频元素加载完成')
  videoLoaded.value = true
  checkAndStartNavigation()
}

// 初始化导航模式
const initNavigationMode = async () => {
  if (navigationStarted.value) return
  navigationStarted.value = true
  
  console.log('初始化导航模式')
  captureAndSendFrame()
}

// 检查并启动导航
const checkAndStartNavigation = () => {
  if (cameraReady.value && locationReady.value && videoLoaded.value && !navigationStarted.value) {
    console.log('所有条件满足，开始导航模式')
    initNavigationMode()
  } else {
    console.log('等待条件满足:', {
      相机就绪: cameraReady.value,
      位置就绪: locationReady.value,
      视频加载完成: videoLoaded.value,
      导航已启动: navigationStarted.value
    })
  }
}

// 初始化相机流
const initCamera = async () => {
  // 检查浏览器兼容性
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    const errorMsg = '您的浏览器不支持摄像头API，请使用最新版Chrome、Firefox或Edge浏览器';
    console.error(errorMsg);
    cameraError.value = errorMsg;
    return;
  }
  
  cameraStatusMessage.value = '正在请求摄像头权限...';
  console.log('开始请求摄像头权限');
  
  try {
    // 请求相机权限并获取视频流
    mediaStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1440 },
        height: { ideal: 2560 },
        facingMode: "environment" // 指定使用后置摄像头
      }
    })
    
    console.log('摄像头权限获取成功，准备设置视频流');
    cameraStatusMessage.value = '摄像头权限已获取，正在设置视频流...';
    
    // 将视频流设置到video元素
    if (videoElement.value) {
      videoElement.value.srcObject = mediaStream;
      console.log('视频流已设置到video元素');
      
      // 设置canvas尺寸
      canvas.width = 540;
      canvas.height = 720;
      cameraReady.value = true;
      cameraStatusMessage.value = '相机初始化成功';
      console.log('相机初始化成功');
      checkAndStartNavigation();
    } else {
      const errorMsg = '视频元素未找到，DOM可能未完全加载';
      console.error(errorMsg);
      cameraError.value = errorMsg;
    }
  } catch (error: unknown) {
    console.error('相机访问失败:', error);
    const media_wronga = new Audio(mediaWrongAudio)
    media_wronga.play()
    // 根据错误类型提供具体的错误信息
    const mediaError = error as MediaError;
    if (mediaError.name === 'NotAllowedError' || mediaError.name === 'PermissionDeniedError') {
      cameraError.value = '摄像头权限被拒绝，请在浏览器设置中允许访问摄像头';
    } else if (mediaError.name === 'NotFoundError' || mediaError.name === 'DevicesNotFoundError') {
      cameraError.value = '未检测到摄像头设备，请确认设备已连接并正常工作';
    } else if (mediaError.name === 'NotReadableError' || mediaError.name === 'TrackStartError') {
      cameraError.value = '摄像头设备无法启动，可能被其他应用占用或硬件故障';
    } else if (mediaError.name === 'OverconstrainedError') {
      cameraError.value = '摄像头不支持请求的分辨率，尝试降低分辨率要求';
    } else {
      cameraError.value = `摄像头初始化失败: ${mediaError.message || '未知错误'}`;
    }
  }
}

// 获取地理位置
const initGeolocation = () => {
  if ('geolocation' in navigator) {
    locationWatchId = navigator.geolocation.watchPosition(
      (position) => {
        locationInfo.value = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        }
        if (!locationReady.value) {
          locationReady.value = true
          console.log('位置初始化成功')
          checkAndStartNavigation()
        }
        console.log('位置更新:', locationInfo.value)
      },
      (error) => {
        console.error('获取位置失败:', error)
      },
      {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 5000
      }
    )
  } else {
    console.error('浏览器不支持地理位置API')
  }
}

// 捕获视频帧并发送到后端
const captureAndSendFrame = async () => {
  // 确保所有必要条件都满足
  if (!videoElement.value || !locationInfo.value || !cameraReady.value) {
    // console.log('条件不满足，延迟拍照', {
    //   视频元素: !!videoElement.value,
    //   位置信息: !!locationInfo.value,
    //   相机就绪: cameraReady.value
    // })
    setTimeout(captureAndSendFrame, 1000) // 1秒后重试
    return
  }
  
  try {
    // 在canvas上绘制当前视频帧
    if (context && videoElement.value) {
      context.drawImage(videoElement.value, 0, 0, canvas.width, canvas.height)
      // 将canvas内容转换为base64编码的图像
      const imageData = canvas.toDataURL('image/jpeg', 0.7)
      
      console.log('成功捕获视频帧，准备发送到后端')
      
      // 清空之前的导航响应
      navigationResponse.value = '';
      
      // 使用fetch API发送请求并处理流式响应
      const response = await fetch('http://101.42.16.55:5000/api/navigate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          image: imageData,
          location: locationInfo.value,
          heading: compassHeading.value,
          user_token: localStorage.getItem('user_token')
        })
      })

      if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`)
      if (!response.body) throw new Error('无法获取响应流')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let receivedText = ''
      navigationResponse.value = ''

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
              console.log('导航指引完成')
            } else {
              receivedText += content
              navigationResponse.value = receivedText
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
      }
    }
  } catch (error) {
    console.error('拍照过程中出错:', error);
    setTimeout(captureAndSendFrame, 2000); // 2秒后重试
  }
   
  // // 检查音频队列状态，决定下一次捕获的时间
  if (audioQueue.value.length === 0 && !isPlayingAudio.value) {
    // 如果没有音频在播放且队列为空，等待较短时间后再次捕获
    setTimeout(captureAndSendFrame, 300);
  } else {
    // 如果有音频在播放或队列非空，等待音频处理完成后再捕获
    const checkAudioStatus = () => {
      if (audioQueue.value.length === 0 && !isPlayingAudio.value) {
        setTimeout(captureAndSendFrame, 300);
      } else {
        // 继续检查直到条件满足
        setTimeout(checkAudioStatus, 500);
      }
    };
    setTimeout(checkAudioStatus, 500);
  }
}

onMounted(() => {
  console.log('组件挂载，开始初始化')
  // 初始化相机和地理位置
  initCamera()
  initGeolocation()
  // 初始化音频上下文
  audioContext.value = new (window.AudioContext || (window as any).webkitAudioContext)()
  // 初始化指南针
  // 检查设备是否支持方向事件
  if (window.DeviceOrientationEvent) {
    hasDeviceOrientation.value = true
    console.log('设备支持方向事件，初始化指南针')
    
    // 处理设备方向变化事件
    const handleDeviceOrientation = (event: DeviceOrientationEvent) => {
      // iOS 设备需要特殊处理
      if (typeof (event as any).webkitCompassHeading !== 'undefined') {
        // iOS 设备直接提供指南针朝向
        compassHeading.value = (event as any).webkitCompassHeading
      } else if (event.alpha !== null) {
        // 安卓设备需要通过 alpha 值计算
        compassHeading.value = 360 - event.alpha
      }
    }
    
    // 检查是否需要请求权限（iOS 13+ 需要）
    if (typeof (DeviceOrientationEvent as any).requestPermission === 'function') {
      // iOS 13+ 设备需要请求权限
      document.addEventListener('click', async () => {
        try {
          const permission = await (DeviceOrientationEvent as any).requestPermission()
          if (permission === 'granted') {
            window.addEventListener('deviceorientation', handleDeviceOrientation, false)
            console.log('iOS 设备方向权限已获取')
          } else {
            console.error('iOS 设备方向权限被拒绝')
          }
        } catch (error) {
          console.error('请求设备方向权限失败:', error)
        }
      }, { once: true })
    } else {
      // 其他设备直接添加监听
      window.addEventListener('deviceorientation', handleDeviceOrientation, false)
      console.log('设备方向事件监听已添加')
    }
  } else {
    console.log('设备不支持方向事件，无法获取指南针数据')
  }
})

// 组件卸载时清理资源
onUnmounted(() => {
  // 清理相机资源
  if (mediaStream) {
    mediaStream.getTracks().forEach((track: MediaStreamTrack) => track.stop())
  }
  
  // 清理地理位置监听
  if (locationWatchId !== null) {
    navigator.geolocation.clearWatch(locationWatchId)
  }
  
  // 清理设备方向事件监听
  if (hasDeviceOrientation.value) {
    window.removeEventListener('deviceorientation', () => {}, false)
  }
})
</script>

<style scoped>
.navigation-layout {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 20px);
}

.camera-container {
  flex: 3;
  margin: 3%;
  height: 100%;
  border-radius: 15px;
  overflow: hidden; /* 确保内部视频不会溢出圆角边框 */
}

.map-container {
  flex: 2;
  height: 40%;
  margin-top: 10px;
}

.map-placeholder {
  color: #666;
  font-size: 14px;
}

video {
  width: 80%;
  height: 80%;
  object-fit: cover;
  border-radius: 15px;
}

.location-info {
  position: absolute;
  bottom: 10px;
  left: 10px;
  background-color: rgba(0, 0, 0, 0.5);
  color: white;
  padding: 3px 6px;
  border-radius: 3px;
  font-size: 10px;
}

.navigation-response {
  margin:3%;
  height: 15%;
  width: 80%;
  background-color: rgb(0, 255, 170);
  color: rgb(0, 0, 0);
  padding: 8px;
  border-radius: 15px;
  font-size: 12px;
  max-height: 50%;
  overflow-y: auto;
}

.status-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 8px 12px;
  border-radius: 5px;
  font-size: 14px;
  z-index: 10;
}

.error-message {
  position: absolute;
  top: 60%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgba(255, 0, 0, 0.7);
  color: white;
  padding: 8px 12px;
  border-radius: 5px;
  font-size: 14px;
  z-index: 10;
  max-width: 80%;
  text-align: center;
}
</style>