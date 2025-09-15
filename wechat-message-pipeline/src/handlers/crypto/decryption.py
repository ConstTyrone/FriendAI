# -*- coding: utf-8 -*-
"""
消息解密处理器 - 解密微信/企微的AES加密消息

从原有系统的 wework_client.py 迁移而来的消息解密逻辑。
"""

import base64
import logging
from typing import Optional
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from ...core import MessageHandler, MessageContext, DecryptionError


logger = logging.getLogger(__name__)


class MessageDecryptionHandler(MessageHandler):
    """
    消息解密处理器

    解密来自微信/企微平台的AES加密消息。
    支持多种解密格式，兼容不同平台的消息格式差异。
    """

    def __init__(
        self,
        encoding_aes_key: str,
        **kwargs
    ):
        """
        初始化消息解密处理器

        Args:
            encoding_aes_key: AES加密密钥（Base64编码）
            **kwargs: 其他参数传递给父类
        """
        super().__init__(name="MessageDecryption", priority=20, **kwargs)
        self.encoding_aes_key = encoding_aes_key

    async def process(self, context: MessageContext) -> MessageContext:
        """
        解密消息

        Args:
            context: 消息上下文

        Returns:
            MessageContext: 处理后的上下文
        """
        # 检查是否为URL验证请求
        if context.get_metadata('url_verification'):
            echostr = context.get_metadata('echostr')
            if echostr:
                try:
                    # 解密echostr
                    decrypted_echostr = self._decrypt_message(echostr)
                    context.set_metadata('decrypted_echostr', decrypted_echostr)
                    context.add_log("URL验证echostr解密成功")
                    return context
                except Exception as e:
                    context.add_error(f"URL验证echostr解密失败: {str(e)}")
                    raise DecryptionError(f"URL验证失败: {str(e)}")

        # 处理消息解密
        if not context.encrypted_message:
            context.add_warning("没有找到需要解密的消息")
            return context

        try:
            decrypted_content = self._decrypt_message(context.encrypted_message)
            context.decrypted_message = decrypted_content
            context.add_log("消息解密成功")

            # 记录解密后的消息长度（不记录具体内容以保护隐私）
            context.set_processing_stat('decrypted_length', len(decrypted_content))

        except Exception as e:
            error_msg = f"消息解密失败: {str(e)}"
            context.add_error(error_msg)
            raise DecryptionError(
                error_msg,
                context={
                    'encrypted_length': len(context.encrypted_message) if context.encrypted_message else 0,
                    'key_configured': bool(self.encoding_aes_key)
                }
            )

        return context

    def _decrypt_message(self, encrypt_msg: str) -> str:
        """
        解密消息的核心逻辑

        Args:
            encrypt_msg: 加密的消息内容

        Returns:
            str: 解密后的消息内容

        Raises:
            DecryptionError: 解密失败时抛出
        """
        try:
            # 1. Base64解码
            msg_bytes = base64.b64decode(encrypt_msg)
            logger.debug(f"Base64解码后长度: {len(msg_bytes)}")

            # 2. 解码AES密钥
            key = base64.b64decode(self.encoding_aes_key + '=')
            logger.debug(f"AES密钥长度: {len(key)}")

            # 3. 提取IV（前16字节）
            iv = msg_bytes[:16]
            logger.debug(f"IV: {iv.hex()}")

            # 4. 提取加密数据（16字节之后的部分）
            encrypted_data = msg_bytes[16:]
            logger.debug(f"加密数据长度: {len(encrypted_data)}")

            # 5. 创建AES解密器
            cipher = AES.new(key, AES.MODE_CBC, iv)

            # 6. 解密数据
            decrypted = cipher.decrypt(encrypted_data)
            logger.debug(f"解密后数据长度: {len(decrypted)}")

            # 7. 尝试去除PKCS#7填充
            try:
                decrypted = unpad(decrypted, AES.block_size)
                logger.debug("PKCS#7填充去除成功")
            except ValueError as pad_error:
                logger.warning(f"去除填充失败: {pad_error}")
                # 如果去除填充失败，尝试直接使用解密后的数据

            # 8. 提取消息内容
            if len(decrypted) < 20:
                raise DecryptionError("解密后的数据长度不足")

            # 尝试多种格式解析
            content = self._extract_content_from_decrypted(decrypted)

            return content

        except Exception as e:
            logger.error(f"解密过程出错: {e}", exc_info=True)
            raise DecryptionError(f"消息解密失败: {e}")

    def _extract_content_from_decrypted(self, decrypted: bytes) -> str:
        """
        从解密后的数据中提取消息内容

        根据微信平台文档，解密后的格式可能有差异，需要灵活处理：
        - 标准格式：前16字节为随机字符串，接着4字节为消息长度，后面是消息内容
        - 其他格式：前4字节为消息长度，后面是消息内容

        Args:
            decrypted: 解密后的字节数据

        Returns:
            str: 提取的消息内容

        Raises:
            DecryptionError: 提取失败时抛出
        """
        # 方法1: 尝试标准格式解析（前16字节为随机字符串）
        try:
            if len(decrypted) >= 20:
                content_length = int.from_bytes(decrypted[16:20], byteorder='big')
                logger.debug(f"标准格式 - 消息长度: {content_length}")

                if 0 < content_length <= len(decrypted) - 20:
                    content = decrypted[20:20+content_length].decode('utf-8')
                    logger.debug("使用标准格式解析成功")
                    return content
        except (UnicodeDecodeError, ValueError) as e:
            logger.debug(f"标准格式解析失败: {e}")

        # 方法2: 尝试另一种格式（前4字节为长度）
        try:
            if len(decrypted) >= 4:
                alternative_length = int.from_bytes(decrypted[:4], byteorder='big')
                logger.debug(f"替代格式 - 消息长度: {alternative_length}")

                if 0 < alternative_length <= len(decrypted) - 4:
                    content = decrypted[4:4+alternative_length].decode('utf-8')
                    logger.debug("使用替代格式解析成功")
                    return content
        except (UnicodeDecodeError, ValueError) as e:
            logger.debug(f"替代格式解析失败: {e}")

        # 方法3: 尝试直接返回剩余数据（跳过前20字节）
        try:
            if len(decrypted) > 20:
                remaining_data = decrypted[20:]
                # 寻找可能的字符串结束位置（去除尾部的0字节）
                content = remaining_data.rstrip(b'\x00').decode('utf-8')
                logger.debug("使用直接解析成功")
                return content
        except UnicodeDecodeError as e:
            logger.debug(f"直接解析失败: {e}")

        # 方法4: 尝试从不同位置开始解析
        for start_pos in [0, 4, 16, 20]:
            try:
                if len(decrypted) > start_pos:
                    content = decrypted[start_pos:].rstrip(b'\x00').decode('utf-8')
                    if content.strip():  # 确保不是空内容
                        logger.debug(f"从位置 {start_pos} 解析成功")
                        return content
            except UnicodeDecodeError:
                continue

        # 如果所有方法都失败，返回十六进制表示
        content_hex = decrypted.hex()
        logger.warning(f"无法解析为UTF-8字符串，返回十六进制: {content_hex[:100]}...")
        return content_hex

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

        # 检查是否需要解密
        return (
            context.encrypted_message or  # 有加密消息
            context.get_metadata('url_verification')  # 或是URL验证
        )