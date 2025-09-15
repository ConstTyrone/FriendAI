# -*- coding: utf-8 -*-
"""
XML消息解析处理器 - 解析微信/企微的XML消息格式

从原有系统的 message_handler.py 中的 parse_message 函数迁移而来。
"""

import xml.etree.ElementTree as ET
import logging
from typing import Dict, Any, Optional
from ...core import MessageHandler, MessageContext, ParsingError


logger = logging.getLogger(__name__)


class XMLMessageParser(MessageHandler):
    """
    XML消息解析处理器

    解析微信/企微平台发送的XML格式消息，提取消息的各个字段。
    """

    def __init__(self, **kwargs):
        """
        初始化XML消息解析处理器

        Args:
            **kwargs: 其他参数传递给父类
        """
        super().__init__(name="XMLMessageParser", priority=30, **kwargs)

    async def process(self, context: MessageContext) -> MessageContext:
        """
        解析XML消息

        Args:
            context: 消息上下文

        Returns:
            MessageContext: 处理后的上下文
        """
        # 如果是URL验证请求，不需要解析XML
        if context.get_metadata('url_verification'):
            context.add_log("URL验证请求，跳过XML解析")
            return context

        # 检查是否有解密后的消息
        if not context.decrypted_message:
            context.add_warning("没有找到需要解析的XML消息")
            return context

        try:
            # 解析XML消息
            parsed_data = self._parse_xml_message(context.decrypted_message)

            # 更新上下文
            context.parsed_message = parsed_data
            context.add_log(f"XML消息解析成功，包含 {len(parsed_data)} 个字段")

            # 提取关键信息
            self._extract_key_fields(context, parsed_data)

            # 记录统计信息
            context.set_processing_stat('parsed_fields_count', len(parsed_data))

        except Exception as e:
            error_msg = f"XML消息解析失败: {str(e)}"
            context.add_error(error_msg)
            raise ParsingError(
                error_msg,
                context={
                    'message_length': len(context.decrypted_message) if context.decrypted_message else 0,
                    'message_preview': context.decrypted_message[:200] if context.decrypted_message else None
                }
            )

        return context

    def _parse_xml_message(self, xml_data: str) -> Dict[str, Any]:
        """
        解析XML消息数据的核心逻辑

        Args:
            xml_data: XML消息内容

        Returns:
            Dict[str, Any]: 解析后的消息字段

        Raises:
            ParsingError: 解析失败时抛出
        """
        try:
            # 清理XML数据
            xml_data = xml_data.strip()

            # 解析XML
            root = ET.fromstring(xml_data)
            message = {}

            # 提取所有子元素
            for child in root:
                if child.text:
                    # 去除首尾空白字符
                    field_value = child.text.strip()
                    message[child.tag] = field_value

                    logger.debug(f"解析字段: {child.tag} = {field_value[:50]}...")

            # 如果没有解析到任何字段，记录警告
            if not message:
                logger.warning("XML解析成功但没有提取到任何字段")

            return message

        except ET.ParseError as e:
            logger.error(f"XML格式错误: {e}")
            logger.error(f"XML内容预览: {xml_data[:500]}...")
            raise ParsingError(f"XML格式错误: {e}")

        except Exception as e:
            logger.error(f"XML解析过程出错: {e}", exc_info=True)
            raise ParsingError(f"XML解析失败: {e}")

    def _extract_key_fields(self, context: MessageContext, parsed_data: Dict[str, Any]) -> None:
        """
        从解析后的数据中提取关键字段

        Args:
            context: 消息上下文
            parsed_data: 解析后的消息数据
        """
        # 提取用户ID
        user_id = parsed_data.get('FromUserName')
        if user_id:
            context.user_id = user_id
            context.add_log(f"提取用户ID: {user_id}")

        # 提取消息类型
        msg_type = parsed_data.get('MsgType')
        if msg_type:
            context.message_type = msg_type
            context.add_log(f"提取消息类型: {msg_type}")

        # 提取消息ID
        msg_id = parsed_data.get('MsgId')
        if msg_id:
            context.set_metadata('message_id', msg_id)

        # 提取时间戳
        create_time = parsed_data.get('CreateTime')
        if create_time:
            context.set_metadata('create_time', create_time)

        # 提取企微相关字段
        external_user_id = parsed_data.get('ExternalUserId')
        if external_user_id:
            context.external_user_id = external_user_id
            context.add_log(f"提取企微用户ID: {external_user_id}")

        # 提取内容文本（针对文本消息）
        if msg_type == 'text':
            content = parsed_data.get('Content')
            if content:
                context.content_text = content
                context.add_log(f"提取文本内容: {content[:50]}...")

        # 提取事件信息
        if msg_type == 'event':
            event_type = parsed_data.get('Event')
            if event_type:
                context.set_metadata('event_type', event_type)
                context.add_log(f"提取事件类型: {event_type}")

        # 提取媒体信息
        if msg_type in ['image', 'voice', 'video', 'file']:
            media_id = parsed_data.get('MediaId')
            if media_id:
                context.set_metadata('media_id', media_id)
                context.add_log(f"提取媒体ID: {media_id}")

        # 提取位置信息
        if msg_type == 'location':
            location_x = parsed_data.get('Location_X')
            location_y = parsed_data.get('Location_Y')
            if location_x and location_y:
                context.set_metadata('location', {
                    'latitude': location_y,
                    'longitude': location_x,
                    'scale': parsed_data.get('Scale'),
                    'label': parsed_data.get('Label')
                })

        # 记录所有提取的关键字段
        key_fields = ['FromUserName', 'MsgType', 'MsgId', 'CreateTime', 'ExternalUserId']
        extracted_fields = [field for field in key_fields if field in parsed_data]
        context.set_metadata('extracted_key_fields', extracted_fields)

    def can_process(self, context: MessageContext) -> bool:
        """
        检查是否可以处理该消息

        Args:
            context: 消息上下文

        Returns:
            bool: 是否可以处理
        """
        if not super().can_process(context):
            return False

        # 只有在有解密消息或者是URL验证请求时才处理
        return (
            context.decrypted_message or
            context.get_metadata('url_verification')
        )