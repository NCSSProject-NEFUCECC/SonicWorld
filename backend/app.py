# -*- coding: utf-8 -*-
from gen_audio import TTS, AueType
from gen_text import STT
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import Response, stream_with_context
import os
import json
import io
import base64
import time
import traceback
from navigator import ana_msg,get_region
from chater import intent_recognition
import chater
from datetime import datetime
from database import db, User
from weather import get_time_of_day,weather_map,weather_url
import requests
import uuid
import time
import wave
import re
from auth_util import gen_sign_headers
from functions_call import *

def debug_write_messages(messages_with_system, context=""):
    """将messages_with_system的内容写入debug_msg.txt文件"""
    try:
        debug_content = f"\n=== {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {context} ===\n"
        debug_content += json.dumps(messages_with_system, ensure_ascii=False, indent=2)
        debug_content += "\n" + "="*80 + "\n"
        
        with open('debug_msg.txt', 'a', encoding='utf-8') as f:
            f.write(debug_content)
    except Exception as e:
        print(f"调试写入失败: {str(e)}")

def extract_function_names(api_response: str):
    """
    从包含<APIs>标签的文本中提取所有函数名
    
    参数:
        api_response: 可能包含API调用信息的字符串，例如：
        '聊天内容<APIs>[{"name":"func1"},{"name":"func2"}]</APIs>其他内容'
        
    返回:
        提取到的函数名列表（如 ["func1", "func2"]）
        
    异常:
        ValueError: 当没有找到有效API声明时抛出
    """
    # 第一步：提取<APIs>标签内的内容
    api_match = re.search(r'<APIs>(.*?)</APIs>', api_response, re.DOTALL)
    if not api_match:
        raise ValueError("未找到<APIs>标签")
    
    api_content = api_match.group(1).strip()
    
    # 第二步：解析JSON数组（支持多种格式）
    try:
        # 处理可能存在的尾部逗号（非标准JSON）
        cleaned_content = re.sub(r',\s*\]', ']', api_content)
        api_list = json.loads(cleaned_content)
        
        if not isinstance(api_list, list):
            api_list = [api_list]  # 处理单对象非数组情况
            
        # 提取所有有效函数名
        return [
            str(item['name']) 
            for item in api_list 
            if isinstance(item, dict) and 'name' in item
        ]
    
    except json.JSONDecodeError:
        # 第三步：如果JSON解析失败，使用正则表达式兜底提取
        return re.findall(r'"name":\s*"([^"]+)"', api_content)
def extract_text_content(line_text):
    """从vivo大模型的流式响应中提取文本内容"""
    try:
        # 检查是否是data:开头的JSON格式
        if line_text.startswith('data:'):
            # 提取JSON部分
            json_text = line_text[5:].strip()
            if json_text:
                # 解析JSON
                json_data = json.loads(json_text)
                # 提取message字段
                text_content = json_data.get('message', '')
                message_type = json_data.get('type', 'text')
                
                if text_content and message_type == 'text':
                    return text_content
        else:
            # 尝试直接解析JSON
            line_data = json.loads(line_text)
            text_content = line_data.get('text', '')
            if text_content:
                return text_content
    except json.JSONDecodeError:
        # 如果不是JSON格式，直接使用文本
        print(f"非JSON格式: {line_text}")
    except Exception as e:
        print(f"解析文本内容错误: {str(e)}")
    
    return None

def filter_apis_content(text):
    """过滤掉APIs标签，返回正常对话内容"""
    if '<APIs>' not in text or '</APIs>' not in text:
        return text
    
    # 使用正则表达式移除所有APIs标签及其内容
    filtered_content = re.sub(r'<APIs>.*?</APIs>', '', text, flags=re.DOTALL)
    
    # 清理多余的空白字符
    filtered_content = re.sub(r'\s+', ' ', filtered_content).strip()
    
    return filtered_content

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)
db.init_app(app)

with app.app_context():
    db.create_all()

# 请替换APP_ID、APP_KEY
APP_ID = '2025881276'
APP_KEY = 'SUzaUkzFYhnDSYwM'
URI = '/vivogpt/completions/stream'
DOMAIN = 'api-ai.vivo.com.cn'
METHOD = 'POST'
user_messages_dic = {}

# 全局变量初始化
history_msg = []
weather_info = ""
time_info = ""

def generate_tts_audio_cpy(text):
    print("要生成的文本:", text)
    """生成TTS音频的通用函数"""
    try:
        input_params = {
            'app_id': "2025881276",
            'app_key': "SUzaUkzFYhnDSYwM",
            'engineid': 'long_audio_synthesis_screen'
        }
        tts = TTS(**input_params)
        ws_connection = tts.open()
        if ws_connection:
            audio_data = tts.gen_radio(aue=AueType.PCM, vcn='x2_yige', text=text)
            if audio_data:
                print(f"生成的音频数据长度: {len(audio_data)} 字节")
                yield f"data: audio,{audio_data.hex()}\n\n"
                print("已发送音频")
            else:
                print("TTS音频生成失败：返回空数据")
        else:
            print("TTS连接失败：无法建立websocket连接")
    except Exception as e:
        error_info = traceback.format_exc()
        print(f"TTS音频生成错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
        print(f"详细错误信息:\n{error_info}")

def generate_tts_audio(text):
    print("要生成的文本:", text)
    """生成TTS音频的通用函数"""
    try:
        input_params = {
            'app_id': "2025881276",
            'app_key': "SUzaUkzFYhnDSYwM",
            'engineid': 'long_audio_synthesis_screen'
        }
        tts = TTS(**input_params)
        ws_connection = tts.open()
        if ws_connection:
            audio_data = tts.gen_radio(aue=AueType.PCM, vcn='x2_yige', text=text)
            if audio_data:
                print(f"生成的音频数据长度: {len(audio_data)} 字节")
                yield f"data:audio,{audio_data.hex()}\n\n"
                print("已发送音频")
            else:
                print("TTS音频生成失败：返回空数据")
        else:
            print("TTS连接失败：无法建立websocket连接")
    except Exception as e:
        error_info = traceback.format_exc()
        print(f"TTS音频生成错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
        print(f"详细错误信息:\n{error_info}")

def encode_image(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_timestamp():
    now = datetime.now()
    return now.strftime("[%Y-%m-%d %H:%M:%S.%f]")

@app.route('/api/weather', methods=['POST'])
def get_weather():
    global weather_info
    
    try:
        data = request.json
        location = data.get('location', {})
        # print("location:",location)
        if not location or 'longitude' not in location or 'latitude' not in location:
            text = f"{get_time_of_day()}。位置信息不可用，天气信息暂时无法获取。"
        else:
            # 构建坐标字符串
            coordinates = f"{location['longitude']},{location['latitude']}"
            
            try:
                response = requests.get(weather_url(coordinates))
                weather_data = response.json()
                
                if weather_data['status'] == 'ok':
                    weather = weather_data['result']['realtime']
                    
                    # 获取天气数据
                    temperature = round(weather['temperature'])  # 温度
                    weather_desc = weather_map.get(weather['skycon'], '未知天气')  # 天气描述
                    humidity = round(weather['humidity'] * 100)  # 湿度
                    comfort = weather["life_index"]["comfort"]["desc"]
                    text = f"{get_time_of_day()}。今天{comfort}，气温{temperature}°C，天气是{weather_desc}，湿度{humidity}%"
                    print(text)
                else:
                    print(f"天气API返回错误: {weather_data}")
                    text = f"{get_time_of_day()}。天气信息暂时无法获取，请稍后再试。"
            except Exception as weather_error:
                print(f"获取天气信息失败: {str(weather_error)}")
                text = f"{get_time_of_day()}。天气信息暂时无法获取，请稍后再试。"
        
        weather_info = text
        
        input_params = {
            'app_id': APP_ID,
            'app_key': APP_KEY,
            'engineid': 'short_audio_synthesis_jovi'
        }
        tts = TTS(**input_params)
        if tts.open():
            audio_data = tts.gen_radio(aue=AueType.PCM, vcn='x2_yunye', text=text)
            if audio_data:
                return jsonify({
                    'status': 'success',
                    'data': {
                        'message': text,
                        'audio': audio_data.hex()
                    }
                }), 200
                
            else:
                return jsonify({
                    'status': 'error',
                    'message': '语音合成失败'
                }), 500
        else:
            return jsonify({
                'status': 'error',
                'message': 'TTS服务连接失败'
            }), 500
            
    except Exception as e:
        error_info = traceback.format_exc()
        print(f"获取天气信息错误 - 文件: {__file__}, 函数: get_weather, 错误: {str(e)}")
        print(f"详细错误信息:\n{error_info}")
        return jsonify({
            'status': 'error',
            'message': '抱歉，没有获取到天气信息'
        }), 500
  
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_messages = data.get('messages', '')
        user_message = user_messages[-1].get('content', '')
        try:
            user_location = (data.get('longitude', 0), data.get('latitude', 0))
            if user_location:
                pass
            else:
                user_location = None
                print('位置信息不完整或格式错误')
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"获取位置信息错误 - 文件: {__file__}, 函数: chat, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
            print(f"详细错误信息:\n{error_info}")
            user_location = None

        try:
            user_token = data.get('user_token', '')
            print("这条消息来自用户",user_token,"msg:",user_message)
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"获取用户token错误 - 文件: {__file__}, 函数: chat, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
            print(f"详细错误信息:\n{error_info}")
            user_token = "None"
        image_data = data.get('image', '')
        # print(len(user_message),user_message)
        if not user_message:
            print("消息不能为空")
            return jsonify({"error": "消息不能为空"}), 400
        
        # 意图识别
        intent = intent_recognition(user_messages)

        
        # 获取生成器函数
        image_path = None
        if image_data:
            # 如果有图像数据，保存图像
            image_path = save_image(image_data)
        
        generator = call_llm_api(intent, user_messages, image_path, user_token, user_location)
        
        # 返回流式响应
        return Response(stream_with_context(generator), 
                       content_type='text/event-stream',
                       headers={
                           'Cache-Control': 'no-cache',
                           'X-Accel-Buffering': 'no'
                       })
    except Exception as e:
        error_info = traceback.format_exc()
        print(f"聊天服务错误 - 文件: {__file__}, 函数: chat, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
        print(f"详细错误信息:\n{error_info}")
        return jsonify({"error": "服务器内部错误"}), 500

# 新增导航API端点
@app.route('/api/navigate', methods=['POST'])
def navigate():
    try:
        data = request.json
        image_data = data.get('image', '')
        location = data.get('location', {})
        try:
            heading = data.get('heading', 0)
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"获取朝向信息错误 - 文件: {__file__}, 函数: navigate, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
            print(f"详细错误信息:\n{error_info}")
            heading = None
        # print("获取到朝向",heading)
        user_token = data.get('user_token', '')
        print("当前用户：",user_token)
        try:
            user_message = user_messages_dic.get(user_token, 'none')
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"获取用户消息错误 - 文件: {__file__}, 函数: navigate, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
            print(f"详细错误信息:\n{error_info}")
            user_message = "none"
        # print("-"*10,user_message,"-"*10)
        if not image_data or not location:
            return jsonify({"error": "图像、位置信息或导航指令不能为空"}), 400
        
        # 保存接收到的图像
        image_path = save_image(image_data,name="navigation.png")
        destination = ana_msg(user_message)
        # 调用导航函数处理图像和位置信息，返回流式响应
        return process_navigation(image_path, location,destination,heading)
    
    except Exception as e:
        error_info = traceback.format_exc()
        print(f"导航错误 - 文件: {__file__}, 函数: navigate, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
        print(f"详细错误信息:\n{error_info}")
        return jsonify({"error": "导航服务器内部错误"}), 500

@app.route('/api/cpny', methods=['POST'])
def cpny_chat():
    global history_msg, weather_info, time_info
    
    def generate_response():
        global history_msg, weather_info, time_info
        full_text = ""
        
        try:
            # 处理音频文件上传
            if 'audio' in request.files:
                audio_file = request.files['audio']
                audio_data = audio_file.read()
                print(f"[陪伴模式] 接收到音频文件: {audio_file.filename}, 大小: {len(audio_data)} 字节")
            else:
                audio_data = request.data
                print(f"[陪伴模式] 接收到音频数据: {len(audio_data)} 字节")
                
            print(f"[陪伴模式] 开始语音识别...")
            # 语音转文字
            text = STT(audio_data)
            print(f"[陪伴模式] STT识别结果: '{text}'")
            print(f"[陪伴模式] 识别文本长度: {len(text) if text else 0} 字符")
            
            if not text or not text.strip():
                yield f"data: 抱歉，没有识别到语音内容，请重新说话。\n\n"
                return
                
            # 发送STT结果给前端
            yield f"data: STT:{text.strip()}\n\n"
            
            # 添加用户消息到历史记录
            history_msg.append({"role": "user", "content": text.strip()})
            
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"STT API错误 - 文件: {__file__}, 函数: cpny_chat, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
            print(f"详细错误信息:\n{error_info}")
            yield f"data: 抱歉，语音识别失败，请重试。\n\n"
            return
            
        
        # 初始化时间和天气信息
        time_info = datetime.now().strftime("%Y年%m月%d日%H时")
        if not weather_info:
            weather_info = "天气信息暂时无法获取"
        
        try:

            print("已进入普通聊天部分")
            print("weather_info:",weather_info)
            
            # 准备BlueLM模型调用参数
            params = {
                'requestId': str(uuid.uuid4())
            }
            print('requestId:', params['requestId'])
            
            # 构建请求数据
            system_prompt = f'这里是一些可能有用的信息，供你参考，但你不能主动提及。天气信息与位置信息:{weather_info}，时间信息:{time_info}，只有当用户问你这些信息时，你才应该告诉用户。'
            
            # 将system_prompt添加到历史消息中
            messages_with_system = []
            if len(history_msg) > 0 and history_msg[0].get('role') != 'system':
                messages_with_system.append({"role": "system", "content": system_prompt})
            messages_with_system.extend(history_msg)
            debug_write_messages(messages_with_system, "初始化messages_with_system(陪伴模式)")
            
            data = {
                'prompt': system_prompt,
                'sessionId': str(uuid.uuid4()),
                'model': 'vivo-BlueLM-TB-Pro',
                'messages': messages_with_system
            }
            
            # 生成认证头部
            headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)
            headers['Content-Type'] = 'application/json'
            
            # 发起请求
            url = 'http://{}{}'.format(DOMAIN, URI)
            start_time = time.time()
            response = requests.post(url, json=data, headers=headers, params=params, stream=True)
        
            if response.status_code == 200:
                first_line = True
                for line in response.iter_lines():
                    if line:
                        try:
                            if first_line:
                                first_line = False
                                fl_time = time.time()
                                fl_timecost = fl_time - start_time
                                print("首字耗时: %.2f秒" % fl_timecost)
                            
                            # 解析返回的数据
                            line_text = line.decode('utf-8', errors='ignore')
                            print(line_text)
                            
                            # 从返回的数据中提取文本内容
                            try:
                                # 检查是否是data:开头的JSON格式
                                if line_text.startswith('data:'):
                                    # 提取JSON部分
                                    json_text = line_text[5:].strip()
                                    if json_text:
                                        # 解析JSON
                                        json_data = json.loads(json_text)
                                        # 提取message字段
                                        text_content = json_data.get('message', '')
                                        message_type = json_data.get('type', 'text')
                                        
                                        if text_content and message_type == 'text':
                                            print(f"解析到消息: {text_content}")
                                            full_text += text_content
                                            # 发送文本内容到前端
                                            yield f"data: {text_content}\n\n"
                                else:
                                    # 尝试直接解析JSON
                                    line_data = json.loads(line_text)
                                    text_content = line_data.get('text', '')
                                    if text_content:
                                        print(f"{text_content}")
                                        full_text += text_content
                                        # 发送文本内容到前端
                                        yield f"data: {text_content}\n\n"
                            except json.JSONDecodeError:
                                # 如果不是JSON格式，直接使用文本
                                print(f"非JSON格式: {line_text}")

                        except Exception as e:
                            error_info = traceback.format_exc()
                            print(f"处理流式输出行错误 - 文件: {__file__}, 函数: cpny_chat, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                            print(f"详细错误信息:\n{error_info}")
                            continue
            
                # 计算总耗时
                yield from generate_tts_audio_cpy(full_text)
                end_time = time.time()
                timecost = end_time - start_time
                print("请求耗时: %.2f秒" % timecost)
            else:
                print(f"BlueLM API错误: {response.status_code}, {response.text}")
                yield f"data: 抱歉，模型服务返回错误，状态码: {response.status_code}\n\n"
            
            # 发送完成标志
            yield f"data: [完成]\n\n"
            
            # 添加AI回复到历史记录
            if full_text.strip():
                history_msg.append({"role": "assistant", "content": full_text})
                
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"陪伴模式API调用错误 - 文件: {__file__}, 函数: cpny_chat, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
            print(f"详细错误信息:\n{error_info}")
            if "Connection" in str(e):
                yield f"data: 抱歉，服务连接出现问题，请稍后再试。\n\n"
            else:
                yield f"data: 抱歉，处理您的请求时出现了问题。\n\n"
    
    # 返回流式响应
    return Response(stream_with_context(generate_response()), 
                   content_type='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no'
                   })
# 保存Base64编码的图像到文件
def save_image(image_data,name="rec.png"):
    # 从Base64字符串中提取图像数据
    if image_data.startswith('data:image'):
        # 移除MIME类型前缀
        image_data = image_data.split(',')[1]
    
    # 确保目录存在
    if not os.path.exists('img'):
        os.makedirs('img')
    
    # 使用固定文件名保存图片，覆盖之前的图片
    image_path = os.path.join('img', name)
    
    # 解码并保存图像
    with open(image_path, "wb") as image_file:
        image_file.write(base64.b64decode(image_data))
    
    return image_path

# 处理导航请求
def process_navigation(image_path, location, destination=None, heading=None):
    try:
        # 调用navigator模块处理导航请求
        from navigator import process_navigation_request
        from flask import Response, stream_with_context
        
        # 获取生成器函数
        generator = process_navigation_request(image_path, location, destination, heading)
        
        # 返回流式响应
        return Response(stream_with_context(generator()), 
                       content_type='text/event-stream',
                       headers={
                           'Cache-Control': 'no-cache',
                           'X-Accel-Buffering': 'no'
                       })
    except Exception as e:
        error_info = traceback.format_exc()
        print(f"处理导航请求错误 - 文件: {__file__}, 函数: process_navigation, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
        print(f"详细错误信息:\n{error_info}")
        return jsonify({"error": "导航处理失败，请稍后再试"}), 500

def call_llm_api(llm_lr_response, history_msg, image_path=None, user_token="", user_location=None):
    # 处理用户消息
    user_messages_dic[user_token] = history_msg
    # 如果没有提供图像路径，使用默认图像
    if not image_path:
        image_path = r"img/default.png"

    base64_image = encode_image(image_path)

    if user_location:
        region_info = get_region(user_location)
        print("-"*10,region_info,"-"*10)
        wuser_location = str(user_location[0]) + "," + str(user_location[1])
        try:
            response = requests.get(weather_url(wuser_location))
            data = response.json()
            
            if data['status'] == 'ok':
                weather = data['result']['realtime']
                
                # 获取天气数据
                temperature = round(weather['temperature'])  # 温度
                weather_desc = weather_map.get(weather['skycon'], '未知天气')  # 天气描述
                humidity = round(weather['humidity'] * 100)  # 湿度
                comfort = weather["life_index"]["comfort"]["desc"]
                weather_info = f"{region_info}今天{comfort}，气温{temperature}°C，天气是{weather_desc}，湿度{humidity}%"
            else:
                print(f"天气API返回错误: {data}")
                weather_info = "今天天气信息暂时无法获取"
        except Exception as e:
            print(f"获取天气信息失败: {str(e)}")
            weather_info = "今天天气信息暂时无法获取"
    else:
        weather_info = "今天天气信息暂时无法获取"
    # 获取时间信息
    time_info = datetime.now().strftime("%Y年%m月%d日%H时")
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
        error_info = traceback.format_exc()
        print(f"数据处理错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
        print(f"详细错误信息:\n{error_info}")
        yield f"data: 抱歉，系统处理出现错误。\n\n"
        return
    llm_visual_finder = [
                {"role": "system", "content": chater.finder},
            ]
    llm_visual_recoder = [
                {"role": "system", "content": chater.recoder},
            ]
    llm_text_reader = [
                {"role": "system", "content": chater.reader},
            ]
    llm_legal_consultant = [
                {"role": "system", "content": chater.legal_consultant},
            ]   
                    
    try:
        input_params = {
        'app_id': APP_ID,
        'app_key': APP_KEY,
        'engineid': 'long_audio_synthesis_screen'
        }
        tts = TTS(**input_params)
        tts.open()
        # 设置请求超时时间
        timeout = 30
        full_text = ""
        if intent == "普通聊天":
            try:
                print("已进入普通聊天部分")
                print("weather_info:", weather_info)
                # 准备BlueLM模型调用参数
                params = {
                    'requestId': str(uuid.uuid4())
                }
                print('requestId:', params['requestId'])
                
                # 构建请求数据
                system_prompt = f'这里是一些可能有用的信息，供你参考，但你不能主动提及。天气信息与位置信息:{weather_info}，时间信息:{time_info}，只有当用户问你这些信息时，你才应该告诉用户。'
                system_prompt += chater.normal_chater
                
                # 将system_prompt添加到历史消息中
                messages_with_system = []
                if len(history_msg) > 0 and history_msg[0].get('role') != 'system':
                    messages_with_system.append({"role": "system", "content": system_prompt})
                messages_with_system.extend(history_msg)
                debug_write_messages(messages_with_system, "初始化messages_with_system")
                
                # 处理流式响应的生成器函数
                def process_stream_response():
                    nonlocal full_text, history_msg, messages_with_system
                    
                    data = {
                        'prompt': system_prompt,
                        'sessionId': str(uuid.uuid4()),
                        'model': 'vivo-BlueLM-TB-Pro',
                        'messages': messages_with_system
                    }
                    
                    debug_write_messages(messages_with_system, f"第{iteration_count}轮发送API请求前")
                    
                    # 生成认证头部
                    headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)
                    headers['Content-Type'] = 'application/json'
                    
                    # 发起请求
                    url = 'http://{}{}'.format(DOMAIN, URI)
                    start_time = time.time()
                    response = requests.post(url, json=data, headers=headers, params=params, stream=True)
                    
                    if response.status_code == 200:
                        first_line = True
                        for line in response.iter_lines():
                            if line:
                                try:
                                    if first_line:
                                        first_line = False
                                        fl_time = time.time()
                                        fl_timecost = fl_time - start_time
                                        print("首字耗时: %.2f秒" % fl_timecost)
                                    
                                    # 解析返回的数据
                                    line_text = line.decode('utf-8', errors='ignore')
                                    print(line_text)
                                    
                                    # 从返回的数据中提取文本内容
                                    text_content = extract_text_content(line_text)
                                    if text_content:
                                        # print(f"解析到消息: {text_content}")
                                        full_text += text_content
                                        yield f"data: {text_content}\n\n"
                                        
                                except Exception as e:
                                    error_info = traceback.format_exc()
                                    print(f"处理流式输出行错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                                    print(f"详细错误信息:\n{error_info}")
                                    continue
                        
                        # 计算总耗时
                        end_time = time.time()
                        timecost = end_time - start_time
                        print("请求耗时: %.2f秒" % timecost)
                    else:
                        print(f"BlueLM API错误: {response.status_code}, {response.text}")
                        yield f"data: 抱歉，模型服务返回错误，状态码: {response.status_code}\n\n"
                
                def process_function_names(function_names):
                    lenth = len(function_names)
                    if lenth == 1:
                        return function_names[0]
                    elif lenth == 2:
                        return f"{function_names[0]}和{function_names[1]}"
                    else:
                        return ", ".join(function_names[:-1]) + f"和{function_names[-1]}"
                
                
                # 持续循环处理，直到模型不再请求function call
                max_iterations = 10  # 防止无限循环的安全措施
                iteration_count = 0
                
                while iteration_count < max_iterations:
                    iteration_count += 1
                    print(f"开始第{iteration_count}轮模型调用")
                    
                    # 调用模型获取响应
                    yield from process_stream_response()
                    
                    # 检查是否包含function call
                    if '<APIs>' in full_text and '</APIs>' in full_text:
                        
                        print(f"第{iteration_count}轮检测到function call，开始处理")
                        
                        # 先过滤掉APIs标签，获取正常对话内容
                        normal_content = filter_apis_content(full_text)
                        if normal_content.strip():
                            print(f"检测到正常对话内容，生成语音: {normal_content}")
                            yield from generate_tts_audio(normal_content)
                        
                        function_names = extract_function_names(full_text)
                        function_names = process_function_names(function_names)
                        
                        # 通知用户正在调用函数
                        notification_text = f"我将去调用这些工具：{function_names}。容我思考一下。。"
                        yield f"data: {notification_text}\n\n"
                        yield from generate_tts_audio(notification_text)
                        
                        # 处理function call
                        call_result = handle_function_call(full_text)
                        print(f"第{iteration_count}轮API调用结果: {call_result}")
                        
                        # 按照API要求的格式添加消息：user->assistant->function->assistant
                        # 1. 先添加assistant的function call请求
                        assistant_call_msg = {"role": "assistant", "content": full_text}
                        history_msg.append(assistant_call_msg)
                        messages_with_system.append(assistant_call_msg)
                        
                        # 2. 再添加function的执行结果
                        function_result_msg = {"role": "function", "content": call_result}
                        history_msg.append(function_result_msg)
                        messages_with_system.append(function_result_msg)
                        
                        debug_write_messages(messages_with_system, f"第{iteration_count}轮添加assistant call和function结果")
                        
                        # 重置full_text，准备接收新的响应
                        full_text = ""
                        
                        # 继续下一轮循环，让模型基于function call结果生成新的响应
                        continue
                    else:
                        # 没有检测到function call，说明模型已经完成所有需要的调用
                        print(f"第{iteration_count}轮未检测到function call，对话完成")
                        break
                
                # 如果达到最大迭代次数，输出警告
                if iteration_count >= max_iterations:
                    print(f"警告：达到最大迭代次数({max_iterations})，强制结束循环")
                    yield f"data: [系统提示：达到最大函数调用次数限制]\n\n"
                
                # 生成最终响应的TTS音频
                if full_text.strip():
                    yield from generate_tts_audio(full_text)
                yield f"data: [完成]\n\n"
                
                # 只有在没有function call的情况下才添加最终的assistant消息
                # 如果有function call，assistant消息已经在循环中正确添加了
                if iteration_count == 1 and '<APIs>' not in full_text:
                    # 这是一个普通对话，没有function call
                    history_msg.append({"role": "assistant", "content": full_text})
                elif iteration_count > 1 and full_text.strip():
                    # 这是function call后的最终响应
                    history_msg.append({"role": "assistant", "content": full_text})
                
            except Exception as e:
                error_info = traceback.format_exc()
                print(f"普通聊天API调用错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                print(f"详细错误信息:\n{error_info}")
                if "Connection" in str(e):
                    yield f"data: 抱歉，服务连接出现问题，请稍后再试。\n\n"
                else:
                    yield f"data: 抱歉，处理您的请求时出现了问题。\n\n"
                
        elif intent == "查找某物的位置":
            try:
                # 先添加历史对话（除了最后一个元素，即当前用户输入）
                llm_visual_finder.extend(history_msg[:-1])  # 添加除最后一个元素外的所有历史消息
                # 提取当前用户输入的文本部分
                user_message = history_msg[-1].get('content', '')
                yield f"data: 查找某物位置：\n\n"
                
                # 准备BlueLM多模态模型调用参数
                params = {
                    'requestId': str(uuid.uuid4())
                }
                print('requestId:', params['requestId'])
                
                # 读取图片并转换为Base64
                with open(image_path, "rb") as f:
                    b_image = f.read()
                image = base64.b64encode(b_image).decode('utf-8')
                
                # 构建请求数据
                data = {
                    'prompt': '你好',
                    'sessionId': str(uuid.uuid4()),
                    'requestId': params['requestId'],
                    'model': 'vivo-BlueLM-V-2.0',
                    "messages": [
                        {
                            "role": "system",
                            "content": chater.finder,
                            "contentType": "text"
                        },
                        {
                            "role": "user",
                            "content": "data:image/JPEG;base64," + image,
                            "contentType": "image"
                        },
                        {
                            "role": "user",
                            "content": user_message,
                            "contentType": "text"
                        }
                    ],
                }
                
                # 生成认证头部
                headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)
                headers['Content-Type'] = 'application/json'
                
                # 发起请求
                url = 'http://{}{}' .format(DOMAIN, URI)
                response = requests.post(url, json=data, headers=headers, params=params, stream=True)
                
                if response.status_code == 200:
                    first_line = True
                    for line in response.iter_lines():
                        if line:
                            try:
                                if first_line:
                                    first_line = False
                                    fl_time = time.time()
                                    fl_timecost = fl_time - start_time
                                    print("首字耗时: %.2f秒" % fl_timecost)
                                
                                line_text = line.decode('utf-8', errors='ignore')
                                print(line_text)
                                
                                # 从返回的数据中提取文本内容
                                try:
                                    # 检查是否是data:开头的JSON格式
                                    if line_text.startswith('data:'):
                                        # 提取JSON部分
                                        json_text = line_text[5:].strip()
                                        # 解析JSON
                                        json_data = json.loads(json_text)
                                        # 提取message字段
                                        text_content = json_data.get('message', '')
                                        message_type = json_data.get('type', 'text')
                                        
                                        if text_content and message_type == 'text':
                                            print(f"解析到消息: {text_content}")
                                            full_text += text_content
                                            # 发送文本内容到前端
                                            yield f"data: {text_content}\n\n"
                                    else:
                                        # 尝试直接解析JSON
                                        line_data = json.loads(line_text)
                                        text_content = line_data.get('text', '')
                                        if text_content:
                                            print(f"{text_content}")
                                            full_text += text_content
                                            # 发送文本内容到前端
                                            yield f"data: {text_content}\n\n"
                                except json.JSONDecodeError:
                                    # 如果不是JSON格式，直接使用文本
                                    print(f"非JSON格式: {line_text}")
                            except Exception as e:
                                error_info = traceback.format_exc()
                                print(f"处理流式输出行错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                                print(f"详细错误信息:\n{error_info}")
                                continue
                            # 流式合成语音                           
                            # 发送音频数据
                            #audio_data = bytes(tts.gen_radio(text=text_content))
                            if audio_data:
                                yield f"data:audio,{audio_data.hex()}\n\n"
                                print("发送音频数据，长度：", len(audio_data))
                # 生成最终响应的TTS音频
                if full_text.strip():
                    yield from generate_tts_audio(full_text)
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": full_text})
                print("响应全文：", full_text)
            except Exception as e:
                error_info = traceback.format_exc()
                print(f"位置查找API调用错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                print(f"详细错误信息:\n{error_info}")
                if "Connection" in str(e):
                    error_text = "抱歉，服务连接出现问题，请稍后再试。"
                else:
                    error_text = "抱歉，无法处理位置查找请求。"
                yield f"data: {error_text}\n\n"
                # 生成语音回复
                yield from generate_tts_audio(error_text)
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": error_text})

        elif intent == "识别前方的情况":
            try:
                # 先添加历史对话（除了最后一个元素，即当前用户输入）
                llm_visual_recoder.extend(history_msg[:-1])  # 添加除最后一个元素外的所有历史消息
                # 提取当前用户输入的文本部分
                user_message = history_msg[-1].get('content', '')
                yield f"data: 识别前方的情况: \n\n"
                
                # 准备BlueLM多模态模型调用参数
                params = {
                    'requestId': str(uuid.uuid4())
                }
                print('requestId:', params['requestId'])
                
                # 读取图片并转换为Base64
                with open(image_path, "rb") as f:
                    b_image = f.read()
                image = base64.b64encode(b_image).decode('utf-8')
                
                # 构建请求数据
                data = {
                    'prompt': '你好',
                    'sessionId': str(uuid.uuid4()),
                    'requestId': params['requestId'],
                    'model': 'vivo-BlueLM-V-2.0',
                    "messages": [
                        {
                            "role": "system",
                            "content": chater.recoder,
                            "contentType": "text"
                        },
                        {
                            "role": "user",
                            "content": "data:image/JPEG;base64," + image,
                            "contentType": "image"
                        },
                        {
                            "role": "user",
                            "content": user_message,
                            "contentType": "text"
                        }
                    ],
                }
                
                # 生成认证头部
                headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)
                headers['Content-Type'] = 'application/json'
                
                # 发起请求
                url = 'http://{}{}' .format(DOMAIN, URI)
                response = requests.post(url, json=data, headers=headers, params=params, stream=True)
                
                if response.status_code == 200:
                    first_line = True
                    for line in response.iter_lines():
                        if line:
                            try:
                                if first_line:
                                    first_line = False
                                    fl_time = time.time()
                                    fl_timecost = fl_time - start_time
                                    print("首字耗时: %.2f秒" % fl_timecost)
                                
                                line_text = line.decode('utf-8', errors='ignore')
                                print(line_text)
                                
                                # 从返回的数据中提取文本内容
                                try:
                                    # 检查是否是data:开头的JSON格式
                                    if line_text.startswith('data:'):
                                        # 提取JSON部分
                                        json_text = line_text[5:].strip()
                                        # 解析JSON
                                        json_data = json.loads(json_text)
                                        # 提取message字段
                                        text_content = json_data.get('message', '')
                                        message_type = json_data.get('type', 'text')
                                        
                                        if text_content and message_type == 'text':
                                            print(f"解析到消息: {text_content}")
                                            full_text += text_content
                                            # 发送文本内容到前端
                                            yield f"data: {text_content}\n\n"
                                    else:
                                        # 尝试直接解析JSON
                                        line_data = json.loads(line_text)
                                        text_content = line_data.get('text', '')
                                        if text_content:
                                            print(f"{text_content}")
                                            full_text += text_content
                                            # 发送文本内容到前端
                                            yield f"data: {text_content}\n\n"
                                except json.JSONDecodeError:
                                    # 如果不是JSON格式，直接使用文本
                                    print(f"非JSON格式: {line_text}")
                            except Exception as e:
                                error_info = traceback.format_exc()
                                print(f"处理流式输出行错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                                print(f"详细错误信息:\n{error_info}")
                                continue
                            # 流式合成语音          
                            # 发送音频数据
                            #audio_data = bytes(tts.gen_radio(text=text_content))
                            if audio_data:
                                yield f"data:audio,{audio_data.hex()}\n\n"
                # 生成最终响应的TTS音频
                if full_text.strip():
                    yield from generate_tts_audio(full_text)
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": full_text})
                print("响应全文：", full_text)
            except Exception as e:
                error_info = traceback.format_exc()
                print(f"视觉识别API调用错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                print(f"详细错误信息:\n{error_info}")
                if "Connection" in str(e):
                    error_text = "抱歉，服务连接出现问题，请稍后再试。"
                else:
                    error_text = "抱歉，无法处理识别前方的情况。"
                yield f"data: {error_text}\n\n"
                # 生成语音回复
                yield from generate_tts_audio(error_text)
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": error_text})

        elif intent == "阅读文字":
            try:
                # 先添加历史对话（除了最后一个元素，即当前用户输入）
                llm_text_reader.extend(history_msg[:-1])  # 添加除最后一个元素外的所有历史消息
                # 提取当前用户输入的文本部分
                user_message = history_msg[-1].get('content', '')
                yield f"data: 阅读文字：\n\n"
                
                # 准备BlueLM多模态模型调用参数
                params = {
                    'requestId': str(uuid.uuid4())
                }
                print('requestId:', params['requestId'])
                
                # 读取图片并转换为Base64
                with open(image_path, "rb") as f:
                    b_image = f.read()
                image = base64.b64encode(b_image).decode('utf-8')
                
                # 构建请求数据
                data = {
                    'prompt': '你好',
                    'sessionId': str(uuid.uuid4()),
                    'requestId': params['requestId'],
                    'model': 'vivo-BlueLM-V-2.0',
                    "messages": [
                        {
                            "role": "system",
                            "content": chater.reader,
                            "contentType": "text"
                        },
                        {
                            "role": "user",
                            "content": "data:image/JPEG;base64," + image,
                            "contentType": "image"
                        },
                        {
                            "role": "user",
                            "content": user_message,
                            "contentType": "text"
                        }
                    ],
                }
                
                # 生成认证头部
                headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)
                headers['Content-Type'] = 'application/json'
                
                # 发起请求
                url = 'http://{}{}' .format(DOMAIN, URI)
                response = requests.post(url, json=data, headers=headers, params=params, stream=True)
                
                if response.status_code == 200:
                    first_line = True
                    for line in response.iter_lines():
                        if line:
                            try:
                                if first_line:
                                    first_line = False
                                    fl_time = time.time()
                                    fl_timecost = fl_time - start_time
                                    print("首字耗时: %.2f秒" % fl_timecost)
                                
                                line_text = line.decode('utf-8', errors='ignore')
                                print(line_text)
                                
                                # 从返回的数据中提取文本内容
                                try:
                                    # 检查是否是data:开头的JSON格式
                                    if line_text.startswith('data:'):
                                        # 提取JSON部分
                                        json_text = line_text[5:].strip()
                                        # 解析JSON
                                        json_data = json.loads(json_text)
                                        # 提取message字段
                                        text_content = json_data.get('message', '')
                                        message_type = json_data.get('type', 'text')
                                        
                                        if text_content and message_type == 'text':
                                            print(f"解析到消息: {text_content}")
                                            full_text += text_content
                                            # 发送文本内容到前端
                                            yield f"data: {text_content}\n\n"
                                    else:
                                        # 尝试直接解析JSON
                                        line_data = json.loads(line_text)
                                        text_content = line_data.get('text', '')
                                        if text_content:
                                            print(f"{text_content}")
                                            full_text += text_content
                                            # 发送文本内容到前端
                                            yield f"data: {text_content}\n\n"
                                except json.JSONDecodeError:
                                    # 如果不是JSON格式，直接使用文本
                                    print(f"非JSON格式: {line_text}")
                            except Exception as e:
                                error_info = traceback.format_exc()
                                print(f"处理流式输出行错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                                print(f"详细错误信息:\n{error_info}")
                                continue
                # 生成最终响应的TTS音频
                if full_text.strip():
                    yield from generate_tts_audio(full_text)
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": full_text})
                print("响应全文：", full_text)
            except Exception as e:
                error_info = traceback.format_exc()
                print(f"文字阅读API调用错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                print(f"详细错误信息:\n{error_info}")
                if "Connection" in str(e):
                    error_text = "抱歉，服务连接出现问题，请稍后再试。"
                else:
                    error_text = "抱歉，无法处理文字阅读请求。"
                yield f"data: {error_text}\n\n"
                # 生成语音回复
                yield from generate_tts_audio(error_text)
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": error_text})
                
        elif intent == "领航任务":
            try:
                # print(user_token == None, user_token == "", user_token == "None","UserToken:",user_token)   
                if user_token !="" and user_token != None and user_token!="None": 
                    this_message = history_msg[-1]['content']
                    # 将用户消息存储在字典中，使用token作为键
                    user_messages_dic[user_token] = this_message
                    # print("当前字典：",user_messages_dic)
                    response_text = "领航模式已启动，正在为您提供导航服务。"
                    yield f"data: {response_text}\n\n"
                    # 生成语音回复
                    yield from generate_tts_audio(response_text)
                    yield f"data: [完成]\n\n"
                    history_msg.append({"role": "assistant", "content": response_text})
                else:
                    response_text = "未登录，无法使用领航模式"
                    yield f"data: {response_text}\n\n"
                    # 生成语音回复
                    yield from generate_tts_audio(response_text)
                    yield f"data: [完成]\n\n"
                    history_msg.append({"role": "assistant", "content": response_text})
            except Exception as e:
                error_info = traceback.format_exc()
                print(f"领航任务API调用错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                print(f"详细错误信息:\n{error_info}")
                if "Connection" in str(e):
                    error_text = "抱歉，服务连接出现问题，请稍后再试。"
                else:
                    error_text = "抱歉，无法处理领航任务请求。"
                yield f"data: {error_text}\n\n"
                # 生成语音回复
                yield from generate_tts_audio(error_text)
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": error_text})
        elif intent == "陪伴模式":
            try: 
                if user_token !="" and user_token != None and user_token!="None": 
                    response_text = "陪伴模式已启动，我将陪伴您进行语音对话。"
                    yield f"data: {response_text}\n\n"
                    # 生成语音回复
                    yield from generate_tts_audio(response_text)
                    yield f"data: [完成]\n\n"
                    history_msg.append({"role": "assistant", "content": response_text})
                else:
                    response_text = "未登录，无法使用陪伴模式"
                    yield f"data: {response_text}\n\n"
                    # 生成语音回复
                    yield from generate_tts_audio(response_text)
                    yield f"data: [完成]\n\n"
                    history_msg.append({"role": "assistant", "content": response_text})
            except Exception as e:
                error_info = traceback.format_exc()
                print(f"陪伴模式调用错误 - 文件: {__file__}, 函数: call_llm_api, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
                print(f"详细错误信息:\n{error_info}")
                if "Connection" in str(e):
                    error_text = "抱歉，服务连接出现问题，请稍后再试。"
                else:
                    error_text = "抱歉，无法处理陪伴模式请求。"
                yield f"data: {error_text}\n\n"
                # 生成语音回复
                yield from generate_tts_audio(error_text)
                yield f"data: [完成]\n\n"
                history_msg.append({"role": "assistant", "content": error_text})
        else:
            response_text = "抱歉，我无法理解您的意图。请尝试重新描述您的需求。"
            yield f"data: {response_text}\n\n"
            # 生成语音回复
            yield from generate_tts_audio(response_text)
            yield f"data: [完成]\n\n"
            history_msg.append({"role": "assistant", "content": response_text})

    except Exception as e:
        print(f"整体API调用错误: {str(e)}")
        error_info = traceback.format_exc()
        print(f"详细错误信息:\n{error_info}")
        
        if "Connection" in str(e):
            error_text = "抱歉，服务连接出现问题，请稍后再试。"
        else:
            error_text = "抱歉，系统处理出现未知错误。"
        
        try:
            # 为错误信息生成语音回复
            yield f"data: {error_text}\n\n"
            yield from generate_tts_audio(error_text)
            yield f"data: [完成]\n\n"
            history_msg.append({"role": "assistant", "content": error_text})
        except:
            # 如果语音生成也失败，至少返回文本
            yield f"data: {error_text}\n\n"
            yield f"data: [完成]\n\n"

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data:
            return jsonify({
                "status": "error",
                "message": "请求数据为空",
                "error": "无效的请求格式"
            }), 400
            
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                "status": "error",
                "message": "用户名和密码不能为空",
                "error": "缺少必要参数"
            }), 400
            
        print("登录请求，用户名：", username, "密码：", password)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "请求格式错误",
            "error": str(e)
        }), 400
    
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
            error_info = traceback.format_exc()
            print(f"用户创建失败 - 文件: {__file__}, 函数: login, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
            print(f"详细错误信息:\n{error_info}")
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