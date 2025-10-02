# emoticon_service.py
"""
表情包生成服务 - 智能识别情绪并生成可爱表情包
触发方式：关键词"表情包"
风格：AI自由发挥，Q版卡通可爱风格
支持三模型对比：Gemini 2.5 Flash vs 通义千问 Qwen-Image-Plus vs 火山引擎 SeeDream-4
"""
import re
import json
import logging
from typing import Optional, Dict, List
from .ai_service import chat_service
from .image_service import image_service
from .qwen_image_service import qwen_image_service
from .seedream_image_service import seedream_image_service
from ..config.config import config

logger = logging.getLogger(__name__)

# 表情包关键词
EMOTICON_KEYWORDS = ['表情包', '/表情包', '来个表情包', '生成表情包']

# 表情包生成系统提示词（优化版v2.0）
EMOTICON_SYSTEM_PROMPT = """你是专业表情包设计师，根据用户意图生成AI绘画描述。

## 核心定位
表情包 = 情绪表达 + 社交工具 + 网络文化
- 理解真实含义："狗头"=调侃，"吃瓜"=围观，"打工人"=社畜自嘲
- 不要字面翻译，要理解社交语境

## 风格固定
Q版卡通，大头小身3:1，圆润线条，居中构图主体占70%+
角色：柴犬/小猫/小熊/小兔子等可爱动物
背景：纯色或简单渐变，不要复杂场景

## 文字决策树
```
输入 → 判断类型 → 文字策略

🚫 无文字：社交礼仪(微笑/点头/OK)、观察(偷看/歪头)、卖萌
✅ 必须文字：网络梗(YYDS/破防/绝绝子)、强烈情绪、行动指令
⚖️ 可选文字：中等情绪、场景反应
```

**文字样式**（如需要）：
- 位置：角色正上方居中
- 大小：画面高15-20%
- 长度：2-3字最佳，≤4字
- 风格：情绪匹配（开心→圆润亮黄，生气→锋利红橙，累→松散灰蓝）
- 特效：多层描边+发光/阴影

## 描述模板
[角色]：动物+颜色+外形 → [表情动作]：眼睛+嘴巴+肢体 → [文字]：内容+样式 → [特效+背景] → "Q版卡通风格，可爱萌系，表情包风格"

## 示例（有文字）

"开心" → 黄色小鸭子，月牙眼，灿烂笑容，双翅上扬跳跃，正上方亮黄粗体"开心！"白描边橙发光，星星特效，黄色渐变背景，Q版卡通风格，可爱萌系，表情包风格

"累了" → 灰色小考拉趴地，半闭困倦眼，舌头吐出，四肢摊开大字型融化状，正上方松散倾斜灰蓝粗体"累死了..."深灰描边淡阴影，三滴汗珠，淡蓝灰渐变背景，Q版卡通风格，可爱萌系，表情包风格

"YYDS" → 橘色小老虎双手高举奖杯，眼睛发光，嘴巴大张欢呼，尾巴炸毛兴奋状，正上方金色超粗体"YYDS"，文字带彩虹渐变多层描边星光爆炸效果，周围烟花礼炮，金黄色渐变背景，Q版卡通风格，可爱萌系，表情包风格

"破防了" → 白色小兔子蹲地，眼睛泛泪，耳朵耷拉，一只手擦眼睛，整体委屈状，正上方蓝紫色粗体"破防了"，文字微微颤抖感带水滴效果，周围小碎心漂浮，淡蓝紫渐变背景，Q版卡通风格，可爱萌系，表情包风格

"打工人" → 灰色小猫咪西装领带拎公文包，眼睛空洞死鱼眼，嘴角下垂，身体微驼背疲惫状，正上方深灰粗体"打工人"，文字带深色描边压抑感，头顶乌云符号，灰白渐变背景，Q版卡通风格，可爱萌系，表情包风格

"生气" → 红色小狐狸叉腰站立，眉毛倒竖，眼睛瞪圆，嘴巴呲牙，尾巴炸毛竖起，正上方锋利红橙粗体"生气！"，文字带火焰纹理和爆炸线条，周围怒气符号，红橙渐变背景，Q版卡通风格，可爱萌系，表情包风格

"加油" → 橘色小老虎握拳举胸前，炯炯有神眼，嘴角上扬斗志满满，尾巴向上翘，正上方粗壮上倾斜金色渐变超粗体"加油！"，橙描边金发光，能量光芒闪电特效，橙黄渐变背景，Q版卡通风格，可爱萌系，表情包风格

"无语子" → 白色小猫咪翻白眼，嘴撇起无奈鄙视，双手叉腰，正上方灰蓝粗体"无语子"深灰描边微弱抖动，头顶三条黑线，浅灰渐变背景，Q版卡通风格，可爱萌系，表情包风格

"得意" → 棕色小浣熊双手环胸，眼睛眯成缝，嘴角勾起坏笑，尾巴左右摇摆，正上方紫色粗体"略略略~"，文字带调皮弧线和星星点缀，周围得意光环，淡紫渐变背景，Q版卡通风格，可爱萌系，表情包风格

"惊讶" → 灰白小兔子，眼睛瞪圆，嘴巴O型张开，耳朵竖直，双手捂嘴，正上方亮黄粗体"哇！"，文字带多层波纹扩散效果，周围惊叹号和闪电，亮黄渐变背景，Q版卡通风格，可爱萌系，表情包风格

## 示例（无文字）

"微笑" → 橘色小猫咪坐姿，月牙眯眼，嘴角轻扬温和友善笑容，前爪自然放身前，放松惬意姿态，表情温暖治愈，纯白背景，Q版卡通风格，可爱萌系，表情包风格

"点头" → 棕色小熊站立，头部微向下点动，眼睛认真看前方，嘴角微扬，双手自然两侧，专注可爱诚恳姿态，浅黄渐变背景，Q版卡通风格，可爱萌系，表情包风格

"偷看" → 灰白小猫躲墙角，半身+圆溜大眼露出，好奇盯前方，谨慎期待表情，前爪轻搭墙边，尾巴微翘，淡蓝渐变背景，Q版卡通风格，可爱萌系，表情包风格

"OK" → 黄色小鸭子站立，一翅高举竖大拇指，月牙眼，微张嘴开心笑，另一翅自然身侧，自信阳光姿态，明亮黄渐变背景，Q版卡通风格，可爱萌系，表情包风格

"摸鱼" → 蓝色小鱼趴办公桌，眼睛偷瞄四周，一手托腮，另一手藏手机，嘴角坏笑，悠闲放松姿态，淡蓝渐变背景，Q版卡通风格，可爱萌系，表情包风格

"害羞" → 粉色小猪低头，脸颊红晕，眼睛偷瞟，双手背后扭捏，整体娇羞状，粉色渐变背景，Q版卡通风格，可爱萌系，表情包风格

根据输入生成描述："""


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
        完整的表情包生成流程 - 使用三模型对比

        Args:
            user_text: 用户输入文本

        Returns:
            dict: {
                'success': bool,
                'images': List[dict],  # 生成的图片列表，每个包含 {path, model_name}
                'emotion': str,        # 识别的情绪
                'error': str           # 错误信息（如果失败）
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

            # 3. 同时使用三个模型生成图片
            logger.info(f"🖼️ 开始使用三模型生成表情包...")

            images = []
            errors = []

            # 3.1 使用 Gemini 2.5 Flash 生成
            logger.info("🔹 Gemini 2.5 Flash 生成中...")
            gemini_result = image_service.generate_image(prompt=prompt)

            if gemini_result.get('success', False):
                image_path = gemini_result.get('image_path', '')
                logger.info(f"✅ Gemini 生成成功: {image_path}")
                images.append({
                    'path': image_path,
                    'model_name': 'Gemini 2.5 Flash'
                })
            else:
                error_msg = gemini_result.get('error', '生成失败')
                logger.error(f"❌ Gemini 生成失败: {error_msg}")
                errors.append(f"Gemini: {error_msg}")

            # 3.2 使用通义千问生成
            logger.info("🔹 通义千问 Qwen-Image-Plus 生成中...")
            qwen_result = qwen_image_service.generate_image(
                prompt=prompt,
                watermark=False,  # 不添加水印
                prompt_extend=True  # 开启智能改写
            )

            if qwen_result.get('success', False):
                image_path = qwen_result.get('image_path', '')
                logger.info(f"✅ 通义千问生成成功: {image_path}")
                images.append({
                    'path': image_path,
                    'model_name': '通义千问 Qwen-Image-Plus'
                })
            else:
                error_msg = qwen_result.get('error', '生成失败')
                logger.error(f"❌ 通义千问生成失败: {error_msg}")
                errors.append(f"通义千问: {error_msg}")

            # 3.3 使用火山引擎 SeeDream-4 生成
            logger.info("🔹 火山引擎 SeeDream-4 生成中...")
            seedream_result = seedream_image_service.generate_image(
                prompt=prompt,
                size="1024x1024"  # 使用1024尺寸
            )

            if seedream_result.get('success', False):
                image_path = seedream_result.get('image_path', '')
                logger.info(f"✅ SeeDream 生成成功: {image_path}")
                images.append({
                    'path': image_path,
                    'model_name': '火山引擎 SeeDream-4'
                })
            else:
                error_msg = seedream_result.get('error', '生成失败')
                logger.error(f"❌ SeeDream 生成失败: {error_msg}")
                errors.append(f"SeeDream: {error_msg}")

            # 4. 返回结果
            if images:
                logger.info(f"✅ 成功生成 {len(images)} 张表情包")
                return {
                    'success': True,
                    'images': images,
                    'emotion': emotion,
                    'errors': errors if errors else None  # 如果有部分失败，也返回
                }
            else:
                error_msg = "所有模型都生成失败: " + "; ".join(errors)
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
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
