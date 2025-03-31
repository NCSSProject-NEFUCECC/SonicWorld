<template>
    <div id="root" ref="refRoot"></div>
  </template>
  
  <script lang="ts" setup>
  import { onMounted, ref } from 'vue';
  import { ElMessageBox } from 'element-plus';
  
  const refRoot = ref<HTMLElement | null>(null);
  onMounted(() => {
    const script = document.createElement('script');
    script.src = 'https://g.alicdn.com/apsara-media-aui/amaui-web-aicall/1.6.2/aicall-ui.js';
    console.log('1');
    script.onload = () => {
        console.log('2');
      if (refRoot.value) {
        // @ts-ignore
        console.log('3');
        // @ts-ignore 忽略 TypeScript 类型检查，因为 ARTCAICallUI 是动态加载的
        new (window as any).ARTCAICallUI({
          userId: localStorage.getItem('user_token') || '',
          root: refRoot.value,
          shareToken: localStorage.getItem('accompany_token') || (() => {
            ElMessageBox.alert('请先输入陪伴模式令牌', '提示');
            return '';
          })(),
        }).render();
      }
    };
    document.head.appendChild(script);
  });
  </script>