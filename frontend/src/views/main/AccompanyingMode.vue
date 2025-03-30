<template>
    <div id="root" ref="refRoot">111</div>
  </template>
  
  <script lang="ts" setup>
  import { onMounted, ref } from 'vue';
  
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
          shareToken: 'eyJSZXF1ZXN0SWQiOiI0RjVCN0NENy0zNDc1LTUwRDEtODZFRS02OTU3RUU2N0U3QzciLCJXb3JrZmxvd1R5cGUiOiJWb2ljZUNoYXQiLCJUZW1wb3JhcnlBSUFnZW50SWQiOiI1MmYzNzdmOGU1NzM0ZDU2OTg1NWU1ZDZhYTIxNDBkYyIsIkV4cGlyZVRpbWUiOiIyMDI1LTA0LTAyIDA0OjA2OjIxIiwiTmFtZSI6IklpQmM2enMyIiwiUmVnaW9uIjoiY24tYmVpamluZyJ9',
        }).render();
      }
    };
    document.head.appendChild(script);
  });
  </script>