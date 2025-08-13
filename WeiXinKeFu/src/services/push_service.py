"""
推送服务模块
实现意图匹配结果的推送通知
"""

import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger(__name__)

class PushService:
    """推送服务类"""
    
    def __init__(self, db_path: str = "user_profiles.db"):
        self.db_path = db_path
        self.push_queue = []  # 推送队列
        
    def check_push_eligibility(self, user_id: str, intent_id: int) -> bool:
        """
        检查是否可以推送
        
        Args:
            user_id: 用户ID
            intent_id: 意图ID
            
        Returns:
            是否可以推送
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取用户推送偏好设置
            cursor.execute("""
                SELECT push_enabled, push_frequency, quiet_hours_start, quiet_hours_end
                FROM user_push_preferences
                WHERE user_id = ?
            """, (user_id,))
            
            pref_row = cursor.fetchone()
            if not pref_row:
                # 没有设置，使用默认值
                push_enabled = True
                push_frequency = "realtime"
                quiet_hours_start = None
                quiet_hours_end = None
            else:
                push_enabled, push_frequency, quiet_hours_start, quiet_hours_end = pref_row
            
            # 检查是否启用推送
            if not push_enabled:
                logger.info(f"用户 {user_id} 已禁用推送")
                return False
            
            # 检查静默时间
            if quiet_hours_start and quiet_hours_end:
                current_hour = datetime.now().hour
                start_hour = int(quiet_hours_start.split(':')[0])
                end_hour = int(quiet_hours_end.split(':')[0])
                
                if start_hour <= current_hour < end_hour:
                    logger.info(f"当前在用户 {user_id} 的静默时间内")
                    return False
            
            # 检查意图的每日推送限制
            cursor.execute("""
                SELECT max_push_per_day FROM user_intents
                WHERE id = ? AND user_id = ?
            """, (intent_id, user_id))
            
            intent_row = cursor.fetchone()
            if not intent_row:
                conn.close()
                return False
            
            max_push_per_day = intent_row[0] or 5
            
            # 检查今日已推送次数
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cursor.execute("""
                SELECT COUNT(*) FROM push_history
                WHERE user_id = ? AND intent_id = ?
                AND pushed_at >= ?
            """, (user_id, intent_id, today_start.isoformat()))
            
            today_count = cursor.fetchone()[0]
            
            conn.close()
            
            if today_count >= max_push_per_day:
                logger.info(f"意图 {intent_id} 今日推送已达上限 {max_push_per_day}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查推送资格失败: {e}")
            return False
    
    def record_push(self, user_id: str, intent_id: int, profile_id: int, 
                   match_id: int) -> bool:
        """
        记录推送历史
        
        Args:
            user_id: 用户ID
            intent_id: 意图ID
            profile_id: 联系人ID
            match_id: 匹配记录ID
            
        Returns:
            是否记录成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 记录推送历史
            cursor.execute("""
                INSERT INTO push_history (
                    user_id, intent_id, profile_id, match_id,
                    push_type, push_status
                ) VALUES (?, ?, ?, ?, 'match_notification', 'sent')
            """, (user_id, intent_id, profile_id, match_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"记录推送历史成功: 用户{user_id}, 意图{intent_id}, 联系人{profile_id}")
            return True
            
        except Exception as e:
            logger.error(f"记录推送失败: {e}")
            return False
    
    def prepare_push_message(self, match_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备推送消息内容
        
        Args:
            match_data: 匹配数据
            
        Returns:
            推送消息对象
        """
        profile_name = match_data.get('profile_name', '某联系人')
        intent_name = match_data.get('intent_name', '您的意图')
        score = match_data.get('score', 0)
        explanation = match_data.get('explanation', '符合您的需求')
        
        return {
            "title": f"找到匹配的联系人",
            "content": f"{profile_name} 符合 [{intent_name}]",
            "detail": explanation,
            "score": f"{score:.0%}匹配度",
            "action": {
                "type": "view_profile",
                "profile_id": match_data.get('profile_id'),
                "intent_id": match_data.get('intent_id')
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def send_push_notification(self, user_id: str, message: Dict[str, Any]) -> bool:
        """
        发送推送通知（异步）
        
        Args:
            user_id: 用户ID
            message: 推送消息
            
        Returns:
            是否发送成功
        """
        try:
            # TODO: 实际的推送实现
            # 这里可以集成：
            # 1. 微信服务通知（需要用户订阅）
            # 2. 企业微信应用消息
            # 3. 邮件通知
            # 4. 短信通知
            
            logger.info(f"推送消息给用户 {user_id}: {message['title']}")
            
            # 模拟推送延迟
            await asyncio.sleep(0.1)
            
            # 将消息加入队列（用于批量推送）
            self.push_queue.append({
                "user_id": user_id,
                "message": message,
                "created_at": datetime.now()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"发送推送失败: {e}")
            return False
    
    def process_match_for_push(self, match_data: Dict[str, Any], user_id: str) -> bool:
        """
        处理匹配结果并决定是否推送
        
        Args:
            match_data: 匹配数据
            user_id: 用户ID
            
        Returns:
            是否推送成功
        """
        try:
            intent_id = match_data.get('intent_id')
            profile_id = match_data.get('profile_id')
            match_id = match_data.get('match_id')
            
            # 检查是否可以推送
            if not self.check_push_eligibility(user_id, intent_id):
                return False
            
            # 准备推送消息
            message = self.prepare_push_message(match_data)
            
            # 发送推送（同步方式）
            # 实际使用时应该用异步方式
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(
                self.send_push_notification(user_id, message)
            )
            loop.close()
            
            if success:
                # 记录推送历史
                self.record_push(user_id, intent_id, profile_id, match_id)
            
            return success
            
        except Exception as e:
            logger.error(f"处理推送失败: {e}")
            return False
    
    def batch_process_matches(self, matches: List[Dict[str, Any]], user_id: str):
        """
        批量处理匹配结果的推送
        
        Args:
            matches: 匹配结果列表
            user_id: 用户ID
        """
        pushed_count = 0
        max_batch_push = 3  # 批量推送上限
        
        for match in matches[:max_batch_push]:  # 限制批量推送数量
            if self.process_match_for_push(match, user_id):
                pushed_count += 1
        
        logger.info(f"批量推送完成：成功推送 {pushed_count}/{len(matches)} 个匹配")
    
    def get_push_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户推送统计
        
        Args:
            user_id: 用户ID
            
        Returns:
            推送统计数据
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 今日推送数
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cursor.execute("""
                SELECT COUNT(*) FROM push_history
                WHERE user_id = ? AND pushed_at >= ?
            """, (user_id, today_start.isoformat()))
            today_count = cursor.fetchone()[0]
            
            # 本周推送数
            week_start = datetime.now() - timedelta(days=7)
            cursor.execute("""
                SELECT COUNT(*) FROM push_history
                WHERE user_id = ? AND pushed_at >= ?
            """, (user_id, week_start.isoformat()))
            week_count = cursor.fetchone()[0]
            
            # 总推送数
            cursor.execute("""
                SELECT COUNT(*) FROM push_history
                WHERE user_id = ?
            """, (user_id,))
            total_count = cursor.fetchone()[0]
            
            # 最近推送
            cursor.execute("""
                SELECT * FROM push_history
                WHERE user_id = ?
                ORDER BY pushed_at DESC
                LIMIT 5
            """, (user_id,))
            
            recent_pushes = []
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                recent_pushes.append(dict(zip(columns, row)))
            
            conn.close()
            
            return {
                "today_count": today_count,
                "week_count": week_count,
                "total_count": total_count,
                "recent_pushes": recent_pushes
            }
            
        except Exception as e:
            logger.error(f"获取推送统计失败: {e}")
            return {
                "today_count": 0,
                "week_count": 0,
                "total_count": 0,
                "recent_pushes": []
            }

# 全局推送服务实例
push_service = PushService()