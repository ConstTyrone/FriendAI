# redis_state_manager.py
"""
Redis状态管理器
用于持久化存储消息游标、事件去重标记和对话历史，解决服务重启后状态丢失问题
"""
import redis
import logging
import json
import os
from typing import Optional
from ..config.config import config

logger = logging.getLogger(__name__)

class RedisStateManager:
    """Redis状态管理器 - 持久化存储游标和去重信息"""

    def __init__(self):
        """初始化Redis连接"""
        try:
            self.redis_client = redis.Redis(
                host=getattr(config, 'redis_host', 'localhost'),
                port=getattr(config, 'redis_port', 6379),
                db=getattr(config, 'redis_db', 0),
                password=getattr(config, 'redis_password', None),
                decode_responses=True,  # 自动解码为字符串
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )

            # 测试连接
            self.redis_client.ping()
            logger.info("✅ Redis连接成功")
            self._redis_available = True

        except redis.ConnectionError as e:
            logger.warning(f"⚠️ Redis连接失败，将使用内存存储（服务重启后会丢失状态）: {e}")
            self.redis_client = None
            self._redis_available = False
            # 降级方案：使用内存存储
            self._memory_cursors = {}
            self._memory_events = set()
        except Exception as e:
            logger.error(f"❌ Redis初始化异常: {e}")
            self.redis_client = None
            self._redis_available = False
            self._memory_cursors = {}
            self._memory_events = set()

    def is_available(self) -> bool:
        """检查Redis是否可用"""
        return self._redis_available

    # ========== 消息游标管理 ==========

    def get_cursor(self, kf_id: str) -> Optional[str]:
        """
        获取消息游标

        Args:
            kf_id: 客服账号ID

        Returns:
            str: 游标字符串，不存在返回None
        """
        try:
            if self._redis_available:
                cursor = self.redis_client.get(f"kf:cursor:{kf_id}")
                logger.debug(f"从Redis获取游标: kf_id={kf_id}, cursor={cursor}")
                return cursor
            else:
                # 降级：内存存储
                cursor = self._memory_cursors.get(kf_id)
                logger.debug(f"从内存获取游标: kf_id={kf_id}, cursor={cursor}")
                return cursor
        except Exception as e:
            logger.error(f"获取游标失败: {e}")
            return None

    def set_cursor(self, kf_id: str, cursor: str, ttl: int = 86400 * 7):
        """
        保存消息游标

        Args:
            kf_id: 客服账号ID
            cursor: 游标字符串
            ttl: 过期时间（秒），默认7天
        """
        try:
            if self._redis_available:
                self.redis_client.setex(f"kf:cursor:{kf_id}", ttl, cursor)
                logger.debug(f"保存游标到Redis: kf_id={kf_id}, cursor={cursor}, ttl={ttl}s")
            else:
                # 降级：内存存储
                self._memory_cursors[kf_id] = cursor
                logger.debug(f"保存游标到内存: kf_id={kf_id}, cursor={cursor}")
        except Exception as e:
            logger.error(f"保存游标失败: {e}")

    # ========== 事件去重管理 ==========

    def is_event_processed(self, event_id: str) -> bool:
        """
        检查事件是否已处理

        Args:
            event_id: 事件唯一标识

        Returns:
            bool: True表示已处理，False表示未处理
        """
        try:
            if self._redis_available:
                exists = self.redis_client.exists(f"event:processed:{event_id}")
                logger.debug(f"检查事件: event_id={event_id}, processed={bool(exists)}")
                return bool(exists)
            else:
                # 降级：内存存储
                exists = event_id in self._memory_events
                logger.debug(f"检查事件(内存): event_id={event_id}, processed={exists}")
                return exists
        except Exception as e:
            logger.error(f"检查事件状态失败: {e}")
            # 出错时返回False，允许处理（避免消息丢失）
            return False

    def mark_event_processed(self, event_id: str, ttl: int = 86400):
        """
        标记事件已处理

        Args:
            event_id: 事件唯一标识
            ttl: 过期时间（秒），默认24小时
        """
        try:
            if self._redis_available:
                self.redis_client.setex(f"event:processed:{event_id}", ttl, "1")
                logger.debug(f"标记事件已处理: event_id={event_id}, ttl={ttl}s")
            else:
                # 降级：内存存储
                self._memory_events.add(event_id)
                logger.debug(f"标记事件已处理(内存): event_id={event_id}")

                # 内存存储需要定期清理，避免无限增长
                if len(self._memory_events) > 10000:
                    logger.warning("内存事件集合过大，清理一半旧数据")
                    # 简单策略：清理一半
                    events_list = list(self._memory_events)
                    self._memory_events = set(events_list[len(events_list)//2:])

        except Exception as e:
            logger.error(f"标记事件失败: {e}")

    # ========== 对话历史管理 ==========

    def get_conversation_history(self, user_id: str, max_messages: int = 20) -> list:
        """
        获取用户对话历史

        Args:
            user_id: 用户ID
            max_messages: 最多返回多少条消息（默认20条=10轮对话）

        Returns:
            list: 对话消息列表，格式 [{"role": "user", "content": "..."}, ...]
        """
        try:
            if self._redis_available:
                # 从Redis获取
                key = f"chat:history:{user_id}"
                # 获取最近的max_messages条消息
                messages_json = self.redis_client.lrange(key, -max_messages, -1)

                # 解析JSON
                messages = []
                for msg_json in messages_json:
                    try:
                        messages.append(json.loads(msg_json))
                    except json.JSONDecodeError:
                        logger.warning(f"解析对话历史失败: {msg_json}")
                        continue

                logger.debug(f"从Redis获取对话历史: user_id={user_id}, count={len(messages)}")
                return messages
            else:
                # 降级：内存存储
                if not hasattr(self, '_memory_conversation_history'):
                    self._memory_conversation_history = {}

                history = self._memory_conversation_history.get(user_id, [])
                logger.debug(f"从内存获取对话历史: user_id={user_id}, count={len(history)}")
                return history[-max_messages:] if history else []

        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []

    def add_conversation_message(self, user_id: str, role: str, content: str, ttl: int = 86400 * 7):
        """
        添加一条对话消息到历史

        Args:
            user_id: 用户ID
            role: 角色（user/assistant/system）
            content: 消息内容
            ttl: 过期时间（秒），默认7天
        """
        try:
            message = {
                "role": role,
                "content": content
            }
            message_json = json.dumps(message, ensure_ascii=False)

            if self._redis_available:
                # 保存到Redis
                key = f"chat:history:{user_id}"
                self.redis_client.rpush(key, message_json)

                # 设置过期时间
                self.redis_client.expire(key, ttl)

                # 限制历史长度（最多保留100条消息=50轮对话）
                list_len = self.redis_client.llen(key)
                if list_len > 100:
                    # 删除最旧的消息，保留最新的100条
                    self.redis_client.ltrim(key, -100, -1)

                logger.debug(f"添加对话消息到Redis: user_id={user_id}, role={role}")
            else:
                # 降级：内存存储
                if not hasattr(self, '_memory_conversation_history'):
                    self._memory_conversation_history = {}

                if user_id not in self._memory_conversation_history:
                    self._memory_conversation_history[user_id] = []

                self._memory_conversation_history[user_id].append(message)

                # 限制历史长度
                if len(self._memory_conversation_history[user_id]) > 100:
                    self._memory_conversation_history[user_id] = \
                        self._memory_conversation_history[user_id][-100:]

                logger.debug(f"添加对话消息到内存: user_id={user_id}, role={role}")

        except Exception as e:
            logger.error(f"添加对话消息失败: {e}")

    def clear_conversation_history(self, user_id: str):
        """清除指定用户的对话历史"""
        try:
            if self._redis_available:
                key = f"chat:history:{user_id}"
                self.redis_client.delete(key)
                logger.info(f"清除对话历史: user_id={user_id}")
            else:
                if hasattr(self, '_memory_conversation_history') and \
                   user_id in self._memory_conversation_history:
                    del self._memory_conversation_history[user_id]
                    logger.info(f"清除对话历史(内存): user_id={user_id}")
        except Exception as e:
            logger.error(f"清除对话历史失败: {e}")

    # ========== 辅助方法 ==========

    def clear_cursor(self, kf_id: str):
        """清除游标（用于测试或重置）"""
        try:
            if self._redis_available:
                self.redis_client.delete(f"kf:cursor:{kf_id}")
                logger.info(f"清除游标: kf_id={kf_id}")
            else:
                self._memory_cursors.pop(kf_id, None)
                logger.info(f"清除游标(内存): kf_id={kf_id}")
        except Exception as e:
            logger.error(f"清除游标失败: {e}")

    def get_stats(self) -> dict:
        """获取状态统计信息"""
        try:
            if self._redis_available:
                # Redis统计
                cursor_keys = self.redis_client.keys("kf:cursor:*")
                event_keys = self.redis_client.keys("event:processed:*")
                return {
                    "storage_type": "redis",
                    "redis_available": True,
                    "cursor_count": len(cursor_keys),
                    "event_count": len(event_keys)
                }
            else:
                # 内存统计
                return {
                    "storage_type": "memory",
                    "redis_available": False,
                    "cursor_count": len(self._memory_cursors),
                    "event_count": len(self._memory_events)
                }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}

    def health_check(self) -> dict:
        """健康检查"""
        try:
            if self._redis_available:
                self.redis_client.ping()
                return {
                    "status": "healthy",
                    "storage": "redis",
                    "message": "Redis connection OK"
                }
            else:
                return {
                    "status": "degraded",
                    "storage": "memory",
                    "message": "Using memory storage (state will be lost on restart)"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "storage": "unknown",
                "message": str(e)
            }

# 全局状态管理器实例
state_manager = RedisStateManager()
