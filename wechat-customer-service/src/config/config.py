# config.py
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """配置管理类"""

    def __init__(self):
        # 微信客服/企业微信配置
        self.corp_id = os.getenv('WEWORK_CORP_ID')
        self.secret = os.getenv('WEWORK_SECRET')
        self.token = os.getenv('WEWORK_TOKEN')
        self.encoding_aes_key = os.getenv('WEWORK_AES_KEY')

        # AI服务配置
        self.qwen_api_key = os.getenv('QWEN_API_KEY')
        self.qwen_api_endpoint = os.getenv('QWEN_API_ENDPOINT', 'https://dashscope.aliyuncs.com/compatible-mode/v1')

        # 图片生成服务配置（用于表情包生成）
        self.image_api_url = os.getenv('IMAGE_API_URL', 'https://genaiapi.cloudsway.net/v1/ai/hiMUPFhuWCQtVMpp/chat/completions')
        self.image_api_token = os.getenv('IMAGE_API_TOKEN', '405O8mEjMUXeJlht83JA')

        # 火山引擎 SeeDream 配置
        self.seedream_api_key = os.getenv('SEEDREAM_API_KEY', '4f3d9b80-3a62-4ef8-9902-5d6742113c91')

        # 表情包服务配置
        self.emoticon_enabled = os.getenv('EMOTICON_ENABLED', 'true').lower() == 'true'  # 是否启用表情包功能

        # 数据库配置
        self.database_path = os.getenv('DATABASE_PATH', 'wechat_profiles.db')

        # 服务器配置
        self.local_server_port = int(os.getenv('LOCAL_SERVER_PORT', '3001'))
        self.environment = os.getenv('ENVIRONMENT', 'development')

        # 语音识别配置（可选）
        self.asr_appkey = os.getenv('ASR_APPKEY', 'NM5zdrGkIl8xqSzO')  # 预配置AppKey
        self.asr_token = os.getenv('ASR_TOKEN', 'be3d7dfd4e51401db4c122e2d74b06ba')  # 手动Token（向后兼容）
        self.asr_url = os.getenv('ASR_URL', 'wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1')

        # 阿里云AccessKey配置（用于自动获取ASR Token）
        # 支持多种环境变量命名方式
        self.aliyun_ak_id = os.getenv('ALIYUN_AK_ID') or os.getenv('accessKeyId')
        self.aliyun_ak_secret = os.getenv('ALIYUN_AK_SECRET') or os.getenv('accessKeySecret')

        # FFmpeg配置（可选）
        self.ffmpeg_path = os.getenv('FFMPEG_PATH', 'ffmpeg')

        # Redis配置（用于状态管理和消息去重）
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        self.redis_db = int(os.getenv('REDIS_DB', '0'))
        self.redis_password = os.getenv('REDIS_PASSWORD', None)

        # ETL4LM服务配置（预配置）
        self.etl_base_url = os.getenv('ETL_BASE_URL', 'http://110.16.193.170:50103')
        self.etl_predict_endpoint = os.getenv('ETL_PREDICT_ENDPOINT', '/v1/etl4llm/predict')

        self._validate_config()

    def _validate_config(self):
        """验证必需的配置项"""
        required_configs = {
            'WEWORK_CORP_ID': self.corp_id,
            'WEWORK_SECRET': self.secret,
            'WEWORK_TOKEN': self.token,
            'WEWORK_AES_KEY': self.encoding_aes_key,
            'QWEN_API_KEY': self.qwen_api_key
        }

        missing_configs = [key for key, value in required_configs.items() if not value]

        if missing_configs:
            raise ValueError(f"缺少必需的环境变量配置: {', '.join(missing_configs)}")

# 创建全局配置实例
config = Config()