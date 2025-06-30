# 音频播放问题诊断与解决方案

## 问题描述
前端显示文本消息但没有播放对应的音频，特别是在function call场景中出现"现在，我将去调用XXX，容我思考一下。。。"的文本但无音频播放。

## 已发现的问题

### 1. 后端TTS错误处理不足
**问题**: 原代码没有对TTS初始化和音频生成进行充分的错误处理，导致TTS连接失败时静默失败。

**解决方案**: 
- 添加了TTS websocket连接状态检查
- 增加了详细的错误日志输出
- 对音频生成失败情况进行明确提示

### 2. 前端采样率不匹配
**问题**: NavigationModel.vue中使用22050Hz采样率，而后端TTS输出24000Hz。

**解决方案**: 
- 将NavigationModel.vue中的采样率从22050改为24000
- 确保前后端采样率一致

### 3. 缺少websocket依赖
**问题**: requirements.txt中缺少websocket-client库。

**解决方案**: 
- 添加websocket-client>=1.0.0到requirements.txt
- 添加requests>=2.25.0确保网络请求正常

### 4. 前端音频数据验证不足
**问题**: 前端没有验证接收到的音频数据是否有效。

**解决方案**: 
- 添加音频数据有效性检查
- 过滤全零或空的音频数据
- 增加详细的音频数据分析日志

## 修复的文件

### 后端文件
1. `backend/app.py` - 添加TTS错误处理
2. `backend/requirements.txt` - 添加websocket依赖
3. `backend/test_tts.py` - 新增TTS测试脚本

### 前端文件
1. `frontend/src/views/main/NavigationModel.vue` - 修复采样率
2. `frontend/src/views/main/AIChatView.vue` - 增强音频数据验证

## 诊断步骤

### 1. 运行TTS测试脚本
```bash
cd backend
python test_tts.py
```

### 2. 检查后端日志
查看控制台输出，关注以下信息：
- "TTS连接失败：无法建立websocket连接"
- "TTS音频生成失败：返回空数据"
- "生成的音频数据长度: X 字节"

### 3. 检查前端控制台
在浏览器开发者工具中查看：
- "收到音频数据"
- "SSE音频数据转换完成，长度: X"
- "音频数据验证 - 零字节占比: X%"
- "AudioContext initialized, state: running"

### 4. 检查网络连接
确保能够访问TTS服务：
- 检查网络连接
- 验证API密钥是否正确
- 确认防火墙设置

## 常见问题排查

### 问题1: "TTS连接失败：无法建立websocket连接"
**可能原因**:
- 网络连接问题
- websocket-client库未安装
- API密钥错误
- 防火墙阻止连接

**解决方法**:
```bash
pip install websocket-client
```
检查网络和API配置

### 问题2: "音频数据全为零，跳过播放"
**可能原因**:
- TTS服务返回空数据
- 文本内容不适合语音合成
- 服务器端错误

**解决方法**:
- 检查TTS服务状态
- 尝试简单文本测试
- 查看服务器日志

### 问题3: "AudioContext not initialized"
**可能原因**:
- 浏览器音频策略限制
- 用户未进行交互
- AudioContext创建失败

**解决方法**:
- 确保用户已点击页面
- 检查浏览器音频权限
- 尝试手动初始化AudioContext

### 问题4: 音频播放卡顿或失真
**可能原因**:
- 采样率不匹配
- 音频数据损坏
- 浏览器兼容性问题

**解决方法**:
- 确认前后端采样率一致(24000Hz)
- 检查音频数据完整性
- 尝试不同浏览器

## 预防措施

1. **定期测试**: 使用test_tts.py定期测试TTS功能
2. **监控日志**: 关注后端TTS相关错误日志
3. **用户反馈**: 建立音频播放问题的用户反馈机制
4. **降级方案**: 考虑在TTS失败时提供文本提示

## 技术细节

### TTS音频格式
- 格式: 16位PCM
- 采样率: 24000Hz
- 声道: 单声道
- 字节序: 小端序

### 前端音频处理流程
1. 接收十六进制音频数据
2. 转换为Uint8Array
3. 验证数据有效性
4. 封装为WAV格式
5. 使用AudioContext播放

### 后端TTS调用流程
1. 初始化TTS实例
2. 建立websocket连接
3. 发送文本合成请求
4. 接收音频数据流
5. 返回完整音频数据