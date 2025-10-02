# seedream_image_service.py
"""
火山引擎 SeeDream-4 图片生成服务
API文档: https://www.volcengine.com/docs/82379/1541523
模型: doubao-seedream-4-0
"""
import os
import time
import requests
import logging
from typing import Optional
from ..config.config import config

logger = logging.getLogger(__name__)

class SeeDreamImageService:
    """火山引擎 SeeDream-4 图片生成服务"""

    def __init__(self):
        # 火山引擎API配置
        self.api_key = os.getenv('SEEDREAM_API_KEY', '4f3d9b80-3a62-4ef8-9902-5d6742113c91')
        # 火山引擎图片生成API端点
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def generate_image(
        self,
        prompt: str,
        model: str = "doubao-seedream-4-0",
        size: str = "1024x1024",
        n: int = 1
    ) -> dict:
        """
        生成图片

        Args:
            prompt (str): 文本提示词
            model (str): 模型名称，默认 doubao-seedream-4-0
            size (str): 图片尺寸，支持：
                - "1024x1024" (默认)
                - "2048x2048" (2K)
                - "4096x4096" (4K，需要额外配置)
            n (int): 生成图片数量，默认1

        Returns:
            dict: {
                'success': bool,
                'image_url': str,   # 生成的图片URL
                'image_path': str,  # 下载后的本地路径
                'error': str        # 错误信息（如果失败）
            }
        """
        try:
            logger.info(f"🎨 火山引擎SeeDream开始生成图片: prompt='{prompt[:50]}...'")

            # 构建请求体
            payload = {
                "model": model,
                "prompt": prompt[:800],  # 限制最大长度
                "size": size,
                "n": n
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
            # 记录响应状态，不输出完整响应（避免base64数据污染日志）
            logger.info(f"📥 SeeDream API响应: status_code={response.status_code}, has_data={('data' in result)}")

            # 检查是否有错误
            if 'error' in result:
                error_msg = f"API返回错误: {result['error'].get('message', '未知错误')}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            # 提取图片URL
            if 'data' in result and len(result['data']) > 0:
                # SeeDream返回格式: {"data": [{"url": "http://..."}]}
                image_url = result['data'][0].get('url', '')

                if image_url:
                    # 下载图片到本地
                    image_path = self._download_image(image_url)

                    logger.info(f"✅ SeeDream图片生成成功: {image_path}")
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
            image_url: 图片URL

        Returns:
            str: 本地文件路径
        """
        try:
            # 确保临时目录存在
            temp_dir = "data/temp_images"
            os.makedirs(temp_dir, exist_ok=True)

            # 生成文件名
            timestamp = int(time.time() * 1000)
            filename = f"seedream_generated_{timestamp}.png"
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


# 创建全局火山引擎图片生成服务实例
seedream_image_service = SeeDreamImageService()
