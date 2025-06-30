import json
import random
import re
import requests
import json
import time

def handle_function_call(llm_msg):
    print("LLM输出的函数调用是：",llm_msg)
    match = re.search(r"<APIs>(.*?)</APIs>", llm_msg, re.DOTALL)
    if match:
        api_str = match.group(1).strip()
    else:
        return "Error: <APIs> tags not found or malformed."
    print("清理后的函数调用是：",api_str)

    result = []
    try:
        api_list = json.loads(api_str)
        for api_call in api_list:
            function_name = api_call.get("name")
            parameters = api_call.get("parameters", {})
            if function_name == "test":
                result.append(test(**parameters))
            elif function_name == "weibo_hot":
                result.append(weibo_hot(**parameters))
            elif function_name == "horoscope":
                result.append(horoscope(**parameters))
            elif function_name == "exchange_rate":
                result.append(exchange_rate(**parameters))
            else:
                print("未知的函数调用：",function_name)
                return f"Unknown function: {function_name}"
        return '\n'.join(str(item) for item in result)
    except json.JSONDecodeError:
        return "Error: Invalid JSON format in API call."

def test():
    return f"Function Call测试成功！你需要告诉用户的内容是：HelloWorld！"

def weibo_hot():
    max_retries = 3
    retry_delay = 1  # 重试间隔时间（秒）
    
    for attempt in range(max_retries):
        try:
            res = requests.get("https://api.vvhan.com/api/hotlist/wbHot", timeout=10)
            res.raise_for_status()  # 检查HTTP状态码
            # print(res.text)
            hot_list = json.loads(res.text)
            hotest = hot_list['data'][0]["title"]
            # print(hotest)
            return "现在最热门的事件是",hotest
        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"第{attempt + 1}次尝试失败: {str(e)}")
            if attempt < max_retries - 1:
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避策略
            else:
                print("所有重试尝试都失败了")
                return "获取热门事件失败，请稍后再试", ""
def horoscope(horoscope_type):
    """
    获取星座运势
    :param horoscope_type: 星座类型
    :return: 详细的运势信息
    """
    max_retries = 3
    retry_delay = 1  # 重试间隔时间（秒）
    
    for attempt in range(max_retries):
        try:
            res = requests.get(f"https://api.vvhan.com/api/horoscope?type={horoscope_type}&time=today", timeout=10)
            res.raise_for_status()  # 检查HTTP状态码
            
            response_data = json.loads(res.text)
            
            if not response_data.get('success', False):
                return "获取运势失败", "API返回错误状态"
            
            data = response_data.get('data', {})
            
            # 构建详细的运势信息
            result = f"{data.get('title', '未知星座')} {data.get('time', '今日')}运势\n\n"
            result += f"运势概况：{data.get('shortcomment', '暂无')}\n\n"
            
            # 运势指数
            index = data.get('index', {})
            result += "运势指数：\n"
            result += f"• 综合运势：{index.get('all', 'N/A')}\n"
            result += f"• 爱情运势：{index.get('love', 'N/A')}\n"
            result += f"• 工作运势：{index.get('work', 'N/A')}\n"
            result += f"• 财运指数：{index.get('money', 'N/A')}\n"
            result += f"• 健康指数：{index.get('health', 'N/A')}\n\n"
            
            # 详细运势文本
            fortunetext = data.get('fortunetext', {})
            if fortunetext.get('all'):
                result += f"综合运势：{fortunetext['all']}\n\n"
            if fortunetext.get('love'):
                result += f"爱情运势：{fortunetext['love']}\n\n"
            if fortunetext.get('work'):
                result += f"工作运势：{fortunetext['work']}\n\n"
            if fortunetext.get('money'):
                result += f"财运分析：{fortunetext['money']}\n\n"
            if fortunetext.get('health'):
                result += f"健康提醒：{fortunetext['health']}\n\n"
            
            # 今日宜忌
            todo = data.get('todo', {})
            if todo:
                result += "今日宜忌：\n"
                if todo.get('yi'):
                    result += f"• 宜：{todo['yi']}\n"
                if todo.get('ji'):
                    result += f"• 忌：{todo['ji']}\n\n"
            
            # 幸运元素
            result += "幸运元素：\n"
            result += f"幸运数字：{data.get('luckynumber', 'N/A')}\n"
            result += f"幸运颜色：{data.get('luckycolor', 'N/A')}\n"
            result += f"幸运星座：{data.get('luckyconstellation', 'N/A')}"
            
            return "这是用户所需的数据，你需要总结一下，但不要丢失要点，要包括今日宜忌、幸运元素：", result
            
        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"第{attempt + 1}次尝试失败: {str(e)}")
            if attempt < max_retries - 1:
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避策略
            else:
                print("所有重试尝试都失败了")
                return "获取运势失败，请稍后再试", ""

def exchange_rate(from_currency, to_currency, amount=1):
    """
    获取汇率转换信息
    :param from_currency: 源货币代码（如USD）
    :param to_currency: 目标货币代码（如CNY）
    :param amount: 转换金额，默认为1
    :return: 汇率转换结果
    """
    max_retries = 3
    retry_delay = 1  # 重试间隔时间（秒）
    
    for attempt in range(max_retries):
        try:
            url = f"https://v2.xxapi.cn/api/exchange?from={from_currency}&to={to_currency}&amount={amount}"
            res = requests.get(url, timeout=10)
            res.raise_for_status()  # 检查HTTP状态码
            
            response_data = json.loads(res.text)
            
            # 检查API响应状态
            if response_data.get('code') != 200:
                return "汇率转换失败", response_data.get('msg', '未知错误')
            
            data = response_data.get('data', {})
            
            # 构建汇率转换结果
            result = f"💱 汇率转换结果\n\n"
            result += f"📊 转换信息：\n"
            result += f"• 源货币：{from_currency.upper()}\n"
            result += f"• 目标货币：{to_currency.upper()}\n"
            result += f"• 转换金额：{amount}\n\n"
            
            result += f"💰 转换结果：\n"
            result += f"• {amount} {from_currency.upper()} = {data.get('result', 'N/A')} {to_currency.upper()}\n"
            result += f"• 汇率：1 {from_currency.upper()} = {data.get('rate', 'N/A')} {to_currency.upper()}\n\n"
            
            result += f"🕐 更新时间：{data.get('time', '未知')}"
            
            return "汇率转换成功：", result
            
        except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:
            print(f"汇率转换第{attempt + 1}次尝试失败: {str(e)}")
            if attempt < max_retries - 1:
                print(f"等待{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避策略
            else:
                print("所有重试尝试都失败了")
                return "获取汇率失败，请稍后再试", ""


if __name__ == '__main__':
    weibo_hot()