# -*- coding: utf-8 -*-
"""
消息处理管道 - 串联所有消息处理器的核心组件

这个模块定义了MessagePipeline类，它负责管理和执行整个消息处理流程。
"""

import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Callable
from .context import MessageContext
from .handler import MessageHandler
from .exceptions import (
    ProcessingError,
    HandlerNotFoundError,
    TimeoutError,
    ConfigurationError
)


logger = logging.getLogger(__name__)


class MessagePipeline:
    """
    消息处理管道

    管理和执行一系列消息处理器，提供完整的消息处理流程。
    支持处理器优先级、条件执行、错误处理、性能监控等功能。
    """

    def __init__(
        self,
        name: str = "MessagePipeline",
        timeout: float = 30.0,
        max_retries: int = 0,
        fail_fast: bool = False,
        enable_metrics: bool = True
    ):
        """
        初始化消息处理管道

        Args:
            name: 管道名称
            timeout: 处理超时时间（秒）
            max_retries: 最大重试次数
            fail_fast: 遇到错误时是否立即停止
            enable_metrics: 是否启用性能监控
        """
        self.name = name
        self.timeout = timeout
        self.max_retries = max_retries
        self.fail_fast = fail_fast
        self.enable_metrics = enable_metrics

        self._handlers: List[MessageHandler] = []
        self._middleware: List[Callable] = []
        self._error_handlers: Dict[type, Callable] = {}

        # 性能统计
        self.metrics = {
            'total_processed': 0,
            'total_errors': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0,
            'handler_count': 0
        }

        # 事件钩子
        self._hooks = {
            'before_process': [],
            'after_process': [],
            'on_error': [],
            'on_success': []
        }

    def use(self, handler: MessageHandler) -> 'MessagePipeline':
        """
        添加消息处理器

        Args:
            handler: 消息处理器实例

        Returns:
            MessagePipeline: 返回自身以支持链式调用
        """
        if not isinstance(handler, MessageHandler):
            raise ConfigurationError(f"处理器必须是MessageHandler的实例，获得: {type(handler)}")

        self._handlers.append(handler)
        # 按优先级排序
        self._handlers.sort(key=lambda h: h.priority)
        self.metrics['handler_count'] = len(self._handlers)

        logger.info(f"管道 {self.name} 添加处理器: {handler.name} (优先级: {handler.priority})")
        return self

    def remove(self, handler_name: str) -> bool:
        """
        移除指定名称的处理器

        Args:
            handler_name: 处理器名称

        Returns:
            bool: 是否成功移除
        """
        for i, handler in enumerate(self._handlers):
            if handler.name == handler_name:
                removed_handler = self._handlers.pop(i)
                self.metrics['handler_count'] = len(self._handlers)
                logger.info(f"管道 {self.name} 移除处理器: {removed_handler.name}")
                return True
        return False

    def get_handler(self, handler_name: str) -> Optional[MessageHandler]:
        """
        获取指定名称的处理器

        Args:
            handler_name: 处理器名称

        Returns:
            Optional[MessageHandler]: 处理器实例或None
        """
        for handler in self._handlers:
            if handler.name == handler_name:
                return handler
        return None

    def add_middleware(self, middleware: Callable) -> 'MessagePipeline':
        """
        添加中间件

        Args:
            middleware: 中间件函数

        Returns:
            MessagePipeline: 返回自身以支持链式调用
        """
        self._middleware.append(middleware)
        return self

    def add_error_handler(
        self,
        exception_type: type,
        handler: Callable[[Exception, MessageContext], MessageContext]
    ) -> 'MessagePipeline':
        """
        添加错误处理器

        Args:
            exception_type: 异常类型
            handler: 错误处理函数

        Returns:
            MessagePipeline: 返回自身以支持链式调用
        """
        self._error_handlers[exception_type] = handler
        return self

    def add_hook(self, event: str, hook: Callable) -> 'MessagePipeline':
        """
        添加事件钩子

        Args:
            event: 事件名称 (before_process, after_process, on_error, on_success)
            hook: 钩子函数

        Returns:
            MessagePipeline: 返回自身以支持链式调用
        """
        if event in self._hooks:
            self._hooks[event].append(hook)
        else:
            logger.warning(f"未知的钩子事件: {event}")
        return self

    async def process(self, context: MessageContext) -> MessageContext:
        """
        处理消息

        Args:
            context: 消息上下文

        Returns:
            MessageContext: 处理后的消息上下文

        Raises:
            TimeoutError: 处理超时
            ProcessingError: 处理失败
        """
        start_time = time.time()

        try:
            # 执行前置钩子
            await self._execute_hooks('before_process', context)

            # 设置超时
            result = await asyncio.wait_for(
                self._process_with_retries(context),
                timeout=self.timeout
            )

            # 执行成功钩子
            await self._execute_hooks('on_success', result)

            # 执行后置钩子
            await self._execute_hooks('after_process', result)

            # 更新性能统计
            if self.enable_metrics:
                processing_time = time.time() - start_time
                self._update_metrics(processing_time, success=True)

            return result

        except asyncio.TimeoutError:
            error = TimeoutError(f"消息处理超时 ({self.timeout}s)")
            context.add_error(str(error))
            await self._execute_hooks('on_error', context)

            if self.enable_metrics:
                processing_time = time.time() - start_time
                self._update_metrics(processing_time, success=False)

            raise error

        except Exception as e:
            context.add_error(f"管道处理失败: {str(e)}")
            await self._execute_hooks('on_error', context)

            if self.enable_metrics:
                processing_time = time.time() - start_time
                self._update_metrics(processing_time, success=False)

            # 尝试使用错误处理器
            error_handler = self._get_error_handler(type(e))
            if error_handler:
                try:
                    return await error_handler(e, context)
                except Exception as handler_error:
                    logger.error(f"错误处理器执行失败: {handler_error}")

            if self.fail_fast:
                raise

            return context

    async def _process_with_retries(self, context: MessageContext) -> MessageContext:
        """带重试的处理逻辑"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    context.add_log(f"重试处理，第 {attempt} 次尝试")

                return await self._execute_handlers(context)

            except Exception as e:
                last_exception = e
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # 指数退避
                    context.add_log(f"处理失败，{wait_time}s 后重试: {str(e)}")
                    await asyncio.sleep(wait_time)
                else:
                    context.add_error(f"重试 {self.max_retries} 次后仍然失败")

        if last_exception:
            raise last_exception

    async def _execute_handlers(self, context: MessageContext) -> MessageContext:
        """执行所有处理器"""
        if not self._handlers:
            raise HandlerNotFoundError("管道中没有可用的处理器")

        current_context = context

        for handler in self._handlers:
            # 应用中间件
            for middleware in self._middleware:
                current_context = await middleware(current_context)

            # 执行处理器
            current_context = await handler.execute(current_context)

            # 如果处理过程中出现错误且启用了fail_fast，停止处理
            if self.fail_fast and current_context.has_error:
                break

        return current_context

    async def _execute_hooks(self, event: str, context: MessageContext) -> None:
        """执行事件钩子"""
        for hook in self._hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(context)
                else:
                    hook(context)
            except Exception as e:
                logger.warning(f"钩子函数执行失败 ({event}): {e}")

    def _get_error_handler(self, exception_type: type) -> Optional[Callable]:
        """获取异常处理器"""
        # 精确匹配
        if exception_type in self._error_handlers:
            return self._error_handlers[exception_type]

        # 查找父类匹配
        for exc_type, handler in self._error_handlers.items():
            if issubclass(exception_type, exc_type):
                return handler

        return None

    def _update_metrics(self, processing_time: float, success: bool) -> None:
        """更新性能统计"""
        self.metrics['total_processed'] += 1
        self.metrics['total_processing_time'] += processing_time

        if not success:
            self.metrics['total_errors'] += 1

        # 计算平均处理时间
        if self.metrics['total_processed'] > 0:
            self.metrics['avg_processing_time'] = (
                self.metrics['total_processing_time'] / self.metrics['total_processed']
            )

    def get_metrics(self) -> Dict[str, Any]:
        """获取管道性能指标"""
        handler_metrics = [handler.get_metrics() for handler in self._handlers]

        return {
            'pipeline_name': self.name,
            'pipeline_metrics': {
                **self.metrics,
                'error_rate': (
                    self.metrics['total_errors'] / self.metrics['total_processed']
                    if self.metrics['total_processed'] > 0 else 0
                ),
                'timeout': self.timeout,
                'max_retries': self.max_retries,
                'fail_fast': self.fail_fast
            },
            'handler_metrics': handler_metrics
        }

    def reset_metrics(self) -> None:
        """重置性能统计"""
        self.metrics = {
            'total_processed': 0,
            'total_errors': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0,
            'handler_count': len(self._handlers)
        }

        # 重置所有处理器的统计
        for handler in self._handlers:
            handler.reset_metrics()

    def get_handler_chain(self) -> List[str]:
        """获取处理器链信息"""
        return [f"{h.name}(p={h.priority})" for h in self._handlers]

    def __str__(self) -> str:
        return f"MessagePipeline(name={self.name}, handlers={len(self._handlers)})"

    def __repr__(self) -> str:
        return f"<MessagePipeline: {self.name}, {len(self._handlers)} handlers>"