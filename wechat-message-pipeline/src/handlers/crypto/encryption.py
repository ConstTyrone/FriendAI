# -*- coding: utf-8 -*-
"""
消息加密处理器 - 对回复消息进行AES加密

用于对发送给微信/企微平台的回复消息进行加密处理。
"""

import base64
import os
import time
import logging
from typing import Optional
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from ...core import MessageHandler, MessageContext, EncryptionError


logger = logging.getLogger(__name__)


class MessageEncryptionHandler(MessageHandler):
    """
    消息加密处理器

    对回复消息进行AES加密，以符合微信/企微平台的安全要求。
    """

    def __init__(
        self,
        encoding_aes_key: str,
        corp_id: Optional[str] = None,
        **kwargs
    ):
        """
        初始化消息加密处理器

        Args:
            encoding_aes_key: AES加密密钥（Base64编码）
            corp_id: 企业ID（某些情况下需要）
            **kwargs: 其他参数传递给父类
        """
        super().__init__(name="MessageEncryption", priority=80, **kwargs)
        self.encoding_aes_key = encoding_aes_key
        self.corp_id = corp_id

    async def process(self, context: MessageContext) -> MessageContext:
        """
        加密回复消息

        Args:
            context: 消息上下文

        Returns:
            MessageContext: 处理后的上下文
        """
        # 只有需要回复且有回复消息时才加密
        if not context.should_reply or not context.response_message:
            context.add_log("无需加密回复消息")
            return context

        try:
            # 加密回复消息
            encrypted_message = self._encrypt_message(context.response_message)

            # 构建加密回复的XML格式
            encrypted_xml = self._build_encrypted_response(encrypted_message)

            # 更新上下文
            context.response_data['encrypted_message'] = encrypted_message
            context.response_data['encrypted_xml'] = encrypted_xml
            context.set_metadata('message_encrypted', True)

            context.add_log("回复消息加密成功")

        except Exception as e:
            error_msg = f"消息加密失败: {str(e)}"
            context.add_error(error_msg)
            raise EncryptionError(
                error_msg,
                context={
                    'message_length': len(context.response_message) if context.response_message else 0,
                    'key_configured': bool(self.encoding_aes_key)
                }
            )

        return context

    def _encrypt_message(self, message: str) -> str:
        """
        加密消息的核心逻辑

        Args:
            message: 要加密的消息内容

        Returns:
            str: 加密后的Base64编码字符串

        Raises:
            EncryptionError: 加密失败时抛出
        """
        try:
            # 1. 生成随机字符串（16字节）
            random_bytes = os.urandom(16)

            # 2. 消息内容转为字节
            message_bytes = message.encode('utf-8')
            message_length = len(message_bytes)

            # 3. 构建待加密的数据
            # 格式：16字节随机字符串 + 4字节消息长度 + 消息内容 + corp_id
            length_bytes = message_length.to_bytes(4, byteorder='big')

            data_to_encrypt = random_bytes + length_bytes + message_bytes

            # 如果有corp_id，添加到末尾
            if self.corp_id:
                data_to_encrypt += self.corp_id.encode('utf-8')

            # 4. 进行PKCS#7填充
            padded_data = pad(data_to_encrypt, AES.block_size)

            # 5. 解码AES密钥
            key = base64.b64decode(self.encoding_aes_key + '=')

            # 6. 生成随机IV
            iv = os.urandom(16)

            # 7. 创建AES加密器
            cipher = AES.new(key, AES.MODE_CBC, iv)

            # 8. 加密数据
            encrypted_data = cipher.encrypt(padded_data)

            # 9. 组合IV和加密数据
            encrypted_with_iv = iv + encrypted_data

            # 10. Base64编码
            encrypted_base64 = base64.b64encode(encrypted_with_iv).decode('utf-8')

            logger.debug(f"消息加密成功，原长度: {message_length}, 加密后长度: {len(encrypted_base64)}")

            return encrypted_base64

        except Exception as e:
            logger.error(f"加密过程出错: {e}", exc_info=True)
            raise EncryptionError(f"消息加密失败: {e}")

    def _build_encrypted_response(self, encrypted_message: str) -> str:
        """
        构建加密回复的XML格式

        Args:
            encrypted_message: 加密后的消息

        Returns:
            str: XML格式的回复
        """
        timestamp = str(int(time.time()))
        nonce = self._generate_nonce()

        xml_template = """<xml>
<Encrypt><![CDATA[{encrypted_message}]]></Encrypt>
<MsgSignature><![CDATA[{msg_signature}]]></MsgSignature>
<TimeStamp>{timestamp}</TimeStamp>
<Nonce><![CDATA[{nonce}]]></Nonce>
</xml>"""

        # 这里需要计算消息签名，但需要token信息
        # 在实际使用中，应该通过配置或从其他处理器获取
        msg_signature = "placeholder_signature"  # 这个需要正确计算

        return xml_template.format(
            encrypted_message=encrypted_message,
            msg_signature=msg_signature,
            timestamp=timestamp,
            nonce=nonce
        )

    def _generate_nonce(self) -> str:
        """生成随机nonce"""
        import string
        import random

        length = 10
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

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

        # 只有需要回复且有回复消息时才处理
        return context.should_reply and bool(context.response_message)