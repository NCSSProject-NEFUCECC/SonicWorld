import { createAlertDialog } from '@/components/message'
import type {  Message } from '@/datasource/types'
import axios from 'axios'

// 聊天服务函数
export const chat = async (messages : Message[]): Promise<string> => {
  try {
console.log("messages", messages)
 
    const data = await axios.post('/api/chat', {"messages": messages})

    return data.data.response as string
  } catch (error) {
    // const message = error instanceof Error ? error.message : '未知错误'
    createAlertDialog(error as string)
    throw error
  }
}

// // 辅助函数：管理历史消息(目前不用)
// export const manageMessages = (messages: Message[], newInput: string): Message[] => {
//   // 添加用户消息
//   const updatedMessages = [...messages, { role: 'user', content: newInput }] as Message[]

//   // // 添加系统消息（根据需求决定位置）
//   // if (!updatedMessages.some(msg => msg.role === 'system')) {
//   //   updatedMessages.unshift({
//   //     role: 'system',
//   //     content: '你是 Kimi，由 Moonshot AI 提供的人工智能助手...'
//   //   })
//   // }

//   // 应用 maxHistory 限制
//   const maxHistory = 20
//   return updatedMessages.slice(-maxHistory)
// }
