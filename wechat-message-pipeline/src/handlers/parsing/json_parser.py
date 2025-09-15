# -*- coding: utf-8 -*-
"""
JSON消息解析处理器 - 解析JSON格式的消息

为了扩展性而提供的JSON消息解析器，可用于处理其他平台或API的JSON消息。
"""

import json
import logging
from typing import Dict, Any
from ...core import MessageHandler, MessageContext, ParsingError


logger = logging.getLogger(__name__)


class JSONMessageParser(MessageHandler):
    """
    JSON消息解析处理器

    解析JSON格式的消息内容，提取消息的各个字段。
    主要用于扩展性，支持其他可能的消息格式。
    """

    def __init__(self, **kwargs):
        """
        初始化JSON消息解析处理器

        Args:
            **kwargs: 其他参数传递给父类
        """
        super().__init__(name="JSONMessageParser", priority=31, **kwargs)

    async def process(self, context: MessageContext) -> MessageContext:
        """
        解析JSON消息

        Args:
            context: 消息上下文

        Returns:
            MessageContext: 处理后的上下文
        """
        # 检查是否有需要解析的消息
        message_to_parse = context.decrypted_message or context.raw_body

        if not message_to_parse:
            context.add_warning("没有找到需要解析的JSON消息")
            return context

        # 检查是否看起来像JSON
        if not self._looks_like_json(message_to_parse):
            context.add_log("消息内容不像JSON格式，跳过JSON解析")
            return context

        try:
            # 解析JSON消息
            parsed_data = self._parse_json_message(message_to_parse)

            # 更新上下文（如果还没有解析数据或者JSON解析的数据更完整）
            if not context.parsed_message or len(parsed_data) > len(context.parsed_message):
                context.parsed_message = parsed_data
                context.add_log(f"JSON消息解析成功，包含 {len(parsed_data)} 个字段")

                # 提取关键信息
                self._extract_key_fields(context, parsed_data)

                # 记录统计信息
                context.set_processing_stat('json_parsed_fields_count', len(parsed_data))

        except Exception as e:
            # JSON解析失败不是致命错误，只记录警告
            warning_msg = f"JSON消息解析失败: {str(e)}"
            context.add_warning(warning_msg)
            logger.debug(warning_msg)

        return context

    def _looks_like_json(self, data: str) -> bool:
        """
        检查数据是否看起来像JSON格式

        Args:
            data: 要检查的数据

        Returns:
            bool: 是否看起来像JSON
        """
        if not data:
            return False

        data = data.strip()

        # 简单检查：以 { 或 [ 开头，以 } 或 ] 结尾
        return (
            (data.startswith('{') and data.endswith('}')) or
            (data.startswith('[') and data.endswith(']'))
        )

    def _parse_json_message(self, json_data: str) -> Dict[str, Any]:
        """
        解析JSON消息数据的核心逻辑

        Args:
            json_data: JSON消息内容

        Returns:
            Dict[str, Any]: 解析后的消息字段

        Raises:
            ParsingError: 解析失败时抛出
        """
        try:
            # 清理JSON数据
            json_data = json_data.strip()

            # 解析JSON
            parsed = json.loads(json_data)

            # 如果顶层是数组，尝试取第一个对象
            if isinstance(parsed, list) and len(parsed) > 0:
                if isinstance(parsed[0], dict):
                    parsed = parsed[0]
                    logger.debug("从JSON数组中提取第一个对象")

            # 如果不是字典，转换为字典
            if not isinstance(parsed, dict):
                parsed = {'data': parsed}

            logger.debug(f"JSON解析成功，字段数: {len(parsed)}")

            return parsed

        except json.JSONDecodeError as e:
            logger.debug(f"JSON格式错误: {e}")
            raise ParsingError(f"JSON格式错误: {e}")

        except Exception as e:
            logger.error(f"JSON解析过程出错: {e}", exc_info=True)
            raise ParsingError(f"JSON解析失败: {e}")

    def _extract_key_fields(self, context: MessageContext, parsed_data: Dict[str, Any]) -> None:
        """
        从解析后的JSON数据中提取关键字段

        Args:
            context: 消息上下文
            parsed_data: 解析后的消息数据
        """
        # 尝试提取常见的字段名变体
        user_id_fields = ['user_id', 'userId', 'from_user', 'fromUser', 'sender_id', 'senderId']
        for field in user_id_fields:
            if field in parsed_data and not context.user_id:
                context.user_id = str(parsed_data[field])
                context.add_log(f"从JSON提取用户ID: {context.user_id}")
                break

        # 提取消息类型
        type_fields = ['type', 'message_type', 'messageType', 'msg_type', 'msgType']
        for field in type_fields:
            if field in parsed_data and not context.message_type:
                context.message_type = str(parsed_data[field])
                context.add_log(f"从JSON提取消息类型: {context.message_type}")
                break

        # 提取内容文本
        content_fields = ['content', 'text', 'message', 'body', 'data']
        for field in content_fields:
            if field in parsed_data and not context.content_text:
                content = parsed_data[field]
                if isinstance(content, str):
                    context.content_text = content
                    context.add_log(f"从JSON提取文本内容: {content[:50]}...")
                    break

        # 提取时间戳
        time_fields = ['timestamp', 'time', 'create_time', 'createTime', 'created_at']
        for field in time_fields:
            if field in parsed_data:
                context.set_metadata('create_time', parsed_data[field])
                break

        # 提取消息ID
        id_fields = ['id', 'message_id', 'messageId', 'msg_id', 'msgId']
        for field in id_fields:
            if field in parsed_data:
                context.set_metadata('message_id', parsed_data[field])
                break

        # 记录JSON特有的元数据
        context.set_metadata('parsed_as_json', True)
        context.set_metadata('json_top_level_keys', list(parsed_data.keys()))

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

        # 有消息内容且还没有解析结果，或者明确指定要尝试JSON解析
        message_to_parse = context.decrypted_message or context.raw_body
        return bool(message_to_parse) and (
            not context.parsed_message or
            context.get_metadata('force_json_parsing', False)
        )