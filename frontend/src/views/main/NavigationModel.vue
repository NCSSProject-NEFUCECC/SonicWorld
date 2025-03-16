<template>
  <div class="camera-container">
    <video ref="videoElement" autoplay playsinline @loadedmetadata="handleVideoLoaded"></video>
    <div v-if="locationInfo" class="location-info">
      <p>经度: {{ locationInfo.longitude }}</p>
      <p>纬度: {{ locationInfo.latitude }}</p>
    </div>
    <div v-if="navigationResponse" class="navigation-response">
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
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { chat } from '@/services/AIService'

// 定义类型接口
interface LocationInfo {
  latitude: number;
  longitude: number;
}

interface MediaError {
  name: string;
  message?: string;
}

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
        width: { ideal: 1280 },
        height: { ideal: 720 },
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
      canvas.width = 1280;
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
const captureAndSendFrame = () => {
  // 确保所有必要条件都满足
  if (!videoElement.value || !locationInfo.value || !cameraReady.value) {
    console.log('条件不满足，延迟拍照', {
      视频元素: !!videoElement.value,
      位置信息: !!locationInfo.value,
      相机就绪: cameraReady.value
    })
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
      navigationResponse.value = '正在分析环境...';
      
      // 使用fetch API发送请求并处理流式响应
      fetch('http://101.42.16.55:5000/api/navigate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          image: imageData,
          location: locationInfo.value
        })
      })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        // 获取响应的可读流
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('无法获取响应流');
        }
        navigationResponse.value = '';
        // 处理流式响应
        const processStream = async () => {
          try {
            let receivedText = '';
            
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
                    receivedText += content + ' ';
                    navigationResponse.value = receivedText;
                  }
                }
              }
            }
            
            // 3秒后再次拍照发送
            setTimeout(captureAndSendFrame, 500);
            
          } catch (error) {
            console.error('处理流式响应时出错:', error);
            setTimeout(captureAndSendFrame, 5000); // 5秒后重试
          }
        };
        
        // 开始处理流
        processStream();
      })
      .catch(error => {
        console.error('导航数据发送失败:', error);
        navigationResponse.value = `发送失败: ${error.message}`;
        // 发生错误时也尝试重新发送
        setTimeout(captureAndSendFrame, 5000); // 5秒后重试
      });
    }
  } catch (error) {
    console.error('拍照过程中出错:', error);
    setTimeout(captureAndSendFrame, 2000); // 2秒后重试
  }
}

// 组件挂载时初始化相机和地理位置
onMounted(() => {
  console.log('组件挂载，开始初始化')
  // 初始化相机和地理位置
  initCamera()
  initGeolocation()
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
})
</script>

<style scoped>
.camera-container {
  width: 100%;
  height: 20vh;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  position: relative;
}

video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.location-info {
  position: absolute;
  bottom: 10px;
  left: 10px;
  background-color: rgba(0, 0, 0, 0.5);
  color: white;
  padding: 5px 10px;
  border-radius: 5px;
  font-size: 12px;
}

.navigation-response {
  position: absolute;
  top: 10px;
  left: 10px;
  right: 10px;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 10px;
  border-radius: 5px;
  font-size: 14px;
  max-height: 60%;
  overflow-y: auto;
}

.status-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 10px 20px;
  border-radius: 5px;
  font-size: 16px;
  z-index: 10;
}

.error-message {
  position: absolute;
  top: 60%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgba(255, 0, 0, 0.7);
  color: white;
  padding: 10px 20px;
  border-radius: 5px;
  font-size: 16px;
  z-index: 10;
  max-width: 80%;
  text-align: center;
}
</style>
