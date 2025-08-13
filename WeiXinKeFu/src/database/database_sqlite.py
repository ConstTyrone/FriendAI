# database_sqlite.py
"""
SQLite数据库兼容层 - 提供与PostgreSQL相同的接口
"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SQLiteDatabase:
    """SQLite 数据库管理器 - 简化版"""
    
    def __init__(self):
        self.db_path = os.getenv('DATABASE_PATH', 'user_profiles.db')
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建简化的用户画像表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wechat_user_id TEXT NOT NULL,
                    profile_name TEXT NOT NULL,
                    profile_data TEXT NOT NULL,
                    message_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(wechat_user_id, profile_name)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ SQLite数据库初始化成功")
            
        except Exception as e:
            logger.error(f"SQLite数据库初始化失败: {e}")
    
    def save_user_profile(
        self,
        wechat_user_id: str,
        profile_data: Dict[str, Any],
        raw_message: str,
        message_type: str,
        ai_response: Dict[str, Any]
    ) -> Optional[int]:
        """保存用户画像（兼容PostgreSQL接口）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 将画像数据转换为JSON
            profile_json = json.dumps({
                'profile': profile_data,
                'ai_response': ai_response,
                'raw_message': raw_message[:1000]  # 限制长度
            }, ensure_ascii=False)
            
            # 插入或更新
            cursor.execute('''
                INSERT OR REPLACE INTO user_profiles 
                (wechat_user_id, profile_name, profile_data, message_type)
                VALUES (?, ?, ?, ?)
            ''', (
                wechat_user_id,
                profile_data.get('name', '未知'),
                profile_json,
                message_type
            ))
            
            profile_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"✅ 保存用户画像成功 (SQLite): {profile_data.get('name', '未知')}")
            return profile_id
            
        except Exception as e:
            logger.error(f"保存用户画像失败 (SQLite): {e}")
            return None
    
    def log_message(
        self,
        wechat_user_id: str,
        message_id: str,
        message_type: str,
        success: bool = True,
        error_message: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        profile_id: Optional[int] = None
    ):
        """记录消息日志（SQLite版本暂不实现）"""
        pass
    
    def get_user_profiles(self, wechat_user_id: str, limit: int = 20, offset: int = 0):
        """获取用户画像列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM user_profiles 
                WHERE wechat_user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (wechat_user_id, limit, offset))
            
            profiles = []
            for row in cursor.fetchall():
                profile_data = json.loads(row['profile_data'])
                profiles.append({
                    'id': row['id'],
                    'profile_name': row['profile_name'],
                    'message_type': row['message_type'],
                    'created_at': row['created_at'],
                    **profile_data.get('profile', {})
                })
            
            conn.close()
            return profiles, len(profiles)
            
        except Exception as e:
            logger.error(f"获取用户画像失败 (SQLite): {e}")
            return [], 0

# 全局实例
database_manager = SQLiteDatabase()