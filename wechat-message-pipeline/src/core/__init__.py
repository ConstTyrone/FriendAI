# -*- coding: utf-8 -*-
"""
消息处理管道核心模块

提供消息处理的核心抽象类和接口。
"""

from .context import MessageContext
from .handler import MessageHandler, ConditionalHandler, MessageTypeHandler, MessageCategoryHandler
from .pipeline import MessagePipeline
from .exceptions import (
    MessagePipelineException,
    ProcessingError,
    SignatureVerificationError,
    DecryptionError,
    EncryptionError,
    ParsingError,
    ValidationError,
    RoutingError,
    HandlerNotFoundError,
    ConfigurationError,
    PlatformError,
    TimeoutError,
    RateLimitError,
    AuthenticationError,
    AuthorizationError
)

__all__ = [
    'MessageContext',
    'MessageHandler',
    'ConditionalHandler',
    'MessageTypeHandler', 
    'MessageCategoryHandler',
    'MessagePipeline',
    'MessagePipelineException',
    'ProcessingError',
    'SignatureVerificationError',
    'DecryptionError',
    'EncryptionError',
    'ParsingError',
    'ValidationError',
    'RoutingError',
    'HandlerNotFoundError',
    'ConfigurationError',
    'PlatformError',
    'TimeoutError',
    'RateLimitError',
    'AuthenticationError',
    'AuthorizationError'
]
