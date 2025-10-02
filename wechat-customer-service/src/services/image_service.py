# image_service.py
"""
图片生成服务 - 使用 Gemini 2.5 Flash Image Preview 模型
支持文本生图和图生图功能
"""
import base64
import os
import tempfile
import time
import requests
import logging
from typing import Optional, List
from ..config.config import config

logger = logging.getLogger(__name__)

class ImageGenerationService:
    """图片生成服务"""

    def __init__(self):
        self.api_url = config.image_api_url
        self.api_token = config.image_api_token
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }

    def generate_image(
        self,
        prompt: str,
        base_image_path: Optional[str] = None,
        image_urls: Optional[List[str]] = None
    ) -> dict:
        """
        生成图片

        Args:
            prompt (str): 文本提示词
            base_image_path (str): 本地图片路径，用于图生图（可选）
            image_urls (list): 图片URL列表，用于图生图（可选）

        Returns:
            dict: {
                'success': bool,
                'image_path': str,  # 生成的图片本地路径
                'error': str        # 错误信息（如果失败）
            }
        """
        try:
            logger.info(f"🎨 开始生成图片: prompt='{prompt[:50]}...'")

            # 构建消息
            messages = self._build_messages(prompt, base_image_path, image_urls)

            # 调用API
            payload = {
                "model": "gemini-2.5-flash-image-preview",
                "temperature": 0,
                "stream": False,
                "messages": messages
            }

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
            # 记录响应状态，不输出完整响应（避免base64图片数据污染日志）
            logger.info(f"📥 Gemini API响应: status_code={response.status_code}, has_choices={('choices' in result)}")

            # 提取生成的图片
            if 'choices' in result and len(result['choices']) > 0:
                images = result['choices'][0]['message'].get('images', [])

                if images and len(images) > 0:
                    image_url = images[0]['image_url']['url']
                    base64_image = image_url.split(";base64,")[1]

                    # 保存图片到临时文件
                    image_path = self._save_image(base64_image)

                    logger.info(f"✅ 图片生成成功: {image_path}")
                    return {
                        'success': True,
                        'image_path': image_path
                    }
                else:
                    error_msg = "API未返回生成的图片"
                    logger.error(f"{error_msg}: {result}")
                    return {
                        'success': False,
                        'error': error_msg
                    }
            else:
                error_msg = "API返回格式错误"
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

    def _build_messages(self, prompt: str, base_image_path: Optional[str], image_urls: Optional[List[str]]) -> list:
        """构建API请求消息"""
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]

        # 处理本地图片文件
        if base_image_path and os.path.exists(base_image_path):
            try:
                with open(base_image_path, "rb") as f:
                    suffix = os.path.splitext(base_image_path)[1].lstrip('.')
                    image_data = f.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    base64_image = f"data:image/{suffix};base64,{base64_image}"
                    messages[0]["content"].append({
                        "type": "image_url",
                        "image_url": {"url": base64_image}
                    })
                    logger.info(f"📎 添加本地图片: {base_image_path}")
            except Exception as e:
                logger.error(f"读取本地图片失败: {e}")

        # 处理图片URL列表
        if image_urls:
            for url in image_urls:
                if url:
                    messages[0]["content"].append({
                        "type": "image_url",
                        "image_url": {"url": url}
                    })
                    logger.info(f"🔗 添加图片URL: {url}")

        return messages

    def _save_image(self, base64_image: str) -> str:
        """保存base64图片到临时文件"""
        # 确保临时目录存在
        temp_dir = "data/temp_images"
        os.makedirs(temp_dir, exist_ok=True)

        # 生成文件名
        timestamp = int(time.time() * 1000)
        filename = f"generated_{timestamp}.png"
        filepath = os.path.join(temp_dir, filename)

        # 解码并保存
        image_bytes = base64.b64decode(base64_image)
        with open(filepath, 'wb') as f:
            f.write(image_bytes)

        logger.info(f"💾 图片已保存: {filepath}")
        return filepath

# 创建全局图片生成服务实例
image_service = ImageGenerationService()
