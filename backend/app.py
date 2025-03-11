# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import json
import base64
import dashscope

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


dashscope.api_key = "sk-6a259a1064144086be0e11e5903c1d49"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def intent_recognition(message):
    try:
        # 设置超时时间
        timeout = 30
        
        llm_ir = dashscope.Generation.call(
            model="qwen-plus",
            messages=[
                {'role': 'system', 'content': '你的任务是分析用户言语的意图，并将这些意图输出。定义以下意图，你分析出的意图不应超出下列给出的意图：1、普通聊天，2、查找某物的位置，3、阅读文字，4、法律咨询，5、识别前方的情况，6、领航任务。这里给出领航任务的解释：当用户说到类似于带我走路、领我走路之类的意思时，将其归纳为领航任务。你的输出应当是json结构化的输出，并且应当包含意图和你收到的原文，你的输出如下：{"intent":"[你判断出的意图]","msg":"[你收到的用户输入的原文]"}。这里给出一个具体例子：用户输入："图书馆在哪儿啊"，你的输出：{"intent":"查找某物的位置","msg":"图书馆在哪儿啊"}。务必注意，你的输出一定要符合上述格式，一定不能超过给定的6个意图，若遇到了难以归类意图，则一律当作普通聊天意图。为了保证工作流正常工作，你的输出必须符合前述的所有要求，否则将造成整个流程工作失败。'},
                {'role': 'user', 'content': message}
            ],
            result_format='message'
        )
        return llm_ir.output.choices[0].message.content
    except Exception as e:
        print(f"错误: {str(e)}")
        # 如果意图识别失败，默认返回普通聊天意图
        return "{\"intent\":\"普通聊天\",\"msg\":\"\' + message + \'\"}"

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"error": "消息不能为空"}), 400
        
        # 调用大模型API
        response = intent_recognition(user_message)
        print(response)
        response = call_llm_api(response)
        
        return jsonify({"response": response})
    
    except Exception as e:
        print(f"错误: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500

@socketio.on('stream_transport')
def call_llm_api(llm_lr_response):
    image_path = r"img/default.png"
    base64_image = encode_image(image_path)
    # 解析传入的意图识别结果
    try:
        intent_data = json.loads(llm_lr_response)
        intent = intent_data.get('intent')
        message = intent_data.get('msg')
    except json.JSONDecodeError:
        print("JSON解析错误")
        return "抱歉，系统处理出现错误。"
    except Exception as e:
        print(f"数据处理错误: {str(e)}")
        return "抱歉，系统处理出现错误。"
    llm_basechat = [
                    {"role": "system", "content": "你是一位情感陪伴专家，你的任务是陪伴一位盲人聊天，在聊天中，你需要关注用户的情感需要，不要反复提及用户残疾的情况。"},
                    {'role': "user", "content": message}
                ]
    llm_visual_finder = [
                    {"role": "system", "content": "你的用户是一位盲人,他正在寻找某建筑某地标或者某物。他现在拍摄了一张他正前方的照片，你需要分析图片和他的需求，告诉他他所寻找的东西在什么地方，他需要怎么做才能达到他的目的。此处给出两个实例：1、用户询问图书馆在哪，你应当回答图书馆的位置，并且告诉他应该怎么走才能到达图书馆；2、用户询问茄子在哪，并上传了一张冰箱内部的图片。你应当告诉他茄子在那一层的那一侧（例如：茄子在冰箱从下往上数第二层的最左边）。注意，你的用户是一位盲人，所以你应当以一个情感专家的语气回答用户，关注用户的情感需要，不要反复提及用户残疾的情况。"},
                    {"role": "user",
                        "content": [
                            {"image": image_path},
                            {"type": "text", "text": message},
                        ],
                    },
                ]
    llm_visual_recoder = [
                    {"role": "system", "content": "你的用户是一位盲人,他向你传入了一张他拍摄的前方的图像，他想知道他的摄像头拍到了什么东西。你需要根据用户的需求，分析图片内容，做出符合用户需求的回答。注意，你的用户是一位盲人，所以你应当以一个情感专家的语气回答用户，关注用户的情感需要，不要反复提及用户残疾的情况。"},
                    {"role": "user",
                        "content": [
                            {"image": image_path},
                            {"type": "text", "text": message},
                        ],
                    },
                ]
    llm_text_reader = [
                    {"role": "system", "content": "你的用户是一位盲人，他现在正在阅读一段文字。你需要帮助用户阅读面前的文件，即你的任务是分析图像，找到用户阅读的东西，并将它们阅读出来"},
                    {"role": "user",
                        "content": [
                            {"image": image_path},
                            {"type": "text", "text": message},
                        ],
                    },
                ]
    llm_legal_consultant = [
                    {"role": "system", "content": "你的用户是一位盲人，他现在正在寻求法律帮助。你需要帮助他找到合适的法律资源，并提供法律建议。"},
                    {"role":'user',"content":message}]
    llm_navigator = [
                    {"role": "system", "content": "你的用户是一位盲人，他现在正在进行导航任务。你需要帮助他找到目的地，并提供导航建议。"},
                    {"role":'user',"content":message}]
                    
                        
    try:
        # 设置请求超时时间
        timeout = 30
        
        if intent == "普通聊天":
            try:
                full_text = ""
                completion = dashscope.Generation.call(
                    model="qwen-plus",
                    messages=llm_basechat,
                    temperature=0.5,
                    extra_body={
                        "enable_search": True
                    },
                    timeout=timeout,
                    stream = True,
                    incremental_output = True,
                    result_format='message'
                )
                for chunk in completion:
                    # print(chunk.output.choices[0].message.content)
                    if chunk.status_code == 200:
                        text_content = chunk.output.choices[0].message.content
                        socketio.emit('new_chunk', {'chunk': text_content})
                        print(text_content)        
                    else:
                        socketio.emit('error', {'message': chunk.message})
                return full_text  # 这里可能导致重复输出
            except Exception as e:
                print(f"普通聊天API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return socketio.emit('error', {'message': "抱歉，服务连接出现问题，请稍后再试。"})
                return socketio.emit('error', {'message': "抱歉，处理您的请求时出现了问题。"})
                
        elif intent == "查找某物的位置":
            try:
                completion = dashscope.MultiModalConversation.call(
                    model="qwen-vl-max",
                    messages=llm_visual_finder,
                    temperature=0.6,
                    result_format='message',
                    timeout=timeout
                )
                return completion.output.choices[0].message.content[0].get('text')
            except Exception as e:
                print(f"查找位置API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return "抱歉，服务连接出现问题，请稍后再试。"
                return "抱歉，无法处理位置查找请求。"

        elif intent == "识别前方的情况":
            try:
                completion = dashscope.MultiModalConversation.call(
                    model="qwen-vl-max",
                    messages=llm_visual_recoder,
                    temperature=0.6,
                    timeout=timeout,
                    result_format='message'
                )
                return completion.output.choices[0].message.content[0].get('text')
            except Exception as e:
                print(f"识别前方的情况API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return "抱歉，服务连接出现问题，请稍后再试。"
                return "抱歉，无法处理识别前方的情况。"

        elif intent == "阅读文字":
            try:
                completion = dashscope.MultiModalConversation.call(
                    model="qwen-vl-max",
                    messages=llm_text_reader,
                    temperature=0.8,
                    result_format='message',
                    timeout=timeout
                )
                return completion.output.choices[0].message.content[0].get('text')
            except Exception as e:
                print(f"文字阅读API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return "抱歉，服务连接出现问题，请稍后再试。"
                return "抱歉，无法处理文字阅读请求。"
                
        elif intent == "法律咨询":
            try:
                completion = dashscope.Generation.call(
                    model="farui-plus",
                    messages=llm_legal_consultant,
                    temperature=0.9,
                    timeout=timeout,
                    result_format='message'
                )
                return completion.output.choices[0].message.content
            except Exception as e:
                print(f"法律咨询API调用错误: {str(e)}")
                if "Connection" in str(e):
                    return "抱歉，服务连接出现问题，请稍后再试。"
                return "抱歉，无法处理法律咨询请求。"
        elif intent == "领航任务":
            pass
        else:
            return "抱歉，我无法理解您的意图。"

    except Exception as e:
        print(f"整体API调用错误: {str(e)}")
        if "Connection" in str(e):
            return "抱歉，服务连接出现问题，请稍后再试。"
        return "抱歉，系统处理出现未知错误。"

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('message')
def handle_message(message):
    response = call_llm_api(message)
    socketio.emit('response', {'response': response})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True, port=5000)