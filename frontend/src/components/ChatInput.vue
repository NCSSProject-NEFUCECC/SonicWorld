<template>
  <div class="chat-input">
    <form @submit.prevent="handleSubmit">
      <input
        v-model="message"
        type="text"
        placeholder="输入消息..."
        :disabled="isLoading"
      />
      <button type="submit" :disabled="!message || isLoading">
        {{ isLoading ? '发送中...' : '发送' }}
      </button>
    </form>
    <div v-if="error" class="error-message">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const emit = defineEmits(['message-sent'])
const message = ref('')
const isLoading = ref(false)
const error = ref(null)

const handleSubmit = async () => {
  if (!message.value) return
  
  try {
    isLoading.value = true
    error.value = null
    
    const response = await axios.post('http://localhost:5000/api/chat', {
      message: message.value
    })

    emit('message-sent', {
      role: 'user',
      content: message.value
    })
    
    emit('message-sent', {
      role: 'assistant',
      content: response.data.response
    })
    
    message.value = ''
  } catch (err) {
    error.value = '消息发送失败，请重试'
    console.error('API请求错误:', err)
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.chat-input {
  padding: 20px;
  background: #f5f5f5;
}

form {
  display: flex;
  gap: 10px;
}

input {
  flex: 1;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

button {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.error-message {
  color: #dc3545;
  margin-top: 8px;
}
</style>