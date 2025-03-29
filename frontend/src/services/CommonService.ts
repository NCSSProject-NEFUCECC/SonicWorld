import axios from 'axios'
import { CookieUtils } from '../utils/cookieUtils'

export class CommonService {
    static loginService = async (username:string,password:string) => {
        const response = await axios.post('http://127.0.0.1:5000/api/login', {
            username: username,
            password: password
          })
          if (response.data.status === 'success') {
            const user_token = response.data.data.username
            // 使用CookieUtils工具类设置cookie，过期时间为15天
            CookieUtils.setCookie('user_token', user_token)
            sessionStorage.setItem('user_token', user_token)
          } 
          return response
      }
}