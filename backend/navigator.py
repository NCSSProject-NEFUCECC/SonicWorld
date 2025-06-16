# -*- coding: utf-8 -*-  
import requests
import json
import os
import base64
import sys
import chater
from datetime import datetime
import numpy as np
import time
import uuid
from gen_audio import TTS
from auth_util import gen_sign_headers
# BlueLM API配置
APP_ID = '2025881276'
APP_KEY = 'SUzaUkzFYhnDSYwM'
METHOD = 'POST'
URI = '/api/v1/chat/completions'
DOMAIN = 'api-bluellm.vivo.com'
input_params = {
'app_id': APP_ID,
'app_key': APP_KEY,
'engineid': 'long_audio_synthesis_screen'
}
tts = TTS(**input_params)
tts.open()
gaode_key = "067edeed4e3b4cc6331c327cdb2b4f45"
def get_timestamp():
    now = datetime.now()
    return now.strftime("[%Y-%m-%d %H:%M:%S.%f]")

def get_direction(heading):
    if 0 <= heading <23:
        return "北"
    elif 23 <= heading <68:
        return "东北"
    elif 68 <= heading <113:
        return "东"
    elif 113 <= heading <158:
        return "东南"
    elif 158 <= heading <203:
        return "南"
    elif 203 <= heading <248:
        return "西南"
    elif 248 <= heading <293:
        return "西"
    elif 293 <= heading <338:
        return "西北"
    elif 338 <= heading <360:
        return "北"
    else:
        return "未知"

def parse_location_result(result):
    """解析高德地图API返回的结果"""
    if result and result.get("status") == "1":
        geocodes = result.get("geocodes", [])
        if geocodes:
            return {
                "location": geocodes[0].get("location"),  # 经纬度
                "formatted_address": geocodes[0].get("formatted_address"),  # 格式化地址
                "province": geocodes[0].get("province"),  # 省份
                "city": geocodes[0].get("city"),  # 城市
                "district": geocodes[0].get("district")  # 区县
            }
    return None

def get_location_info(address):
     """向高德地图API发送请求获取地理编码信息"""
     base_url = "https://restapi.amap.com/v3/geocode/geo"
     params = {
         "key": gaode_key,
         "address": address,
         "output": "JSON"
     }
 
     try:
         response = requests.get(base_url, params=params)
         response.raise_for_status()  # 检查请求是否成功
         # print("get_location_info的返回值是：",response.json(),type(response.json()))
 
         return response.json()
     except requests.RequestException as e:
         print(f"请求失败: {e}")
         return None

def get_region(location):
    # print("get_region的参数是：",location)
    """从高德地图API获取行政区名称"""
    base_url = "https://restapi.amap.com/v3/geocode/regeo"
    params = {
        "key": gaode_key,
        "location": f"{location[0]},{location[1]}",
        "extensions": "base",
        "output": "JSON"
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        res = response.json()
        if res.get("status") == "1":
            return res["regeocode"]["addressComponent"]["district"]
        return res.get('info')
    except requests.RequestException as e:
        print(f"获取行政区信息失败: {e}")
        return f"获取行政区信息失败: {e}"

def get_route_info(start, end):
    print("get_route_info的参数是：",start[0],start[1],end[0],end[1])
    # https://restapi.amap.com/v5/direction/walking?isindoor=0&origin={start[0]},{start[1]}&destination={end[0]},{end[1]}&key=<用户的key>
    base_url = "https://restapi.amap.com/v5/direction/walking"
    params = {
        "isindoor": 0,
        "origin": f"{start[0]},{start[1]}",
        "destination": f"{end[0]},{end[1]}",
        "key": gaode_key
    }
    try:
        response = requests.get(base_url, params=params)
        # response.raise_for_status()  # 检查请求是否成功
        # if response.status == 1:
        res = response.json()
        # print("get_route_info的返回值是：",res)
        # print("提取到第一步：",res['route']['paths'][0]['steps'][0]['instruction'])
        return res['route']['paths'][0]['steps'][0]['instruction']
    except Exception as e:
        print(f"get_route_info请求失败: {e}")
        return None
        
def ana_msg(message):
    print("收到的消息是：",message)
    
    # 准备请求参数
    params = {
        'requestId': str(uuid.uuid4())
    }
    print('requestId:', params['requestId'])
    
    # 构建请求数据
    data = {
        'prompt': '你的任务非常简单，从用户的输入中提取出地址信息，例如，用户说：我要去东北林业大学图书馆，你就输出：{"add":"东北林业大学图书馆"}。如果你没有从中看到目的地，则输出{"add":"None"}。用户输入：' + message,
        'model': 'vivo-BlueLM-TB-Pro',
        'sessionId': str(uuid.uuid4()),
        'extra': {
            'temperature': 0.9
        }
    }
    
    # 生成认证头部
    headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)
    headers['Content-Type'] = 'application/json'
    
    start_time = time.time()
    url = 'https://{}{}'.format(DOMAIN, URI)
    response = requests.post(url, json=data, headers=headers, params=params)
    
    if response.status_code == 200:
        res_obj = response.json()
        print(f'response:{res_obj}')
        if res_obj['code'] == 0 and res_obj.get('data'):
            content = res_obj['data']['content']
            print(f'final content:\n{content}')
            try:
                address = json.loads(content)["add"]
                if address == "None":
                    return None
                lal = get_location_info(address)
                lal = parse_location_result(lal)
                # print(address,"的经纬度为",lal["location"])
                # 将经纬度字符串转换为浮点数元组
                lng, lat = lal["location"].split(",")
                return (float(lng), float(lat))
            except (json.JSONDecodeError, KeyError) as e:
                print(f"解析地址信息失败: {e}")
                return None
    else:
        print(response.status_code, response.text)
        return None
    
    end_time = time.time()
    timecost = end_time - start_time
    print('请求耗时: %.2f秒' % timecost)

def gpslal2gaodelal(location):  #将gps的经纬度转换为高德的经纬度
    base_url = "https://restapi.amap.com/v3/assistant/coordinate/convert"
    params = {
        "key": gaode_key,
        "locations": f"{location[0]},{location[1]}",
        "coordsys": "gps",
        "output": "json"
    }
    response = requests.get(base_url, params=params)
    if response.status_code == 200 and response.json().get("status") == "1":
        res = response.json()
        return res["locations"].split(",")
        # return location
    else:
        return None
    
# 新增处理导航请求的函数
def process_navigation_request(image_path, current_location, destination=None, heading=None):
    from flask import Response, stream_with_context
    
    def generate():
        try:
            # 记录当前位置信息
            current_latitude = current_location.get('latitude')
            current_longitude = current_location.get('longitude')
            
            # 转换当前位置坐标为高德坐标系
            gaode_coords = gpslal2gaodelal((current_longitude, current_latitude))
            if gaode_coords:
                current_longitude, current_latitude = gaode_coords
            
            # print(f"当前位置: 经度 {current_longitude}, 纬度 {current_latitude}")
            yield f"data: 当前位置: 经度 {current_longitude}, 纬度 {current_latitude}\n\n"
            
            # 路线信息
            route_guidance = ""
            
            # 导入BlueLM API所需的模块
            import uuid
            from auth_util import gen_sign_headers
            

            
            # 如果提供了目标地点，获取路线信息
            if destination:
                # 使用navigator函数分析目标地点并获取经纬度
                destination_location = destination
                if destination_location:
                    # 目标位置经纬度字符串转为列表
                    dest_lng, dest_lat = destination_location[0], destination_location[1]
                    
                    # 获取路线指引
                    try:
                        route_info = get_route_info((current_longitude, current_latitude), (dest_lng, dest_lat))
                        # print("获取到导航信息",route_info)
                    except Exception as e:
                        route_info = f"获取路线信息失败: {str(e)}"
                    # yield f"data: 获取到路线信息: {route_info}\n\n"
                print("接收到用户朝向信息",heading)
                system_content = chater.navigator_with_destination
                user_text = f"导航建议：{route_info},用户朝向{get_direction(heading)},{heading},度"
            else:
                # 如果没有目标地点，只分析环境
                system_content = "你是一个导航助手，需要分析用户当前所处的环境图像，并给出适合盲人的指示。例如，当年看到正前方有障碍物时，建议用户向旁边躲避；当你看到盲人正走在马路上时，你应该建议向左或是向右回到人行道上。你的回应应当简洁、理性、高信息密度,不要擅自预测不在图片中的内容。你的输出应当是这样的：前方有。。。"
                user_text = ""
            
            # 准备图片数据
            with open(image_path, "rb") as f:
                b_image = f.read()
                image = base64.b64encode(b_image).decode('utf-8')
            
            # 准备请求参数
            params = {
                'requestId': str(uuid.uuid4())
            }
            print('requestId:', params['requestId'])
            
            # 构建请求数据
            data = {
                'prompt': system_content,
                'sessionId': str(uuid.uuid4()),
                'requestId': params['requestId'],
                'model': 'vivo-BlueLM-V-2.0',
                "messages": [
                    {
                        "role": "user",
                        "content": "data:image/JPEG;base64," + image,
                        "contentType": "image"
                    }
                ]
            }
            
            # 如果有文本内容，添加到消息中
            if user_text:
                data["messages"].append({
                    "role": "user",
                    "content": user_text,
                    "contentType": "text"
                })
            
            # 生成认证头部
            headers = gen_sign_headers(APP_ID, APP_KEY, METHOD, URI, params)
            headers['Content-Type'] = 'application/json'
            
            # 发起请求
            start_time = time.time()
            url = 'http://{}{}'.format(DOMAIN, URI)
            response = requests.post(url, json=data, headers=headers, params=params, stream=True)
            
            # 流式返回模型回复
            if response.status_code == 200:
                first_line = True
                for line in response.iter_lines():
                    if line:
                        if first_line:
                            first_line = False
                            fl_time = time.time()
                            fl_timecost = fl_time - start_time
                            print("首字耗时: %.2f秒" % fl_timecost)
                        
                        text_content = line.decode('utf-8', errors='ignore')
                        print(text_content)
                        # 发送文本内容
                        yield f"data: {text_content}\n\n"
                        synthesizer.streaming_call(text_content)
                        time.sleep(0.1)  # 给合成器处理时间
                        # 发送音频数据
                        audio_data = bytes(tts.gen_radio(text=text_content))
                        if len(audio_data)>0:
                            print("发送音频长度：",len(audio_data))
                            yield f"data:audio,{audio_data.hex()}\n\n"
            else:
                print(f"BlueLM API请求失败: {response.status_code}, {response.text}")
                yield f"data: BlueLM API请求失败: {response.status_code}\n\n"
                
            # 完成语音合成
            yield f"data: [完成]\n\n"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_msg = f"导航处理错误: {str(e)}"
            print(f"错误行号: {exc_tb.tb_lineno}")
            print(error_msg)
            yield f"data: {error_msg}\n\n"
    
    return generate