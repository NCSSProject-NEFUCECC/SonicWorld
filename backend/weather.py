from datetime import datetime

def weather_url(coordinates):
     return f"https://api.caiyunapp.com/v2.6/QoJVR67908vzujP0/{coordinates}/realtime"

def get_weather_word(temperature):
    if temperature < 5:
        return "寒冷"
    elif temperature < 12:
        return "冷"
    elif temperature < 18:
        return "凉爽"  
    elif temperature < 25:
        return "舒适"
    elif temperature < 30:
        return "温暖"
    elif temperature < 35:
        return "热"
    else:
        return "炎热"

def get_time_of_day():
    current_time = datetime.now().time()
    morning_start = datetime.strptime("06:00:00", "%H:%M:%S").time()
    morning_end = datetime.strptime("11:00:00", "%H:%M:%S").time()
    noon_start = datetime.strptime("11:00:00", "%H:%M:%S").time()
    noon_end = datetime.strptime("13:00:00", "%H:%M:%S").time()
    afternoon_start = datetime.strptime("13:00:00", "%H:%M:%S").time()
    afternoon_end = datetime.strptime("18:00:00", "%H:%M:%S").time()
    evening_start = datetime.strptime("18:00:00", "%H:%M:%S").time()
    evening_end = datetime.strptime("23:59:59", "%H:%M:%S").time()
    midnight_start = datetime.strptime("00:00:00", "%H:%M:%S").time()
    midnight_end = datetime.strptime("05:59:59", "%H:%M:%S").time()
    if morning_start <= current_time <= morning_end:
        return "早上好"
    elif noon_start <= current_time <= noon_end:
        return "中午好"
    elif afternoon_start <= current_time <= afternoon_end:
        return "下午好"
    elif evening_start <= current_time <= evening_end:
        return "晚上好"
    elif midnight_start <= current_time <= midnight_end:
        return "夜深了，早点休息哦"

# 天气状况映射表
weather_map = {
    'CLEAR_DAY': '晴天',
    'CLEAR_NIGHT': '晴夜',
    'PARTLY_CLOUDY_DAY': '多云',
    'PARTLY_CLOUDY_NIGHT': '多云',
    'CLOUDY': '阴天',
    'LIGHT_RAIN': '小雨',
    'MODERATE_RAIN': '中雨',
    'HEAVY_RAIN': '大雨',
    'STORM_RAIN': '暴雨',
    'LIGHT_SNOW': '小雪',
    'MODERATE_SNOW': '中雪',
    'HEAVY_SNOW': '大雪',
    'STORM_SNOW': '暴雪',
    'FOG': '雾',
    'DUST': '浮尘',
    'HEAVY_HAZE': '霾',
}