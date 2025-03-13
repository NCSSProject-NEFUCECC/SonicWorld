<script setup lang="ts">

import { ref, reactive } from 'vue'
// import LoadingView from './components/LoadingView.vue';

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
