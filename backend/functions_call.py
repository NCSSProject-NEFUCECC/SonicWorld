import json
import random

import re

def handle_function_call(llm_msg):
    print("LLM输出的函数调用是：",llm_msg)
    match = re.search(r"<APIs>(.*?)</APIs>", llm_msg, re.DOTALL)
    if match:
        api_str = match.group(1).strip()
    else:
        return "Error: <APIs> tags not found or malformed."
    print("清理后的函数调用是：",api_str)
    try:
        api_list = json.loads(api_str)
        for api_call in api_list:
            function_name = api_call.get("name")
            parameters = api_call.get("parameters", {})
            if function_name == "test":
                return test(**parameters)
            else:
                return f"Unknown function: {function_name}"
    except json.JSONDecodeError:
        return "Error: Invalid JSON format in API call."
    return "No API call detected."

def test():
    return f"Function Call测试成功！本次测试id:{random.random()}。你需要将这个数字告诉用户"