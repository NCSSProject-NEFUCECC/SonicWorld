# Function Call 语音生成功能说明

## 功能概述

本功能实现了在模型请求 function call 之前，先过滤掉 APIs 标签，并将剩余的正常对话内容生成为语音的能力。

## 实现原理

### 1. 问题背景

在使用大语言模型时，模型可能会在响应中包含 function call 请求，格式如下：
```
我来帮你查询天气信息。<APIs>[{"name":"get_weather","arguments":{"location":"北京"}}]</APIs>请稍等片刻。
```

在这种情况下，我们希望：
1. 将正常对话部分（"我来帮你查询天气信息。请稍等片刻。"）生成语音
2. 处理 function call 请求
3. 继续后续的对话流程

### 2. 解决方案

#### 2.1 添加过滤函数

在 `app.py` 中添加了 `filter_apis_content()` 函数：

```python
def filter_apis_content(text):
    """过滤掉APIs标签，返回正常对话内容"""
    if '<APIs>' not in text or '</APIs>' not in text:
        return text
    
    # 使用正则表达式移除所有APIs标签及其内容
    filtered_content = re.sub(r'<APIs>.*?</APIs>', '', text, flags=re.DOTALL)
    
    # 清理多余的空白字符
    filtered_content = re.sub(r'\s+', ' ', filtered_content).strip()
    
    return filtered_content
```

#### 2.2 修改处理逻辑

在检测到 function call 时的处理流程中，添加了过滤和语音生成步骤：

```python
# 检查是否包含function call
if '<APIs>' in full_text and '</APIs>' in full_text:
    print(f"第{iteration_count}轮检测到function call，开始处理")
    
    # 先过滤掉APIs标签，获取正常对话内容
    normal_content = filter_apis_content(full_text)
    if normal_content.strip():
        print(f"检测到正常对话内容，生成语音: {normal_content}")
        yield from generate_tts_audio(normal_content)
    
    # 继续处理function call...
```

### 3. 功能特性

#### 3.1 支持多种场景

- **APIs标签前有内容**："我来查询天气<APIs>...</APIs>"
- **APIs标签后有内容**："<APIs>...</APIs>查询完成"
- **APIs标签前后都有内容**："开始查询<APIs>...</APIs>请稍等"
- **多个APIs标签**："查询天气<APIs>...</APIs>然后查询新闻<APIs>...</APIs>完成"
- **跨行APIs标签**：支持包含换行符的APIs标签

#### 3.2 智能处理

- 自动清理多余的空白字符
- 保持文本的自然流畅性
- 只在有正常对话内容时才生成语音

### 4. 使用效果

#### 原始输出：
```
我来帮你查询天气信息。<APIs>[{"name":"get_weather","arguments":{"location":"北京"}}]</APIs>请稍等片刻。
```

#### 处理流程：
1. 检测到 APIs 标签
2. 过滤后得到："我来帮你查询天气信息。请稍等片刻。"
3. 为过滤后的内容生成语音
4. 处理 function call
5. 继续后续流程

### 5. 技术细节

- 使用正则表达式 `r'<APIs>.*?</APIs>'` 进行非贪婪匹配
- 使用 `re.DOTALL` 标志支持跨行匹配
- 通过 `re.sub(r'\s+', ' ', text)` 规范化空白字符
- 保持原有的 function call 处理逻辑不变

## 总结

这个功能确保了用户能够听到模型的正常对话内容，同时不会被 function call 的技术细节干扰，提升了用户体验的连贯性和自然性。