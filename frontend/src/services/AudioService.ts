import { ref } from 'vue'

// 音频上下文和播放器状态
const audioContext = ref<AudioContext | null>(null)
const isPlaying = ref(false)

// 初始化音频上下文
const initAudioContext = () => {
  if (!audioContext.value) {
    try {
      // 创建新的音频上下文
      audioContext.value = new (window.AudioContext || (window as any).webkitAudioContext)()
      console.log('音频上下文已初始化')
    } catch (error) {
      console.error('初始化音频上下文失败:', error)
    }
  }
  return audioContext.value
}

// 播放音频数据
const playAudioData = async (base64AudioData: string) => {
  try {
    const context = initAudioContext()
    if (!context) {
      console.error('音频上下文不可用')
      return
    }

    // 解码Base64音频数据
    const binaryData = atob(base64AudioData)
    const arrayBuffer = new ArrayBuffer(binaryData.length)
    const uint8Array = new Uint8Array(arrayBuffer)
    
    for (let i = 0; i < binaryData.length; i++) {
      uint8Array[i] = binaryData.charCodeAt(i)
    }

    // 解码音频数据
    const audioBuffer = await context.decodeAudioData(arrayBuffer)
    
    // 创建音频源并播放
    const source = context.createBufferSource()
    source.buffer = audioBuffer
    source.connect(context.destination)
    source.start(0)
    
    isPlaying.value = true
    
    // 监听播放结束
    source.onended = () => {
      isPlaying.value = false
    }
  } catch (error) {
    console.error('播放音频数据失败:', error)
    isPlaying.value = false
  }
}

// 从服务器获取文本到语音的流式响应
const streamTextToSpeech = async (text: string, onAudioChunk?: (chunk: string) => void) => {
  try {
    // 初始化音频上下文
    initAudioContext()
    
    // 发送请求到后端
    const response = await fetch('/api/tts', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`)
    }
    
    // 处理流式响应
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法获取响应流')
    }
    
    // 处理音频流
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        console.log('音频流接收完成')
        break
      }
      
      // 将接收到的数据块转换为文本
      const chunk = new TextDecoder().decode(value)
      
      // 处理SSE格式的数据
      const lines = chunk.split('\n\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const content = line.substring(6)
          
          // 检查是否是完成或错误信号
          if (content === '[audio_complete]') {
            console.log('音频合成完成')
            continue
          } else if (content.startsWith('[audio_error]')) {
            console.error('音频合成错误:', content.substring(13))
            continue
          }
          
          // 播放音频数据
          await playAudioData(content)
          
          // 如果有回调函数，调用它
          if (onAudioChunk) {
            onAudioChunk(content)
          }
        }
      }
    }
    
    return 'success'
  } catch (error) {
    console.error('文本转语音流错误:', error)
    throw error
  }
}

export { initAudioContext, playAudioData, streamTextToSpeech, isPlaying }