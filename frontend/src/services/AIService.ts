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