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
        # 火山引擎视频生成API端点（异步接口）
        self.api_url = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
        self.query_url = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
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
        model: str = "doubao-seedance-1-0-pro-250528"
    ) -> dict:
        """
        生成视频（异步接口：创建任务 → 轮询查询 → 下载）

        Args:
            prompt (str): 文本提示词
            image_url (str, optional): 图片URL，如提供则为图生视频
            duration (str): 视频时长，可选 "5s" 或 "10s"
            resolution (str): 分辨率，可选 "480p" 或 "720p" 或 "1080p"
            model (str): 模型名称，默认 doubao-seedance-1-0-pro-250528

        Returns:
            dict: {
                'success': bool,
                'video_url': str,    # 生成的视频URL
                'video_path': str,   # 下载后的本地路径
                'task_id': str,      # 任务ID
                'error': str         # 错误信息（如果失败）
            }
        """
        try:
            logger.info(f"🎬 火山引擎Seedance开始生成视频: prompt='{prompt[:50]}...'")
            if image_url:
                logger.info(f"📷 使用参考图片: {image_url}")

            # 步骤1: 创建视频生成任务
            logger.info(f"📤 创建视频生成任务...")

            # 构建请求体（根据火山引擎API文档）
            # content参数必须是数组格式，包含text和/或image_url对象
            content = [
                {
                    "type": "text",
                    "text": f"{prompt[:800]} --duration {duration.replace('s', '')} --ratio adaptive --rs {resolution}"
                }
            ]

            # 如果提供了图片URL，添加到content数组
            if image_url:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                })

            payload = {
                "model": model,
                "content": content
            }

            # 创建任务
            response = requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )

            if response.status_code != 200:
                error_msg = f"创建任务失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            task_result = response.json()
            logger.info(f"📥 任务创建响应: {task_result}")

            # 检查是否有错误
            if 'error' in task_result:
                error_msg = f"API返回错误: {task_result['error'].get('message', '未知错误')}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            # 提取任务ID（API返回的是id字段）
            task_id = task_result.get('id') or task_result.get('task_id') or task_result.get('data', {}).get('id')

            if not task_id:
                error_msg = f"未获取到任务ID: {task_result}"
                logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

            logger.info(f"✅ 任务已创建: {task_id}")

            # 步骤2: 轮询查询任务状态
            logger.info(f"⏳ 开始轮询任务状态...")
            video_url = self._poll_task_status(task_id)

            if not video_url:
                return {
                    'success': False,
                    'error': '任务超时或失败'
                }

            # 步骤3: 下载视频
            video_path = self._download_video(video_url)

            logger.info(f"✅ Seedance视频生成成功: {video_path}")
            return {
                'success': True,
                'video_url': video_url,
                'video_path': video_path,
                'task_id': task_id
            }

        except requests.Timeout:
            error_msg = "视频生成API请求超时"
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

    def _poll_task_status(self, task_id: str, max_wait: int = 120) -> Optional[str]:
        """
        轮询查询任务状态，直到完成或超时

        Args:
            task_id: 任务ID
            max_wait: 最大等待时间（秒）

        Returns:
            str: 视频URL，失败返回None
        """
        start_time = time.time()
        poll_interval = 5  # 每5秒查询一次

        while time.time() - start_time < max_wait:
            try:
                # 查询任务状态
                query_url = f"{self.query_url}/{task_id}"
                logger.info(f"🔍 查询URL: {query_url}")
                response = requests.get(
                    query_url,
                    headers=self.headers,
                    timeout=10
                )

                logger.info(f"📡 HTTP状态码: {response.status_code}")
                if response.status_code != 200:
                    logger.warning(f"查询任务状态失败: {response.status_code} - {response.text}")
                    time.sleep(poll_interval)
                    continue

                result = response.json()
                logger.info(f"📥 轮询响应: {result}")

                # API返回格式: {"id": "...", "status": "...", "video": {"url": "..."}}
                status = result.get('status')

                logger.info(f"📊 任务状态: {status}")

                if status == 'completed':
                    # 任务完成，提取视频URL
                    video_data = result.get('video', {})
                    video_url = video_data.get('url')
                    if video_url:
                        logger.info(f"✅ 任务完成，获得视频URL")
                        return video_url
                    else:
                        logger.error(f"❌ 任务完成但未找到视频URL: {result}")
                        return None
                elif status == 'failed':
                    # 任务失败
                    error_msg = result.get('error', {}).get('message', '未知错误')
                    logger.error(f"❌ 任务失败: {error_msg}")
                    return None
                else:
                    # 任务进行中（queued, generating等），继续等待
                    elapsed = int(time.time() - start_time)
                    logger.info(f"⏳ 任务状态: {status} ({elapsed}s/{max_wait}s)")
                    time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"查询任务异常: {e}")
                time.sleep(poll_interval)

        logger.error(f"❌ 任务超时（{max_wait}秒）")
        return None

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
