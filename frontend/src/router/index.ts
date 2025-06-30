import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  // history: createWebHistory(import.meta.env.BASE_URL),
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      component: () => import('@/views/index.vue'),
      children: [
        {
          path: 'ai/chat',
          component: () => import('@/views/main/AIChatView.vue'),
        },
        {
          path: 'navigation',
          component: () => import('@/views/main/NavigationModel.vue'),
        },
        {
          path: 'accompany',
          component: () => import('@/views/main/AccompanyingMode.vue')
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
