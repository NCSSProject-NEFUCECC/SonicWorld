import dashscope
from flask import Flask, request, jsonify
import json


# 将普通文本消息转换为多模态格式
def convert_to_multimodal(messages):
    converted_messages = []
    for msg in messages:
        if msg.get('role') == 'user':
            # 将用户消息转换为多模态格式
            converted_msg = {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': msg.get('content', '')}
                ]
            }
            converted_messages.append(converted_msg)
        else:
            # 保持其他角色消息不变
            converted_messages.append(msg)
    return converted_messages

def intent_recognition(message):
    try:
        # 设置超时时间
        timeout = 30
        messages = []
        messages.extend(message)
        # print(messages)
        llm_ir = dashscope.Application.call(
            app_id="c299fa4ad27c4dc5909f87d79fc6d098",
            prompt='你是一个意图分类器，严格按以下规则处理输入：1.分类范围[普通聊天][查找某物的位置][阅读文字][法律咨询][识别前方的情况][领航任务][陪伴模式]；2.领航任务包含引导移动指令如"带路""扶我到"或是用户直接说打开领航模式等；3.结合全部历史消息解析指代（例：前文提到书后说"读它"→阅读文字）；4.输出严格遵循{"intent":"","msg":""}格式,不要越俎代庖擅自向用户提供建议；5.新意图/低置信度(＜80%)归普通聊天；。务必注意！！你的输出只能是JSON格式，且不能有多余的文字,不要自作主张向用户提供建议，那是其他人的任务。你擅自将输出中添加其他东西会导致整个系统失效，务必执行好自己的任务，你只是一个意图识别器，不要自作主张，不要越俎代庖！',
            messages=messages,
        )
        # print(llm_ir)
        intent = llm_ir.output.text
        # print(intent)
        intent = json.loads(intent)
        intent = intent.get('intent')
        print("任务：",intent)
        return intent
    except Exception as e:
        print(f"错误: {str(e)}")
        # 如果意图识别失败，默认返回普通聊天意图
        return jsonify({"intent":"普通聊天","msg":message})  