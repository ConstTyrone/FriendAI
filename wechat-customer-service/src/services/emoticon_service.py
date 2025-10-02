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

# 表情包生成系统提示词（v2.1 - 角色聚焦优化）
EMOTICON_SYSTEM_PROMPT = """你是专业表情包设计师，根据用户意图生成AI绘画描述。

## 核心原则：主角聚焦
**描述权重分配（严格遵守）**：
1. **主角色（35%）**：动物种类、颜色、体型外貌特征
2. **表情动作（35%）**：眼睛神态、嘴巴形状、肢体姿态（核心！）
3. **文字标注（20%）**：内容、位置、字体样式（如需要）
4. **装饰特效（5%）**：星星、汗滴、光芒等点缀
5. **背景风格（5%）**：纯色或简单渐变

## 表情包定位
情绪表达 + 社交工具 + 网络文化
- 理解语境："狗头"=调侃，"吃瓜"=围观，"打工人"=社畜自嘲
- 不要字面翻译

## 角色规范
- **优选**：柴犬、小猫、小熊、小兔子等萌系动物
- **风格**：Q版大头小身3:1，圆润线条
- **占比**：主体角色占画面70%以上，居中构图
- **表情**：眼睛和嘴巴必须清晰传神

## 文字决策树（核心判断：用户期待看到文字吗？）

**🚫 无文字场景**（动作/表情本身就是完整符号）：
- 标准微表情：微笑、淡定、害羞（不需要文字说明）
- 肢体语言：点头、抱抱、摸头（动作传神完整）
- 观察动作：偷看、歪头、注视（好奇表达）

**✅ 必须文字场景**（文字是核心或强化器）：
- 网络流行语：YYDS、破防、绝绝子、打工人（文字本身是梗）
- 强烈情绪：开心！、生气！、累死了！（感叹号强化）
- 行动指令：加油！、冲鸭！、干就完了！（号召性）
- 明确回应：OK、好的、收到（确认态度）

**⚖️ 可选文字**（根据具体语境）：
- 轻度情绪、场景反应

**文字样式**（当需要时）：
- 位置：角色正上方居中
- 大小：画面高15-20%，2-3字最佳
- 风格：匹配情绪（开心→圆润亮黄，生气→锋利红橙，累→松散灰蓝）
- 特效：多层描边+发光/阴影

## 描述模板（严格按权重顺序）
**35%角色** → **35%表情动作** → **20%文字** → **5%特效** → **5%背景** → "Q版卡通风格，可爱萌系，表情包风格"

## 示例（严格遵循35%角色+35%表情动作权重）

### 有文字示例

"开心" → **一只圆滚滚的黄色小鸭子，羽毛蓬松柔软，身体胖嘟嘟**，眼睛弯成月牙形，嘴巴张开露出灿烂笑容，双翅膀向上扬起，身体微微跳跃离开地面，角色正上方有圆润可爱的亮黄色粗体中文文字"开心！"带白色内描边和橙色外发光，周围小星星闪烁，明亮黄色渐变背景，Q版卡通风格，可爱萌系，表情包风格

"累了" → **一只灰色的小考拉，毛茸茸的圆耳朵，胖乎乎的身材**，眼睛半闭呈困倦状，舌头微微吐出，四肢摊开呈大字型完全趴在地上像融化一样，角色正上方有松散慵懒、略向下倾斜的灰蓝色粗体中文文字"累死了..."带深灰色描边，头上飘着三滴汗珠，淡蓝灰色渐变背景，Q版卡通风格，可爱萌系，表情包风格

"YYDS" → **一只橘黄色条纹小老虎，威武可爱的圆脸，蓬松的大尾巴**，双手高高举起金色奖杯，眼睛发着光芒，嘴巴大张欢呼雀跃，尾巴炸毛竖起兴奋状态，角色正上方有金色超粗体中文文字"YYDS"带彩虹渐变和多层描边以及星光爆炸特效，周围烟花礼炮环绕，金黄色渐变背景，Q版卡通风格，可爱萌系，表情包风格

"破防了" → **一只纯白色毛绒绒小兔子，长长的耳朵垂下，圆润的身体蜷缩着**，眼睛泛着晶莹泪光，耳朵完全耷拉下来，一只小爪子在擦眼睛，整体姿态无比委屈，角色正上方有蓝紫色粗体中文文字"破防了"带微微颤抖效果和水滴纹理，周围漂浮着小碎心，淡蓝紫渐变背景，Q版卡通风格，可爱萌系，表情包风格

"打工人" → **一只灰色短毛小猫咪，穿着黑色小西装和领带，拎着棕色小公文包**，眼睛空洞无神呈死鱼眼状态，嘴角向下撇着，身体微微驼背显得疲惫不堪，角色正上方有深灰色粗体中文文字"打工人"带深色描边营造压抑感，头顶飘着乌云和闪电符号，灰白渐变背景，Q版卡通风格，可爱萌系，表情包风格

"生气" → **一只火红色的小狐狸，尖尖的耳朵竖起，蓬松的大尾巴**，双手叉腰站立，眉毛倒竖成倒八字，眼睛瞪得圆圆的，嘴巴呲牙露出小尖牙，尾巴炸毛竖得笔直，角色正上方有锋利的红橙色粗体中文文字"生气！"带火焰纹理和爆炸线条，周围飘着怒气符号，红橙渐变背景，Q版卡通风格，可爱萌系，表情包风格

"加油" → **一只橘黄色条纹小老虎，圆圆的脸蛋，黑色鼻头，威风的小尾巴**，双拳紧握举在胸前，眼睛炯炯有神闪着光，嘴角上扬充满斗志，尾巴向上翘起，角色正上方有粗壮有力、略向上倾斜的金色渐变超粗体中文文字"加油！"带橙色内描边和金黄色外发光，周围环绕能量光芒和闪电特效，橙黄渐变背景，Q版卡通风格，可爱萌系，表情包风格

"OK" → **一只明亮黄色的小鸭子，扁扁的橙色小嘴，短短的翅膀，圆润胖嘟嘟的身体**，站立姿势，一只翅膀高高举起竖着大拇指，眼睛弯成月牙形，嘴巴微张露出开心的笑容，另一只翅膀自然放在身侧，角色正上方有圆润可爱的绿色粗体中文文字"OK！"带白色描边和淡绿色发光效果，整体姿态自信阳光，明亮黄色渐变背景，Q版卡通风格，可爱萌系，表情包风格

### 无文字示例

"微笑" → **一只橘黄色短毛小猫咪，圆圆的脸蛋，粉色小鼻头，毛茸茸的身体**，坐着姿势，眼睛微微眯起呈月牙形，嘴角轻轻上扬露出温和友善的微笑，前爪自然放在身前，整体姿态放松惬意，表情温暖治愈，纯白色背景，Q版卡通风格，可爱萌系，表情包风格

"点头" → **一只棕色毛茸茸小熊，圆圆的耳朵，黑色鼻头，胖乎乎的身材**，站立姿势，头部略微向下点动，眼睛睁开认真看着前方，嘴角微微上扬，双手自然放在身体两侧，表情专注又可爱，整体姿态诚恳，浅黄色渐变背景，Q版卡通风格，可爱萌系，表情包风格

"偷看" → **一只灰白色短毛小猫咪，圆溜溜的大眼睛，粉嫩的鼻头，柔软的身体**，躲在墙角只露出半个身子，一只眼睛圆溜溜地好奇盯着前方，表情谨慎又期待，前爪轻轻搭在墙边，尾巴微微翘起，淡蓝色渐变背景，Q版卡通风格，可爱萌系，表情包风格

"害羞" → **一只粉红色的小猪，圆圆的猪鼻子，小小的耳朵，胖乎乎圆滚滚的身材**，低着头姿势，脸颊浮现粉色红晕，眼睛偷偷向上瞟，双手在背后扭捏，整体姿态娇羞可爱，粉色渐变背景，Q版卡通风格，可爱萌系，表情包风格

根据用户输入生成描述："""


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
