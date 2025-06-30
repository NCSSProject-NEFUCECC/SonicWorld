const getApiBaseUrl = () => {
    return 'http://127.0.0.1:5000'
}

export const API_CONFIG = {
  BASE_URL: getApiBaseUrl(),
  ENDPOINTS: {
    LOGIN: '/api/login',
    CHAT: '/api/chat',
    WEATHER: '/api/weather',
    NAVIGATE: '/api/navigate'
  }
}

// 便捷方法：获取完整的API URL
export const getApiUrl = (endpoint: string) => {
  return `${API_CONFIG.BASE_URL}${endpoint}`
}