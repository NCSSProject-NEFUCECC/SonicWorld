import axios from 'axios'


export class CommonService {
    static loginService = async (username:string,password:string) => {
        const response = await axios.post('http://101.42.16.55:5000/api/login', {
            username: username,
            password: password
          })
          if (response.data.status === 'success') {
            const user_token = response.data.data.username
            sessionStorage.setItem('user_token', user_token)
          } 
          return response
      }
}