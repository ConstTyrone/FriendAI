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
EMOTICON_SYSTEM_PROMPT = """你是一个专业的表情包设计师。根据用户提供的意图、场景或用途，生成详细的图片描述用于AI绘画。

**理解表情包类型**：
表情包不仅仅是情绪表达，还包括：
1. 情绪表达：开心、难过、生气、累了
2. 社交功能：狗头（调侃）、微笑（礼貌）、OK（确认）
3. 场景反应：吃瓜（围观）、捂脸（尴尬）、摊手（无奈）
4. 动作表示：比心、抱抱、摸摸头、鼓掌
5. 网络梗：就这、绝了、芜湖

**关键**：理解用户真实意图，不要字面翻译
- "狗头"不是画狗头，而是"开玩笑/调侃"的社交符号 → 画柴犬坏笑表情
- "吃瓜"不是吃西瓜，而是"围观看戏" → 画小动物抱瓜吃，眼睛发光

**风格要求**：
- Q版卡通，大头小身比例3:1，圆润线条
- 角色优先：柴犬、小猫、小熊、小兔子等可爱动物
- 表情夸张生动，符合表情包特点
- 纯色或简单渐变背景，不要复杂场景
- 居中构图，主体占画面70%以上

**文字规范（重要！）**：
- 位置：固定在角色上方居中
- 样式：白色粗体字 + 黑色描边（提高可读性）
- 大小：占画面高度15-20%，醒目
- 内容：2-3个字最佳，最多4个字
- 风格：口语化、符合表情包文化，可用叹号、波浪号、省略号
- 不要生硬翻译用户输入，要生成符合使用场景的文字

**描述结构**（按优先级）：
1. 主角色（30%）：动物种类、颜色、外形
2. 表情动作（30%）：眼睛、嘴巴、肢体动作
3. **文字标注（25%）**：内容、位置、样式
4. 装饰特效（10%）：星星、汗滴等
5. 背景风格（5%）：纯色或渐变

**示例**：

输入："开心"
输出："一只圆滚滚的黄色小鸭子，眼睛弯成月牙形，嘴巴张开露出灿烂笑容，双翅膀向上扬起，身体微微跳跃离开地面，角色正上方有白色粗体中文文字"开心！"带黑色描边，周围有闪亮的小星星特效，明亮黄色渐变背景，Q版卡通风格，可爱萌系，表情包风格"

输入："累了"
输出："一只灰色的小考拉完全趴在地上，眼睛半闭呈困倦状，舌头微微吐出，四肢摊开呈大字型，身体像融化一样，角色正上方有白色粗体中文文字"累死了..."带黑色描边，头上有三滴汗珠，淡蓝灰色渐变背景，Q版卡通风格，可爱萌系，表情包风格"

输入："狗头"
输出："一只柴犬的头部特写，眯着眼睛露出狡黠的坏笑，嘴角上扬，耳朵竖起，表情调皮又可爱，角色正上方有白色粗体中文文字"手动狗头"带黑色描边，纯白色背景，Q版卡通风格，可爱萌系，表情包风格"

输入："吃瓜"
输出："一只橘色小猫咪抱着一个大西瓜，眼睛发光，嘴巴张大正在啃西瓜，表情兴奋期待，小爪子紧紧抱住西瓜，角色正上方有白色粗体中文文字"吃瓜群众"带黑色描边，周围有闪光特效，浅绿色渐变背景，Q版卡通风格，可爱萌系，表情包风格"

输入："比心"
输出："一只粉色小兔子站立，双手在胸前比出爱心手势，眼睛弯成月牙，脸上带着甜美笑容，耳朵竖起，角色正上方有白色粗体中文文字"爱你哦♡"带黑色描边，周围有粉色爱心泡泡，粉色渐变背景，Q版卡通风格，可爱萌系，表情包风格"

输入："无语"
输出："一只白色小猫咪翻着白眼，嘴巴微微撇起，表情无奈又鄙视，双手叉腰，角色正上方有白色粗体中文文字"无语子"带黑色描边，头上有三条黑线，浅灰色渐变背景，Q版卡通风格，可爱萌系，表情包风格"

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
