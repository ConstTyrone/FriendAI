# wework_client.py
import hashlib
import base64
import time
import requests
import json
import logging
from typing import Optional
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from ..config.config import config

logger = logging.getLogger(__name__)

class WeWorkClient:
    def __init__(self, config):
        self.config = config
        self._access_token = None
        self._token_expires_at = 0
        self._cursor_file = "data/kf_cursors.json"  # 本地cursor备份文件

        # 导入Redis状态管理器
        try:
            from .redis_state_manager import state_manager
            self.state_manager = state_manager
            logger.info("✅ WeWorkClient已集成Redis状态管理")
        except Exception as e:
            logger.warning(f"⚠️ Redis状态管理器加载失败，将使用内存存储: {e}")
            self.state_manager = None
            # 降级方案：内存存储
            self._kf_cursors = {}
            # 尝试从本地文件恢复
            self._load_cursors_from_file()

    def get_access_token(self):
        """获取access_token"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
        params = {
            'corpid': self.config.corp_id,
            'corpsecret': self.config.secret
        }

        response = requests.get(url, params=params)
        data = response.json()

        if data.get('errcode') == 0:
            self._access_token = data['access_token']
            self._token_expires_at = time.time() + data.get('expires_in', 7200) - 300
            return self._access_token

        raise Exception(f"获取token失败: {data.get('errmsg')}")

    def verify_signature(self, signature, timestamp, nonce, encrypt_msg=None):
        """验证签名"""
        # 微信客服/企业微信签名验证需要将token、timestamp、nonce按字典序排序
        params = [self.config.token, timestamp, nonce]

        # 对于消息回调，可能需要包含encrypt参数
        if encrypt_msg:
            params.append(encrypt_msg)

        params.sort()
        sorted_params = ''.join(params)
        sha1_hash = hashlib.sha1(sorted_params.encode()).hexdigest()

        # 签名验证失败时记录错误
        if sha1_hash != signature:
            logger.error(f"签名验证失败 - 期望: {signature}, 实际: {sha1_hash}")
            logger.error(f"参数详情 - token: {self.config.token}, timestamp: {timestamp}, nonce: {nonce}, encrypt_msg: {encrypt_msg}")
            logger.error(f"排序后的参数: {sorted_params}")

        return sha1_hash == signature

    def decrypt_message(self, encrypt_msg):
        """解密消息"""
        try:
            # Base64解码
            msg_bytes = base64.b64decode(encrypt_msg)

            # 解码AES密钥
            key = base64.b64decode(self.config.encoding_aes_key + '=')

            # 提取IV（前16字节）
            iv = msg_bytes[:16]

            # 提取加密数据（16字节之后的部分）
            encrypted_data = msg_bytes[16:]

            # 创建AES解密器
            cipher = AES.new(key, AES.MODE_CBC, iv)

            # 解密数据
            decrypted = cipher.decrypt(encrypted_data)

            # 尝试去除PKCS#7填充
            try:
                decrypted = unpad(decrypted, AES.block_size)
            except ValueError as pad_error:
                logger.warning(f"去除填充失败: {pad_error}")
                # 如果去除填充失败，尝试直接使用解密后的数据

            # 提取消息内容
            # 根据微信平台文档：前16字节为随机字符串，接着4字节为消息长度，后面是消息内容
            # 但实际测试发现格式可能有所不同，需要灵活处理

            if len(decrypted) < 20:
                raise Exception("解密后的数据长度不足")

            # 尝试标准格式解析
            content_length = int.from_bytes(decrypted[16:20], byteorder='big')

            # 检查长度是否合理
            if content_length > 0 and content_length < len(decrypted) - 20:
                content = decrypted[20:20+content_length].decode('utf-8')
                return content

            # 如果标准格式失败，尝试另一种可能的格式
            # 直接使用前4字节作为长度（微信客服可能使用这种格式）
            alternative_length = int.from_bytes(decrypted[:4], byteorder='big')

            if alternative_length > 0 and alternative_length < len(decrypted) - 4:
                content = decrypted[4:4+alternative_length].decode('utf-8')
                return content

            # 如果以上都失败，尝试直接返回剩余数据（特殊情况处理）
            remaining_data = decrypted[20:]  # 跳过前16字节随机字符串和4字节长度字段
            try:
                content = remaining_data.decode('utf-8')
                return content
            except UnicodeDecodeError:
                # 如果还是无法解码，返回十六进制表示
                content_hex = remaining_data.hex()
                return content_hex

        except Exception as e:
            logger.error(f"解密过程出错: {e}", exc_info=True)
            raise Exception(f"消息解密失败: {e}")

    def sync_kf_messages(self, token=None, open_kf_id=None, limit=1000, get_latest_only=True):
        """
        同步微信客服消息 - 拉取所有消息然后返回最新的

        Args:
            token: 回调事件返回的token
            open_kf_id: 客服账号ID
            limit: 每次拉取的消息数量，默认1000（最大值）
            get_latest_only: 是否只返回最新消息，默认True
        """
        logger.info(f"🔍 sync_kf_messages被调用，参数: limit={limit}, get_latest_only={get_latest_only}")

        try:
            # 获取access_token
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("无法获取access_token")

            # 构造请求URL
            url = f"https://qyapi.weixin.qq.com/cgi-bin/kf/sync_msg?access_token={access_token}"

            cursor_key = open_kf_id or "default"
            all_messages = []

            # 循环拉取所有消息，直到has_more=0
            # 使用Redis或内存获取游标
            if self.state_manager:
                current_cursor = self.state_manager.get_cursor(cursor_key) or ""
            else:
                current_cursor = self._kf_cursors.get(cursor_key, "")

            while True:
                # 构造请求参数
                payload = {
                    "token": token,
                    "limit": limit
                }

                if open_kf_id:
                    payload["open_kfid"] = open_kf_id

                if current_cursor:
                    payload["cursor"] = current_cursor
                    logger.info(f"📍 使用cursor拉取: {current_cursor}")
                else:
                    logger.info("📍 首次拉取，不使用cursor")

                logger.info(f"🔗 调用sync_msg接口: {url}")
                logger.info(f"📋 请求参数: {payload}")

                # 发送POST请求
                response = requests.post(url, json=payload)
                result = response.json()

                # 检查是否有错误
                if result.get("errcode") != 0:
                    raise Exception(f"sync_msg接口调用失败: {result.get('errmsg')}")

                # 获取返回数据
                msg_list = result.get("msg_list", [])
                has_more = result.get("has_more", 0)
                next_cursor = result.get("next_cursor", "")

                logger.info(f"✅ 本次获取消息: 消息数={len(msg_list)}, has_more={has_more}")

                # 添加到总消息列表
                if msg_list:
                    all_messages.extend(msg_list)

                # 更新cursor - 使用Redis持久化,失败时降级到本地文件
                if next_cursor:
                    current_cursor = next_cursor
                    if self.state_manager:
                        try:
                            self.state_manager.set_cursor(cursor_key, next_cursor)
                        except Exception as redis_error:
                            logger.warning(f"⚠️ Redis保存cursor失败: {redis_error}")
                            # 降级方案: 保存到本地文件
                            self._save_cursor_to_file(cursor_key, next_cursor)
                    else:
                        # 内存存储 + 本地文件备份
                        self._kf_cursors[cursor_key] = next_cursor
                        self._save_cursor_to_file(cursor_key, next_cursor)
                    logger.info(f"📱 更新cursor: {next_cursor}")

                # 如果没有更多消息，退出循环
                if has_more == 0:
                    logger.info("📭 已拉取完所有消息")
                    break

                # 如果本次没有返回消息但has_more=1，也退出避免死循环
                if not msg_list and has_more == 1:
                    logger.warning("⚠️ has_more=1但msg_list为空，退出循环")
                    break

            logger.info(f"🎉 总共拉取到 {len(all_messages)} 条消息")

            if not all_messages:
                logger.info("📭 没有新消息")
                return []

            if get_latest_only:
                # 按时间排序，返回最新的一条消息
                all_messages.sort(key=lambda x: x.get('send_time', 0), reverse=True)
                latest_message = all_messages[0]
                logger.info(f"🎯 返回最新消息: msgid={latest_message.get('msgid', '')}, send_time={latest_message.get('send_time', 0)}")
                return [latest_message]
            else:
                logger.info(f"📝 返回所有 {len(all_messages)} 条消息")
                return all_messages

        except Exception as e:
            logger.error(f"sync_kf_messages处理失败: {e}", exc_info=True)
            raise Exception(f"同步微信客服消息失败: {e}")

    def _convert_kf_message(self, kf_msg):
        """将微信客服消息格式转换为内部消息格式（简化版，无需绑定）"""
        try:
            logger.info(f"🔍 原始微信客服消息结构: {kf_msg}")

            # 直接使用 external_userid，不再需要绑定转换
            external_userid = kf_msg.get("external_userid", "")

            # 创建基础消息结构
            converted_msg = {
                "MsgType": kf_msg.get("msgtype", "unknown"),
                "FromUserName": external_userid,  # 直接使用 external_userid
                "ToUserName": kf_msg.get("open_kfid", ""),
                "CreateTime": kf_msg.get("send_time", ""),
            }

            # 根据消息类型添加具体内容
            msg_type = kf_msg.get("msgtype")
            if msg_type == "text":
                text_obj = kf_msg.get("text", {})
                converted_msg["Content"] = text_obj.get("content", "")
                converted_msg["MenuId"] = text_obj.get("menu_id", "")  # 支持菜单消息回复
            elif msg_type == "image":
                converted_msg["MediaId"] = kf_msg.get("image", {}).get("media_id", "")
            elif msg_type == "voice":
                converted_msg["MediaId"] = kf_msg.get("voice", {}).get("media_id", "")
            elif msg_type == "video":
                converted_msg["MediaId"] = kf_msg.get("video", {}).get("media_id", "")
            elif msg_type == "file":
                file_info = kf_msg.get("file", {})
                converted_msg["MediaId"] = file_info.get("media_id", "")
                converted_msg["Title"] = file_info.get("filename", "")
                logger.info(f"📁 文件消息详情: media_id={converted_msg['MediaId']}, filename={converted_msg['Title']}")
                logger.info(f"📁 完整file对象: {file_info}")
            elif msg_type == "location":
                converted_msg["Location_X"] = kf_msg.get("location", {}).get("latitude", "")
                converted_msg["Location_Y"] = kf_msg.get("location", {}).get("longitude", "")
                converted_msg["Label"] = kf_msg.get("location", {}).get("name", "")
            elif msg_type == "merged_msg":
                # 处理聊天记录消息
                merged_msg_content = kf_msg.get("merged_msg", {})
                converted_msg["merged_msg"] = merged_msg_content
            elif msg_type == "channels_shop_product":
                # 视频号商品消息
                converted_msg["channels_shop_product"] = kf_msg.get("channels_shop_product", {})
            elif msg_type == "channels_shop_order":
                # 视频号订单消息
                converted_msg["channels_shop_order"] = kf_msg.get("channels_shop_order", {})
            elif msg_type == "channels":
                # 视频号消息
                converted_msg["channels"] = kf_msg.get("channels", {})
            elif msg_type == "note":
                # 笔记消息（暂无详细内容）
                pass
            elif msg_type == "event":
                event_content = kf_msg.get("event", {})
                converted_msg["Event"] = event_content.get("event_type", "")
                converted_msg["OpenKfId"] = event_content.get("open_kfid", "")
                converted_msg["ExternalUserId"] = event_content.get("external_userid", "")
                # 将事件内容添加到消息中
                converted_msg["EventContent"] = event_content

            return converted_msg

        except Exception as e:
            logger.error(f"消息转换失败: {e}", exc_info=True)
            return None

    def _send_message(self, payload):
        """统一的消息发送接口"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("无法获取access_token")

            url = f"https://qyapi.weixin.qq.com/cgi-bin/kf/send_msg?access_token={access_token}"

            logger.info(f"发送消息: {url}")
            logger.info(f"请求参数: {payload}")

            response = requests.post(url, json=payload)
            result = response.json()

            logger.info(f"发送消息接口返回: {result}")

            if result.get("errcode") != 0:
                raise Exception(f"发送消息接口调用失败: {result.get('errmsg')}")

            return result

        except Exception as e:
            logger.error(f"发送消息失败: {e}", exc_info=True)
            raise Exception(f"发送消息失败: {e}")

    def send_text_message(self, external_userid, open_kfid, content, msgid=None):
        """发送文本消息"""
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        if msgid:
            payload["msgid"] = msgid
        return self._send_message(payload)

    def upload_temp_media(self, file_path, media_type='image'):
        """
        上传临时素材到微信服务器

        Args:
            file_path: 文件路径
            media_type: 素材类型 (image/voice/video/file)

        Returns:
            media_id: 素材ID，用于发送消息
        """
        access_token = self.get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type={media_type}"

        try:
            with open(file_path, 'rb') as f:
                files = {'media': f}
                response = requests.post(url, files=files)
                result = response.json()

                if result.get('errcode') == 0 or 'media_id' in result:
                    media_id = result.get('media_id')
                    logger.info(f"✅ 上传临时素材成功: media_id={media_id}, type={media_type}")
                    return media_id
                else:
                    error_msg = f"上传临时素材失败: {result.get('errmsg', '未知错误')}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
        except Exception as e:
            logger.error(f"上传临时素材异常: {e}")
            raise

    def send_image_message(self, external_userid, open_kfid, media_id, msgid=None):
        """发送图片消息"""
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "image",
            "image": {
                "media_id": media_id
            }
        }
        if msgid:
            payload["msgid"] = msgid
        return self._send_message(payload)

    def send_voice_message(self, external_userid, open_kfid, media_id, msgid=None):
        """发送语音消息"""
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "voice",
            "voice": {
                "media_id": media_id
            }
        }
        if msgid:
            payload["msgid"] = msgid
        return self._send_message(payload)

    def send_video_message(self, external_userid, open_kfid, media_id, msgid=None):
        """发送视频消息"""
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "video",
            "video": {
                "media_id": media_id
            }
        }
        if msgid:
            payload["msgid"] = msgid
        return self._send_message(payload)

    def send_file_message(self, external_userid, open_kfid, media_id, msgid=None):
        """发送文件消息"""
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "file",
            "file": {
                "media_id": media_id
            }
        }
        if msgid:
            payload["msgid"] = msgid
        return self._send_message(payload)

    def send_link_message(self, external_userid, open_kfid, title, url, thumb_media_id, desc=None, msgid=None):
        """发送图文链接消息"""
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "link",
            "link": {
                "title": title,
                "url": url,
                "thumb_media_id": thumb_media_id
            }
        }
        if desc:
            payload["link"]["desc"] = desc
        if msgid:
            payload["msgid"] = msgid
        return self._send_message(payload)

    def send_miniprogram_message(self, external_userid, open_kfid, appid, thumb_media_id, pagepath, title=None, msgid=None):
        """发送小程序消息"""
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "miniprogram",
            "miniprogram": {
                "appid": appid,
                "thumb_media_id": thumb_media_id,
                "pagepath": pagepath
            }
        }
        if title:
            payload["miniprogram"]["title"] = title
        if msgid:
            payload["msgid"] = msgid
        return self._send_message(payload)

    def send_menu_message(self, external_userid, open_kfid, menu_items, head_content=None, tail_content=None, msgid=None):
        """
        发送菜单消息

        Args:
            external_userid: 用户ID
            open_kfid: 客服账号ID
            menu_items: 菜单项列表,格式示例:
                [
                    {"type": "click", "click": {"id": "101", "content": "满意"}},
                    {"type": "view", "view": {"url": "https://...", "content": "查看详情"}},
                    {"type": "miniprogram", "miniprogram": {"appid": "...", "pagepath": "...", "content": "打开小程序"}},
                    {"type": "text", "text": {"content": "纯文本", "no_newline": 0}}
                ]
            head_content: 起始文本
            tail_content: 结束文本
            msgid: 消息ID
        """
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "msgmenu",
            "msgmenu": {
                "list": menu_items
            }
        }
        if head_content:
            payload["msgmenu"]["head_content"] = head_content
        if tail_content:
            payload["msgmenu"]["tail_content"] = tail_content
        if msgid:
            payload["msgid"] = msgid
        return self._send_message(payload)

    def send_location_message(self, external_userid, open_kfid, latitude, longitude, name=None, address=None, msgid=None):
        """发送地理位置消息"""
        payload = {
            "touser": external_userid,
            "open_kfid": open_kfid,
            "msgtype": "location",
            "location": {
                "latitude": latitude,
                "longitude": longitude
            }
        }
        if name:
            payload["location"]["name"] = name
        if address:
            payload["location"]["address"] = address
        if msgid:
            payload["msgid"] = msgid
        return self._send_message(payload)

    def send_welcome_message(self, welcome_code, content=None, menu_items=None, msgid=None):
        """
        发送欢迎语 (事件响应消息)

        重要限制:
        - 仅可在收到enter_session事件后20秒内调用
        - 每个welcome_code只能使用一次
        - 仅支持文本和菜单消息

        Args:
            welcome_code: 事件回调返回的welcome_code
            content: 欢迎文本内容 (与menu_items二选一)
            menu_items: 菜单项列表 (与content二选一)
            msgid: 消息ID

        Returns:
            dict: API返回结果
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                raise Exception("无法获取access_token")

            url = f"https://qyapi.weixin.qq.com/cgi-bin/kf/send_msg_on_event?access_token={access_token}"

            # 构造请求参数
            if menu_items:
                # 菜单消息
                payload = {
                    "code": welcome_code,
                    "msgtype": "msgmenu",
                    "msgmenu": {
                        "list": menu_items
                    }
                }
                # 如果提供了content,作为菜单的头部文本
                if content:
                    payload["msgmenu"]["head_content"] = content
            else:
                # 文本消息
                payload = {
                    "code": welcome_code,
                    "msgtype": "text",
                    "text": {
                        "content": content or "您好,欢迎咨询!"
                    }
                }

            if msgid:
                payload["msgid"] = msgid

            logger.info(f"发送欢迎语: code={welcome_code}")
            logger.info(f"请求参数: {payload}")

            response = requests.post(url, json=payload)
            result = response.json()

            logger.info(f"欢迎语接口返回: {result}")

            if result.get("errcode") != 0:
                raise Exception(f"发送欢迎语失败: {result.get('errmsg')}")

            return result

        except Exception as e:
            logger.error(f"发送欢迎语失败: {e}", exc_info=True)
            raise Exception(f"发送欢迎语失败: {e}")

    def _save_cursor_to_file(self, cursor_key, cursor_value):
        """保存cursor到本地文件(降级方案)"""
        try:
            import os
            # 确保data目录存在
            os.makedirs("data", exist_ok=True)

            # 读取现有数据
            cursors = {}
            if os.path.exists(self._cursor_file):
                try:
                    with open(self._cursor_file, 'r', encoding='utf-8') as f:
                        cursors = json.load(f)
                except:
                    pass

            # 更新cursor
            cursors[cursor_key] = {
                "cursor": cursor_value,
                "updated_at": time.time()
            }

            # 写入文件
            with open(self._cursor_file, 'w', encoding='utf-8') as f:
                json.dump(cursors, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 已将cursor保存到本地文件: {cursor_key}")

        except Exception as e:
            logger.error(f"保存cursor到文件失败: {e}")

    def _load_cursors_from_file(self):
        """从本地文件加载cursor(降级方案)"""
        try:
            import os
            if os.path.exists(self._cursor_file):
                with open(self._cursor_file, 'r', encoding='utf-8') as f:
                    cursors = json.load(f)

                # 加载到内存
                for key, data in cursors.items():
                    self._kf_cursors[key] = data.get("cursor", "")

                logger.info(f"📂 从本地文件加载了 {len(cursors)} 个cursor")
        except Exception as e:
            logger.warning(f"从文件加载cursor失败: {e}")


wework_client = WeWorkClient(config)