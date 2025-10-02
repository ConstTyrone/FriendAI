# seedream_video_service.py
"""
火山引擎 Seedance-1.0-pro 视频生成服务
API文档: https://www.volcengine.com/docs/82379/1366800
模型: doubao-seedance-1.0-pro
支持文本生成视频和图片生成视频
"""
import os
import time
import requests
import logging
from typing import Optional
from ..config.config import config

logger = logging.getLogger(__name__)

class SeeDreamVideoService:
    """火山引擎 Seedance 视频生成服务"""

    def __init__(self):
        # 复用SeeDream的API Key
        self.api_key = config.seedream_api_key
        # 火山引擎视频生成API端点
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/contents/generations"
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def generate_video(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        duration: str = "5s",
        resolution: str = "720p",
        model: str = "doubao-seedance-1.0-pro"
    ) -> dict:
        """
        生成视频（支持文本生成视频和图片生成视频）

        Args:
            prompt (str): 文本提示词
            image_url (str, optional): 图片URL，如提供则为图生视频
            duration (str): 视频时长，可选 "5s" 或 "10s"
            resolution (str): 分辨率，可选 "480p" 或 "720p"
            model (str): 模型名称，默认 doubao-seedance-1.0-pro

        Returns:
            dict: {
                'success': bool,
                'video_url': str,    # 生成的视频URL
                'video_path': str,   # 下载后的本地路径
                'error': str         # 错误信息（如果失败）
            }
        """
        try:
            logger.info(f"🎬 火山引擎Seedance开始生成视频: prompt='{prompt[:50]}...'")
            if image_url:
                logger.info(f"📷 使用参考图片: {image_url}")

            # 构建请求体
            payload = {
                "model": model,
                "content_generation_request": {
                    "text": prompt[:800],  # 限制最大长度
                    "duration": duration,
                    "resolution": resolution
                }
            }

            # 如果提供了图片URL，添加图片参数
            if image_url:
                payload["content_generation_request"]["image_url"] = image_url

            # 调用API（同步接口）
            logger.info(f"📤 发送请求到火山引擎...")
            response = requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=120  # 视频生成需要更长时间
            )

            if response.status_code != 200:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            result = response.json()
            logger.info(f"📥 Seedance API响应: status_code={response.status_code}")

            # 检查是否有错误
            if 'error' in result:
                error_msg = f"API返回错误: {result['error'].get('message', '未知错误')}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            # 提取视频URL
            # Seedance返回格式可能是: {"data": {"video_url": "http://..."}} 或类似结构
            video_url = None
            if 'data' in result:
                video_url = result['data'].get('video_url') or result['data'].get('url')
            elif 'video_url' in result:
                video_url = result['video_url']

            if video_url:
                # 下载视频到本地
                video_path = self._download_video(video_url)

                logger.info(f"✅ Seedance视频生成成功: {video_path}")
                return {
                    'success': True,
                    'video_url': video_url,
                    'video_path': video_path
                }

            # 如果没有找到视频URL
            error_msg = f"API未返回视频URL: {result}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

        except requests.Timeout:
            error_msg = "视频生成API请求超时（120秒）"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"视频生成异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }

    def _download_video(self, video_url: str) -> str:
        """
        下载视频到本地

        Args:
            video_url: 视频URL

        Returns:
            str: 本地文件路径
        """
        try:
            # 确保临时目录存在
            temp_dir = "data/temp_videos"
            os.makedirs(temp_dir, exist_ok=True)

            # 生成文件名
            timestamp = int(time.time() * 1000)
            filename = f"seedance_video_{timestamp}.mp4"
            filepath = os.path.join(temp_dir, filename)

            # 下载视频
            logger.info(f"⬇️ 开始下载视频...")
            response = requests.get(video_url, timeout=60, stream=True)
            response.raise_for_status()

            # 保存到本地（流式下载）
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            logger.info(f"💾 视频已下载: {filepath} ({file_size_mb:.2f} MB)")
            return filepath

        except Exception as e:
            logger.error(f"下载视频失败: {e}", exc_info=True)
            # 下载失败时返回临时占位路径
            return f"download_failed_{int(time.time())}.mp4"

    def convert_video_to_gif(self, video_path: str, output_path: Optional[str] = None) -> dict:
        """
        将视频转换为GIF（使用FFmpeg）

        Args:
            video_path: 视频文件路径
            output_path: 输出GIF路径（可选）

        Returns:
            dict: {
                'success': bool,
                'gif_path': str,     # GIF文件路径
                'error': str         # 错误信息（如果失败）
            }
        """
        try:
            import subprocess

            if not os.path.exists(video_path):
                return {
                    'success': False,
                    'error': f"视频文件不存在: {video_path}"
                }

            # 生成输出路径
            if not output_path:
                video_dir = os.path.dirname(video_path)
                video_basename = os.path.splitext(os.path.basename(video_path))[0]
                output_path = os.path.join(video_dir, f"{video_basename}.gif")

            # 检查FFmpeg是否可用
            ffmpeg_path = config.ffmpeg_path

            # 构建FFmpeg命令
            # 参数说明：
            # -i: 输入文件
            # -vf: 视频过滤器
            #   fps=10: 设置帧率为10fps（减小文件大小）
            #   scale=480:-1: 宽度480px，高度自适应
            # -loop 0: 无限循环
            cmd = [
                ffmpeg_path,
                '-i', video_path,
                '-vf', 'fps=10,scale=480:-1:flags=lanczos',
                '-loop', '0',
                '-y',  # 覆盖输出文件
                output_path
            ]

            logger.info(f"🔄 开始转换视频到GIF: {video_path} -> {output_path}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                error_msg = f"FFmpeg转换失败: {result.stderr}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            if os.path.exists(output_path):
                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"✅ GIF转换成功: {output_path} ({file_size_mb:.2f} MB)")
                return {
                    'success': True,
                    'gif_path': output_path
                }
            else:
                return {
                    'success': False,
                    'error': "GIF文件生成失败"
                }

        except FileNotFoundError:
            error_msg = "FFmpeg未安装或路径配置错误"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except subprocess.TimeoutExpired:
            error_msg = "视频转GIF超时（60秒）"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"视频转GIF异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }

    def generate_animated_emoticon(self, prompt: str) -> dict:
        """
        一键生成动态表情包（视频→GIF流程）

        Args:
            prompt: 表情包描述

        Returns:
            dict: {
                'success': bool,
                'video_path': str,   # 视频文件路径
                'gif_path': str,     # GIF文件路径
                'error': str         # 错误信息（如果失败）
            }
        """
        try:
            logger.info(f"🎭 开始生成动态表情包: {prompt}")

            # 步骤1: 生成视频
            video_result = self.generate_video(
                prompt=prompt,
                duration="5s",  # 表情包用5秒足够
                resolution="720p"
            )

            if not video_result.get('success', False):
                return {
                    'success': False,
                    'error': f"视频生成失败: {video_result.get('error', '未知错误')}"
                }

            video_path = video_result.get('video_path', '')

            # 步骤2: 转换为GIF
            gif_result = self.convert_video_to_gif(video_path)

            if not gif_result.get('success', False):
                return {
                    'success': False,
                    'video_path': video_path,  # 即使GIF失败，也返回视频
                    'error': f"GIF转换失败: {gif_result.get('error', '未知错误')}"
                }

            logger.info(f"✅ 动态表情包生成成功")
            return {
                'success': True,
                'video_path': video_path,
                'gif_path': gif_result.get('gif_path', ''),
                'video_url': video_result.get('video_url', '')
            }

        except Exception as e:
            error_msg = f"动态表情包生成异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }


# 创建全局火山引擎视频生成服务实例
seedream_video_service = SeeDreamVideoService()
