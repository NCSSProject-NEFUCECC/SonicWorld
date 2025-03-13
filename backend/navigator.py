import requests
import dashscope
import json
import os
import base64


def get_location_info(address):
    """向高德地图API发送请求获取地理编码信息"""
    base_url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": "720655fed978632fd548b69f8808bc72",
        "address": address,
        "output": "JSON"
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # 检查请求是否成功
        return response.json()
    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return None

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
        response.raise_for_status()  # 检查请求是否成功
        if response.status == 1:
            res = response.json()
            return res['route']['paths'][0]['instruction']
    except Exception as e:
        print(f"请求失败: {e}")
        return None
        

def ana_msg(message):
    """
    导航函数，用于处理用户输入的导航请求
    Args:
        message: 用户输入的导航消息
    Returns:
        location: 目标位置的经纬度
    """
    print(message)
    messages = [
        {
            "role": "system",
            "content": '你的任务非常简单，从用户的输入中提取出地址信息，例如，用户说：我要去东北林业大学图书馆，你就输出：{"add":"东北林业大学图书馆"}。如果用户没有明确的目的地，则输出{"add":"None"}'
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
    lal = get_location_info(address)
    lal = parse_location_result(lal)
    print(address,"的经纬度为",lal["location"])
    return lal["location"]

def gpslal2gaodelal(location):
    """将gps的经纬度转换为高德的经纬度"""
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
    else:
        return None
    

# 新增处理导航请求的函数
def process_navigation_request(image_path, current_location, destination=None):
    """处理前端发送的导航请求
    
    Args:
        image_path: 保存的图像路径
        current_location: 包含经纬度的当前位置信息字典
        destination: 目标地点描述，如果为None则只分析环境不提供路线
    
    Returns:
        导航指令或状态信息
    """
    try:
        # 记录当前位置信息
        current_latitude = current_location.get('latitude')
        current_longitude = current_location.get('longitude')
        
        # 转换当前位置坐标为高德坐标系
        gaode_coords = gpslal2gaodelal((current_latitude, current_longitude))
        if gaode_coords:
            current_latitude, current_longitude = gaode_coords
        
        print(f"当前位置: 纬度 {current_latitude}, 经度 {current_longitude}")
        
        # 路线信息
        route_guidance = ""
        
        # 如果提供了目标地点，获取路线信息
        if destination:
            # 使用navigator函数分析目标地点并获取经纬度
            destination_location = ana_msg(destination)
            if destination_location:
                # 目标位置经纬度字符串转为列表
                dest_lng, dest_lat = destination_location.split(",")
                
                # 获取路线指引
                route_info = get_route_info((current_longitude, current_latitude), (dest_lng, dest_lat))
        
            messages = [
                {
                    "role": "system",
                    "content": "你是一个导航助手，需要分析用户当前所处的环境图像，并提供导航建议。请分析图像中看到的环境，根据导航建议和路况，并给出适合盲人的导航指示。你的回应应当简洁、理性、高信息密度。"
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
                    "content": "你是一个导航助手，需要分析用户当前所处的环境图像，并提供导航建议。简要分析图像中看到的环境，根据路况，并给出适合盲人的导航指示。你的回应应当简洁、理性、高信息密度。"
                },
                {
                    "role": "user",
                    "content": [
                        {"image": image_path}
                    ]
                }
            ]
        
        # 调用多模态模型
        response = dashscope.MultiModalConversation.call(
            model="qwen-vl-max",
            messages=messages,
            result_format='message'
        )
        print(response)
        # 提取模型回复
        navigation_guidance = response.output.choices[0].message.content[0].get('text')
        
        return navigation_guidance
        
    except Exception as e:
        print(f"导航处理错误: {str(e)}")
        return f"导航处理出现错误: {str(e)}"

# 辅助函数：将图像编码为base64字符串
def encode_image(image_path):
    """将图像文件编码为base64字符串"""
    if not os.path.exists(image_path):
        print(f"图像文件不存在: {image_path}")
        return ""
        
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")