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

def process_message_and_reply(message: Dict[str, Any]) -> str:
    """
    处理消息并生成AI回复

    流程: 消息 → 分类 → 转换为纯文本 → AI对话 → 返回回复

    Args:
        message: 消息字典

    Returns:
        str: AI回复内容，如果失败返回空字符串
    """
    try:
        user_id = message.get('FromUserName')
        if not user_id:
            logger.warning("消息中缺少用户ID，跳过处理")
            return ""

        print(f"📨 收到消息 - 用户: {user_id}")

        # 步骤1: 分类消息类型
        message_type = classifier.classify_message(message)
        print(f"🔍 消息分类: {message_type}")

        # 步骤2: 提取纯文本内容
        text_content = text_extractor.extract_text(message, message_type)
        print(f"📝 已提取文本内容: {text_content[:100]}...")
        logger.info(f"提取的文本内容: {text_content[:300]}...")

        # 步骤3: AI对话回复
        print(f"🤖 正在生成AI回复...")
        chat_result = chat_service.chat(
            user_message=text_content,
            user_id=user_id
        )

        if chat_result.get('success', False):
            reply = chat_result.get('reply', '')
            print(f"✅ AI回复成功: {reply[:100]}...")
            logger.info(f"AI回复内容: {reply}")
            return reply
        else:
            error_msg = chat_result.get('error', '未知错误')
            print(f"❌ AI回复失败: {error_msg}")
            logger.error(f"AI回复失败: {error_msg}")
            return "抱歉，我现在遇到了一些问题，请稍后再试。"

    except Exception as e:
        logger.error(f"消息处理过程中发生错误: {e}", exc_info=True)
        print(f"❌ 消息处理失败: {e}")
        return "抱歉，处理您的消息时出现了错误，请稍后再试。"

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

                # 处理消息并获取AI回复
                ai_reply = process_message_and_reply(converted_msg)

                # 发送AI回复给用户
                if ai_reply:
                    external_userid = latest_msg.get('external_userid', '')
                    if external_userid:
                        try:
                            print("📤 发送AI回复给用户...")
                            wework_client.send_text_message(external_userid, open_kfid, ai_reply)
                            print("✅ AI回复已发送给用户")
                            logger.info(f"AI回复已发送给用户 {external_userid}")
                        except Exception as send_error:
                            logger.error(f"发送消息给用户失败: {send_error}")
                            print(f"❌ 发送消息失败: {send_error}")
                    else:
                        logger.warning("缺少用户ID，无法发送回复")
                        print("⚠️ 缺少用户ID，无法发送回复")
                else:
                    print("⚠️ 没有生成AI回复，不发送")
            else:
                logger.error("消息转换失败")
                print("❌ 消息转换失败")
        else:
            print("📭 未获取到新消息")
            logger.info("未获取到新消息")

    except Exception as e:
        logger.error(f"处理微信客服事件时发生错误: {e}", exc_info=True)
        print(f"❌ 处理微信客服事件失败: {e}")
