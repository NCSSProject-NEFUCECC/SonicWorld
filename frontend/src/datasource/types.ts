// 定义消息类型
export interface Message {
    role: 'user' | 'assistant'
    content: string
}