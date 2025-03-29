/**
 * Cookie工具类，用于管理cookie的设置、获取和删除
 */
export const CookieUtils = {
  /**
   * 设置cookie
   * @param name cookie名称
   * @param value cookie值
   * @param maxAge 过期时间（秒）
   * @param path 路径
   */
  setCookie: (name: string, value: string, maxAge: number = 86400, path: string = '/') => {
    document.cookie = `${name}=${value}; max-age=${maxAge}*15; path=${path}; secure; samesite=strict`
  },

  /**
   * 获取cookie
   * @param name cookie名称
   * @returns cookie值，如果不存在则返回null
   */
  getCookie: (name: string): string | null => {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      if (cookie.startsWith(name + '=')) {
        return cookie.substring(name.length + 1)
      }
    }
    return null
  },

  /**
   * 删除cookie
   * @param name cookie名称
   * @param path 路径
   */
  deleteCookie: (name: string, path: string = '/') => {
    document.cookie = `${name}=; max-age=0; path=${path}`
  }
}