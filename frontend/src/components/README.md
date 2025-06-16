# 语音识别组件使用说明

## 概述

本项目提供了一个基于Vivo AI WebSocket API的语音识别组件，支持实时语音转文字功能。

## 文件结构

```
src/
├── components/
│   └── VoiceRecognition.vue    # 语音识别主组件
├── utils/
│   └── voiceUtils.ts           # 语音识别工具函数
└── views/main/
    └── AccompanyingMode.vue    # 使用示例
```

## 快速开始

### 1. 安装依赖

```bash
npm install crypto-js
npm install --save-dev @types/crypto-js
```

### 2. 获取API凭证

1. 访问 [Vivo AI开放平台](https://api-ai.vivo.com.cn)
2. 注册账号并创建应用
3. 获取 `APP_ID` 和 `APP_SECRET`

### 3. 基本使用

```vue
<template>
  <VoiceRecognition
    :app-id="'YOUR_APP_ID'"
    :app-secret="'YOUR_APP_SECRET'"
    :engine-id="'shortasrinput'"
    @result="handleVoiceResult"
    @error="handleVoiceError"
    @status-change="handleStatusChange"
  />
</template>

<script setup>
import VoiceRecognition from '@/components/VoiceRecognition.vue'

const handleVoiceResult = (text) => {
  console.log('识别结果:', text)
}

const handleVoiceError = (error) => {
  console.error('识别错误:', error)
}

const handleStatusChange = (status) => {
  console.log('状态变化:', status)
}
</script>
```

## 组件属性

### VoiceRecognition Props

| 属性名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|---------|
| appId | string | 是 | - | Vivo AI平台分配的应用ID |
| appSecret | string | 是 | - | Vivo AI平台分配的应用密钥 |
| engineId | string | 否 | 'shortasrinput' | 语音识别引擎ID |

### 事件

| 事件名 | 参数 | 说明 |
|--------|------|------|
| result | (text: string) | 语音识别结果 |
| error | (error: string) | 识别错误信息 |
| status-change | (status: string) | 状态变化通知 |

## API 配置说明

### 支持的引擎ID

- `shortasrinput`: 短语音通用模型（推荐）
- 其他模型请参考Vivo AI官方文档

### WebSocket连接参数

组件会自动处理以下参数：

- `model`: 手机型号（默认: 'unknown'）
- `system_version`: 系统版本（默认: 'unknown'）
- `client_version`: 应用版本（默认: 'unknown'）
- `package`: 应用包名（默认: 'unknown'）
- `sdk_version`: SDK版本（默认: 'unknown'）
- `user_id`: 用户ID（自动生成32位字符串）
- `android_version`: Android版本（默认: 'unknown'）
- `system_time`: 系统时间（自动获取）
- `net_type`: 网络类型（默认: '1' - WiFi）
- `engineid`: 引擎ID

### 音频配置

- **采样率**: 16kHz
- **声道**: 单声道
- **格式**: PCM
- **帧长**: 40ms
- **最大时长**: 60秒

## 工具函数说明

### voiceUtils.ts

```typescript
// 生成签名
generateSignature(appId, timestamp, nonce, appSecret): string

// 生成随机字符串
generateNonce(): string

// 生成用户ID
generateUserId(): string

// 检查浏览器支持
checkBrowserSupport(): { webrtc: boolean, mediaRecorder: boolean, websocket: boolean }

// 检查音频格式支持
checkAudioSupport(): { supported: boolean, formats: string[] }

// 音频质量检测
checkAudioQuality(audioData): { quality: 'good'|'fair'|'poor', volume: number, duration: number }

// 错误码映射
getErrorDescription(code): string
```

## 浏览器兼容性

### 必需功能
- WebSocket API
- MediaRecorder API
- getUserMedia API
- Web Audio API

### 支持的浏览器
- Chrome 47+
- Firefox 29+
- Safari 14+
- Edge 79+

### 移动端支持
- iOS Safari 14+
- Chrome Mobile 47+
- Firefox Mobile 68+

## 常见问题

### 1. 麦克风权限被拒绝

**问题**: 浏览器提示麦克风权限被拒绝

**解决方案**:
- 确保网站使用HTTPS协议
- 在浏览器设置中允许麦克风权限
- 检查系统麦克风权限设置

### 2. WebSocket连接失败

**问题**: 无法建立WebSocket连接

**解决方案**:
- 检查APP_ID和APP_SECRET是否正确
- 确认网络连接正常
- 检查防火墙设置

### 3. 签名验证失败

**问题**: 服务器返回签名验证失败

**解决方案**:
- 确认APP_SECRET正确
- 检查系统时间是否准确
- 验证签名算法实现

### 4. 音频格式不支持

**问题**: 浏览器不支持所需的音频格式

**解决方案**:
- 使用现代浏览器
- 检查MediaRecorder API支持情况
- 尝试不同的音频编码格式

## 性能优化建议

### 1. 音频数据传输
- 使用40ms帧长度平衡实时性和网络开销
- 避免发送过长的音频片段
- 及时发送结束信号

### 2. 内存管理
- 及时释放音频流资源
- 清理WebSocket连接
- 避免内存泄漏

### 3. 错误处理
- 实现重连机制
- 提供用户友好的错误提示
- 记录详细的错误日志

## 安全注意事项

1. **API密钥保护**
   - 不要在前端代码中硬编码APP_SECRET
   - 考虑使用环境变量或配置文件
   - 在生产环境中使用服务端代理

2. **用户隐私**
   - 明确告知用户语音数据的使用目的
   - 提供隐私政策说明
   - 支持用户删除语音数据

3. **网络安全**
   - 使用HTTPS协议
   - 验证服务器证书
   - 防止中间人攻击

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 支持基本语音识别功能
- 集成Vivo AI WebSocket API
- 提供完整的工具函数库

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 贡献指南

欢迎提交Issue和Pull Request来改进这个组件。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者

---

**注意**: 使用前请确保已获得Vivo AI平台的API访问权限，并遵守相关服务条款。