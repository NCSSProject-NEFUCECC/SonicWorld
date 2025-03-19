# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import base64
import time
import dashscope
from navigator import ana_msg
from chater import convert_to_multimodal, intent_recognition
import chater
from datetime import datetime
from database import db, User

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
db.init_app(app)

with app.app_context():
    db.create_all()

dashscope.api_key = "sk-6a259a1064144086be0e11e5903c1d49"

user_messages_dic = {}

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_messages = data.get('messages', '')
        user_message = user_messages[-1].get('content', '')
        try:
            user_token = data.get('user_token', '')
            print("这条消息来自用户",user_token,"type=")
        except:
            user_token = "None"
        image_data = data.get('image', '')
        # print(len(user_message),user_message)
        if not user_message:
            print("消息不能为空")
            return jsonify({"error": "消息不能为空"}), 400
        
        # 意图识别
        intent = intent_recognition(user_messages)
        
        # 返回流式响应
        from flask import Response, stream_with_context
        
        # 获取生成器函数
        image_path = None
        if image_data:
            # 如果有图像数据，保存图像
            image_path = save_image(image_data)
        
        generator = call_llm_api(intent, user_messages, image_path, user_token)
        
        # 返回流式响应
        return Response(stream_with_context(generator), 
                       content_type='text/event-stream',
                       headers={
                           'Cache-Control': 'no-cache',
                           'X-Accel-Buffering': 'no'
                       })
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
        user_token = data.get('user_token', '')
        print("当前用户：",user_token)
        try:
            user_message = user_messages_dic.get(user_token, 'none')
        except:
            user_message = "none"
        # print("-"*10,user_message,"-"*10)
        if not image_data or not location:
            return jsonify({"error": "图像、位置信息或导航指令不能为空"}), 400
        
        # 保存接收到的图像
        image_path = save_image(image_data)
        destination = ana_msg(user_message)
        # 调用导航函数处理图像和位置信息，返回流式响应
        return process_navigation(image_path, location,destination)
    
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
    image_path = os.path.join('img', "rec.png")
    
    # 解码并保存图像
    with open(image_path, "wb") as image_file:
        image_file.write(base64.b64decode(image_data))
    
    return image_path

# 处理导航请求
def process_navigation(image_path, location, destination=None):
    try:
        # 调用navigator模块处理导航请求
        from navigator import process_navigation_request
        from flask import Response, stream_with_context
        
        # 获取生成器函数
        generator = process_navigation_request(image_path, location, destination)
        
        # 返回流式响应
        return Response(stream_with_context(generator()), 
                       content_type='text/event-stream',
                       headers={
                           'Cache-Control': 'no-cache',
                           'X-Accel-Buffering': 'no'
                       })
    except Exception as e:
        print(f"处理导航请求错误: {str(e)}")
        return jsonify({"error": "导航处理失败，请稍后再试"}), 500


def call_llm_api(llm_lr_response, history_msg, image_path=None, user_token=""):
    # 如果没有提供图像路径，使用默认图像
    if not image_path:
        image_path = r"img/default.png"
    
    base64_image = encode_image(image_path)
    # 解析传入的意图识别结果
    try:
        intent = llm_lr_response
        message = history_msg
        # print(message)
    except json.JSONDecodeError:
        print("JSON解析错误")
        yield f"data: 抱歉，系统处理出现错误。\n\n"
        return
    except Exception as e:
        print(f"数据处理错误: {str(e)}")
        yield f"data: 抱歉，系统处理出现错误。\n\n"
        return
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
        full_text = ""
        if intent == "普通聊天":
            try:
                print("已进入普通聊天部分")
                llm_basechat.extend(history_msg)
                completion = dashscope.Generation.call(
                    model="qwen-plus",
                    messages=llm_basechat,
                    temperature=0.35,
                    extra_body={
                        "enable_search": True
                    },
                    timeout=timeout,
                    result_format='message',
                    stream=True,
                    # 增量式流式输出
                    incremental_output=True
                )
                for chunk in completion:
                    try:
                        text_content = chunk.output.choices[0].message.content
                        if text_content:
                            print(f"{text_content}")
                            full_text += text_content
                            # 发送文本内容到前端
                            yield f"data: {text_content}\n\n"
                    except Exception as e:
                        print(f"处理流式输出块错误: {str(e)}")
                        continue
                print()
        
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": full_text})
                print("响应全文：", full_text)
            except Exception as e:
                print(f"普通聊天API调用错误: {str(e)}")
                if "Connection" in str(e):
                    yield f"data: 抱歉，服务连接出现问题，请稍后再试。\n\n"
                else:
                    yield f"data: 抱歉，处理您的请求时出现了问题。\n\n"
                
        elif intent == "查找某物的位置":
            try:
                # 先添加历史对话（除了最后一个元素，即当前用户输入）
                llm_visual_finder.extend(history_msg[:-1])  # 添加除最后一个元素外的所有历史消息
                # 转换为多模态格式
                llm_visual_finder = convert_to_multimodal(llm_visual_finder)
                # 提取当前用户输入的文本部分并添加到数组中
                user_message = history_msg[-1].get('content', '')
                llm_visual_finder.append({"role": "user", "content": [{"image": image_path}, {"text": user_message}]})
                # yield f"data: 正在分析图像...\n\n"
                completion = dashscope.MultiModalConversation.call(
                    model="qwen-vl-max",
                    messages=llm_visual_finder,
                    temperature=0.6,
                    result_format='message',
                    timeout=timeout,
                    stream=True,
                    # 增量式流式输出
                    incremental_output=True
                )
                for chunk in completion:
                    try:
                        text_content = chunk.output.choices[0].message.content[0].get('text', '')
                        if text_content:
                            print(f"{text_content}")

                            full_text += text_content
                            yield f"data: {text_content}\n\n"
                    except Exception as e:
                        print(f"处理流式输出块错误: {str(e)}")
                        continue
                print()
        
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": full_text})
                print("响应全文：", full_text)
            except Exception as e:
                print(f"查找位置API调用错误: {str(e)}")
                if "Connection" in str(e):
                    yield f"data: 抱歉，服务连接出现问题，请稍后再试。\n\n"
                else:
                    yield f"data: 抱歉，无法处理位置查找请求。\n\n"

        elif intent == "识别前方的情况":
            try:
                # 先添加历史对话（除了最后一个元素，即当前用户输入）
                llm_visual_recoder.extend(history_msg[:-1])  # 添加除最后一个元素外的所有历史消息
                # 转换为多模态格式
                llm_visual_recoder = convert_to_multimodal(llm_visual_recoder)
                # 提取当前用户输入的文本部分并添加到数组中
                user_message = history_msg[-1].get('content', '')
                llm_visual_recoder.append({"role": "user", "content": [{"image": image_path}, {"text": user_message}]})
                yield f"data: 正在分析图像...\n\n"
                completion = dashscope.MultiModalConversation.call(
                    model="qwen-vl-max",
                    messages=llm_visual_recoder,
                    temperature=0.6,
                    timeout=timeout,
                    result_format='message',
                    stream=True,
                    # 增量式流式输出
                    incremental_output=True
                )
                for chunk in completion:
                    try:
                        text_content = chunk.output.choices[0].message.content[0].get('text', '')
                        if text_content:
                            print(f"{text_content}")

                            full_text += text_content
                            yield f"data: {text_content}\n\n"
                            # 发送音频数据到前端
                    except Exception as e:
                        print(f"处理流式输出块错误: {str(e)}")
                        continue
                print()
        
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": full_text})
                print("响应全文：", full_text)
            except Exception as e:
                print(f"识别前方的情况API调用错误: {str(e)}")
                if "Connection" in str(e):
                    yield f"data: 抱歉，服务连接出现问题，请稍后再试。\n\n"
                else:
                    yield f"data: 抱歉，无法处理识别前方的情况。\n\n"

        elif intent == "阅读文字":
            try:
                # 先添加历史对话（除了最后一个元素，即当前用户输入）
                llm_text_reader.extend(history_msg[:-1])  # 添加除最后一个元素外的所有历史消息
                # 转换为多模态格式
                llm_text_reader = convert_to_multimodal(llm_text_reader)
                # 提取当前用户输入的文本部分并添加到数组中
                user_message = history_msg[-1].get('content', '')
                llm_text_reader.append({"role": "user", "content": [{"image": image_path}, {"text": user_message}]})
                yield f"data: 正在分析文字内容...\n\n"
                completion = dashscope.MultiModalConversation.call(
                    model="qwen-vl-max",
                    messages=llm_text_reader,
                    temperature=0.8,
                    result_format='message',
                    timeout=timeout,
                    stream=True,
                    # 增量式流式输出
                    incremental_output=True
                )
                for chunk in completion:
                    try:
                        text_content = chunk.output.choices[0].message.content[0].get('text', '')
                        if text_content:
                            print(f"{text_content}")
                            full_text += text_content
                            yield f"data: {text_content}\n\n"
                            # 发送音频数据到前端
                    except Exception as e:
                        print(f"处理流式输出块错误: {str(e)}")
                        continue
                print()
        
                yield f"data: [完成]\n\n"
                #synthesizer.streaming_complete()
                history_msg.append({"role": "assistant", "content": full_text})
                print("响应全文：", full_text)
            except Exception as e:
                print(f"文字阅读API调用错误: {str(e)}")
                if "Connection" in str(e):
                    yield f"data: 抱歉，服务连接出现问题，请稍后再试。\n\n"
                else:
                    yield f"data: 抱歉，无法处理文字阅读请求。\n\n"
                
        elif intent == "法律咨询":
            try:
                yield f"data: 正在处理法律咨询...\n\n"
                llm_legal_consultant.extend(history_msg)
                completion = dashscope.Generation.call(
                    model="farui-plus",
                    messages=llm_legal_consultant,
                    temperature=0.9,
                    timeout=timeout,
                    result_format='message',
                    stream=True,
                    # 增量式流式输出
                    incremental_output=True
                )
                for chunk in completion:
                    try:
                        text_content = chunk.output.choices[0].message.content
                        if text_content:
                            print(f"{text_content}")
                            full_text += text_content
                            yield f"data: {text_content}\n\n"
                    except Exception as e:
                        print(f"处理流式输出块错误: {str(e)}")
                        continue
                print()
        
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": full_text})
                print("响应全文：", full_text)
            except Exception as e:
                print(f"法律咨询API调用错误: {str(e)}")
                if "Connection" in str(e):
                    yield f"data: 抱歉，服务连接出现问题，请稍后再试。\n\n"
                else:
                    yield f"data: 抱歉，无法处理法律咨询请求。\n\n"
        elif intent == "领航任务":
            try:
                # print(user_token == None, user_token == "", user_token == "None","UserToken:",user_token)   
                if user_token !="" and user_token != None and user_token!="None": 
                    this_message = history_msg[-1]['content']
                    # 将用户消息存储在字典中，使用token作为键
                    user_messages_dic[user_token] = this_message
                    # print("当前字典：",user_messages_dic)
                    yield f"data: 领航模式\n\n"
                else:
                    yield f"data: 未登录，无法使用领航模式\n\n"
            except Exception as e:
                print(f"领航任务API调用错误: {str(e)}")
                if "Connection" in str(e):
                    yield f"data: 抱歉，服务连接出现问题，请稍后再试。\n\n"
                else:
                    yield f"data: 抱歉，无法处理领航任务请求。\n\n"
        else:
            yield f"data: 抱歉，我无法理解您的意图。\n\n"
            yield f"data: [完成]\n\n"

    except Exception as e:
        print(f"整体API调用错误: {str(e)}")
        if "Connection" in str(e):
            return "抱歉，服务连接出现问题，请稍后再试。"
        return "抱歉，系统处理出现未知错误。"

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    print("登录请求，用户名：", username, "密码：", password)
    
    user = User.query.filter_by(username=username).first()
    
    if user is None:
        # 用户不存在，创建新用户
        try:
            print("用户不存在，尝试创建用户，用户名：", username)
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print("用户创建成功")
            return jsonify({
                "status": "success",
                "message": "注册并登录成功",
                "data": {"username": username}
            }), 201
        except Exception as e:
            db.session.rollback()
            print(f"用户创建失败: {str(e)}")
            return jsonify({
                "status": "error",
                "message": "创建用户失败",
                "error": str(e)
            }), 500
    
    # 用户存在，验证密码
    print("用户存在，验证密码")
    if not user.check_password(password):
        print("密码错误")
        return jsonify({
            "status": "error",
            "message": "密码错误",
            "error": "密码验证失败"
        }), 401
    
    print("密码正确,返回登录成功")
    return jsonify({
        "status": "success",
        "message": "登录成功",
        "data": {"username": username}
    }), 200
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)