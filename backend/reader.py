import time
import pyaudio
import dashscope
import base64
import io
import numpy as np
from dashscope.api_entities.dashscope_response import SpeechSynthesisResponse
from dashscope.audio.tts_v2 import *
from flask import Response, stream_with_context

from datetime import datetime

def get_timestamp():
    now = datetime.now()
    formatted_timestamp = now.strftime("[%Y-%m-%d %H:%M:%S.%f]")
    return formatted_timestamp

# 若没有将API Key配置到环境变量中，需将your-api-key替换为自己的API Key
dashscope.api_key = "sk-6a259a1064144086be0e11e5903c1d49"

model = "cosyvoice-v1"
voice = "longxiaochun"


class Callback(ResultCallback):
    _player = None
    _stream = None

    def on_open(self):
        print("websocket is open.")
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16, channels=1, rate=22050, output=True
        )

    def on_complete(self):
        print(get_timestamp() + " speech synthesis task complete successfully.")

    def on_error(self, message: str):
        print(f"speech synthesis task failed, {message}")

    def on_close(self):
        print(get_timestamp() + " websocket is closed.")
        # 停止播放器
        self._stream.stop_stream()
        self._stream.close()
        self._player.terminate()

    def on_event(self, message):
        pass

    def on_data(self, data: bytes) -> None:
        print(get_timestamp() + " audio result length: " + str(len(data)))
        self._stream.write(data)


class WebCallback(ResultCallback):
    """用于Web流式传输的回调类"""
    def __init__(self):
        self.audio_chunks = []
        self.is_complete = False
        self.error_message = None

    def on_open(self):
        print("Web音频合成开始")
        self.audio_chunks = []
        self.is_complete = False
        self.error_message = None

    def on_complete(self):
        print(get_timestamp() + " Web音频合成完成")
        self.is_complete = True

    def on_error(self, message: str):
        print(f"Web音频合成失败: {message}")
        self.error_message = message

    def on_close(self):
        print(get_timestamp() + " Web音频合成连接关闭")

    def on_event(self, message):
        pass

    def on_data(self, data: bytes) -> None:
        print(get_timestamp() + " Web音频数据长度: " + str(len(data)))
        # 将音频数据转换为Base64编码，以便通过HTTP传输
        encoded_data = base64.b64encode(data).decode('utf-8')
        self.audio_chunks.append(encoded_data)

callback = Callback()
web_callback = WebCallback()

synthesizer = SpeechSynthesizer(
    model=model,
    voice=voice,
    format=AudioFormat.PCM_22050HZ_MONO_16BIT,  
    callback=callback,
)

web_synthesizer = SpeechSynthesizer(
    model=model,
    voice=voice,
    format=AudioFormat.PCM_22050HZ_MONO_16BIT,  
    callback=web_callback,
)

def text_to_speech_stream(text):
    """将文本转换为语音并以流式方式返回"""
    # 重置回调状态
    web_callback.on_open()
    
    # 调用语音合成
    web_synthesizer.streaming_call(text)
    
    # 生成器函数，用于流式传输音频数据
    def generate():
        # 发送已有的音频块
        for chunk in web_callback.audio_chunks:
            yield f"data: {chunk}\n\n"
            web_callback.audio_chunks = web_callback.audio_chunks[1:]
        
        # 等待新的音频块或完成信号
        while not web_callback.is_complete and web_callback.error_message is None:
            if web_callback.audio_chunks:
                chunk = web_callback.audio_chunks[0]
                web_callback.audio_chunks = web_callback.audio_chunks[1:]
                yield f"data: {chunk}\n\n"
            else:
                time.sleep(0.1)  # 短暂等待新数据
        
        # 发送完成信号
        if web_callback.is_complete:
            yield f"data: [audio_complete]\n\n"
        elif web_callback.error_message:
            yield f"data: [audio_error]{web_callback.error_message}\n\n"
    
    # 完成流式合成
    web_synthesizer.streaming_complete()
    
    return Response(stream_with_context(generate()), 
                   content_type='text/event-stream',
                   headers={
                       'Cache-Control': 'no-cache',
                       'X-Accel-Buffering': 'no'
                   })