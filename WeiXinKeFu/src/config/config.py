# config.py
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env.test file for testing
load_dotenv(".env.test")
load_dotenv()

@dataclass
class WeWorkConfig:
    corp_id: str = os.getenv('WEWORK_CORP_ID')
    agent_id: str = os.getenv('WEWORK_AGENT_ID')
    secret: str = os.getenv('WEWORK_SECRET')
    token: str = os.getenv('WEWORK_TOKEN')
    encoding_aes_key: str = os.getenv('WEWORK_AES_KEY')
    local_server_port: int = int(os.getenv('LOCAL_SERVER_PORT', 3001))
    # 通义千问API配置
    qwen_api_key: str = os.getenv('QWEN_API_KEY')
    qwen_api_endpoint: str = os.getenv('QWEN_API_ENDPOINT', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    # 阿里云ASR配置
    asr_appkey: str = os.getenv('ASR_APPKEY', 'NM5zdrGkIl8xqSzO')  # 默认值来自文档
    asr_token: str = os.getenv('ASR_TOKEN', 'be3d7dfd4e51401db4c122e2d74b06ba')  # 默认值来自文档
    asr_url: str = os.getenv('ASR_URL', 'wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1')
    # ffmpeg路径配置
    ffmpeg_path: str = os.getenv('FFMPEG_PATH', r'D:\software\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe')  # 使用用户指定的路径
    
    # 微信小程序配置
    wechat_mini_appid: str = os.getenv('WECHAT_MINI_APPID', 'wx50fc05960f4152a6')  # 你提供的AppID
    wechat_mini_secret: str = os.getenv('WECHAT_MINI_SECRET', '')  # 需要在环境变量中设置

config = WeWorkConfig()