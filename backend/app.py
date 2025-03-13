# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import base64
import time
import dashscope
from navigator import ana_msg

app = Flask(__name__)
CORS(app)


dashscope.api_key = "sk-6a259a1064144086be0e11e5903c1d49"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

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
        messages = [
                {'role': 'system', 'content': '你是一个意图分类器，严格按以下规则处理输入：1.分类范围[普通聊天][查找某物的位置][阅读文字][法律咨询][识别前方的情况][领航任务]；2.领航任务包含引导移动指令如"带路""扶我到"或是用户直接说打开领航模式等；3.结合全部历史消息解析指代（例：前文提到书后说"读它"→阅读文字）；4.输出严格遵循{"intent":"","msg":""}格式,不要越俎代庖擅自向用户提供建议；5.新意图/低置信度(＜80%)归普通聊天；示例：用户输入"带我去电梯"→{"intent":"领航任务","msg":"带我去电梯"}；用户输入"这是什么牌子"→{"intent":"识别前方的情况","msg":"这是什么牌子"}。务必注意！！你的输出只能是JSON格式，且不能有多余的文字,不要自作主张向用户提供建议，那是其他人的任务。你擅自将输出中添加其他东西会导致整个系统失效，务必执行好自己的任务，不要自作主张，不要越俎代庖！'},
            ]
        messages.extend(message)
        # print(messages)
        llm_ir = dashscope.Generation.call(
            model="qwen2.5-14b-instruct-1m",
            messages=messages,
            result_format='message'
        )
        print(llm_ir)
        intent = llm_ir.output.choices[0].message.content
        # print(intent)
        intent = json.loads(intent)
        intent = intent.get('intent')
        print(intent)
        return intent
    except Exception as e:
        print(f"错误: {str(e)}")
        # 如果意图识别失败，默认返回普通聊天意图
        return jsonify({"intent":"普通聊天","msg":message})

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_messages = data.get('messages', '')
        user_message = user_messages[-1].get('content', '')
        # print(len(user_message),user_message)
        if not user_message:
            print("消息不能为空")
            return jsonify({"error": "消息不能为空"}), 400
        
        # 意图识别
        if user_message == "后端启动领航":
            ana_msg(user_message)
            return jsonify({"response": "领航模式已启动"})
        response = intent_recognition(user_messages)
        # print(response)
        response = call_llm_api(response,user_messages)
        
        return jsonify({"response": response})
    
    except Exception as e:
        print(f"错误: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500

# 新增导航API端点
@app.route('/api/navigate', methods=['POST'])
def navigate():
    try:
        data = request.json
        image_data = data.get('image', '')
        location = data.get('location', {})
        
        if not image_data or not location:
            return jsonify({"error": "图像或位置信息不能为空"}), 400
        
        # 保存接收到的图像
        image_path = save_image(image_data)
        
        # 调用导航函数处理图像和位置信息
        navigation_result = process_navigation(image_path, location)
        
        return jsonify({"result": navigation_result})
    
    except Exception as e:
        print(f"导航错误: {str(e)}")
        return jsonify({"error": "导航服务器内部错误"}), 500

# 保存Base64编码的图像到文件
def save_image(image_data):
    # 从Base64字符串中提取图像数据
    if image_data.startswith('data:image'):
        # 移除MIME类型前缀
        image_data = image_data.split(',')[1]
    
    # 确保目录存在
    if not os.path.exists('img'):
        os.makedirs('img')
    
    # 使用固定文件名保存图片，覆盖之前的图片
    image_path = os.path.join('img', "navigation.jpg")
    
    # 解码并保存图像
    with open(image_path, "wb") as image_file:
        image_file.write(base64.b64decode(image_data))
    
    return image_path

# 处理导航请求
def process_navigation(image_path, location):
    try:
        # 调用navigator模块处理导航请求
        from navigator import process_navigation_request
        return process_navigation_request(image_path, location)
    except Exception as e:
        print(f"处理导航请求错误: {str(e)}")
        return "导航处理失败，请稍后再试"


def call_llm_api(llm_lr_response,history_msg):
    image_path = r"img/default.png"
    base64_image = encode_image(image_path)
    # 解析传入的意图识别结果
    try:
        intent = llm_lr_response
        message = history_msg
        # print(message)
    except json.JSONDecodeError:
        print("JSON解析错误")
        return "抱歉，系统处理出现错误。"
    except Exception as e:
        print(f"数据处理错误: {str(e)}")
        return "抱歉，系统处理出现错误。"
    llm_basechat = [
                    {"role": "system", "content": "你是一位情感陪伴专家，你的任务是陪伴一位盲人聊天，在聊天中，你需要关注用户的情感需要，不要反复提及用户残疾的情况。"},
                ]
    llm_visual_finder = [
                    {"role": "system", "content": "你的用户是一位盲人,他正在寻找某建筑某地标或者某物。他现在拍摄了一张他正前方的照片，你需要分析图片和他的需求，告诉他他所寻找的东西在什么地方，他需要怎么做才能达到他的目的。此处给出两个实例：1、用户询问图书馆在哪，你应当回答图书馆的位置，并且告诉他应该怎么走才能到达图书馆；2、用户询问茄子在哪，并上传了一张冰箱内部的图片。你应当告诉他茄子在那一层的那一侧（例如：茄子在冰箱从下往上数第二层的最左边）。注意，你的用户是一位盲人，所以你应当以一个情感专家的语气回答用户，关注用户的情感需要，不要反复提及用户残疾的情况，并且要避免让用户看/观察之类的意思，因为用户是一个盲人，任何让用户看的意思都不应该被输出。"},
                ]
    llm_visual_recoder = [
                    {"role": "system", "content": "你的用户是一位盲人,他向你传入了一张他拍摄的前方的图像，他想知道他的摄像头拍到了什么东西。你需要根据用户的需求，分析图片内容，做出符合用户需求的回答。注意，你的用户是一位盲人，所以你应当以一个情感专家的语气回答用户，关注用户的情感需要，不要反复提及用户残疾的情况，并且要避免让用户看/观察之类的意思，因为用户是一个盲人，任何让用户看的意思都不应该被输出。"},
                ]
    llm_text_reader = [
                    {"role": "system", "content": "你的用户是一位盲人，他现在正在阅读一段文字。你需要帮助用户阅读面前的文件，即你的任务是分析图像，找到用户阅读的东西，并将它们阅读出来，并且要避免让用户看/观察之类的意思，因为用户是一个盲人，任何让用户看的意思都不应该被输出"},
                ]
    llm_legal_consultant = [
                    {"role": "system", "content": "你的用户是一位盲人，他现在正在寻求法律帮助。你需要帮助他找到合适的法律资源，并提供法律建议。"},
                ]
    llm_navigator = [
                    {"role": "system", "content": "你的用户是一位盲人，他现在正在进行导航任务。你需要帮助他找到目的地，并提供导航建议。并且要避免让用户看/观察之类的意思，因为用户是一个盲人，任何让用户看的意思都不应该被输出"},
                ]
                    
                        
    try:
        # 设置请求超时时间
        timeout = 30
        
        if intent == "普通聊天":
            try:
                full_text = ""
                llm_basechat.extend(history_msg)
                completion = dashscope.Generation.call(
                    model="qwen-plus",
                    messages=llm_basechat,
                    temperature=0.35,
                    extra_body={
                        "enable_search": True
                    },
                    timeout=timeout,
                    result_format='message'
                )
                history_msg.append({"role": "assistant", "content": completion.output.choices[0].message.content})
                # print(history_msg)
                return completion.output.choices[0].message.content
            except Exception as e:
                print(f"普通聊天API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return "抱歉，服务连接出现问题，请稍后再试。"
                return "抱歉，处理您的请求时出现了问题。"
                
        elif intent == "查找某物的位置":
            try:
                # 先添加历史对话（除了最后一个元素，即当前用户输入）
                llm_visual_finder.extend(history_msg[:-1])  # 添加除最后一个元素外的所有历史消息
                # 转换为多模态格式
                llm_visual_finder = convert_to_multimodal(llm_visual_finder)
                # 提取当前用户输入的文本部分并添加到数组中
                user_message = history_msg[-1].get('content', '')
                llm_visual_finder.append({"role": "user", "content": [{"image": image_path}, {"text": user_message}]})
                completion = dashscope.MultiModalConversation.call(
                    model="qwen-vl-max",
                    messages=llm_visual_finder,
                    temperature=0.6,
                    result_format='message',
                    timeout=timeout
                )
                history_msg.append({"role": "assistant", "content": completion.output.choices[0].message.content[0].get('text')})
                # print(history_msg)
                return completion.output.choices[0].message.content[0].get('text')
            except Exception as e:
                print(f"查找位置API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return "抱歉，服务连接出现问题，请稍后再试。"
                return "抱歉，无法处理位置查找请求。"

        elif intent == "识别前方的情况":
            try:
                # 先添加历史对话（除了最后一个元素，即当前用户输入）
                llm_visual_recoder.extend(history_msg[:-1])  # 添加除最后一个元素外的所有历史消息
                # 转换为多模态格式
                llm_visual_recoder = convert_to_multimodal(llm_visual_recoder)
                # 提取当前用户输入的文本部分并添加到数组中
                user_message = history_msg[-1].get('content', '')
                llm_visual_recoder.append({"role": "user", "content": [{"image": image_path}, {"text": user_message}]})
                completion = dashscope.MultiModalConversation.call(
                    model="qwen-vl-max",
                    messages=llm_visual_recoder,
                    temperature=0.6,
                    timeout=timeout,
                    result_format='message'
                )
                history_msg.append({"role": "assistant", "content": completion.output.choices[0].message.content[0].get('text')})
                # print(history_msg)
                return completion.output.choices[0].message.content[0].get('text')
            except Exception as e:
                print(f"识别前方的情况API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return "抱歉，服务连接出现问题，请稍后再试。"
                return "抱歉，无法处理识别前方的情况。"

        elif intent == "阅读文字":
            try:
                # 先添加历史对话（除了最后一个元素，即当前用户输入）
                llm_text_reader.extend(history_msg[:-1])  # 添加除最后一个元素外的所有历史消息
                # 转换为多模态格式
                llm_text_reader = convert_to_multimodal(llm_text_reader)
                # 提取当前用户输入的文本部分并添加到数组中
                user_message = history_msg[-1].get('content', '')
                llm_text_reader.append({"role": "user", "content": [{"image": image_path}, {"text": user_message}]})
                completion = dashscope.MultiModalConversation.call(
                    model="qwen-vl-max",
                    messages=llm_text_reader,
                    temperature=0.8,
                    result_format='message',
                    timeout=timeout
                )
                history_msg.append({"role": "assistant", "content": completion.output.choices[0].message.content[0].get('text')})
                return completion.output.choices[0].message.content[0].get('text')
            except Exception as e:
                print(f"文字阅读API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return "抱歉，服务连接出现问题，请稍后再试。"
                return "抱歉，无法处理文字阅读请求。"
                
        elif intent == "法律咨询":
            try:
                llm_legal_consultant.extend(history_msg)
                completion = dashscope.Generation.call(
                    model="farui-plus",
                    messages=llm_legal_consultant,
                    temperature=0.9,
                    timeout=timeout,
                    result_format='message'
                )
                print(completion)
                history_msg.append({"role": "assistant", "content": completion.output.choices[0].message.content})
                return completion.output.choices[0].message.content
            except Exception as e:
                print(f"法律咨询API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return "抱歉，服务连接出现问题，请稍后再试。"
                return "抱歉，无法处理法律咨询请求。"
        elif intent == "领航任务":
            try:
                return "领航模式"
            except Exception as e:
                print(f"领航任务API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return "抱歉，服务连接出现问题，请稍后再试。"
                return "抱歉，无法处理领航任务请求。"
        else:
            return "抱歉，我无法理解您的意图。"

    except Exception as e:
        print(f"整体API调用错误: {str(e)}")
        if "Connection" in str(e):
            return "抱歉，服务连接出现问题，请稍后再试。"
        return "抱歉，系统处理出现未知错误。"


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)