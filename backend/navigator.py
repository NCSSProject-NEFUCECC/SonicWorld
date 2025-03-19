import requests
import dashscope
import json
import os
import base64
import sys
from datetime import datetime
from dashscope.api_entities.dashscope_response import SpeechSynthesisResponse
from dashscope.audio.tts_v2 import *
import sounddevice
import numpy as np


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

def get_route_info(start, end):
    print("get_route_info的参数是：",start[0],start[1],end[0],end[1])
    # https://restapi.amap.com/v5/direction/walking?isindoor=0&origin={start[0]},{start[1]}&destination={end[0]},{end[1]}&key=<用户的key>
    base_url = "https://restapi.amap.com/v5/direction/walking"
    params = {
        "isindoor": 0,
        "origin": f"{start[0]},{start[1]}",
        "destination": f"{end[0]},{end[1]}",
        "key": "720655fed978632fd548b69f8808bc72"
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
    messages = [
        {
            "role": "system",
            "content": '你的任务非常简单，从用户的输入中提取出地址信息，例如，用户说：我要去东北林业大学图书馆，你就输出：{"add":"东北林业大学图书馆"}。如果你没有从中看到目的地，则输出{"add":"None"}，'
        },
        {
            "role": "user",
            "content": message
        }
    ]
    llm_ir = dashscope.Generation.call(
            model="qwen-plus",
            messages=messages,
            result_format='message'
        )
    address = llm_ir.output.choices[0].message.content
    address = json.loads(address)["add"]
    if address == "None":
        return None
    lal = get_location_info(address)
    lal = parse_location_result(lal)
    print(address,"的经纬度为",lal["location"])
    # 将经纬度字符串转换为浮点数元组
    lng, lat = lal["location"].split(",")
    return (float(lng), float(lat))

def gpslal2gaodelal(location):  #将gps的经纬度转换为高德的经纬度
    base_url = "https://restapi.amap.com/v3/assistant/coordinate/convert"
    params = {
        "key": "720655fed978632fd548b69f8808bc72",
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
def process_navigation_request(image_path, current_location, destination=None):
    """处理前端发送的导航请求，以流式方式返回结果
    
    Args:
        image_path: 保存的图像路径
        current_location: 包含经纬度的当前位置信息字典
        destination: 目标地点描述，如果为None则只分析环境不提供路线
    
    Returns:
        生成器，用于流式返回导航指令或状态信息
    """
    from flask import Response, stream_with_context
    
    def generate():
        try:
            # 记录当前位置信息
            current_latitude = current_location.get('latitude')
            current_longitude = current_location.get('longitude')
            
            # 转换当前位置坐标为高德坐标系
            gaode_coords = gpslal2gaodelal((current_latitude, current_longitude))
            if gaode_coords:
                current_latitude, current_longitude = gaode_coords
            
            print(f"当前位置: 纬度 {current_latitude}, 经度 {current_longitude}")
            yield f"data: 当前位置: 纬度 {current_latitude}, 经度 {current_longitude}\n\n"
            
            # 路线信息
            route_guidance = ""
            
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
                        print("获取到导航信息",route_info)
                    except Exception as e:
                        route_info = f"获取路线信息失败: {str(e)}"
                    # yield f"data: 获取到路线信息: {route_info}\n\n"
            
                messages = [
                    {
                        "role": "system",
                        "content": "你是一个导航助手，需要分析用户当前所处的环境图像，并提供导航建议。请分析图像中看到的环境，根据导航建议和路况，并给出适合盲人的导航指示。你的回应应当简洁、理性、高信息密度。不要擅自预测不在图片中的内容。你的输出应当是这样的：当前环境中有。。。/你正处在。。。，导航信息显示。。。，建议。。。"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"image": image_path},
                            {"text": f"导航建议：{route_info}"}
                        ]
                    }
                ]
            else:
                # 如果没有目标地点，只分析环境
                messages = [
                    {
                        "role": "system",
                        "content": "你是一个导航助手，需要分析用户当前所处的环境图像，并提供导航建议。简要分析图像中看到的环境，根据路况，并给出适合盲人的导航指示。你的回应应当简洁、理性、高信息密度,不要擅自预测不在图片中的内容。你的输出应当是这样的：当前环境中有。。。/你正处在。。。，建议。。。"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"image": image_path}
                        ]
                    }
                ]
        
        # 调用多模态模型
            response_stream = dashscope.MultiModalConversation.call(
                model="qwen-vl-max",
                messages=messages,
                result_format='message',
                stream=True,
                # 增量式流式输出
                incremental_output=True,
                presence_penalty = 1
            )
        
        # 流式返回模型回复
            for chunk in response_stream:
                try:
                    text_content = chunk.output.choices[0].message.content[0].get('text', '')
                    if text_content:
                        print(f"{text_content}", end="")
                        # 发送文本内容
                        yield f"data: {text_content}\n\n"
                except Exception as e:
                    print(f"处理流式输出块错误: {str(e)}")
                    continue
            print()
            
            
            yield f"data: [完成]\n\n"
        
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            error_msg = f"导航处理错误: {str(e)}"
            print(f"错误行号: {exc_tb.tb_lineno}")
            print(error_msg)
            yield f"data: {error_msg}\n\n"
    
    return generate

        
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")