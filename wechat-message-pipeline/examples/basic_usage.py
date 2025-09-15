#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基础使用示例 - 演示消息处理管道的基本用法

这个示例展示了如何创建和配置消息处理管道，以及如何处理微信/企微消息。
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import MessagePipeline, MessageContext
from src.handlers.crypto import SignatureVerificationHandler, MessageDecryptionHandler
from src.handlers.parsing import XMLMessageParser


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_basic_pipeline():
    """演示基础的消息处理管道"""
    print("=" * 60)
    print("🚀 微信消息处理管道 - 基础使用示例")
    print("=" * 60)

    # 1. 创建消息处理管道
    pipeline = MessagePipeline(
        name="基础演示管道",
        timeout=10.0,
        enable_metrics=True
    )

    # 2. 配置处理器（按优先级顺序）
    # 注意：这里使用的是示例配置，实际使用时需要替换为真实的配置
    pipeline.use(SignatureVerificationHandler(
        token="demo_token_123456",
        verify_signature=False  # 演示时禁用验证
    ))

    pipeline.use(MessageDecryptionHandler(
        encoding_aes_key="demo_aes_key_base64_encoded_here_32_chars"
    ))

    pipeline.use(XMLMessageParser())

    print(f"✅ 已配置管道，包含 {len(pipeline._handlers)} 个处理器")
    print(f"📋 处理器链: {' → '.join(pipeline.get_handler_chain())}")

    # 3. 创建示例消息上下文
    demo_contexts = [
        create_url_verification_context(),
        create_text_message_context(),
        create_event_message_context()
    ]

    # 4. 处理各种类型的消息
    for i, context in enumerate(demo_contexts, 1):
        print(f"\n📨 处理示例消息 {i}: {context.get_metadata('demo_type')}")
        print("-" * 40)

        try:
            # 处理消息
            result = await pipeline.process(context)

            # 显示处理结果
            print_processing_result(result)

        except Exception as e:
            print(f"❌ 处理失败: {e}")

    # 5. 显示性能统计
    print_pipeline_metrics(pipeline)


def create_url_verification_context() -> MessageContext:
    """创建URL验证请求的上下文"""
    context = MessageContext(
        platform="wework",
        query_params={
            "msg_signature": "demo_signature",
            "timestamp": "1234567890",
            "nonce": "demo_nonce",
            "echostr": "demo_encrypted_echostr"
        }
    )
    context.set_metadata('demo_type', 'URL验证请求')
    return context


def create_text_message_context() -> MessageContext:
    """创建文本消息的上下文"""
    # 模拟一个简单的XML消息（未加密）
    demo_xml = """<xml>
    <ToUserName><![CDATA[toUser]]></ToUserName>
    <FromUserName><![CDATA[fromUser123]]></FromUserName>
    <CreateTime>1234567890</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[Hello, World!]]></Content>
    <MsgId>123456789</MsgId>
</xml>"""

    context = MessageContext(
        platform="wework",
        query_params={
            "msg_signature": "demo_signature",
            "timestamp": "1234567890",
            "nonce": "demo_nonce"
        },
        decrypted_message=demo_xml  # 直接设置解密后的消息，跳过解密步骤
    )
    context.set_metadata('demo_type', '文本消息')
    return context


def create_event_message_context() -> MessageContext:
    """创建事件消息的上下文"""
    demo_xml = """<xml>
    <ToUserName><![CDATA[toUser]]></ToUserName>
    <FromUserName><![CDATA[fromUser456]]></FromUserName>
    <CreateTime>1234567890</CreateTime>
    <MsgType><![CDATA[event]]></MsgType>
    <Event><![CDATA[enter_session]]></Event>
    <ExternalUserId><![CDATA[external_user_123]]></ExternalUserId>
</xml>"""

    context = MessageContext(
        platform="wechat_kf",
        query_params={
            "signature": "demo_signature",
            "timestamp": "1234567890",
            "nonce": "demo_nonce"
        },
        decrypted_message=demo_xml
    )
    context.set_metadata('demo_type', '事件消息')
    return context


def print_processing_result(context: MessageContext):
    """打印处理结果"""
    print(f"🆔 请求ID: {context.request_id}")
    print(f"🏗️  平台: {context.platform}")
    print(f"👤 用户ID: {context.user_id or '未知'}")
    print(f"📝 消息类型: {context.message_type or '未知'}")
    print(f"📊 签名验证: {'✅' if context.signature_verified else '❌'}")

    if context.content_text:
        print(f"💬 消息内容: {context.content_text}")

    if context.external_user_id:
        print(f"🏢 企微用户ID: {context.external_user_id}")

    # 显示处理日志
    if context.processing_logs:
        print("📄 处理日志:")
        for log in context.processing_logs[-3:]:  # 只显示最后3条
            print(f"    {log}")

    # 显示错误信息
    if context.errors:
        print("⚠️  错误信息:")
        for error in context.errors:
            print(f"    ❌ {error}")

    # 显示统计信息
    if context.processing_stats:
        print("📈 处理统计:")
        for key, value in context.processing_stats.items():
            if isinstance(value, float):
                print(f"    {key}: {value:.3f}s")
            else:
                print(f"    {key}: {value}")


def print_pipeline_metrics(pipeline: MessagePipeline):
    """打印管道性能指标"""
    print("\n" + "=" * 60)
    print("📊 管道性能统计")
    print("=" * 60)

    metrics = pipeline.get_metrics()
    pipeline_metrics = metrics['pipeline_metrics']

    print(f"🔢 总处理数: {pipeline_metrics['total_processed']}")
    print(f"❌ 错误数: {pipeline_metrics['total_errors']}")
    print(f"⏱️  总处理时间: {pipeline_metrics['total_processing_time']:.3f}s")
    print(f"📊 平均处理时间: {pipeline_metrics['avg_processing_time']:.3f}s")
    print(f"📉 错误率: {pipeline_metrics['error_rate']:.2%}")

    print("\n📋 处理器性能:")
    for handler_metric in metrics['handler_metrics']:
        print(f"  {handler_metric['name']}:")
        print(f"    处理数: {handler_metric['processed_count']}")
        print(f"    平均时间: {handler_metric['avg_processing_time']:.3f}s")
        print(f"    错误率: {handler_metric['error_rate']:.2%}")


async def demo_error_handling():
    """演示错误处理"""
    print("\n" + "=" * 60)
    print("🔧 错误处理演示")
    print("=" * 60)

    # 创建一个会产生错误的管道
    pipeline = MessagePipeline(
        name="错误演示管道",
        fail_fast=False  # 不立即停止，继续处理
    )

    # 添加一个配置错误的处理器
    pipeline.use(MessageDecryptionHandler(
        encoding_aes_key="invalid_key"  # 无效的密钥
    ))

    # 创建包含加密消息的上下文
    context = MessageContext(
        platform="wework",
        encrypted_message="invalid_encrypted_content"
    )
    context.set_metadata('demo_type', '错误处理演示')

    try:
        result = await pipeline.process(context)
        print_processing_result(result)
    except Exception as e:
        print(f"❌ 管道处理失败: {e}")


async def demo_conditional_processing():
    """演示条件处理"""
    print("\n" + "=" * 60)
    print("🎯 条件处理演示")
    print("=" * 60)

    from src.core import MessageTypeHandler

    # 创建只处理特定类型消息的处理器
    class TextOnlyHandler(MessageTypeHandler):
        def __init__(self):
            super().__init__(
                message_types=['text'],
                name="TextOnlyHandler",
                priority=40
            )

        async def process(self, context: MessageContext) -> MessageContext:
            context.add_log("正在处理文本消息")
            context.set_metadata('processed_by_text_handler', True)
            return context

    # 创建管道
    pipeline = MessagePipeline(name="条件处理演示管道")
    pipeline.use(XMLMessageParser())
    pipeline.use(TextOnlyHandler())

    # 测试不同类型的消息
    test_contexts = [
        create_text_message_context(),
        create_event_message_context()
    ]

    for context in test_contexts:
        print(f"\n🧪 测试 {context.get_metadata('demo_type')}")
        result = await pipeline.process(context)

        processed = result.get_metadata('processed_by_text_handler', False)
        print(f"📝 是否被文本处理器处理: {'✅' if processed else '❌'}")


if __name__ == "__main__":
    async def main():
        """主函数"""
        try:
            await demo_basic_pipeline()
            await demo_error_handling()
            await demo_conditional_processing()

            print("\n" + "=" * 60)
            print("🎉 演示完成！")
            print("=" * 60)

        except KeyboardInterrupt:
            print("\n👋 演示被用户中断")
        except Exception as e:
            logger.error(f"演示过程中发生错误: {e}", exc_info=True)

    # 运行演示
    asyncio.run(main())