# -*- coding: utf-8 -*-
"""
消息处理器基类 - 定义统一的消息处理接口

这个模块定义了MessageHandler抽象基类，所有具体的处理器都需要继承并实现它。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import asyncio
import time
import logging
from .context import MessageContext


logger = logging.getLogger(__name__)


class MessageHandler(ABC):
    """
    消息处理器抽象基类

    所有的消息处理器都必须继承这个类并实现process方法。
    处理器可以是同步的或异步的，支持条件执行、优先级控制等功能。
    """

    def __init__(
        self,
        name: Optional[str] = None,
        priority: int = 50,
        enabled: bool = True,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化消息处理器

        Args:
            name: 处理器名称，如果不指定则使用类名
            priority: 优先级，数字越小优先级越高 (1-100)
            enabled: 是否启用
            config: 处理器配置
        """
        self.name = name or self.__class__.__name__
        self.priority = priority
        self.enabled = enabled
        self.config = config or {}
        self.metrics = {
            'processed_count': 0,
            'error_count': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0
        }

    @abstractmethod
    async def process(self, context: MessageContext) -> MessageContext:
        """
        处理消息的抽象方法

        Args:
            context: 消息上下文

        Returns:
            MessageContext: 处理后的消息上下文

        Raises:
            ProcessingError: 处理过程中的错误
        """
        pass

    def can_process(self, context: MessageContext) -> bool:
        """
        判断是否可以处理该消息

        Args:
            context: 消息上下文

        Returns:
            bool: 是否可以处理
        """
        return self.enabled

    async def execute(self, context: MessageContext) -> MessageContext:
        """
        执行处理器，包含性能统计和错误处理

        Args:
            context: 消息上下文

        Returns:
            MessageContext: 处理后的消息上下文
        """
        if not self.can_process(context):
            logger.debug(f"处理器 {self.name} 跳过处理消息 {context.request_id}")
            return context

        start_time = time.time()
        try:
            logger.debug(f"处理器 {self.name} 开始处理消息 {context.request_id}")
            context.add_log(f"开始执行处理器: {self.name}")

            # 执行具体的处理逻辑
            result_context = await self.process(context)

            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_metrics(processing_time, success=True)

            result_context.set_processing_stat(f"{self.name}_processing_time", processing_time)
            result_context.add_log(f"处理器 {self.name} 执行完成，耗时 {processing_time:.3f}s")

            logger.debug(f"处理器 {self.name} 处理完成，耗时 {processing_time:.3f}s")
            return result_context

        except Exception as e:
            processing_time = time.time() - start_time
            self._update_metrics(processing_time, success=False)

            error_msg = f"处理器 {self.name} 执行失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            context.add_error(error_msg)

            # 根据配置决定是否继续处理
            if self.config.get('stop_on_error', False):
                raise

            return context

    def _update_metrics(self, processing_time: float, success: bool) -> None:
        """更新处理器指标"""
        self.metrics['processed_count'] += 1
        self.metrics['total_processing_time'] += processing_time

        if not success:
            self.metrics['error_count'] += 1

        # 计算平均处理时间
        if self.metrics['processed_count'] > 0:
            self.metrics['avg_processing_time'] = (
                self.metrics['total_processing_time'] / self.metrics['processed_count']
            )

    def get_metrics(self) -> Dict[str, Any]:
        """获取处理器指标"""
        return {
            'name': self.name,
            'priority': self.priority,
            'enabled': self.enabled,
            **self.metrics,
            'error_rate': (
                self.metrics['error_count'] / self.metrics['processed_count']
                if self.metrics['processed_count'] > 0 else 0
            )
        }

    def reset_metrics(self) -> None:
        """重置处理器指标"""
        self.metrics = {
            'processed_count': 0,
            'error_count': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0
        }

    def configure(self, config: Dict[str, Any]) -> None:
        """更新处理器配置"""
        self.config.update(config)

    def enable(self) -> None:
        """启用处理器"""
        self.enabled = True

    def disable(self) -> None:
        """禁用处理器"""
        self.enabled = False

    def __str__(self) -> str:
        return f"{self.name}(priority={self.priority}, enabled={self.enabled})"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"


class ConditionalHandler(MessageHandler):
    """
    条件处理器基类

    提供基于条件的处理器，只有满足特定条件时才会执行处理逻辑。
    """

    def __init__(
        self,
        condition_func: Optional[callable] = None,
        **kwargs
    ):
        """
        初始化条件处理器

        Args:
            condition_func: 条件函数，接受MessageContext，返回bool
            **kwargs: 其他参数传递给父类
        """
        super().__init__(**kwargs)
        self.condition_func = condition_func

    def can_process(self, context: MessageContext) -> bool:
        """检查是否满足处理条件"""
        if not super().can_process(context):
            return False

        if self.condition_func:
            try:
                return self.condition_func(context)
            except Exception as e:
                logger.warning(f"条件检查失败: {e}")
                return False

        return True


class MessageTypeHandler(ConditionalHandler):
    """
    基于消息类型的处理器

    只处理特定类型的消息。
    """

    def __init__(
        self,
        message_types: List[str],
        **kwargs
    ):
        """
        初始化消息类型处理器

        Args:
            message_types: 支持的消息类型列表
            **kwargs: 其他参数传递给父类
        """
        self.message_types = message_types

        def type_condition(context: MessageContext) -> bool:
            return context.is_message_type(*self.message_types)

        super().__init__(condition_func=type_condition, **kwargs)


class MessageCategoryHandler(ConditionalHandler):
    """
    基于消息分类的处理器

    只处理特定分类的消息。
    """

    def __init__(
        self,
        message_categories: List[str],
        **kwargs
    ):
        """
        初始化消息分类处理器

        Args:
            message_categories: 支持的消息分类列表
            **kwargs: 其他参数传递给父类
        """
        self.message_categories = message_categories

        def category_condition(context: MessageContext) -> bool:
            return context.is_message_category(*self.message_categories)

        super().__init__(condition_func=category_condition, **kwargs)