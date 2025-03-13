import os
from dashscope import Generation,MultiModalConversation
import dashscope

def get_response(messages):
    response = MultiModalConversation.call(
        # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
        api_key="sk-6a259a1064144086be0e11e5903c1d49",
        # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
        model="qwen-vl-max",
        messages=messages,
        result_format="message",
    )
    return response

# 初始化一个 messages 数组
messages = [
    {
        "role": "system",
        "content": """你是一名百炼手机商店的店员，你负责给用户推荐手机。手机有两个参数：屏幕尺寸（包括6.1英寸、6.5英寸、6.7英寸）、分辨率（包括2K、4K）。
        你一次只能向用户提问一个参数。如果用户提供的信息不全，你需要反问他，让他提供没有提供的参数。如果参数收集完成，你要说：我已了解您的购买意向，请稍等。""",
    }
]

assistant_output = "欢迎光临百炼手机商店，您需要购买什么尺寸的手机呢？"
print(f"模型输出：{assistant_output}\n")
while "我已了解您的购买意向" not in assistant_output:
    user_input = input("请输入：")
    # 将用户问题信息添加到messages列表中
    messages.append({"role": "user", "content": [{"text": user_input}]})
    print("模型接收到的输入为：",messages)
    print("*"*20)
    res = get_response(messages)
    print(res)
    assistant_output = res.output.choices[0].message.content[0]['text']
    # 将大模型的回复信息添加到messages列表中 ['output']['choices'][0]['message']
    messages.append(res['output']['choices'][0]['message'])
    print("-"*10,assistant_output,"-"*10)
    print("\n")