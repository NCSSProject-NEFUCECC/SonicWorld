<script setup lang="ts">
import { onMounted } from 'vue';
const _plus = (window as any).plus;

document.addEventListener('plusready', function () {
  var context = _plus.android.importClass('android.content.Context');
  var mainActivity = _plus.android.runtimeMainActivity();
  var PackageManager = _plus.android.importClass('android.content.pm.PackageManager');
  var permission = 'android.permission.CAMERA';
  var hasPerm = mainActivity.checkSelfPermission(permission);
  if (hasPerm !== PackageManager.PERMISSION_GRANTED) {
    mainActivity.requestPermissions([permission], {
      onGranted: function () {
        console.log('Camera 权限已授权');
      },
      onDenied: function () {
        console.log('Camera 权限被拒绝');
      }
    });
  } else {
    console.log('Camera 权限已存在');
  }
});


function requestCameraPermission() {
  if (_plus && _plus.os.name === "Android") {
    _plus.runtime.requestPermission("android.permission.CAMERA", () => {
      alert("Camera 权限已授权");
    }, (e: Error) => {
      alert("授权失败，错误信息：" + e.message);
    });
  }
}

onMounted(() => {
  // 立即检查是否有 plus 对象
  if ((window as any).plus) {
    requestCameraPermission();
  } else {
    // plus 尚未加载，采用轮询检查
    const checkPlusInterval = setInterval(() => {
      if ((window as any).plus) {
        clearInterval(checkPlusInterval);
        requestCameraPermission();
      }
    }, 500);
  }
});
</script>


<template>
  <suspense>
    <template #default>
      <router-view />
    </template>
    <template #fallback>
      <!-- <loading-view /> -->
    </template>
  </suspense>
</template>

<style scoped>
</style>
