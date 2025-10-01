# emoticon_service.py
"""
表情包生成服务 - 智能识别情绪并生成可爱表情包
触发方式：关键词"表情包"
风格：AI自由发挥，Q版卡通可爱风格
"""
import re
import json
import logging
from typing import Optional, Dict
from .ai_service import chat_service
from .image_service import image_service
from ..config.config import config

logger = logging.getLogger(__name__)

# 表情包关键词
EMOTICON_KEYWORDS = ['表情包', '/表情包', '来个表情包', '生成表情包']

# 表情包生成系统提示词
EMOTICON_SYSTEM_PROMPT = """你是一个专业的表情包设计师。根据用户提供的情绪或场景描述，生成详细的图片描述用于AI绘画。

**风格要求**：
- Q版卡通风格，可爱萌系
- 角色可以自由选择（小猫、小狗、小熊、小兔子、小鸟等可爱动物）
- 表情和动作要夸张生动，符合表情包特点
- 纯色或简单渐变背景，不要复杂场景
- 居中构图，主体占画面70%以上
- **必须包含文字标注**：在角色旁边或上方添加简短的中文文字（2-4个字）

**回复要求**：
请直接返回图片描述prompt，不要有多余解释。描述要详细具体，包含：
1. 角色外形（什么动物，什么颜色）
2. 表情细节（眼睛、嘴巴、整体神态）
3. 动作姿态（在做什么）
4. **文字标注**（必须！用简短的中文词语，放在显眼位置）
5. 特效元素（星星、汗滴、爱心等，可选）
6. 背景和风格

示例输入："开心"
示例输出："一只圆滚滚的黄色小鸭子，眼睛弯成月牙形，嘴巴张开露出开心的笑容，双翅膀向上扬起，身体微微跳跃离开地面，角色上方有白色粗体中文文字"好开心"，周围有闪亮的小星星特效，纯白色背景，Q版卡通风格，可爱萌系，表情包风格"

示例输入："疲惫"
示例输出："一只灰色的小考拉趴在地上，眼睛半闭呈困倦状，舌头微微吐出，四肢完全摊开呈大字型，身体像融化一样贴在地面，角色旁边有白色粗体中文文字"累瘫了"，头上有三条向下的汗滴，淡蓝色渐变背景，Q版卡通风格，可爱萌系，表情包风格"

示例输入："加油"
示例输出："一只橘色小猫咪举起双手握拳，眼睛炯炯有神，嘴巴微笑露出小虎牙，身体挺直充满力量感，角色上方有黄色粗体中文文字"加油！"，周围有能量光芒特效，纯白色背景，Q版卡通风格，可爱萌系，表情包风格"

现在请根据用户的输入生成表情包描述。"""


class EmoticonService:
    """表情包生成服务"""

    def __init__(self):
        pass

    def detect_emoticon_request(self, text: str) -> bool:
        """
        检测是否为表情包生成请求

        Args:
            text: 用户输入文本

        Returns:
            bool: 是否包含表情包关键词
        """
        return any(keyword in text for keyword in EMOTICON_KEYWORDS)

    def extract_emotion(self, text: str) -> str:
        """
        从用户输入中提取情绪描述

        支持格式：
        - "表情包：开心"
        - "生成表情包：累了"
        - "/表情包 加油"
        - "来个表情包，疲惫的"

        Args:
            text: 用户输入文本

        Returns:
            str: 提取的情绪描述
        """
        # 移除表情包关键词
        emotion_text = text
        for keyword in EMOTICON_KEYWORDS:
            emotion_text = emotion_text.replace(keyword, '')

        # 移除常见分隔符和前缀词
        emotion_text = re.sub(r'[：:，,、]', ' ', emotion_text)
        emotion_text = re.sub(r'^[/\s]+', '', emotion_text)  # 移除开头的斜杠和空格

        # 移除"来个"、"生成"等前缀
        emotion_text = re.sub(r'^(来个|生成|要个|给我|帮我)\s*', '', emotion_text)

        # 清理多余空格和标点
        emotion_text = emotion_text.strip()
        emotion_text = re.sub(r'\s+', ' ', emotion_text)

        # 移除末尾的"的"
        emotion_text = re.sub(r'的$', '', emotion_text)

        # 如果为空，返回默认
        if not emotion_text:
            emotion_text = "开心"

        logger.info(f"提取的情绪描述: {emotion_text}")
        return emotion_text

    def generate_emoticon_prompt(self, emotion: str) -> Dict:
        """
        使用AI生成表情包描述prompt

        Args:
            emotion: 情绪描述（如"开心"、"累了"、"加油"）

        Returns:
            dict: {
                'success': bool,
                'prompt': str,  # 生成的图片描述
                'error': str    # 错误信息（如果失败）
            }
        """
        try:
            logger.info(f"🎨 开始生成表情包prompt，情绪: {emotion}")

            # 调用AI生成prompt
            result = chat_service.chat(
                user_message=emotion,
                system_prompt=EMOTICON_SYSTEM_PROMPT,
                user_id=None  # 不需要历史对话
            )

            if result.get('success', False):
                prompt = result.get('reply', '').strip()
                logger.info(f"✅ Prompt生成成功: {prompt[:100]}...")
                return {
                    'success': True,
                    'prompt': prompt
                }
            else:
                error_msg = result.get('error', '未知错误')
                logger.error(f"❌ Prompt生成失败: {error_msg}")
                return {
                    'success': False,
                    'error': f"AI生成描述失败: {error_msg}"
                }

        except Exception as e:
            error_msg = f"生成表情包prompt异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }

    def create_emoticon(self, user_text: str) -> Dict:
        """
        完整的表情包生成流程

        Args:
            user_text: 用户输入文本

        Returns:
            dict: {
                'success': bool,
                'image_path': str,  # 生成的图片路径
                'emotion': str,     # 识别的情绪
                'error': str        # 错误信息（如果失败）
            }
        """
        try:
            # 1. 提取情绪描述
            emotion = self.extract_emotion(user_text)
            logger.info(f"🎭 用户想要的表情包: {emotion}")

            # 2. 生成表情包prompt
            prompt_result = self.generate_emoticon_prompt(emotion)

            if not prompt_result.get('success', False):
                return {
                    'success': False,
                    'error': prompt_result.get('error', '生成描述失败')
                }

            prompt = prompt_result.get('prompt', '')

            # 3. 调用图片生成服务
            logger.info(f"🖼️ 开始生成表情包图片...")
            image_result = image_service.generate_image(prompt=prompt)

            if image_result.get('success', False):
                image_path = image_result.get('image_path', '')
                logger.info(f"✅ 表情包生成成功: {image_path}")
                return {
                    'success': True,
                    'image_path': image_path,
                    'emotion': emotion
                }
            else:
                error_msg = image_result.get('error', '图片生成失败')
                logger.error(f"❌ 表情包图片生成失败: {error_msg}")
                return {
                    'success': False,
                    'error': f"图片生成失败: {error_msg}"
                }

        except Exception as e:
            error_msg = f"表情包生成异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'error': error_msg
            }


# 创建全局表情包服务实例
emoticon_service = EmoticonService()
