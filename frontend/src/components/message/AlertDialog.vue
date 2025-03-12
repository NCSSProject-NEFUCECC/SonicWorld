<script lang="ts" setup>
import { render } from 'vue'
// 接收信息数据，以及当关闭模态框时的执行函数
// 可选参数，关闭回调函数
const props = defineProps<{ msg: string; close?: () => {} }>()
//
const close = () => {
  // 执行传入的关闭模态框时需执行的操作
  props.close && props.close()
  // 从body移除
  render(null, document.body)
}
</script>
<template>
  <div>
    <div class="modal" @click="close">
      <div class="modal-dialog" @click.stop>
        <div class="modal-header">
          <h3>Exception</h3>
        </div>
        <div class="modal-body">
          {{ props.msg }}
        </div>
        <div class="modal-footer">
          <button class="btn-primary" @click="close">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.modal {
  width: 100vw;
  height: 100vh;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 999;
  background: rgba(0, 0, 0, 0.2);
}

.modal-dialog {
  width: 450px;
  margin: auto;
  background: white;
  top: 100px;
  position: relative;
  border-radius: 5px;
  box-shadow:
    0 4px 8px 0 rgba(0, 0, 0, 0.2),
    0 6px 20px 0 rgba(0, 0, 0, 0.19);
}
.modal-header {
  padding: 10px;
  border-bottom: 1px solid #e5e5e5;
}

.modal-body {
  padding: 15px 15px 30px 15px;
  border-bottom: 1px solid #e5e5e5;
}
.modal-footer {
  padding: 15px 15px 30px 15px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}
.btn-primary {
  padding: 6px;
  width: 50px;
  border: 1px dodgerblue solid;
  background-color: deepskyblue;
  cursor: pointer;
  border-radius: 15%;
  transition: background-color 0.3s;
}
.btn-primary:hover {
  background-color: dodgerblue;
}
</style>
