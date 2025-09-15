# -*- coding: utf-8 -*-
"""
自定义异常类 - 定义消息处理管道中的各种异常

这个模块定义了消息处理过程中可能出现的各种异常类型。
"""


class MessagePipelineException(Exception):
    """消息处理管道基础异常类"""

    def __init__(self, message: str, context: dict = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)


class ProcessingError(MessagePipelineException):
    """处理过程中的一般错误"""
    pass


class SignatureVerificationError(MessagePipelineException):
    """签名验证失败异常"""
    pass


class DecryptionError(MessagePipelineException):
    """消息解密失败异常"""
    pass


class EncryptionError(MessagePipelineException):
    """消息加密失败异常"""
    pass


class ParsingError(MessagePipelineException):
    """消息解析失败异常"""
    pass


class ValidationError(MessagePipelineException):
    """消息验证失败异常"""
    pass


class RoutingError(MessagePipelineException):
    """消息路由失败异常"""
    pass


class HandlerNotFoundError(MessagePipelineException):
    """找不到合适的处理器异常"""
    pass


class ConfigurationError(MessagePipelineException):
    """配置错误异常"""
    pass


class PlatformError(MessagePipelineException):
    """平台相关错误异常"""
    pass


class TimeoutError(MessagePipelineException):
    """超时异常"""
    pass


class RateLimitError(MessagePipelineException):
    """限流异常"""
    pass


class AuthenticationError(MessagePipelineException):
    """认证失败异常"""
    pass


class AuthorizationError(MessagePipelineException):
    """权限不足异常"""
    pass