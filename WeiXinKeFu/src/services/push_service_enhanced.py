"""
增强版推送服务模块
实现微信客服消息推送功能
"""

import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from ..services.wework_client import wework_client

logger = logging.getLogger(__name__)

class EnhancedPushService:
    """增强版推送服务类"""
    
    def __init__(self, db_path: str = "user_profiles.db"):
        self.db_path = db_path
        self.push_queue = []
        self._ensure_push_tables()
    
    def _ensure_push_tables(self):
        """确保推送相关表结构正确"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 确保会话表存在
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wechat_kf_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    external_userid TEXT NOT NULL,
                    open_kfid TEXT NOT NULL,
                    last_message_time TIMESTAMP,
                    message_count_48h INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, open_kfid)
                )
            """)
            
            # 确保推送模板表存在
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS push_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_name TEXT NOT NULL UNIQUE,
                    template_type TEXT NOT NULL,
                    title_template TEXT,
                    content_template TEXT NOT NULL,
                    detail_template TEXT,
                    miniprogram_config TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"确保推送表结构时出错: {e}")
    
    def update_user_session(self, user_id: str, external_userid: str, open_kfid: str):
        """
        更新用户会话信息（在收到用户消息时调用）
        
        Args:
            user_id: 内部用户ID
            external_userid: 微信外部用户ID
            open_kfid: 客服账号ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 更新会话信息
            cursor.execute("""
                INSERT OR REPLACE INTO wechat_kf_sessions (
                    user_id, external_userid, open_kfid, 
                    last_message_time, message_count_48h, updated_at
                ) VALUES (?, ?, ?, ?, 0, ?)
            """, (user_id, external_userid, open_kfid, 
                  datetime.now().isoformat(), datetime.now().isoformat()))
            
            # 同时更新用户推送偏好表
            cursor.execute("""
                UPDATE user_push_preferences 
                SET open_kfid = ?, external_userid = ?, last_message_time = ?
                WHERE user_id = ?
            """, (open_kfid, external_userid, datetime.now().isoformat(), user_id))
            
            if cursor.rowcount == 0:
                # 如果不存在，创建新记录
                cursor.execute("""
                    INSERT INTO user_push_preferences (
                        user_id, open_kfid, external_userid, 
                        last_message_time, enable_push
                    ) VALUES (?, ?, ?, ?, 1)
                """, (user_id, open_kfid, external_userid, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"更新用户会话信息成功: {user_id} -> {open_kfid}")
            
        except Exception as e:
            logger.error(f"更新用户会话信息失败: {e}")
    
    def get_user_session(self, user_id: str) -> Optional[Tuple[str, str]]:
        """
        获取用户的会话信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            (external_userid, open_kfid) 或 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 优先从会话表获取
            cursor.execute("""
                SELECT external_userid, open_kfid, last_message_time
                FROM wechat_kf_sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                external_userid, open_kfid, last_msg_time = row
                
                # 检查48小时限制
                if last_msg_time:
                    last_time = datetime.fromisoformat(last_msg_time)
                    if datetime.now() - last_time > timedelta(hours=48):
                        logger.warning(f"用户 {user_id} 超过48小时未发消息，无法推送")
                        return None
                
                return external_userid, open_kfid
            
            return None
            
        except Exception as e:
            logger.error(f"获取用户会话信息失败: {e}")
            return None
    
    def check_push_eligibility_enhanced(self, user_id: str, intent_id: int) -> Tuple[bool, str]:
        """
        增强版推送资格检查
        
        Args:
            user_id: 用户ID
            intent_id: 意图ID
            
        Returns:
            (是否可推送, 原因说明)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查用户是否有有效会话
            session_info = self.get_user_session(user_id)
            if not session_info:
                return False, "用户无有效会话或超过48小时限制"
            
            # 获取用户推送偏好
            cursor.execute("""
                SELECT enable_push, quiet_hours, push_count_48h, last_message_time
                FROM user_push_preferences
                WHERE user_id = ?
            """, (user_id,))
            
            pref_row = cursor.fetchone()
            if not pref_row:
                # 没有设置，使用默认值
                push_enabled = True
                quiet_hours = None
                push_count_48h = 0
                last_msg_time = None
            else:
                push_enabled, quiet_hours, push_count_48h, last_msg_time = pref_row
            
            # 检查是否启用推送
            if not push_enabled:
                conn.close()
                return False, "用户已禁用推送"
            
            # 检查48小时内推送次数（微信限制5条）
            if push_count_48h and push_count_48h >= 5:
                conn.close()
                return False, "48小时内推送已达上限(5条)"
            
            # 检查静默时间
            if quiet_hours:
                try:
                    hours_parts = quiet_hours.split('-')
                    if len(hours_parts) == 2:
                        start_time = hours_parts[0]
                        end_time = hours_parts[1]
                        current_hour = datetime.now().hour
                        start_hour = int(start_time.split(':')[0])
                        end_hour = int(end_time.split(':')[0])
                        
                        # 处理跨夜的情况
                        if start_hour > end_hour:
                            if current_hour >= start_hour or current_hour < end_hour:
                                conn.close()
                                return False, "当前在静默时间内"
                        else:
                            if start_hour <= current_hour < end_hour:
                                conn.close()
                                return False, "当前在静默时间内"
                except Exception as e:
                    logger.warning(f"解析静默时间失败: {e}")
            
            # 检查意图的每日推送限制
            cursor.execute("""
                SELECT max_push_per_day FROM user_intents
                WHERE id = ? AND user_id = ?
            """, (intent_id, user_id))
            
            intent_row = cursor.fetchone()
            if not intent_row:
                conn.close()
                return False, "意图不存在"
            
            max_push_per_day = intent_row[0] or 5
            
            # 检查今日已推送次数
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 使用用户独立的推送历史表
            history_table = f"push_history_{user_id.replace('-', '_')}"
            
            # 检查表是否存在
            cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{history_table}'
            """)
            
            if cursor.fetchone():
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {history_table}
                    WHERE intent_id = ? AND created_at >= ?
                """, (intent_id, today_start.isoformat()))
                
                today_count = cursor.fetchone()[0]
                
                if today_count >= max_push_per_day:
                    conn.close()
                    return False, f"意图今日推送已达上限({max_push_per_day}条)"
            
            conn.close()
            return True, "可以推送"
            
        except Exception as e:
            logger.error(f"检查推送资格失败: {e}")
            return False, f"检查失败: {e}"
    
    def format_push_message(self, match_data: Dict[str, Any], template_name: str = 'match_notification_text') -> str:
        """
        使用模板格式化推送消息
        
        Args:
            match_data: 匹配数据
            template_name: 模板名称
            
        Returns:
            格式化后的消息内容
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取模板
            cursor.execute("""
                SELECT template_type, title_template, content_template, detail_template
                FROM push_templates
                WHERE template_name = ? AND is_active = 1
            """, (template_name,))
            
            template_row = cursor.fetchone()
            conn.close()
            
            if not template_row:
                # 使用默认模板
                content = f"""🎯 找到匹配的联系人

【{match_data.get('profile_name', '某联系人')}】符合您的意图【{match_data.get('intent_name', '您的意图')}】

匹配度：{match_data.get('score', 0):.0%}
{match_data.get('explanation', '符合您的需求')}

回复"查看{match_data.get('profile_id', '')}"了解详情"""
            else:
                template_type, title_template, content_template, detail_template = template_row
                
                # 准备替换数据
                format_data = {
                    'profile_name': match_data.get('profile_name', '某联系人'),
                    'intent_name': match_data.get('intent_name', '您的意图'),
                    'score': f"{match_data.get('score', 0)*100:.0f}",
                    'explanation': match_data.get('explanation', ''),
                    'profile_id': match_data.get('profile_id', ''),
                    'matched_conditions': ', '.join(match_data.get('matched_conditions', []))
                }
                
                # 格式化内容
                content = content_template.format(**format_data)
            
            return content
            
        except Exception as e:
            logger.error(f"格式化推送消息失败: {e}")
            # 返回简单消息
            return f"找到匹配：{match_data.get('profile_name')} 符合 {match_data.get('intent_name')}"
    
    def send_wechat_push(self, user_id: str, message_content: str, 
                         message_type: str = 'text', extra_params: Dict = None) -> bool:
        """
        发送微信客服推送消息
        
        Args:
            user_id: 用户ID
            message_content: 消息内容
            message_type: 消息类型（text, miniprogram）
            extra_params: 额外参数（如小程序配置）
            
        Returns:
            是否发送成功
        """
        try:
            # 获取用户会话信息
            session_info = self.get_user_session(user_id)
            if not session_info:
                logger.warning(f"用户 {user_id} 无有效会话，无法推送")
                return False
            
            external_userid, open_kfid = session_info
            
            # 根据消息类型发送
            if message_type == 'text':
                # 发送文本消息
                result = wework_client.send_text_message(
                    external_userid=external_userid,
                    open_kfid=open_kfid,
                    content=message_content
                )
            elif message_type == 'miniprogram' and extra_params:
                # 发送小程序消息
                result = self._send_miniprogram_message(
                    external_userid, open_kfid, message_content, extra_params
                )
            else:
                # 默认发送文本消息
                result = wework_client.send_text_message(
                    external_userid=external_userid,
                    open_kfid=open_kfid,
                    content=message_content
                )
            
            if result and result.get('errcode') == 0:
                # 更新推送计数
                self._update_push_count(user_id)
                logger.info(f"推送成功: 用户{user_id}, 消息ID: {result.get('msgid')}")
                return True
            else:
                logger.error(f"推送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"发送推送失败: {e}")
            return False
    
    def _send_miniprogram_message(self, external_userid: str, open_kfid: str, 
                                  title: str, extra_params: Dict) -> Dict:
        """
        发送小程序消息
        
        Args:
            external_userid: 外部用户ID
            open_kfid: 客服账号ID
            title: 标题
            extra_params: 小程序参数
            
        Returns:
            API响应
        """
        try:
            import requests
            
            access_token = wework_client.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/kf/send_msg?access_token={access_token}"
            
            payload = {
                "touser": external_userid,
                "open_kfid": open_kfid,
                "msgtype": "miniprogram",
                "miniprogram": {
                    "appid": extra_params.get('appid', 'wx50fc05960f4152a6'),
                    "title": title,
                    "thumb_media_id": extra_params.get('thumb_media_id', ''),
                    "pagepath": extra_params.get('pagepath', 'pages/matches/matches.html')
                }
            }
            
            response = requests.post(url, json=payload)
            return response.json()
            
        except Exception as e:
            logger.error(f"发送小程序消息失败: {e}")
            return {"errcode": -1, "errmsg": str(e)}
    
    def _update_push_count(self, user_id: str):
        """更新推送计数"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 更新48小时内推送计数
            cursor.execute("""
                UPDATE user_push_preferences
                SET push_count_48h = COALESCE(push_count_48h, 0) + 1,
                    updated_at = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            
            # 更新会话表计数
            cursor.execute("""
                UPDATE wechat_kf_sessions
                SET message_count_48h = COALESCE(message_count_48h, 0) + 1,
                    updated_at = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"更新推送计数失败: {e}")
    
    def process_match_for_push(self, match_data: Dict[str, Any], user_id: str) -> bool:
        """
        处理匹配结果并推送
        
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
            
            # 检查推送资格
            can_push, reason = self.check_push_eligibility_enhanced(user_id, intent_id)
            if not can_push:
                logger.info(f"不推送: {reason}")
                return False
            
            # 格式化推送消息
            message_content = self.format_push_message(match_data)
            
            # 发送推送
            success = self.send_wechat_push(user_id, message_content)
            
            if success:
                # 记录推送历史
                self.record_push_enhanced(user_id, intent_id, profile_id, match_id)
            
            return success
            
        except Exception as e:
            logger.error(f"处理推送失败: {e}")
            return False
    
    def record_push_enhanced(self, user_id: str, intent_id: int, 
                            profile_id: int, match_id: int) -> bool:
        """
        记录推送历史（增强版）
        
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
            
            # 获取会话信息
            session_info = self.get_user_session(user_id)
            external_userid = session_info[0] if session_info else None
            open_kfid = session_info[1] if session_info else None
            
            # 使用用户独立的推送历史表
            table_name = f"push_history_{user_id.replace('-', '_')}"
            
            # 确保表存在
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    intent_id INTEGER,
                    profile_id INTEGER,
                    match_id INTEGER,
                    push_type TEXT,
                    push_status TEXT,
                    push_channel TEXT,
                    external_userid TEXT,
                    open_kfid TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 记录推送历史
            cursor.execute(f"""
                INSERT INTO {table_name} (
                    user_id, intent_id, profile_id, match_id,
                    push_type, push_status, push_channel,
                    external_userid, open_kfid
                ) VALUES (?, ?, ?, ?, 'match_notification', 'sent', 'wechat_kf', ?, ?)
            """, (user_id, intent_id, profile_id, match_id, external_userid, open_kfid))
            
            # 更新匹配记录的推送状态
            cursor.execute("""
                UPDATE intent_matches
                SET is_pushed = 1, pushed_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), match_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"记录推送历史成功: 用户{user_id}, 意图{intent_id}, 联系人{profile_id}")
            return True
            
        except Exception as e:
            logger.error(f"记录推送失败: {e}")
            return False
    
    def reset_48h_counter(self, user_id: str):
        """
        重置48小时计数器（当用户发送新消息时调用）
        
        Args:
            user_id: 用户ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 重置推送计数
            cursor.execute("""
                UPDATE user_push_preferences
                SET push_count_48h = 0,
                    last_message_time = ?,
                    updated_at = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), datetime.now().isoformat(), user_id))
            
            # 更新会话表
            cursor.execute("""
                UPDATE wechat_kf_sessions
                SET message_count_48h = 0,
                    last_message_time = ?,
                    updated_at = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), datetime.now().isoformat(), user_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"重置用户 {user_id} 的48小时计数器")
            
        except Exception as e:
            logger.error(f"重置计数器失败: {e}")

# 全局增强版推送服务实例
enhanced_push_service = EnhancedPushService()