from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# 初始化阿里云DashScope客户端
client = OpenAI(
    api_key="sk-6a259a1064144086be0e11e5903c1d49",
    base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'
)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({"error": "消息不能为空"}), 400
        
        # 调用大模型API
        response = call_llm_api(user_message)
        
        return jsonify({"response": response})
    
    except Exception as e:
        print(f"错误: {str(e)}")
        return jsonify({"error": "服务器内部错误"}), 500

def call_llm_api(message):
    try:
        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {'role': 'system', 'content': '你是一个有帮助的助手。'},
                {'role': 'user', 'content': message}
            ]
        )
        return completion.choices[0].message.content
    
    except Exception as e:
        print(f"API调用错误: {str(e)}")
        return f"抱歉，处理您的请求时出现了问题。{str(e)}"

if __name__ == '__main__':
    app.run(debug=True, port=5000)