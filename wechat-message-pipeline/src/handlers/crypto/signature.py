# -*- coding: utf-8 -*-
"""
签名验证处理器 - 验证微信/企微消息的数字签名

从原有系统的 wework_client.py 迁移而来的签名验证逻辑。
"""

import hashlib
import logging
from typing import Optional
from ...core import MessageHandler, MessageContext, SignatureVerificationError


logger = logging.getLogger(__name__)


class SignatureVerificationHandler(MessageHandler):
    """
    签名验证处理器

    验证来自微信/企微平台的消息签名，确保消息的完整性和来源的可信性。
    支持两种验证模式：URL验证和消息验证。
    """

    def __init__(
        self,
        token: str,
        verify_signature: bool = True,
        **kwargs
    ):
        """
        初始化签名验证处理器

        Args:
            token: 平台配置的Token
            verify_signature: 是否启用签名验证
            **kwargs: 其他参数传递给父类
        """
        super().__init__(name="SignatureVerification", priority=10, **kwargs)
        self.token = token
        self.verify_signature = verify_signature

    async def process(self, context: MessageContext) -> MessageContext:
        """
        验证消息签名

        Args:
            context: 消息上下文

        Returns:
            MessageContext: 处理后的上下文
        """
        if not self.verify_signature:
            context.add_log("签名验证已禁用，跳过验证")
            context.signature_verified = True
            return context

        # 从查询参数获取签名信息
        signature = context.query_params.get('msg_signature') or context.query_params.get('signature')
        timestamp = context.query_params.get('timestamp')
        nonce = context.query_params.get('nonce')

        if not all([signature, timestamp, nonce]):
            missing_params = []
            if not signature: missing_params.append('signature')
            if not timestamp: missing_params.append('timestamp')
            if not nonce: missing_params.append('nonce')

            error_msg = f"缺少签名验证参数: {', '.join(missing_params)}"
            context.add_error(error_msg)
            raise SignatureVerificationError(error_msg)

        context.signature = signature

        # 检查是否为URL验证请求
        echostr = context.query_params.get('echostr')
        encrypt_msg = None

        # 如果是消息回调，尝试从加密消息中获取encrypt参数
        if not echostr and context.encrypted_message:
            encrypt_msg = context.encrypted_message

        # 执行签名验证
        is_valid = self._verify_signature(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce,
            token=self.token,
            encrypt_msg=encrypt_msg
        )

        if is_valid:
            context.signature_verified = True
            context.add_log("签名验证成功")
        else:
            error_msg = "签名验证失败"
            context.add_error(error_msg)
            raise SignatureVerificationError(
                error_msg,
                context={
                    'signature': signature,
                    'timestamp': timestamp,
                    'nonce': nonce,
                    'token_prefix': self.token[:4] + '***' if self.token else None
                }
            )

        # 如果是URL验证且有echostr，需要解密echostr
        if echostr:
            context.set_metadata('url_verification', True)
            context.set_metadata('echostr', echostr)
            context.add_log("检测到URL验证请求")

        return context

    def _verify_signature(
        self,
        signature: str,
        timestamp: str,
        nonce: str,
        token: str,
        encrypt_msg: Optional[str] = None
    ) -> bool:
        """
        验证签名

        Args:
            signature: 期望的签名值
            timestamp: 时间戳
            nonce: 随机数
            token: 验证Token
            encrypt_msg: 加密消息（可选）

        Returns:
            bool: 验证是否成功
        """
        try:
            # 构建参数列表
            params = [token, timestamp, nonce]

            # 对于消息回调，可能需要包含encrypt参数
            if encrypt_msg:
                params.append(encrypt_msg)

            # 按字典序排序
            params.sort()
            sorted_params = ''.join(params)

            # 计算SHA1哈希
            sha1_hash = hashlib.sha1(sorted_params.encode()).hexdigest()

            # 记录调试信息
            logger.debug(f"签名验证参数: token={token[:4]}***, timestamp={timestamp}, nonce={nonce}")
            logger.debug(f"排序后参数: {sorted_params[:50]}...")
            logger.debug(f"计算得到的签名: {sha1_hash}")
            logger.debug(f"期望的签名: {signature}")

            return sha1_hash == signature

        except Exception as e:
            logger.error(f"签名验证过程出错: {e}")
            return False

    def can_process(self, context: MessageContext) -> bool:
        """
        检查是否可以处理该消息

        Args:
            context: 消息上下文

        Returns:
            bool: 是否可以处理
        """
        # 只有启用了验证且有相关参数才处理
        if not super().can_process(context):
            return False

        # 检查是否有签名相关的参数
        has_signature_params = any([
            context.query_params.get('msg_signature'),
            context.query_params.get('signature'),
            context.query_params.get('timestamp'),
            context.query_params.get('nonce')
        ])

        return has_signature_params