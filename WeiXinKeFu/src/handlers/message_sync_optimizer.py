# message_sync_optimizer.py
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageSyncOptimizer:
    """消息同步优化器 - 解决分页和重复处理问题"""
    
    def __init__(self):
        # 存储每个客服账号的最后处理时间和消息ID
        self._last_processed = {}
        # 存储游标信息
        self._cursors = {}
        # 存储已处理的消息ID，防止重复处理
        self._processed_messages = set()
        # 清理时间间隔（秒）
        self._cleanup_interval = 3600  # 1小时
        self._last_cleanup = time.time()
    
    def get_new_messages_optimized(self, wework_client, token: str, open_kfid: str) -> List[Dict[str, Any]]:
        """
        优化的消息获取策略
        
        策略1: 增量同步 - 使用cursor获取新消息
        策略2: 智能分页 - 根据消息量动态调整limit
        策略3: 时间戳过滤 - 只处理最新的消息
        """
        try:
            # 清理过期数据
            self._cleanup_if_needed()
            
            # 生成客服账号的唯一键
            kf_key = f"{open_kfid}_{token}"
            
            # 策略1: 尝试增量同步
            new_messages = self._try_incremental_sync(wework_client, token, open_kfid, kf_key)
            
            if new_messages:
                logger.info(f"增量同步成功，获取到 {len(new_messages)} 条新消息")
                return new_messages
            
            # 策略2: 智能分页获取
            logger.info("增量同步无新消息，尝试智能分页获取")
            return self._try_smart_pagination(wework_client, token, open_kfid, kf_key)
            
        except Exception as e:
            logger.error(f"优化消息获取失败: {e}")
            # 降级到原始方法
            return self._fallback_sync(wework_client, token, open_kfid)
    
    def _try_incremental_sync(self, wework_client, token: str, open_kfid: str, kf_key: str) -> List[Dict[str, Any]]:
        """尝试增量同步"""
        try:
            # 使用较小的limit进行增量同步
            messages = wework_client.sync_kf_messages(token, limit=20, open_kf_id=open_kfid, use_cursor=True)
            
            if not messages:
                return []
            
            # 过滤掉已处理的消息
            new_messages = []
            last_processed_time = self._last_processed.get(kf_key, {}).get('timestamp', 0)
            
            for msg in messages:
                msg_id = msg.get('msgid', '')
                send_time = msg.get('send_time', 0)
                
                # 检查是否是新消息
                if (msg_id not in self._processed_messages and 
                    send_time > last_processed_time):
                    new_messages.append(msg)
                    self._processed_messages.add(msg_id)
            
            # 更新最后处理时间
            if new_messages:
                latest_time = max(msg.get('send_time', 0) for msg in new_messages)
                self._last_processed[kf_key] = {
                    'timestamp': latest_time,
                    'msgid': new_messages[0].get('msgid', ''),
                    'update_time': time.time()
                }
                logger.info(f"更新最后处理时间: {datetime.fromtimestamp(latest_time)}")
            
            return new_messages
            
        except Exception as e:
            logger.warning(f"增量同步失败: {e}")
            return []
    
    def _try_smart_pagination(self, wework_client, token: str, open_kfid: str, kf_key: str) -> List[Dict[str, Any]]:
        """智能分页获取"""
        try:
            # 根据历史情况动态调整limit
            base_limit = 50
            max_limit = 200
            
            # 如果之前没有处理过消息，使用较大的limit
            if kf_key not in self._last_processed:
                current_limit = max_limit
                logger.info(f"首次同步，使用大limit: {current_limit}")
            else:
                # 根据上次获取到的消息数量调整limit
                current_limit = min(base_limit * 2, max_limit)
                logger.info(f"智能调整limit: {current_limit}")
            
            # 获取消息
            messages = wework_client.sync_kf_messages(token, limit=current_limit, open_kf_id=open_kfid)
            
            if not messages:
                return []
            
            # 按时间排序，确保最新的在前面
            messages.sort(key=lambda x: x.get('send_time', 0), reverse=True)
            
            # 过滤新消息
            new_messages = []
            last_processed_time = self._last_processed.get(kf_key, {}).get('timestamp', 0)
            
            for msg in messages:
                msg_id = msg.get('msgid', '')
                send_time = msg.get('send_time', 0)
                
                # 只处理比上次处理时间更新的消息
                if send_time > last_processed_time and msg_id not in self._processed_messages:
                    new_messages.append(msg)
                    self._processed_messages.add(msg_id)
                else:
                    # 如果遇到已处理的消息，说明已经获取到历史消息，可以停止
                    break
            
            # 更新处理状态
            if new_messages:
                latest_time = max(msg.get('send_time', 0) for msg in new_messages)
                self._last_processed[kf_key] = {
                    'timestamp': latest_time,
                    'msgid': new_messages[0].get('msgid', ''),
                    'update_time': time.time()
                }
            
            logger.info(f"智能分页获取到 {len(new_messages)} 条新消息")
            return new_messages
            
        except Exception as e:
            logger.error(f"智能分页失败: {e}")
            return []
    
    def _fallback_sync(self, wework_client, token: str, open_kfid: str) -> List[Dict[str, Any]]:
        """降级同步方法"""
        try:
            logger.info("使用降级同步方法")
            # 使用更大的limit作为兜底方案
            messages = wework_client.sync_kf_messages(token, limit=300, open_kf_id=open_kfid)
            
            if messages:
                # 只返回最新的一条消息，避免重复处理
                return [messages[0]]
            
            return []
            
        except Exception as e:
            logger.error(f"降级同步也失败: {e}")
            return []
    
    def _cleanup_if_needed(self):
        """定期清理过期数据"""
        current_time = time.time()
        
        if current_time - self._last_cleanup > self._cleanup_interval:
            # 清理1小时前的处理记录
            cutoff_time = current_time - 3600
            
            # 清理过期的处理状态
            expired_keys = [
                key for key, value in self._last_processed.items()
                if value.get('update_time', 0) < cutoff_time
            ]
            
            for key in expired_keys:
                del self._last_processed[key]
            
            # 清理过期的消息ID（保留最近1000条）
            if len(self._processed_messages) > 1000:
                # 简单的LRU清理，保留一半
                messages_list = list(self._processed_messages)
                self._processed_messages = set(messages_list[:500])
            
            self._last_cleanup = current_time
            logger.info(f"清理完成，删除了 {len(expired_keys)} 个过期记录")
    
    def mark_message_processed(self, msg_id: str, send_time: int, kf_key: str):
        """标记消息已处理"""
        self._processed_messages.add(msg_id)
        
        # 更新最后处理状态
        current_info = self._last_processed.get(kf_key, {})
        if send_time > current_info.get('timestamp', 0):
            self._last_processed[kf_key] = {
                'timestamp': send_time,
                'msgid': msg_id,
                'update_time': time.time()
            }
    
    def is_message_processed(self, msg_id: str) -> bool:
        """检查消息是否已处理"""
        return msg_id in self._processed_messages
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        return {
            'tracked_kf_accounts': len(self._last_processed),
            'processed_messages_count': len(self._processed_messages),
            'last_cleanup': datetime.fromtimestamp(self._last_cleanup).strftime('%Y-%m-%d %H:%M:%S'),
            'kf_accounts': {
                key: {
                    'last_processed_time': datetime.fromtimestamp(value['timestamp']).strftime('%Y-%m-%d %H:%M:%S'),
                    'last_msg_id': value['msgid']
                }
                for key, value in self._last_processed.items()
            }
        }

# 全局消息同步优化器实例
sync_optimizer = MessageSyncOptimizer()