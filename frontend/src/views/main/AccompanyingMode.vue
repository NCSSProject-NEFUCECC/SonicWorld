<template>
  <div id="root"></div>
</template>
<script src="https://g.alicdn.com/apsara-media-aui/amaui-web-aicall/1.6.2/aicall-ui.js">
  new ARTCAICallUI({
    userId: '123',                          // 进入rtc的用户id，建议使用当前登录用户的UserId
    root: document.getElementById('root'),  // 页面渲染到的节点，画面完整填充整个区域
    shareToken: 'eyJSZXF1ZXN0SWQiOiJCRUMxMjk5Ni01QTBBLTU4MkItQjRGNy00NEFGMjdDNEIzRkIiLCJXb3JrZmxvd1R5cGUiOiJWb2ljZUNoYXQiLCJUZW1wb3JhcnlBSUFnZW50SWQiOiJlOGVhODdjNjEwNzY0MzAwYjg3MGYyYTRiM2JjNDIxYSIsIkV4cGlyZVRpbWUiOiIyMDI1LTAzLTMwIDEwOjI2OjUxIiwiTmFtZSI6Ilhsc3JVa0k4IiwiUmVnaW9uIjoiY24tYmVpamluZyJ9',                     // 填入分享ID
  }).render();
</script>
  