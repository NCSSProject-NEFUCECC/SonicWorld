import { createRouter, createWebHistory } from 'vue-router'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '',
      component: () => import('@/views/index.vue'),
      children: [
        {
          path: 'ai/chat',
          component: () => import('@/views/main/AIChatView.vue'),
        },
      ],
    },

    {
      path: '',
      redirect: '/ai/chat',
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/ai/chat'
    },
    
  ],
})

export default router
