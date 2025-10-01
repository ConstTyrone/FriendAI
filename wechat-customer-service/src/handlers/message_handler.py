# message_handler.py
import logging
import xml.etree.ElementTree as ET
import time
from typing import Dict, Any
from .message_classifier import classifier
from .message_formatter import text_extractor
from ..services.ai_service import profile_extractor

logger = logging.getLogger(__name__)

# 智能选择数据库
from ..database.database_simple import db

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

def process_message(message: Dict[str, Any]) -> None:
    """
    统一的消息处理流程 - 用于用户画像提取

    流程: 消息 → 分类 → 转换为纯文本 → AI提取用户画像 → 存储/显示画像
    """
    start_time = time.time()
    try:
        user_id = message.get('FromUserName')
        message_id = message.get('MsgId', '')
        if not user_id:
            logger.warning("消息中缺少用户ID，跳过处理")
            return

        print(f"📨 收到消息 - 用户: {user_id}")

        # 步骤1: 分类消息类型
        message_type = classifier.classify_message(message)
        print(f"🔍 消息分类: {message_type}")

        # 步骤2: 提取纯文本内容
        text_content = text_extractor.extract_text(message, message_type)
        print(f"📝 已提取文本内容")
        logger.info(f"提取的文本内容: {text_content[:300]}...")

        # 步骤3: AI提取用户画像
        print(f"🤖 正在分析用户画像...")
        is_chat_record = (message_type == 'chat_record')
        if is_chat_record:
            print(f"📋 检测到聊天记录，将分析聊天记录中主要对话者的用户画像（排除转发者，仅返回一人）")
        profile_result = profile_extractor.extract_user_profile(text_content, is_chat_record)

        if profile_result.get('success', False):
            profile_data = profile_result.get('data', {})
            summary = profile_data.get('summary', '')
            user_profiles = profile_data.get('user_profiles', [])

            print(f"✅ 用户画像分析成功")
            print(f"📋 消息总结: {summary}")

            if user_profiles:
                print(f"👤 提取到 {len(user_profiles)} 个用户画像:")
                for i, profile in enumerate(user_profiles, 1):
                    print(f"\n=== 用户画像 {i} ===")
                    for key, value in profile.items():
                        if value and value != "未知":
                            key_name = {
                                'name': '姓名',
                                'gender': '性别',
                                'age': '年龄',
                                'phone': '电话',
                                'location': '所在地',
                                'marital_status': '婚育状况',
                                'education': '学历',
                                'company': '公司',
                                'position': '职位',
                                'asset_level': '资产水平',
                                'personality': '性格'
                            }.get(key, key)
                            print(f"  {key_name}: {value}")

                    # 保存到数据库
                    try:
                        profile_id = db.save_user_profile(
                            external_userid=user_id,
                            profile_data=profile,
                            raw_message=text_content,
                            message_type=message_type,
                            ai_response=profile_data
                        )

                        if profile_id:
                            print(f"💾 用户画像已保存到数据库 (ID: {profile_id})")
                        else:
                            print("⚠️ 用户画像保存失败")

                    except Exception as save_error:
                        logger.error(f"保存用户画像到数据库失败: {save_error}")
                        print(f"❌ 数据库保存失败: {save_error}")
            else:
                print("📋 未能从消息中提取到明确的用户画像信息")

            logger.info(f"用户画像分析结果: {profile_data}")

        else:
            error_msg = profile_result.get('error', '未知错误')
            print(f"❌ 用户画像分析失败: {error_msg}")
            logger.error(f"用户画像分析失败: {profile_result}")

        print(f"✅ 消息处理完成 - 类型: {message_type}")

    except Exception as e:
        logger.error(f"消息处理过程中发生错误: {e}", exc_info=True)
        print(f"❌ 消息处理失败: {e}")

def process_message_and_get_result(message: Dict[str, Any]) -> str:
    """
    处理消息并返回格式化的分析结果文本，用于发送给用户

    返回: 格式化的用户画像分析结果文本
    """
    start_time = time.time()
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
        print(f"📝 已提取文本内容")
        logger.info(f"提取的文本内容: {text_content[:300]}...")

        # 步骤3: AI提取用户画像
        print(f"🤖 正在分析用户画像...")
        is_chat_record = (message_type == 'chat_record')
        if is_chat_record:
            print(f"📋 检测到聊天记录，将分析聊天记录中主要对话者的用户画像（排除转发者，仅返回一人）")
        profile_result = profile_extractor.extract_user_profile(text_content, is_chat_record)

        if profile_result.get('success', False):
            profile_data = profile_result.get('data', {})
            summary = profile_data.get('summary', '')
            user_profiles = profile_data.get('user_profiles', [])

            print(f"✅ 用户画像分析成功")
            logger.info(f"用户画像分析结果: {profile_data}")

            # 构建格式化的回复文本
            result_text = "🤖 AI分析结果\n\n"

            if summary:
                result_text += f"📋 消息总结:\n{summary}\n\n"

            if user_profiles:
                result_text += f"👤 用户画像分析 (共{len(user_profiles)}个):\n\n"

                for i, profile in enumerate(user_profiles, 1):
                    result_text += f"=== 用户画像 {i} ===\n"

                    key_mapping = {
                        'name': '姓名',
                        'gender': '性别',
                        'age': '年龄',
                        'phone': '电话',
                        'location': '所在地',
                        'marital_status': '婚育状况',
                        'education': '学历',
                        'company': '公司',
                        'position': '职位',
                        'asset_level': '资产水平',
                        'personality': '性格'
                    }

                    # 只显示有值且不为"未知"的字段
                    valid_fields = []
                    for key, value in profile.items():
                        if value and value != "未知":
                            key_name = key_mapping.get(key, key)
                            valid_fields.append(f"{key_name}: {value}")

                    if valid_fields:
                        result_text += "\n".join(valid_fields)
                    else:
                        result_text += "暂无明确信息"

                    result_text += "\n\n"

                    # 保存到数据库
                    try:
                        profile_id = db.save_user_profile(
                            external_userid=user_id,
                            profile_data=profile,
                            raw_message=text_content,
                            message_type=message_type,
                            ai_response=profile_data
                        )

                        if profile_id:
                            logger.info(f"💾 用户画像已保存到数据库 (ID: {profile_id})")
                        else:
                            logger.warning("用户画像保存失败")

                    except Exception as save_error:
                        logger.error(f"保存用户画像到数据库失败: {save_error}")
            else:
                result_text += "📋 未能从消息中提取到明确的用户画像信息。\n\n"

            result_text += "---\n✨ 由AI智能分析生成"

            print(f"✅ 消息处理完成 - 类型: {message_type}")
            return result_text

        else:
            error_msg = profile_result.get('error', '未知错误')
            print(f"❌ 用户画像分析失败: {error_msg}")
            logger.error(f"用户画像分析失败: {profile_result}")

            return f"❌ 消息分析失败: {error_msg}\n请稍后再试或联系技术支持。"

    except Exception as e:
        logger.error(f"消息处理过程中发生错误: {e}", exc_info=True)
        print(f"❌ 消息处理失败: {e}")
        return f"❌ 消息处理出现异常: {str(e)}\n请稍后再试或联系技术支持。"

def classify_and_handle_message(message: Dict[str, Any]) -> None:
    """
    处理普通消息的入口函数
    """
    process_message(message)

def handle_wechat_kf_event(message: Dict[str, Any]) -> None:
    """
    处理微信客服事件消息 - 简化版本，只获取最新一条消息（无验证码绑定）
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
        print("🔄 拉取所有消息，获取最新的...")
        logger.info("开始调用sync_kf_messages接口拉取所有消息")
        messages = wework_client.sync_kf_messages(token=token, open_kf_id=open_kfid, get_latest_only=True)
        logger.info(f"sync_kf_messages调用完成，共获取到 {len(messages) if messages else 0} 条消息")
        print(f"共获取到 {len(messages) if messages else 0} 条消息")

        if messages:
            print(f"✅ 获取到最新消息")
            logger.info(f"获取到 {len(messages)} 条最新消息")

            # 只处理最新的一条消息
            latest_msg = messages[0]

            # 转换消息格式（直接使用 external_userid，无需绑定检查）
            converted_msg = wework_client._convert_kf_message(latest_msg)

            if converted_msg:
                print(f"📝 处理消息: {latest_msg.get('msgid', '')}")

                # 处理消息并获取用户画像结果
                profile_result = process_message_and_get_result(converted_msg)

                # 发送分析结果给用户
                if profile_result:
                    external_userid = latest_msg.get('external_userid', '')
                    if external_userid:
                        try:
                            print("📤 发送分析结果给用户...")
                            wework_client.send_text_message(external_userid, open_kfid, profile_result)
                            print("✅ 分析结果已发送给用户")
                            logger.info(f"分析结果已发送给用户 {external_userid}")
                        except Exception as send_error:
                            logger.error(f"发送消息给用户失败: {send_error}")
                            print(f"❌ 发送消息失败: {send_error}")
                    else:
                        logger.warning("缺少用户ID，无法发送回复")
                        print("⚠️ 缺少用户ID，无法发送回复")
                else:
                    print("⚠️ 没有生成分析结果，不发送回复")
            else:
                logger.error("消息转换失败")
                print("❌ 消息转换失败")
        else:
            print("📭 未获取到新消息")
            logger.info("未获取到新消息")

    except Exception as e:
        logger.error(f"处理微信客服事件时发生错误: {e}", exc_info=True)
        print(f"❌ 处理微信客服事件失败: {e}")