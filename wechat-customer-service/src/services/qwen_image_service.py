# qwen_image_service.py
"""
阿里云通义千问图片生成服务 - Qwen-Image-Plus 模型
API文档: https://help.aliyun.com/zh/model-studio/developer-reference/qwen-image-api
"""
import os
import time
import requests
import logging
from typing import Optional
from ..config.config import config

logger = logging.getLogger(__name__)

class QwenImageService:
    """阿里云通义千问图片生成服务"""

    def __init__(self):
        self.api_key = config.qwen_api_key
        # 使用北京地域的多模态生成接口
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def generate_image(
        self,
        prompt: str,
        size: str = "1328*1328",
        watermark: bool = False,
        prompt_extend: bool = True
    ) -> dict:
        """
        生成图片（同步接口）

        Args:
            prompt (str): 文本提示词（最多800字符）
            size (str): 图片分辨率，可选：
                - "1664*928" (16:9)
                - "1472*1140" (4:3)
                - "1328*1328" (1:1，默认)
                - "1140*1472" (3:4)
                - "928*1664" (9:16)
            watermark (bool): 是否添加水印（右下角"Qwen-Image生成"）
            prompt_extend (bool): 是否开启prompt智能改写

        Returns:
            dict: {
                'success': bool,
                'image_url': str,   # 生成的图片URL（24小时有效）
                'image_path': str,  # 下载后的本地路径
                'error': str        # 错误信息（如果失败）
            }
        """
        try:
            logger.info(f"🎨 阿里云通义千问开始生成图片: prompt='{prompt[:50]}...'")

            # 构建请求体
            payload = {
                "model": "qwen-image-plus",
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"text": prompt[:800]}  # 限制最大长度
                            ]
                        }
                    ]
                },
                "parameters": {
                    "size": size,
                    "watermark": watermark,
                    "prompt_extend": prompt_extend,
                    "n": 1
                }
            }

            # 调用API
            response = requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=60
            )

            if response.status_code != 200:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            result = response.json()
            logger.info(f"📥 API响应: {result}")

            # 检查是否有错误
            if 'code' in result and result['code']:
                error_msg = f"API返回错误: {result.get('code')} - {result.get('message', '未知错误')}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            # 提取图片URL
            if 'output' in result and 'choices' in result['output']:
                choices = result['output']['choices']
                if choices and len(choices) > 0:
                    message = choices[0].get('message', {})
                    content = message.get('content', [])

                    if content and len(content) > 0:
                        image_url = content[0].get('image', '')

                        if image_url:
                            # 下载图片到本地
                            image_path = self._download_image(image_url)

                            logger.info(f"✅ 阿里云图片生成成功: {image_path}")
                            return {
                                'success': True,
                                'image_url': image_url,
                                'image_path': image_path
                            }

            # 如果没有找到图片
            error_msg = "API未返回生成的图片"
            logger.error(f"{error_msg}: {result}")
            return {
                'success': False,
                'error': error_msg
            }

        except requests.Timeout:
            error_msg = "图片生成API请求超时"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"图片生成异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }

    def _download_image(self, image_url: str) -> str:
        """
        下载图片到本地

        Args:
            image_url: 图片URL（24小时有效）

        Returns:
            str: 本地文件路径
        """
        try:
            # 确保临时目录存在
            temp_dir = "data/temp_images"
            os.makedirs(temp_dir, exist_ok=True)

            # 生成文件名
            timestamp = int(time.time() * 1000)
            filename = f"qwen_generated_{timestamp}.png"
            filepath = os.path.join(temp_dir, filename)

            # 下载图片
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            # 保存到本地
            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"💾 图片已下载: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"下载图片失败: {e}", exc_info=True)
            # 下载失败时返回临时占位路径
            return f"download_failed_{int(time.time())}.png"


# 创建全局阿里云图片生成服务实例
qwen_image_service = QwenImageService()
