// 语音识别配置文件
// 注意：在生产环境中，请将敏感信息放在环境变量或服务端

export interface VoiceConfig {
  appId: string
  appSecret: string
  engineId: string
  apiDomain: string
  maxRecordingTime: number // 最大录音时长（秒）
  frameSize: number // 音频帧大小（毫秒）
  endVadTime: number // 语音活动检测结束时间（毫秒）
}

// 默认配置
export const defaultVoiceConfig: VoiceConfig = {
  appId: '2025881276',
  appSecret: 'SUzaUkzFYhnDSYwM',
  engineId: 'shortasrinput',
  apiDomain: 'api-ai.vivo.com.cn',
  maxRecordingTime: 60,
  frameSize: 40,
  endVadTime: 3000
}

// 验证配置
export const validateVoiceConfig = (config: VoiceConfig): { valid: boolean; errors: string[] } => {
  const errors: string[] = []
  
  if (!config.appId || config.appId === 'YOUR_APP_ID') {
    errors.push('请设置有效的APP_ID')
  }
  
  if (!config.appSecret || config.appSecret === 'YOUR_APP_SECRET') {
    errors.push('请设置有效的APP_SECRET')
  }
  
  if (!config.engineId) {
    errors.push('请设置引擎ID')
  }
  
  if (!config.apiDomain) {
    errors.push('请设置API域名')
  }
  
  if (config.maxRecordingTime <= 0 || config.maxRecordingTime > 300) {
    errors.push('录音时长应在1-300秒之间')
  }
  
  if (config.frameSize <= 0 || config.frameSize > 1000) {
    errors.push('音频帧大小应在1-1000毫秒之间')
  }
  
  return {
    valid: errors.length === 0,
    errors
  }
}

// 获取环境配置
export const getEnvironmentConfig = (): Partial<VoiceConfig> => {
  return {
    appId: defaultVoiceConfig.appId,
    appSecret: defaultVoiceConfig.appSecret,
    apiDomain: defaultVoiceConfig.apiDomain
  }
}

// 合并配置
export const mergeConfig = (userConfig: Partial<VoiceConfig>): VoiceConfig => {
  const envConfig = getEnvironmentConfig()
  return {
    ...defaultVoiceConfig,
    ...envConfig,
    ...userConfig
  }
}

// 开发环境配置示例
export const developmentConfig: VoiceConfig = {
  ...defaultVoiceConfig,
  // 开发环境可以使用测试凭证
  appId: 'dev_app_id',
  appSecret: 'dev_app_secret'
}

// 生产环境配置示例
export const productionConfig: VoiceConfig = {
  ...defaultVoiceConfig,
  // 生产环境必须使用真实凭证
  maxRecordingTime: 30, // 生产环境可能需要更短的录音时长
  frameSize: 40
}

// 获取当前配置（主要导出函数）
export const getVoiceConfig = (): VoiceConfig => {
  // 尝试从环境变量获取配置
  const envAppId = import.meta.env.VITE_VIVO_APP_ID
  const envAppSecret = import.meta.env.VITE_VIVO_APP_SECRET
  const envApiDomain = import.meta.env.VITE_VIVO_API_DOMAIN
  
  // 如果环境变量存在，使用环境变量配置
  if (envAppId && envAppSecret) {
    return {
      ...defaultVoiceConfig,
      appId: envAppId,
      appSecret: envAppSecret,
      apiDomain: envApiDomain || defaultVoiceConfig.apiDomain
    }
  }
  
  // 否则返回默认配置
  return defaultVoiceConfig
}