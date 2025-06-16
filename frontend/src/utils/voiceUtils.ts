import CryptoJS from 'crypto-js'

/**
 * 生成8位随机字符串
 */
export const generateNonce = (): string => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < 8; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

/**
 * 生成32位用户ID（包括数字和小写字母）
 */
export const generateUserId = (): string => {
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < 32; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

/**
 * 生成签名
 * 根据Vivo AI官方文档的签名算法
 * signing_string = HTTP Method + "\n" + HTTP URI + "\n" + canonical_query_string + "\n" + app_id + "\n" + timestamp + "\n" + signed_headers_string
 */
export const generateSignature = (
  appId: string,
  timestamp: string,
  nonce: string,
  appSecret: string,
  queryParams?: Record<string, string>
): string => {
  // HTTP方法（WebSocket升级请求使用GET）
  const method = 'GET'
  
  // HTTP URI（必须以"/"开头）
  const uri = '/asr/v2'
  
  // 生成canonical_query_string - 排除认证相关参数
  let canonicalQueryString = ''
  if (queryParams && Object.keys(queryParams).length > 0) {
    // 过滤掉认证相关的参数，只保留业务参数
    const filteredParams: Record<string, string> = {}
    Object.keys(queryParams).forEach(key => {
      if (!key.startsWith('x-ai-gateway-')) {
        filteredParams[key] = queryParams[key]
      }
    })
    
    // 按key的字典顺序排序
    const sortedKeys = Object.keys(filteredParams).sort()
    const encodedParams = sortedKeys.map(key => {
      const encodedKey = encodeURIComponent(key)
      const encodedValue = encodeURIComponent(filteredParams[key] || '')
      return `${encodedKey}=${encodedValue}`
    })
    canonicalQueryString = encodedParams.join('&')
  }
  
  // 构建signed_headers_string
  const signedHeadersString = [
    `x-ai-gateway-app-id:${appId}`,
    `x-ai-gateway-timestamp:${timestamp}`,
    `x-ai-gateway-nonce:${nonce}`
  ].join('\n')
  
  // 构建完整的签名字符串
  const signingString = [
    method,
    uri,
    canonicalQueryString,
    appId,
    timestamp,
    signedHeadersString
  ].join('\n')
  
  console.log('签名字符串:', signingString) // 调试用
  
  // 使用HMAC-SHA256生成签名，然后Base64编码
  const signature = CryptoJS.HmacSHA256(signingString, appSecret).toString(CryptoJS.enc.Base64)
  
  console.log('生成的签名:', signature) // 调试用
  
  return signature
}

/**
 * URL编码工具函数
 */
export const encodeURIComponentSafe = (str: string): string => {
  return encodeURIComponent(str)
    .replace(/[!'()*]/g, (c) => {
      return '%' + c.charCodeAt(0).toString(16).toUpperCase()
    })
}

/**
 * 验证音频格式支持
 */
export const checkAudioSupport = (): {
  supported: boolean
  formats: string[]
} => {
  const audio = document.createElement('audio')
  const formats: string[] = []
  
  // 检查支持的音频格式
  if (audio.canPlayType('audio/webm; codecs="pcm"')) {
    formats.push('webm-pcm')
  }
  if (audio.canPlayType('audio/webm')) {
    formats.push('webm')
  }
  if (audio.canPlayType('audio/wav')) {
    formats.push('wav')
  }
  if (audio.canPlayType('audio/ogg')) {
    formats.push('ogg')
  }
  
  return {
    supported: formats.length > 0,
    formats
  }
}

/**
 * 检查浏览器是否支持WebRTC和MediaRecorder
 */
export const checkBrowserSupport = (): {
  webrtc: boolean
  mediaRecorder: boolean
  websocket: boolean
} => {
  return {
    webrtc: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
    mediaRecorder: typeof MediaRecorder !== 'undefined',
    websocket: typeof WebSocket !== 'undefined'
  }
}

/**
 * 音频数据转换工具
 * 将WebM音频转换为PCM格式
 */
export const convertWebMToPCM = async (webmBlob: Blob): Promise<ArrayBuffer> => {
  return new Promise((resolve, reject) => {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    const fileReader = new FileReader()
    
    fileReader.onload = async (e) => {
      try {
        const arrayBuffer = e.target?.result as ArrayBuffer
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
        
        // 转换为16位PCM
        const pcmData = audioBufferToPCM16(audioBuffer)
        resolve(pcmData)
      } catch (error) {
        reject(error)
      }
    }
    
    fileReader.onerror = () => reject(new Error('文件读取失败'))
    fileReader.readAsArrayBuffer(webmBlob)
  })
}

/**
 * 将AudioBuffer转换为16位PCM数据
 */
const audioBufferToPCM16 = (audioBuffer: AudioBuffer): ArrayBuffer => {
  const length = audioBuffer.length
  const numberOfChannels = audioBuffer.numberOfChannels
  const sampleRate = audioBuffer.sampleRate
  
  // 如果是立体声，混合为单声道
  let samples: Float32Array
  if (numberOfChannels === 2) {
    const left = audioBuffer.getChannelData(0)
    const right = audioBuffer.getChannelData(1)
    samples = new Float32Array(length)
    for (let i = 0; i < length; i++) {
      samples[i] = (left[i] + right[i]) / 2
    }
  } else {
    samples = audioBuffer.getChannelData(0)
  }
  
  // 转换为16位整数
  const pcm16 = new Int16Array(length)
  for (let i = 0; i < length; i++) {
    const sample = Math.max(-1, Math.min(1, samples[i]))
    pcm16[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
  }
  
  return pcm16.buffer
}

/**
 * 错误码映射
 */
export const ERROR_CODES: Record<number, string> = {
  0: '成功',
  1001: '请求超时',
  1002: '网络错误',
  1003: '服务不可用',
  1004: '参数错误',
  1005: '签名验证失败',
  1006: '应用ID无效',
  1007: '音频格式不支持',
  1008: '音频数据异常',
  1009: '识别失败',
  1010: '服务器内部错误'
}

/**
 * 获取错误描述
 */
export const getErrorDescription = (code: number): string => {
  return ERROR_CODES[code] || `未知错误 (${code})`
}

/**
 * 音频质量检测
 */
export const checkAudioQuality = (audioData: ArrayBuffer): {
  quality: 'good' | 'fair' | 'poor'
  volume: number
  duration: number
} => {
  const view = new DataView(audioData)
  const samples = audioData.byteLength / 2
  let sum = 0
  let max = 0
  
  for (let i = 0; i < samples; i++) {
    const sample = Math.abs(view.getInt16(i * 2, true))
    sum += sample
    max = Math.max(max, sample)
  }
  
  const average = sum / samples
  const volume = max / 32768 // 归一化到0-1
  const duration = samples / 16000 // 假设16kHz采样率
  
  let quality: 'good' | 'fair' | 'poor'
  if (volume > 0.1 && average > 1000) {
    quality = 'good'
  } else if (volume > 0.05 && average > 500) {
    quality = 'fair'
  } else {
    quality = 'poor'
  }
  
  return { quality, volume, duration }
}

/**
 * 音频可视化数据生成
 */
export const generateVisualizationData = (audioData: ArrayBuffer, bins: number = 32): number[] => {
  const view = new DataView(audioData)
  const samples = audioData.byteLength / 2
  const binSize = Math.floor(samples / bins)
  const result: number[] = []
  
  for (let i = 0; i < bins; i++) {
    let sum = 0
    const start = i * binSize
    const end = Math.min(start + binSize, samples)
    
    for (let j = start; j < end; j++) {
      sum += Math.abs(view.getInt16(j * 2, true))
    }
    
    result.push(sum / (end - start) / 32768) // 归一化
  }
  
  return result
}