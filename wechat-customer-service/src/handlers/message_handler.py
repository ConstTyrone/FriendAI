# message_handler.py
"""
消息处理器 - 处理微信客服消息并提供AI对话回复
"""
import logging
import xml.etree.ElementTree as ET
import time
from typing import Dict, Any
from .message_classifier import classifier
from .message_formatter import text_extractor
from ..services.ai_service import chat_service
from ..services.emoticon_service import emoticon_service
from ..database.audit_database import audit_db

logger = logging.getLogger(__name__)

def parse_message(xml_data: str) -> Dict[str, Any]:
    """解析XML消息数据"""
    try:
        root = ET.fromstring(xml_data)
        message = {}

        for child in root:
            if child.text:
                message[child.tag] = child.text.strip()

        return message
    except Exception as e:
        logger.error(f"消息解析失败: {e}")
        return {}


def process_message_and_reply(message: Dict[str, Any], open_kfid: str = None) -> dict:
    """
    处理消息并生成AI回复或图片

    流程: 消息 → 分类 → 转换为纯文本 → 检测生图指令 → AI对话/生成图片 → 返回回复

    Args:
        message: 消息字典
        open_kfid: 客服账号ID（用于发送图片）

    Returns:
        dict: {
            'type': 'text' | 'image',
            'content': str,  # 文本内容或图片路径
            'error': str     # 错误信息（可选）
        }
    """
    try:
        user_id = message.get('FromUserName')
        if not user_id:
            logger.warning("消息中缺少用户ID，跳过处理")
            return {'type': 'text', 'content': ''}

        print(f"📨 收到消息 - 用户: {user_id}")

        # 记录用户活动（埋点）
        audit_db.record_message(user_id, 'text')

        # 步骤0: 检测是否为菜单点击消息
        menu_id = message.get('MenuId', '')
        if menu_id:
            print(f"🎯 检测到菜单点击: {menu_id}")
            logger.info(f"用户点击菜单: {menu_id}")

            # 根据菜单ID模拟用户输入
            if menu_id == 'chat_help':
                # 我有问题要问: 返回提示语
                return {
                    'type': 'text',
                    'content': '您好!我是AI智能助手,请告诉我您的问题,我会尽力为您解答。\n\n💡 小提示: 发送"表情包：开心"可以生成表情包哦~'
                }
            elif menu_id == 'emoticon_happy':
                # 表情包：开心
                print(f"😊 用户点击: 表情包-开心")
                message['Content'] = '表情包：开心'
                message['MenuId'] = ''  # 清除MenuId,避免重复处理
                # 继续正常流程处理
            elif menu_id == 'emoticon_tired':
                # 表情包：累了
                print(f"😴 用户点击: 表情包-累了")
                message['Content'] = '表情包：累了'
                message['MenuId'] = ''  # 清除MenuId
                # 继续正常流程处理
            else:
                return {
                    'type': 'text',
                    'content': '收到您的选择,请问有什么可以帮助您的？'
                }

        # 步骤1: 分类消息类型
        message_type = classifier.classify_message(message)
        print(f"🔍 消息分类: {message_type}")

        # 步骤2: 提取纯文本内容
        text_content = text_extractor.extract_text(message, message_type)
        print(f"📝 已提取文本内容: {text_content[:100]}...")
        logger.info(f"提取的文本内容: {text_content[:300]}...")

        # 步骤3: 检测是否为表情包生成请求
        if emoticon_service.detect_emoticon_request(text_content):
            print(f"🎨 检测到表情包生成请求")
            logger.info(f"检测到表情包生成请求: {text_content}")

            # 调用表情包生成服务（双模型对比）
            emoticon_result = emoticon_service.create_emoticon(text_content)

            if emoticon_result.get('success', False):
                images = emoticon_result.get('images', [])
                emotion = emoticon_result.get('emotion', '')
                errors = emoticon_result.get('errors', [])

                print(f"✅ 表情包生成成功: {emotion} - 共{len(images)}张图片")
                logger.info(f"表情包生成成功: {emotion} - {len(images)}张图片")

                # 记录表情包生成活动
                audit_db.record_message(user_id, 'emoticon')

                # 返回多张图片
                return {
                    'type': 'images',  # 注意：改为复数形式
                    'content': images,  # 格式: [{'path': '...', 'model_name': '...'}, ...]
                    'emotion': emotion,
                    'errors': errors
                }
            else:
                error_msg = emoticon_result.get('error', '表情包生成失败')
                print(f"❌ 表情包生成失败: {error_msg}")
                logger.error(f"表情包生成失败: {error_msg}")
                return {
                    'type': 'text',
                    'content': f"抱歉，表情包生成失败: {error_msg}"
                }

        # 步骤4: 普通AI对话回复
        print(f"🤖 正在生成AI回复...")
        chat_result = chat_service.chat(
            user_message=text_content,
            user_id=user_id
        )

        if chat_result.get('success', False):
            reply = chat_result.get('reply', '')
            print(f"✅ AI回复成功: {reply[:100]}...")
            logger.info(f"AI回复内容: {reply}")

            # 记录AI对话活动
            audit_db.record_message(user_id, 'ai_chat')

            return {
                'type': 'text',
                'content': reply
            }
        else:
            error_msg = chat_result.get('error', '未知错误')
            print(f"❌ AI回复失败: {error_msg}")
            logger.error(f"AI回复失败: {error_msg}")
            return {
                'type': 'text',
                'content': "抱歉，我现在遇到了一些问题，请稍后再试。"
            }

    except Exception as e:
        logger.error(f"消息处理过程中发生错误: {e}", exc_info=True)
        print(f"❌ 消息处理失败: {e}")
        return {
            'type': 'text',
            'content': "抱歉，处理您的消息时出现了错误，请稍后再试。"
        }

def classify_and_handle_message(message: Dict[str, Any]) -> None:
    """
    处理普通消息的入口函数（用于后台异步处理）

    注意：这个函数只处理消息，不发送回复
    """
    try:
        user_id = message.get('FromUserName')
        if not user_id:
            logger.warning("消息中缺少用户ID，跳过处理")
            return

        # 处理并获取回复（但不发送，由调用方决定是否发送）
        reply = process_message_and_reply(message)
        if reply:
            logger.info(f"消息处理完成，生成回复: {reply[:100]}...")
        else:
            logger.warning("未生成有效回复")

    except Exception as e:
        logger.error(f"消息处理失败: {e}", exc_info=True)

def handle_event_by_type(event_content: Dict[str, Any], open_kfid: str) -> None:
    """
    根据事件类型进行不同处理

    Args:
        event_content: 事件内容
        open_kfid: 客服账号ID
    """
    from ..services.wework_client import wework_client

    event_type = event_content.get('event_type', '')

    if event_type == 'enter_session':
        # 用户进入会话事件
        external_userid = event_content.get('external_userid', '')
        welcome_code = event_content.get('welcome_code', '')
        scene = event_content.get('scene', '')
        scene_param = event_content.get('scene_param', '')

        logger.info(f"👋 用户进入会话: {external_userid}, 场景: {scene}, 参数: {scene_param}")

        # 准备欢迎语内容和菜单
        welcome_text = "您好,欢迎咨询!我是AI智能助手,可以为您提供以下服务:"

        # 如果是视频号场景,添加特定欢迎语
        wechat_channels = event_content.get('wechat_channels', {})
        if wechat_channels:
            channel_name = wechat_channels.get('nickname', '') or wechat_channels.get('shop_nickname', '')
            if channel_name:
                welcome_text = f"您好,欢迎从视频号《{channel_name}》咨询!我是AI智能助手,可以为您提供以下服务:"

        # 构建功能菜单 - 具体明确的选项
        menu_items = [
            {"type": "click", "click": {"id": "chat_help", "content": "💬 我有问题要问"}},
            {"type": "click", "click": {"id": "emoticon_happy", "content": "😊 表情包：开心"}},
            {"type": "click", "click": {"id": "emoticon_tired", "content": "😴 表情包：累了"}}
        ]

        # 只有当有welcome_code时才发送欢迎菜单
        if welcome_code:
            try:
                logger.info(f"✨ 使用welcome_code发送欢迎语菜单")
                result = wework_client.send_welcome_message(
                    welcome_code,
                    content=welcome_text,
                    menu_items=menu_items
                )

                if result.get('errcode') == 0:
                    logger.info(f"✅ 欢迎语菜单发送成功")
                    print(f"✅ 已向用户 {external_userid} 发送欢迎语菜单")
                else:
                    error_msg = result.get('errmsg', '未知错误')
                    logger.warning(f"⚠️ 欢迎语菜单发送失败: {error_msg}")
                    print(f"⚠️ 欢迎语菜单发送失败: {error_msg}")
            except Exception as e:
                logger.error(f"❌ 发送欢迎语菜单异常: {e}", exc_info=True)
                print(f"❌ 发送欢迎语菜单异常: {e}")
        else:
            # 没有welcome_code时不发送菜单
            logger.info(f"📝 无welcome_code,跳过欢迎菜单发送")
            print(f"📝 用户 {external_userid} 进入会话（无welcome_code）")

        # 检查视频号场景
        wechat_channels = event_content.get('wechat_channels', {})
        if wechat_channels:
            channel_scene = wechat_channels.get('scene', 0)
            channel_name = wechat_channels.get('nickname', '') or wechat_channels.get('shop_nickname', '')
            logger.info(f"📺 来自视频号: {channel_name}, 场景值: {channel_scene}")

    elif event_type == 'msg_send_fail':
        # 消息发送失败事件
        external_userid = event_content.get('external_userid', '')
        fail_msgid = event_content.get('fail_msgid', '')
        fail_type = event_content.get('fail_type', 0)

        fail_type_map = {
            0: "未知原因",
            10: "用户拒收",
            11: "企业未有成员登录企业微信App",
            13: "安全限制"
        }
        fail_reason = fail_type_map.get(fail_type, f"错误码{fail_type}")

        logger.warning(f"❌ 消息发送失败: 用户={external_userid}, msgid={fail_msgid}, 原因={fail_reason}")
        print(f"⚠️ 消息发送失败: {fail_reason}")

    elif event_type == 'user_recall_msg':
        # 用户撤回消息事件
        external_userid = event_content.get('external_userid', '')
        recall_msgid = event_content.get('recall_msgid', '')

        logger.info(f"↩️ 用户撤回消息: 用户={external_userid}, msgid={recall_msgid}")
        print(f"📝 用户撤回了消息: {recall_msgid}")

    else:
        logger.info(f"❓ 收到未处理的事件类型: {event_type}")

def handle_wechat_kf_event(message: Dict[str, Any]) -> None:
    """
    处理微信客服事件消息 - AI对话版本

    流程: 拉取消息 → 解析文本 → AI对话 → 发送回复
    """
    try:
        # 防重复处理机制 - 使用Redis持久化
        corp_id = message.get('ToUserName', '')
        open_kfid = message.get('OpenKfId', '')
        token = message.get('Token', '')
        create_time = message.get('CreateTime', '')

        event_id = f"{corp_id}_{open_kfid}_{token}_{create_time}"

        # 导入Redis状态管理器
        try:
            from ..services.redis_state_manager import state_manager

            # 使用Redis去重
            if state_manager.is_event_processed(event_id):
                print(f"⚠️ 事件 {event_id} 已经处理过，跳过重复处理")
                logger.info(f"事件 {event_id} 已经处理过，跳过重复处理")
                return

            # 标记事件已处理
            state_manager.mark_event_processed(event_id)

        except Exception as e:
            logger.warning(f"⚠️ Redis去重失败，使用内存去重: {e}")
            # 降级方案：内存去重
            if not hasattr(handle_wechat_kf_event, '_processed_events'):
                handle_wechat_kf_event._processed_events = set()

            if event_id in handle_wechat_kf_event._processed_events:
                print(f"⚠️ 事件 {event_id} 已经处理过，跳过重复处理")
                logger.info(f"事件 {event_id} 已经处理过，跳过重复处理")
                return

            handle_wechat_kf_event._processed_events.add(event_id)

        print(f"[微信客服事件] 企业ID: {corp_id}, 事件: kf_msg_or_event, 客服账号: {open_kfid}")
        print(f"Token: {token}, 时间: {create_time}")

        from ..services.wework_client import wework_client

        # 拉取所有消息，返回最新的1条
        print("🔄 拉取最新消息...")
        logger.info("开始调用sync_kf_messages接口拉取最新消息")
        messages = wework_client.sync_kf_messages(token=token, open_kf_id=open_kfid, get_latest_only=True)
        logger.info(f"sync_kf_messages调用完成，共获取到 {len(messages) if messages else 0} 条消息")
        print(f"共获取到 {len(messages) if messages else 0} 条消息")

        if messages:
            print(f"✅ 获取到最新消息")
            logger.info(f"获取到 {len(messages)} 条最新消息")

            # 只处理最新的一条消息
            latest_msg = messages[0]

            # 转换消息格式
            converted_msg = wework_client._convert_kf_message(latest_msg)

            if converted_msg:
                print(f"📝 处理消息: {latest_msg.get('msgid', '')}")

                # 如果是事件消息,调用事件处理函数
                if converted_msg.get('MsgType') == 'event':
                    event_content = converted_msg.get('EventContent', {})
                    handle_event_by_type(event_content, open_kfid)
                    # 事件处理完成,不需要AI回复
                    return

                # 处理消息并获取AI回复或图片
                reply_result = process_message_and_reply(converted_msg, open_kfid)

                # 发送回复给用户
                if reply_result and reply_result.get('content'):
                    external_userid = latest_msg.get('external_userid', '')
                    if external_userid:
                        try:
                            reply_type = reply_result.get('type', 'text')
                            content = reply_result.get('content', '')

                            if reply_type == 'images':
                                # 发送多张图片（双模型对比）
                                images = content  # List[{'path': '...', 'model_name': '...'}]
                                emotion = reply_result.get('emotion', '')
                                errors = reply_result.get('errors', [])

                                print(f"🖼️ 准备发送{len(images)}张表情包图片...")

                                # 先发送说明文本
                                intro_text = f"✨ 为您生成了【{emotion}】表情包，使用三个AI模型对比："
                                wework_client.send_text_message(external_userid, open_kfid, intro_text)

                                # 依次发送每张图片
                                for idx, img_info in enumerate(images, 1):
                                    image_path = img_info.get('path', '')
                                    model_name = img_info.get('model_name', '未知模型')

                                    # 发送标注
                                    label_text = f"【{idx}】{model_name}"
                                    wework_client.send_text_message(external_userid, open_kfid, label_text)

                                    # 上传并发送图片
                                    media_id = wework_client.upload_temp_media(image_path, 'image')
                                    wework_client.send_image_message(external_userid, open_kfid, media_id)

                                    print(f"✅ 已发送 {model_name} 生成的图片")

                                # 如果有部分失败，发送错误提示
                                if errors:
                                    error_text = "⚠️ 部分模型生成失败:\n" + "\n".join(errors)
                                    wework_client.send_text_message(external_userid, open_kfid, error_text)

                                print(f"✅ 所有图片已发送给用户")
                                logger.info(f"{len(images)}张表情包图片已发送给用户 {external_userid}")

                            elif reply_type == 'image':
                                # 发送单张图片（兼容旧格式）
                                print("🖼️ 上传并发送图片给用户...")
                                media_id = wework_client.upload_temp_media(content, 'image')
                                wework_client.send_image_message(external_userid, open_kfid, media_id)
                                print("✅ 图片已发送给用户")
                                logger.info(f"图片已发送给用户 {external_userid}")
                            else:
                                # 发送文本消息
                                print("📤 发送AI回复给用户...")
                                wework_client.send_text_message(external_userid, open_kfid, content)
                                print("✅ AI回复已发送给用户")
                                logger.info(f"AI回复已发送给用户 {external_userid}")

                        except Exception as send_error:
                            logger.error(f"发送消息给用户失败: {send_error}")
                            print(f"❌ 发送消息失败: {send_error}")
                    else:
                        logger.warning("缺少用户ID，无法发送回复")
                        print("⚠️ 缺少用户ID，无法发送回复")
                else:
                    print("⚠️ 没有生成回复内容，不发送")
            else:
                logger.error("消息转换失败")
                print("❌ 消息转换失败")
        else:
            print("📭 未获取到新消息")
            logger.info("未获取到新消息")

    except Exception as e:
        logger.error(f"处理微信客服事件时发生错误: {e}", exc_info=True)
        print(f"❌ 处理微信客服事件失败: {e}")
