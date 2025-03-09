<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { ref, reactive } from 'vue'
import HelloWorld from './components/HelloWorld.vue'
import ChatInput from './components/ChatInput.vue'
import ChatMessages from './components/ChatMessages.vue'

const messages = reactive([])
const isLoading = ref(false)
const error = ref(null)

const handleMessageSent = (newMsg) => {
  messages.push({
    ...newMsg,
    timestamp: Date.now()
  })
}
</script>

<template>
  <header>
    <img alt="Vue logo" class="logo" src="@/assets/logo.svg" width="125" height="125" />

    <div class="wrapper">
      <ChatMessages 
    :messages="messages"
    :isLoading="isLoading"
    :error="error"
    class="messages-area"
  />
  <ChatInput 
    @message-sent="handleMessageSent"
    class="input-area"
  />
    </div>
  </header>

  <RouterView />
</template>

<style scoped>
header {
  line-height: 1.5;
  max-height: 100vh;
}

.logo {
  display: block;
  margin: 0 auto 2rem;
}

nav {
  width: 100%;
  font-size: 12px;
  text-align: center;
  margin-top: 2rem;
}

nav a.router-link-exact-active {
  color: var(--color-text);
}

nav a.router-link-exact-active:hover {
  background-color: transparent;
}

nav a {
  display: inline-block;
  padding: 0 1rem;
  border-left: 1px solid var(--color-border);
}

nav a:first-of-type {
  border: 0;
}

@media (min-width: 1024px) {
  header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }

  .logo {
    margin: 0 2rem 0 0;
  }

  .chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0 auto;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.input-area {
  flex-shrink: 0;
  border-top: 1px solid #eee;
}

  nav {
    text-align: left;
    margin-left: -1rem;
    font-size: 1rem;

    padding: 1rem 0;
    margin-top: 1rem;
  }
}
</style>
