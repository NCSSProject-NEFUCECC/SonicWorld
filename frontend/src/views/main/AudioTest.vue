<template>
  <div class="audio-test">
    <h2>音频播放测试</h2>
    
    <div class="test-section">
      <h3>1. 测试音频上下文初始化</h3>
      <button @click="testAudioContext">初始化AudioContext</button>
      <p>状态: {{ audioContextStatus }}</p>
    </div>
    
    <div class="test-section">
      <h3>2. 测试音频播放</h3>
      <button @click="testAudioPlay">播放测试音频</button>
      <p>播放状态: {{ playStatus }}</p>
    </div>
    
    <div class="test-section">
      <h3>3. 测试十六进制音频数据</h3>
      <button @click="testHexAudio">播放十六进制音频</button>
      <p>十六进制测试状态: {{ hexStatus }}</p>
    </div>
    
    <div class="test-section">
      <h3>4. 控制台日志</h3>
      <div class="log-area">
        <div v-for="(log, index) in logs" :key="index" class="log-item">
          {{ log }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const audioContextStatus = ref('未初始化')
const playStatus = ref('未开始')
const hexStatus = ref('未开始')
const logs = ref<string[]>([])

// 音频相关状态
const audioContext = ref<AudioContext | null>(null)
const audioQueue = ref<Uint8Array[]>([])
const isPlayingAudio = ref(false)
const activeAudioSource = ref<AudioBufferSourceNode | null>(null)

const addLog = (message: string) => {
  const timestamp = new Date().toLocaleTimeString()
  logs.value.push(`[${timestamp}] ${message}`)
  console.log(message)
}

// 初始化音频上下文
const initAudioContext = () => {
  try {
    if (!audioContext.value) {
      audioContext.value = new (window.AudioContext || (window as any).webkitAudioContext)()
      addLog(`AudioContext initialized, state: ${audioContext.value.state}`)
      audioContextStatus.value = `已初始化 (${audioContext.value.state})`
    }
  } catch (error) {
    addLog(`AudioContext初始化失败: ${error}`)
    audioContextStatus.value = '初始化失败'
  }
}

// WAV编码器
const encodeWav = (pcmData: Uint8Array, sampleRate: number): ArrayBuffer => {
  const numChannels = 1
  const bytesPerSample = 2
  const dataSize = pcmData.length
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  addLog(`编码WAV - PCM数据长度: ${dataSize} 字节`)

  // RIFF头部
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(view, 8, 'WAVE')

  // fmt子块
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
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

// 播放音频函数
const playAudio = (audioData: Uint8Array): Promise<void> => {
  return new Promise((resolve) => {
    if (!audioContext.value) {
      addLog('AudioContext not initialized')
      return resolve()
    }

    addLog(`开始播放音频，数据长度: ${audioData.length}`)
    
    if (audioContext.value.state === 'suspended') {
      audioContext.value.resume().then(() => {
        playAudioInternal(audioData, resolve)
      }).catch((error: any) => {
        addLog(`Error resuming AudioContext: ${error}`)
        resolve()
      })
    } else {
      playAudioInternal(audioData, resolve)
    }
  })
}

const playAudioInternal = (audioData: Uint8Array, resolve: () => void) => {
  try {
    const wavBuffer = encodeWav(audioData, 24000)
    addLog(`WAV buffer created, size: ${wavBuffer.byteLength}`)
    
    audioContext.value!.decodeAudioData(wavBuffer).then(audioBuffer => {
      addLog(`音频解码成功，时长: ${audioBuffer.duration} 秒`)
      
      const source = audioContext.value!.createBufferSource()
      const gainNode = audioContext.value!.createGain()
      
      activeAudioSource.value = source
      source.buffer = audioBuffer
      
      gainNode.gain.value = 1.0
      addLog(`音量设置为: 1.0`)
      
      source.connect(gainNode)
      gainNode.connect(audioContext.value!.destination)
      
      source.onended = () => {
        addLog('音频播放结束')
        isPlayingAudio.value = false
        activeAudioSource.value = null
        resolve()
      }
      
      isPlayingAudio.value = true
      source.start(0)
      addLog('音频开始播放')
      
    }).catch((error: any) => {
      addLog(`Error decoding audio: ${error}`)
      isPlayingAudio.value = false
      resolve()
    })
    
  } catch (error) {
    addLog(`播放音频时出错: ${error}`)
    isPlayingAudio.value = false
    resolve()
  }
}

// 测试函数
const testAudioContext = () => {
  addLog('开始测试AudioContext初始化')
  initAudioContext()
}

const testAudioPlay = async () => {
  addLog('开始测试音频播放')
  playStatus.value = '播放中...'
  
  // 生成一个简单的测试音频（440Hz正弦波，1秒）
  const sampleRate = 24000
  const duration = 1 // 1秒
  const samples = sampleRate * duration
  const audioData = new Uint8Array(samples * 2) // 16位PCM
  
  for (let i = 0; i < samples; i++) {
    const sample = Math.sin(2 * Math.PI * 440 * i / sampleRate) * 0.5
    const intSample = Math.round(sample * 32767)
    audioData[i * 2] = intSample & 0xFF
    audioData[i * 2 + 1] = (intSample >> 8) & 0xFF
  }
  
  try {
    await playAudio(audioData)
    playStatus.value = '播放完成'
  } catch (error) {
    playStatus.value = `播放失败: ${error}`
    addLog(`播放测试失败: ${error}`)
  }
}

const testHexAudio = () => {
  addLog('开始测试十六进制音频数据')
  hexStatus.value = '处理中...'
  
  // 模拟一个简单的十六进制音频数据
  const testHex = '52494646240000005741564566666D74100000000100010080BB000000EE02000200100064617461000000000000000000000000'
  
  try {
    initAudioContext()
    
    const audioData = new Uint8Array(
      testHex.match(/.{1,2}/g)?.map((byte: string) => parseInt(byte, 16)) || []
    )
    
    if (audioData.length > 0) {
      addLog(`音频数据转换完成，长度: ${audioData.length}`)
      audioQueue.value.push(audioData)
      playAudio(audioData).then(() => {
        hexStatus.value = '播放完成'
      }).catch((error) => {
        hexStatus.value = `播放失败: ${error}`
      })
    } else {
      hexStatus.value = '数据转换失败'
      addLog('收到空的音频十六进制字符串')
    }
    
  } catch (error) {
    hexStatus.value = `处理失败: ${error}`
    addLog(`音频数据处理失败: ${error}`)
  }
}

onMounted(() => {
  addLog('音频测试页面已加载')
})
</script>

<style scoped>
.audio-test {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.test-section {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #f9f9f9;
}

.test-section h3 {
  margin-top: 0;
  color: #333;
}

button {
  padding: 10px 20px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 10px;
}

button:hover {
  background: #0056b3;
}

.log-area {
  max-height: 300px;
  overflow-y: auto;
  background: #000;
  color: #0f0;
  padding: 10px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
}

.log-item {
  margin-bottom: 2px;
}
</style>