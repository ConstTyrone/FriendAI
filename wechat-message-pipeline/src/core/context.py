# -*- coding: utf-8 -*-
"""
消息上下文类 - 贯穿整个消息处理管道的上下文对象

这个模块定义了MessageContext类，它携带着消息在处理管道中流转时的所有相关信息。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


@dataclass
class MessageContext:
    """
    消息处理上下文类

    这个类在整个消息处理管道中传递，包含原始消息、解密后的消息、
    处理结果、用户信息、平台信息等所有相关数据。
    """

    # 请求相关信息
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    platform: Optional[str] = None  # 'wework' 或 'wechat_kf'

    # 原始请求数据
    raw_body: Optional[str] = None
    query_params: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)

    # 验证相关
    signature: Optional[str] = None
    signature_verified: bool = False

    # 消息解密和解析
    encrypted_message: Optional[str] = None
    decrypted_message: Optional[str] = None
    parsed_message: Dict[str, Any] = field(default_factory=dict)

    # 消息分类和路由
    message_type: Optional[str] = None  # 'text', 'voice', 'image', 'file', 'event', etc.
    message_category: Optional[str] = None  # 'verify_code', 'chat', 'event', 'media'
    content_text: Optional[str] = None

    # 用户信息
    user_id: Optional[str] = None  # FromUserName
    external_user_id: Optional[str] = None  # 企微的external_userid
    user_info: Dict[str, Any] = field(default_factory=dict)

    # 业务处理结果
    business_result: Dict[str, Any] = field(default_factory=dict)
    processing_logs: List[str] = field(default_factory=list)

    # 响应数据
    response_data: Dict[str, Any] = field(default_factory=dict)
    response_message: Optional[str] = None
    should_reply: bool = False

    # 错误处理
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    has_error: bool = False

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_stats: Dict[str, float] = field(default_factory=dict)

    def add_log(self, message: str, level: str = 'info') -> None:
        """添加处理日志"""
        log_entry = f"[{level.upper()}] {datetime.now().isoformat()}: {message}"
        self.processing_logs.append(log_entry)

    def add_error(self, error: str) -> None:
        """添加错误信息"""
        self.errors.append(error)
        self.has_error = True
        self.add_log(f"ERROR: {error}", 'error')

    def add_warning(self, warning: str) -> None:
        """添加警告信息"""
        self.warnings.append(warning)
        self.add_log(f"WARNING: {warning}", 'warning')

    def set_processing_stat(self, key: str, value: float) -> None:
        """设置处理统计信息"""
        self.processing_stats[key] = value

    def get_processing_stat(self, key: str, default: float = 0.0) -> float:
        """获取处理统计信息"""
        return self.processing_stats.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据"""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)

    def set_user_info(self, key: str, value: Any) -> None:
        """设置用户信息"""
        self.user_info[key] = value

    def get_user_info(self, key: str, default: Any = None) -> Any:
        """获取用户信息"""
        return self.user_info.get(key, default)

    def set_business_result(self, key: str, value: Any) -> None:
        """设置业务处理结果"""
        self.business_result[key] = value

    def get_business_result(self, key: str, default: Any = None) -> Any:
        """获取业务处理结果"""
        return self.business_result.get(key, default)

    def is_message_type(self, *types: str) -> bool:
        """检查消息类型是否匹配"""
        return self.message_type in types if self.message_type else False

    def is_message_category(self, *categories: str) -> bool:
        """检查消息分类是否匹配"""
        return self.message_category in categories if self.message_category else False

    def has_parsed_field(self, field: str) -> bool:
        """检查解析后的消息是否包含某个字段"""
        return field in self.parsed_message

    def get_parsed_field(self, field: str, default: Any = None) -> Any:
        """获取解析后消息的字段值"""
        return self.parsed_message.get(field, default)

    def set_parsed_field(self, field: str, value: Any) -> None:
        """设置解析后消息的字段值"""
        self.parsed_message[field] = value

    def summary(self) -> Dict[str, Any]:
        """获取上下文摘要信息，用于日志记录"""
        return {
            'request_id': self.request_id,
            'platform': self.platform,
            'message_type': self.message_type,
            'message_category': self.message_category,
            'user_id': self.user_id,
            'has_error': self.has_error,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'processing_logs_count': len(self.processing_logs),
            'signature_verified': self.signature_verified,
            'should_reply': self.should_reply
        }