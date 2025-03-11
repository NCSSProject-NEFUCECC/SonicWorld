import os
import dashscope

dashscope.api_key = "sk-6a259a1064144086be0e11e5903c1d49"

messages = [
    {'role': 'system', 'content': 'You are a helpful assistant.'},
    {'role': 'user', 'content': '你是谁？'}
]

response = dashscope.Generation.call(
    model="qwen-plus", 
    messages=messages,
    result_format='message'
)

# 提取 content 内容
if response.status_code == 200:
    content = response.output.choices[0].message.content
    print(content)
else:
    print("请求失败:", response.message)



