# database_simple.py
"""
简化的SQLite数据库管理器
单表存储所有用户画像，使用 external_userid 作为用户标识
"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class SimpleDatabase:
    """简化的SQLite数据库管理器"""

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
        """初始化数据库表结构"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 创建用户画像表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        external_userid TEXT NOT NULL,
                        name TEXT,
                        gender TEXT,
                        age TEXT,
                        phone TEXT,
                        location TEXT,
                        marital_status TEXT,
                        education TEXT,
                        company TEXT,
                        position TEXT,
                        asset_level TEXT,
                        personality TEXT,
                        raw_message TEXT,
                        message_type TEXT,
                        ai_response TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_external_userid ON profiles(external_userid)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON profiles(name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON profiles(created_at)')

                conn.commit()
                logger.info("✅ SQLite数据库初始化成功")

        except Exception as e:
            logger.error(f"SQLite数据库初始化失败: {e}")

    def save_user_profile(
        self,
        external_userid: str,
        profile_data: Dict[str, Any],
        raw_message: str,
        message_type: str,
        ai_response: Dict[str, Any]
    ) -> Optional[int]:
        """
        保存用户画像到数据库

        Args:
            external_userid: 微信客服用户ID
            profile_data: 用户画像数据字典
            raw_message: 原始消息文本
            message_type: 消息类型
            ai_response: AI完整响应

        Returns:
            保存的画像ID，失败返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 提取画像字段
                name = profile_data.get('name', '')
                gender = profile_data.get('gender', '')
                age = profile_data.get('age', '')
                phone = profile_data.get('phone', '')
                location = profile_data.get('location', '')
                marital_status = profile_data.get('marital_status', '')
                education = profile_data.get('education', '')
                company = profile_data.get('company', '')
                position = profile_data.get('position', '')
                asset_level = profile_data.get('asset_level', '')
                personality = profile_data.get('personality', '')

                # 序列化AI响应
                ai_response_json = json.dumps(ai_response, ensure_ascii=False)

                # 插入数据
                cursor.execute('''
                    INSERT INTO profiles (
                        external_userid, name, gender, age, phone, location,
                        marital_status, education, company, position,
                        asset_level, personality, raw_message, message_type,
                        ai_response, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    external_userid, name, gender, age, phone, location,
                    marital_status, education, company, position,
                    asset_level, personality, raw_message, message_type,
                    ai_response_json, datetime.now(), datetime.now()
                ))

                conn.commit()
                profile_id = cursor.lastrowid

                logger.info(f"✅ 用户画像保存成功: ID={profile_id}, external_userid={external_userid}, name={name}")
                return profile_id

        except Exception as e:
            logger.error(f"保存用户画像失败: {e}", exc_info=True)
            return None

    def get_profiles_by_user(
        self,
        external_userid: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取指定用户的所有画像记录

        Args:
            external_userid: 微信客服用户ID
            limit: 返回记录数限制
            offset: 偏移量

        Returns:
            画像记录列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, external_userid, name, gender, age, phone, location,
                           marital_status, education, company, position,
                           asset_level, personality, message_type, created_at
                    FROM profiles
                    WHERE external_userid = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (external_userid, limit, offset))

                rows = cursor.fetchall()

                profiles = []
                for row in rows:
                    profiles.append({
                        'id': row['id'],
                        'external_userid': row['external_userid'],
                        'name': row['name'],
                        'gender': row['gender'],
                        'age': row['age'],
                        'phone': row['phone'],
                        'location': row['location'],
                        'marital_status': row['marital_status'],
                        'education': row['education'],
                        'company': row['company'],
                        'position': row['position'],
                        'asset_level': row['asset_level'],
                        'personality': row['personality'],
                        'message_type': row['message_type'],
                        'created_at': row['created_at']
                    })

                return profiles

        except Exception as e:
            logger.error(f"查询用户画像失败: {e}")
            return []

    def get_profile_by_id(self, profile_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单个画像详情

        Args:
            profile_id: 画像ID

        Returns:
            画像详情字典，未找到返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM profiles WHERE id = ?
                ''', (profile_id,))

                row = cursor.fetchone()

                if row:
                    return {
                        'id': row['id'],
                        'external_userid': row['external_userid'],
                        'name': row['name'],
                        'gender': row['gender'],
                        'age': row['age'],
                        'phone': row['phone'],
                        'location': row['location'],
                        'marital_status': row['marital_status'],
                        'education': row['education'],
                        'company': row['company'],
                        'position': row['position'],
                        'asset_level': row['asset_level'],
                        'personality': row['personality'],
                        'raw_message': row['raw_message'],
                        'message_type': row['message_type'],
                        'ai_response': row['ai_response'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    }

                return None

        except Exception as e:
            logger.error(f"查询画像详情失败: {e}")
            return None

    def search_profiles(
        self,
        external_userid: str,
        search_query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        搜索用户的画像记录

        Args:
            external_userid: 微信客服用户ID
            search_query: 搜索关键词
            limit: 返回记录数限制

        Returns:
            匹配的画像记录列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                search_pattern = f"%{search_query}%"

                cursor.execute('''
                    SELECT id, external_userid, name, gender, age, phone, location,
                           marital_status, education, company, position,
                           asset_level, personality, message_type, created_at
                    FROM profiles
                    WHERE external_userid = ? AND (
                        name LIKE ? OR
                        phone LIKE ? OR
                        location LIKE ? OR
                        company LIKE ? OR
                        position LIKE ?
                    )
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (external_userid, search_pattern, search_pattern, search_pattern,
                      search_pattern, search_pattern, limit))

                rows = cursor.fetchall()

                profiles = []
                for row in rows:
                    profiles.append({
                        'id': row['id'],
                        'external_userid': row['external_userid'],
                        'name': row['name'],
                        'gender': row['gender'],
                        'age': row['age'],
                        'phone': row['phone'],
                        'location': row['location'],
                        'marital_status': row['marital_status'],
                        'education': row['education'],
                        'company': row['company'],
                        'position': row['position'],
                        'asset_level': row['asset_level'],
                        'personality': row['personality'],
                        'message_type': row['message_type'],
                        'created_at': row['created_at']
                    })

                return profiles

        except Exception as e:
            logger.error(f"搜索画像失败: {e}")
            return []

    def delete_profile(self, profile_id: int, external_userid: str) -> bool:
        """
        删除指定画像记录

        Args:
            profile_id: 画像ID
            external_userid: 用户ID（用于权限验证）

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 删除画像
                cursor.execute('''
                    DELETE FROM profiles
                    WHERE id = ? AND external_userid = ?
                ''', (profile_id, external_userid))

                conn.commit()

                if cursor.rowcount > 0:
                    logger.info(f"✅ 画像删除成功: ID={profile_id}")
                    return True
                else:
                    logger.warning(f"未找到画像或权限不足: ID={profile_id}")
                    return False

        except Exception as e:
            logger.error(f"删除画像失败: {e}")
            return False

    def get_user_statistics(self, external_userid: str) -> Dict[str, Any]:
        """
        获取用户的统计数据

        Args:
            external_userid: 微信客服用户ID

        Returns:
            统计数据字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 总画像数
                cursor.execute('''
                    SELECT COUNT(*) as total FROM profiles
                    WHERE external_userid = ?
                ''', (external_userid,))
                total = cursor.fetchone()['total']

                # 唯一姓名数
                cursor.execute('''
                    SELECT COUNT(DISTINCT name) as unique_names FROM profiles
                    WHERE external_userid = ? AND name != '' AND name IS NOT NULL
                ''', (external_userid,))
                unique_names = cursor.fetchone()['unique_names']

                # 最近画像时间
                cursor.execute('''
                    SELECT MAX(created_at) as last_profile FROM profiles
                    WHERE external_userid = ?
                ''', (external_userid,))
                last_profile = cursor.fetchone()['last_profile']

                return {
                    'total_profiles': total,
                    'unique_names': unique_names,
                    'last_profile_at': last_profile
                }

        except Exception as e:
            logger.error(f"获取统计数据失败: {e}")
            return {
                'total_profiles': 0,
                'unique_names': 0,
                'last_profile_at': None
            }


# 创建全局数据库实例
db = SimpleDatabase()