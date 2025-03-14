import { createAlertDialog } from '@/components/message'
import type {  Message } from '@/datasource/types'
import axios from 'axios'

// 聊天服务函数 - 流式响应版本
export const chat = async (messages : Message[], onChunk?: (chunk: string) => void): Promise<string> => {
  try {
    console.log("messages", messages)
    
    // 使用流式响应
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({"messages": messages})
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    // 处理流式响应
    const reader = response.body?.getReader()
    const decoder = new TextDecoder()
    let fullText = ''
    
    if (reader) {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const text = decoder.decode(value)
        const lines = text.split('\n')
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const content = line.slice(6) // 移除 'data: ' 前缀
            if (content === '[完成]') continue
            
            fullText += content
            if (onChunk) onChunk(content)
          }
        }
      }
    }
    
    return fullText
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
