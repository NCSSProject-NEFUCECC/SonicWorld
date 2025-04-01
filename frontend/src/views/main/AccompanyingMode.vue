<template>
    <div id="root" ref="refRoot"></div>
  </template>
  
  <script lang="ts" setup>
  import { onMounted, ref } from 'vue';
  import { ElMessageBox } from 'element-plus';
  import accompanyInvalidationAudio from '@/assets/audio/general/accompany_invalidation.mp3';
  
  const refRoot = ref<HTMLElement | null>(null);
  const checkRootEmpty = () => {
  return new Promise((resolve) => {
    setTimeout(() => {
      if (refRoot.value && refRoot.value.innerHTML.trim() === '') {
        console.error('Token失效: 根元素为空');
        console.log('Token='+localStorage.getItem('accompany_token'))
        if (refRoot.value) refRoot.value.innerHTML = '';
        localStorage.removeItem('accompany_token');
        const audio = new Audio(accompanyInvalidationAudio);
        audio.play();
        ElMessageBox.prompt('令牌无效，请重新输入', '提示', {
          confirmButtonText: '确认',
          cancelButtonText: '取消',
          inputPattern: /^\S+$/,
          inputErrorMessage: '令牌不能为空',
        }).then(({ value }) => {
          localStorage.setItem('accompany_token', value);
          if (refRoot.value) refRoot.value.innerHTML = '';
          window.location.reload();
        }).catch(() => {
          // 用户取消输入
        });
        resolve(true);
      } else {
        resolve(false);
      }
    }, 1000); // 延迟1秒检查
  });
};

onMounted(async () => {
  
  const script = document.createElement('script');
  script.src = 'https://g.alicdn.com/apsara-media-aui/amaui-web-aicall/1.6.2/aicall-ui.js';
  script.onload = () => {
    if (refRoot.value) {
        // @ts-ignore 忽略 TypeScript 类型检查，因为 ARTCAICallUI 是动态加载的
        try {
          new (window as any).ARTCAICallUI({
            userId: localStorage.getItem('user_token') || '',
            root: refRoot.value,
            shareToken: localStorage.getItem('accompany_token') || (() => {
              let token = '';
              ElMessageBox.prompt('请输入陪伴模式令牌', '提示', {
                confirmButtonText: '确认',
                cancelButtonText: '取消',
                inputPattern: /^\S+$/,
                inputErrorMessage: '令牌不能为空',
              }).then(({ value }) => {
                token = value;
                localStorage.setItem('accompany_token', value);
                // 重新加载组件
                if (refRoot.value) refRoot.value.innerHTML = '';
                window.location.reload();
              }).catch(() => {
                token = '';
              });
              return token;
            })(),
          }).render();
        } catch (error) {
          console.error('Token无效:', error);
          if (refRoot.value) refRoot.value.innerHTML = '';
          localStorage.removeItem('accompany_token');
          const audio = new Audio(accompanyInvalidationAudio);
          audio.play();
          ElMessageBox.prompt('令牌无效，请重新输入', '提示', {
            confirmButtonText: '确认',
            cancelButtonText: '取消',
            inputPattern: /^\S+$/,
            inputErrorMessage: '令牌不能为空',
          }).then(({ value }) => {
            localStorage.setItem('accompany_token', value);
            // 重新加载组件
            if (refRoot.value) refRoot.value.innerHTML = '';
            window.location.reload();
          }).catch(() => {
            // 用户取消输入
          });
        }
      }
    };
    document.head.appendChild(script);
    if (await checkRootEmpty()) return;
  });
  </script>