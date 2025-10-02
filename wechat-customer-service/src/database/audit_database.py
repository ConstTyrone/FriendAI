# audit_database.py
"""
简化版用户活动审计数据库
记录用户使用统计：总用户数、活跃度、消息次数等
"""
import os
import sqlite3
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class AuditDatabase:
    """用户活动审计数据库"""

    def __init__(self):
        self.db_path = os.getenv('DATABASE_PATH', 'wechat_profiles.db')
        self._init_database()

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """初始化审计表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 创建用户活动表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_activity (
                        external_userid TEXT PRIMARY KEY,
                        first_visit TIMESTAMP NOT NULL,
                        last_visit TIMESTAMP NOT NULL,
                        message_count INTEGER DEFAULT 0,
                        ai_chat_count INTEGER DEFAULT 0,
                        emoticon_count INTEGER DEFAULT 0,
                        text_message_count INTEGER DEFAULT 0,
                        voice_message_count INTEGER DEFAULT 0,
                        image_message_count INTEGER DEFAULT 0,
                        file_message_count INTEGER DEFAULT 0,
                        last_active_date TEXT NOT NULL
                    )
                ''')

                # 为已存在的表添加新字段（如果不存在）
                try:
                    cursor.execute('ALTER TABLE user_activity ADD COLUMN text_message_count INTEGER DEFAULT 0')
                except:
                    pass  # 字段已存在
                try:
                    cursor.execute('ALTER TABLE user_activity ADD COLUMN voice_message_count INTEGER DEFAULT 0')
                except:
                    pass
                try:
                    cursor.execute('ALTER TABLE user_activity ADD COLUMN image_message_count INTEGER DEFAULT 0')
                except:
                    pass
                try:
                    cursor.execute('ALTER TABLE user_activity ADD COLUMN file_message_count INTEGER DEFAULT 0')
                except:
                    pass

                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_active_date ON user_activity(last_active_date)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_visit ON user_activity(last_visit)')

                conn.commit()
                logger.info("✅ 审计数据库表初始化成功")

        except Exception as e:
            logger.error(f"审计数据库初始化失败: {e}")

    def record_message(
        self,
        external_userid: str,
        business_type: str,
        input_type: str = None
    ) -> bool:
        """
        记录用户消息活动

        Args:
            external_userid: 用户ID
            business_type: 业务类型 ('ai_chat' 或 'emoticon')
            input_type: 输入类型 ('text', 'voice', 'image', 'file')，可选

        Returns:
            是否记录成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                now = datetime.now()
                today = date.today().isoformat()

                # 检查用户是否存在
                cursor.execute(
                    'SELECT external_userid FROM user_activity WHERE external_userid = ?',
                    (external_userid,)
                )
                existing = cursor.fetchone()

                if existing:
                    # 更新现有用户
                    update_fields = {
                        'last_visit': now,
                        'last_active_date': today,
                        'message_count': 'message_count + 1'
                    }

                    # 根据业务类型增加对应计数
                    if business_type == 'ai_chat':
                        update_fields['ai_chat_count'] = 'ai_chat_count + 1'
                    elif business_type == 'emoticon':
                        update_fields['emoticon_count'] = 'emoticon_count + 1'

                    # 根据输入类型增加对应计数（如果提供）
                    if input_type == 'text':
                        update_fields['text_message_count'] = 'text_message_count + 1'
                    elif input_type == 'voice':
                        update_fields['voice_message_count'] = 'voice_message_count + 1'
                    elif input_type == 'image':
                        update_fields['image_message_count'] = 'image_message_count + 1'
                    elif input_type == 'file':
                        update_fields['file_message_count'] = 'file_message_count + 1'

                    # 构建UPDATE语句
                    counter_fields = ['message_count', 'ai_chat_count', 'emoticon_count',
                                     'text_message_count', 'voice_message_count',
                                     'image_message_count', 'file_message_count']
                    set_clause = ', '.join([
                        f"{k} = {v}" if k in counter_fields else f"{k} = ?"
                        for k, v in update_fields.items()
                    ])
                    params = [v for k, v in update_fields.items() if k not in counter_fields]
                    params.append(external_userid)

                    cursor.execute(
                        f'UPDATE user_activity SET {set_clause} WHERE external_userid = ?',
                        params
                    )
                else:
                    # 插入新用户
                    ai_count = 1 if business_type == 'ai_chat' else 0
                    emoticon_count = 1 if business_type == 'emoticon' else 0
                    text_count = 1 if input_type == 'text' else 0
                    voice_count = 1 if input_type == 'voice' else 0
                    image_count = 1 if input_type == 'image' else 0
                    file_count = 1 if input_type == 'file' else 0

                    cursor.execute('''
                        INSERT INTO user_activity (
                            external_userid, first_visit, last_visit,
                            message_count, ai_chat_count, emoticon_count,
                            text_message_count, voice_message_count,
                            image_message_count, file_message_count,
                            last_active_date
                        ) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                    ''', (external_userid, now, now, ai_count, emoticon_count,
                          text_count, voice_count, image_count, file_count, today))

                conn.commit()
                return True

        except Exception as e:
            logger.error(f"记录用户活动失败: {e}", exc_info=True)
            return False

    def get_total_stats(self) -> Dict[str, Any]:
        """
        获取总体统计数据

        Returns:
            统计数据字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                today = date.today().isoformat()

                # 总用户数
                cursor.execute('SELECT COUNT(*) as total FROM user_activity')
                total_users = cursor.fetchone()['total']

                # 今日活跃用户数（DAU）
                cursor.execute(
                    'SELECT COUNT(*) as dau FROM user_activity WHERE last_active_date = ?',
                    (today,)
                )
                dau = cursor.fetchone()['dau']

                # 总消息数
                cursor.execute('SELECT SUM(message_count) as total FROM user_activity')
                total_messages = cursor.fetchone()['total'] or 0

                # AI对话总数
                cursor.execute('SELECT SUM(ai_chat_count) as total FROM user_activity')
                ai_chats = cursor.fetchone()['total'] or 0

                # 表情包总数
                cursor.execute('SELECT SUM(emoticon_count) as total FROM user_activity')
                emoticons = cursor.fetchone()['total'] or 0

                # 各类型消息统计
                cursor.execute('SELECT SUM(text_message_count) as total FROM user_activity')
                text_messages = cursor.fetchone()['total'] or 0

                cursor.execute('SELECT SUM(voice_message_count) as total FROM user_activity')
                voice_messages = cursor.fetchone()['total'] or 0

                cursor.execute('SELECT SUM(image_message_count) as total FROM user_activity')
                image_messages = cursor.fetchone()['total'] or 0

                cursor.execute('SELECT SUM(file_message_count) as total FROM user_activity')
                file_messages = cursor.fetchone()['total'] or 0

                return {
                    'total_users': total_users,
                    'active_today': dau,
                    'total_messages': total_messages,
                    'ai_chats': ai_chats,
                    'emoticons': emoticons,
                    'text_messages': text_messages,
                    'voice_messages': voice_messages,
                    'image_messages': image_messages,
                    'file_messages': file_messages
                }

        except Exception as e:
            logger.error(f"获取总体统计失败: {e}")
            return {
                'total_users': 0,
                'active_today': 0,
                'total_messages': 0,
                'ai_chats': 0,
                'emoticons': 0,
                'text_messages': 0,
                'voice_messages': 0,
                'image_messages': 0,
                'file_messages': 0
            }

    def get_message_type_distribution(self) -> Dict[str, int]:
        """
        获取消息类型分布

        Returns:
            各类型消息数量
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT
                        SUM(text_message_count) as text_count,
                        SUM(voice_message_count) as voice_count,
                        SUM(image_message_count) as image_count,
                        SUM(file_message_count) as file_count,
                        SUM(emoticon_count) as emoticon_count
                    FROM user_activity
                ''')

                row = cursor.fetchone()
                return {
                    'text': row['text_count'] or 0,
                    'voice': row['voice_count'] or 0,
                    'image': row['image_count'] or 0,
                    'file': row['file_count'] or 0,
                    'emoticon': row['emoticon_count'] or 0
                }

        except Exception as e:
            logger.error(f"获取消息类型分布失败: {e}")
            return {
                'text': 0,
                'voice': 0,
                'image': 0,
                'file': 0,
                'emoticon': 0
            }

    def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最活跃用户排行

        Args:
            limit: 返回数量

        Returns:
            用户列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT
                        external_userid,
                        message_count,
                        ai_chat_count,
                        emoticon_count,
                        first_visit,
                        last_visit
                    FROM user_activity
                    ORDER BY message_count DESC
                    LIMIT ?
                ''', (limit,))

                rows = cursor.fetchall()
                users = []
                for row in rows:
                    users.append({
                        'userid': row['external_userid'],
                        'message_count': row['message_count'],
                        'ai_chat_count': row['ai_chat_count'],
                        'emoticon_count': row['emoticon_count'],
                        'first_visit': row['first_visit'],
                        'last_visit': row['last_visit']
                    })

                return users

        except Exception as e:
            logger.error(f"获取活跃用户失败: {e}")
            return []

    def get_user_stats(self, external_userid: str) -> Optional[Dict[str, Any]]:
        """
        获取单个用户的统计数据

        Args:
            external_userid: 用户ID

        Returns:
            用户统计数据
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM user_activity WHERE external_userid = ?
                ''', (external_userid,))

                row = cursor.fetchone()
                if row:
                    return {
                        'userid': row['external_userid'],
                        'first_visit': row['first_visit'],
                        'last_visit': row['last_visit'],
                        'message_count': row['message_count'],
                        'ai_chat_count': row['ai_chat_count'],
                        'emoticon_count': row['emoticon_count'],
                        'last_active_date': row['last_active_date']
                    }

                return None

        except Exception as e:
            logger.error(f"获取用户统计失败: {e}")
            return None


# 创建全局审计数据库实例
audit_db = AuditDatabase()
