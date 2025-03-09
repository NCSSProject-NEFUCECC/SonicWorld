<template>
  <div class="chat-messages">
    <div v-for="(msg, index) in messages" :key="index" class="message" :class="msg.role">
      <div class="message-bubble">
        <div class="content">{{ msg.content }}</div>
        <div class="timestamp">{{ formatTimestamp(msg.timestamp) }}</div>
      </div>
    </div>
    
    <div v-if="isLoading" class="loading-indicator">
      <div class="loader"></div>
      正在思考中...
    </div>
    
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  isLoading: Boolean,
  error: String
})

const formatTimestamp = (ts) => {
  return new Date(ts).toLocaleTimeString('zh-CN', { 
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #fff;
}

.message {
  display: flex;
  margin-bottom: 16px;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 12px;
  background: #f1f0f0;
}

.message.user .message-bubble {
  background: #007bff;
  color: white;
}

.content {
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.timestamp {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.5);
}

.message.user .timestamp {
  color: rgba(255, 255, 255, 0.7);
}

.loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  color: #666;
}

.loader {
  width: 16px;
  height: 16px;
  margin-right: 8px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  padding: 12px;
  background: #ffe3e3;
  color: #dc3545;
  border-radius: 4px;
  margin: 10px 0;
  text-align: center;
}
</style>