from gevent import monkey
monkey.patch_all()
import gevent
import soundfile
import struct
import json
import sys
import time
from websocket import create_connection
from auth_util import gen_sign_headers
from urllib import parse
NUM = 1


def read_wave_data(wav_path):
    wav_data, sample_rate = soundfile.read(wav_path, dtype='int16')
    return wav_data, sample_rate

def send_process(ws, wav_path):
    try:
        for i in range(NUM):
            wav_data, sample_rate = read_wave_data(wav_path)

            nlen = len(wav_data)
            nframes = nlen * 2
            pack_data = struct.pack('%dh' % nlen, *wav_data)
            wav_data_c = list(struct.unpack('B' * nframes, pack_data))

            cur_frames = 0
            sample_frames = 1280

            start_data = {
                "type": "started",
                "request_id": "req_id",
                "asr_info": {
                    "front_vad_time": 6000,
                    "end_vad_time": 2000,
                    "audio_type": "pcm",
                    "chinese2digital": 1,
                    "punctuation": 2,
                },
                "business_info": "{\"scenes_pkg\":\"com.tencent.qqlive\", \"editor_type\":\"3\", \"pro_id\":\"2addc42b7ae689dfdf1c63e220df52a2-2020\"}"
            }

            start_data_json_str = json.dumps(start_data)
            ws.send(start_data_json_str)

            while cur_frames < nframes:
                samp_remaining = nframes-cur_frames
                num_samp = sample_frames if sample_frames < samp_remaining else samp_remaining

                list_tmp = [None] * num_samp

                for j in range(num_samp):
                    list_tmp[j] = wav_data_c[cur_frames + j]

                pack_data_2 = struct.pack('%dB' % num_samp, *list_tmp)
                cur_frames += num_samp

                if len(pack_data_2) < 1280:
                    break

                ws.send_binary(pack_data_2)

                time.sleep(0.04)

            enddata = b'--end--'
            ws.send_binary(enddata)

        closedata = b'--close--'
        ws.send_binary(closedata)
    except Exception as e:
        error_info = traceback.format_exc()
        print(f"send_process 错误 - 文件: {__file__}, 函数: send_process, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
        print(f"详细错误信息:\n{error_info}")
        return

def recv_process(ws, tbegin, wav_path):
    index = 1
    cnt = 1
    first_world = 1
    first_world_time = 0

    while True:
        try:
            r = ws.recv()
            print(r)
            tmpobj = json.loads(r)

            if tmpobj["action"] == "error" or tmpobj["action"] == "vad":
                r = json.dumps(tmpobj)
                print("{}".format(r.encode('utf-8').decode('unicode_escape')))
                path = wav_path
                sid = tmpobj["sid"]
                code = tmpobj["code"]
                t3 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                print("{} {} {} {}".format(path, sid, code, t3))

            if tmpobj["action"] == "result":
                if tmpobj["type"] == "asr":
                    if first_world == 1:
                        if tmpobj["data"]["text"] != "":
                            tfirst = int(round(time.time() * 1000))
                            first_world = 0
                            first_world_time = tfirst - tbegin

                    if tmpobj["data"]["is_last"] is True:
                        r = json.dumps(tmpobj)
                        tend = int(round(time.time() * 1000))
                        path = wav_path
                        text = tmpobj["data"]["text"]
                        sid = tmpobj["sid"]
                        rid = tmpobj.get("request_id", "NULL")
                        code = tmpobj["code"]
                        t1 = first_world_time
                        t2 = tend - tbegin
                        t3 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        print("{}#{}#{}#{}#{}#{}#{}#{}".format(path, text, rid, sid, code, t1, t2, t3))
                        first_world = 1
                        tbegin = int(round(time.time() * 1000))
                        cnt = cnt + 1
                        if cnt > NUM:
                            return

        except Exception as e:
            error_info = traceback.format_exc()
            print(f"recv_process 错误 - 文件: {__file__}, 函数: recv_process, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
            print(f"详细错误信息:\n{error_info}")
            path = wav_path
            err = "exception"
            t3 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print("{} {} {}".format(path, err, t3))
            return


def control_process(wav_path):
    t = int(round(time.time() * 1000))

    params = {'client_version': parse.quote('unknown'), 'product': parse.quote('x'), 'package': parse.quote('unknown'),
              'sdk_version': parse.quote('unknown'), 'user_id': parse.quote('2addc42b7ae689dfdf1c63e220df52a2'),
              'android_version': parse.quote('unknown'), 'system_time': parse.quote(str(t)), 'net_type': 1,
              'engineid': "shortasrinput"}

    appid = 'your_app_id'
    appkey = 'your_app_key'
    uri = '/asr/v2'
    domain = 'api-ai.vivo.com.cn'

    headers = gen_sign_headers(appid, appkey, 'GET', uri, params)

    param_str = ''
    seq = ''

    for key, value in params.items():
        value = str(value)
        param_str = param_str + seq + key + '=' + value
        seq = '&'

    ws = create_connection('ws://' + domain + '/asr/v2?' + param_str, header=headers)
    co1 = gevent.spawn(send_process, ws, wav_path)
    co2 = gevent.spawn(recv_process, ws, t, wav_path)
    gevent.joinall([co1, co2])
    time.sleep(0.04)

# 全局变量存储STT识别结果
recognition_result = ""

def recv_process_stt(ws, tbegin):
    """专门用于STT的接收处理函数"""
    global recognition_result
    
    while True:
        try:
            r = ws.recv()
            print(f"STT接收: {r}")
            tmpobj = json.loads(r)
            
            if tmpobj["action"] == "error":
                print(f"STT错误: {tmpobj}")
                return
                
            if tmpobj["action"] == "result":
                if tmpobj["type"] == "asr":
                    if tmpobj["data"]["is_last"] is True:
                        recognition_result = tmpobj["data"]["text"]
                        print(f"STT识别结果: {recognition_result}")
                        return
                        
        except Exception as e:
            error_info = traceback.format_exc()
            print(f"STT接收处理错误 - 文件: {__file__}, 函数: recv_process_stt, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
            print(f"详细错误信息:\n{error_info}")
            return

def STT(audio_data):
    import tempfile
    import os
    import soundfile
    
    # 创建临时文件保存音频数据
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_file.write(audio_data)
        temp_wav_path = temp_file.name
    
    try:
        # 使用现有的语音识别流程
        t = int(round(time.time() * 1000))
        
        params = {
            'client_version': parse.quote('unknown'), 
            'product': parse.quote('x'), 
            'package': parse.quote('unknown'),
            'sdk_version': parse.quote('unknown'), 
            'user_id': parse.quote('2addc42b7ae689dfdf1c63e220df52a2'),
            'android_version': parse.quote('unknown'), 
            'system_time': parse.quote(str(t)), 
            'net_type': 1,
            'engineid': "shortasrinput"
        }
        
        appid = '2025881276'
        appkey = 'SUzaUkzFYhnDSYwM'
        uri = '/asr/v2'
        domain = 'api-ai.vivo.com.cn'
        
        headers = gen_sign_headers(appid, appkey, 'GET', uri, params)
        
        param_str = ''
        seq = ''
        
        for key, value in params.items():
            value = str(value)
            param_str = param_str + seq + key + '=' + value
            seq = '&'
        
        # 创建WebSocket连接
        ws = create_connection('ws://' + domain + '/asr/v2?' + param_str, header=headers)
        
        # 重置识别结果
        global recognition_result
        recognition_result = ""
        
        # 启动发送和接收协程
        co1 = gevent.spawn(send_process, ws, temp_wav_path)
        co2 = gevent.spawn(recv_process_stt, ws, t)
        gevent.joinall([co1, co2])
        
        # 关闭WebSocket连接
        ws.close()
        
        return recognition_result
        
    except Exception as e:
        error_info = traceback.format_exc()
        print(f"STT错误 - 文件: {__file__}, 函数: STT, 行号: {traceback.extract_tb(e.__traceback__)[-1].lineno}, 错误: {str(e)}")
        print(f"详细错误信息:\n{error_info}")
        return ""
    finally:
        # 清理临时文件
        if os.path.exists(temp_wav_path):
            os.unlink(temp_wav_path)

def main():
    if len(sys.argv) < 2:
        print('usage :  python %s conf' % sys.argv[0])
        print('example: python %s %s' % (sys.argv[0], 'audio.conf'))
        sys.exit(1)
    else:
        config = sys.argv[1]

    with open(config, 'rt') as f:
        line = f.readline().strip()

    coro = []
    t = gevent.spawn(control_process, line)
    coro.append(t)
    gevent.joinall(coro)


if __name__ == "__main__":
    main()
