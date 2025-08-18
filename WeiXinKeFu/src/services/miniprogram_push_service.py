"""
微信小程序订阅消息推送服务
实现意图匹配成功后的小程序通知推送
"""

import json
import sqlite3
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..config.config import config

logger = logging.getLogger(__name__)

class MiniProgramPushService:
    """微信小程序推送服务"""
    
    def __init__(self, db_path: str = "user_profiles.db"):
        self.db_path = db_path
        self.access_token = None
        self.token_expires_at = 0
        self._ensure_subscription_table()
    
    def _ensure_subscription_table(self):
        """确保订阅表存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建用户订阅表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    openid TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    template_name TEXT,
                    subscribe_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    remaining_times INTEGER DEFAULT 1,
                    UNIQUE(user_id, template_id)
                )
            """)
            
            # 创建推送记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS miniprogram_push_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    openid TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    intent_id INTEGER,
                    profile_id INTEGER,
                    match_id INTEGER,
                    push_data TEXT,
                    push_status TEXT,
                    error_msg TEXT,
                    pushed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"创建订阅表失败: {e}")
    
    def get_access_token(self) -> Optional[str]:
        """
        获取小程序 access_token
        """
        import time
        
        # 检查缓存的token是否有效
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        try:
            # 调用微信API获取access_token
            url = "https://api.weixin.qq.com/cgi-bin/token"
            params = {
                "grant_type": "client_credential",
                "appid": config.wechat_mini_appid,
                "secret": config.wechat_mini_secret
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if "access_token" in data:
                self.access_token = data["access_token"]
                # 提前5分钟过期，避免边界情况
                self.token_expires_at = time.time() + data.get("expires_in", 7200) - 300
                logger.info("获取小程序access_token成功")
                return self.access_token
            else:
                logger.error(f"获取access_token失败: {data}")
                return None
                
        except Exception as e:
            logger.error(f"获取access_token异常: {e}")
            return None
    
    def save_user_subscription(self, user_id: str, openid: str, 
                              template_id: str, template_name: str = None):
        """
        保存用户订阅信息
        
        Args:
            user_id: 系统用户ID
            openid: 微信openid
            template_id: 订阅消息模板ID
            template_name: 模板名称（可选）
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_subscriptions (
                    user_id, openid, template_id, template_name,
                    subscribe_time, is_active, remaining_times
                ) VALUES (?, ?, ?, ?, ?, 1, 1)
            """, (user_id, openid, template_id, template_name, 
                  datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"保存用户订阅: {user_id} -> {template_id}")
            return True
            
        except Exception as e:
            logger.error(f"保存订阅信息失败: {e}")
            return False
    
    def get_user_subscriptions(self, user_id: str) -> List[Dict]:
        """
        获取用户的有效订阅
        
        Args:
            user_id: 用户ID
            
        Returns:
            订阅列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT openid, template_id, template_name, remaining_times
                FROM user_subscriptions
                WHERE user_id = ? AND is_active = 1 AND remaining_times > 0
            """, (user_id,))
            
            subscriptions = []
            for row in cursor.fetchall():
                subscriptions.append({
                    "openid": row[0],
                    "template_id": row[1],
                    "template_name": row[2],
                    "remaining_times": row[3]
                })
            
            conn.close()
            return subscriptions
            
        except Exception as e:
            logger.error(f"获取订阅信息失败: {e}")
            return []
    
    def send_match_notification(self, user_id: str, match_data: Dict[str, Any]) -> bool:
        """
        发送匹配成功通知
        
        Args:
            user_id: 用户ID
            match_data: 匹配数据，包含:
                - profile_name: 联系人名称
                - intent_name: 意图名称
                - score: 匹配分数
                - match_id: 匹配ID
                
        Returns:
            是否发送成功
        """
        # 获取用户订阅信息
        subscriptions = self.get_user_subscriptions(user_id)
        if not subscriptions:
            logger.warning(f"用户 {user_id} 没有有效订阅")
            return False
        
        # 使用第一个有效订阅（通常是匹配通知模板）
        subscription = subscriptions[0]
        openid = subscription["openid"]
        template_id = subscription["template_id"]
        
        # 获取access_token
        access_token = self.get_access_token()
        if not access_token:
            logger.error("无法获取access_token")
            return False
        
        # 构建推送数据
        push_data = self._build_push_data(
            openid=openid,
            template_id=template_id,
            match_data=match_data
        )
        
        # 发送订阅消息
        success = self._send_subscribe_message(access_token, push_data)
        
        # 记录推送历史
        self._record_push_history(
            user_id=user_id,
            openid=openid,
            template_id=template_id,
            match_data=match_data,
            success=success
        )
        
        # 更新剩余次数
        if success:
            self._update_remaining_times(user_id, template_id)
        
        return success
    
    def _build_push_data(self, openid: str, template_id: str, 
                        match_data: Dict[str, Any]) -> Dict:
        """
        构建推送数据
        
        注意：这里需要根据实际的模板配置来调整字段
        在微信公众平台配置的模板示例：
        - thing1: 匹配对象
        - thing2: 意图名称
        - number3: 匹配度
        - time4: 匹配时间
        """
        # 格式化匹配度
        score_text = f"{int(match_data.get('score', 0) * 100)}%"
        
        # 截断过长的文本（微信限制20个字符）
        profile_name = match_data.get('profile_name', '新联系人')[:20]
        intent_name = match_data.get('intent_name', '您的意图')[:20]
        
        return {
            "touser": openid,
            "template_id": template_id,
            "page": f"pages/matches/matches?id={match_data.get('match_id', '')}",
            "miniprogram_state": "formal",  # formal正式版，developer开发版，trial体验版
            "lang": "zh_CN",
            "data": {
                "thing1": {
                    "value": profile_name
                },
                "thing2": {
                    "value": intent_name
                },
                "number3": {
                    "value": score_text
                },
                "time4": {
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
            }
        }
    
    def _send_subscribe_message(self, access_token: str, push_data: Dict) -> bool:
        """
        调用微信API发送订阅消息
        
        Args:
            access_token: 访问令牌
            push_data: 推送数据
            
        Returns:
            是否成功
        """
        try:
            url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}"
            
            response = requests.post(url, json=push_data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"订阅消息发送成功: {push_data['touser']}")
                return True
            else:
                logger.error(f"订阅消息发送失败: {result}")
                # 处理特殊错误码
                if result.get("errcode") == 43101:
                    logger.warning("用户拒绝接收消息")
                elif result.get("errcode") == 47003:
                    logger.warning("模板参数不正确")
                elif result.get("errcode") == 40003:
                    logger.warning("openid不正确")
                return False
                
        except Exception as e:
            logger.error(f"发送订阅消息异常: {e}")
            return False
    
    def _record_push_history(self, user_id: str, openid: str, template_id: str,
                            match_data: Dict, success: bool):
        """记录推送历史"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO miniprogram_push_history (
                    user_id, openid, template_id,
                    intent_id, profile_id, match_id,
                    push_data, push_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, openid, template_id,
                match_data.get('intent_id'),
                match_data.get('profile_id'),
                match_data.get('match_id'),
                json.dumps(match_data),
                'success' if success else 'failed'
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录推送历史失败: {e}")
    
    def _update_remaining_times(self, user_id: str, template_id: str):
        """更新剩余推送次数"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 减少剩余次数
            cursor.execute("""
                UPDATE user_subscriptions
                SET remaining_times = remaining_times - 1
                WHERE user_id = ? AND template_id = ? AND remaining_times > 0
            """, (user_id, template_id))
            
            # 如果次数用完，标记为非活跃
            cursor.execute("""
                UPDATE user_subscriptions
                SET is_active = 0
                WHERE user_id = ? AND template_id = ? AND remaining_times <= 0
            """, (user_id, template_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"更新剩余次数失败: {e}")
    
    def batch_send_notifications(self, matches: List[Dict[str, Any]]) -> int:
        """
        批量发送通知
        
        Args:
            matches: 匹配列表，每个包含user_id和match_data
            
        Returns:
            成功发送的数量
        """
        success_count = 0
        
        for match in matches:
            user_id = match.get('user_id')
            match_data = match.get('match_data')
            
            if self.send_match_notification(user_id, match_data):
                success_count += 1
        
        logger.info(f"批量推送完成: {success_count}/{len(matches)}")
        return success_count

# 全局实例
miniprogram_push_service = MiniProgramPushService()