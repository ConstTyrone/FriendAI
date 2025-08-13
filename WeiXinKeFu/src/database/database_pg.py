# database_pg.py
import os
import json
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import SimpleConnectionPool
from ..config.config import config

logger = logging.getLogger(__name__)

class PostgreSQLDatabase:
    """PostgreSQL 数据库管理器 - 用户画像存储系统"""
    
    def __init__(self):
        """初始化数据库连接"""
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/user_profiles_db')
        
        try:
            # 尝试创建连接池
            self.pool = SimpleConnectionPool(
                1, 20,  # 最小1个连接，最大20个连接
                self.database_url
            )
            
            # 初始化数据库表
            self._init_database()
            
        except psycopg2.OperationalError as e:
            logger.warning(f"⚠️ PostgreSQL连接失败: {e}")
            logger.info("💡 提示：")
            logger.info("1. 请确保PostgreSQL服务已启动")
            logger.info("2. 创建数据库: CREATE DATABASE user_profiles_db;")
            logger.info("3. 配置环境变量: DATABASE_URL=postgresql://user:password@localhost:5432/user_profiles_db")
            logger.info("4. 系统将继续使用SQLite数据库")
            
            # 回退到SQLite
            self.pool = None
        
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            # 读取SQL文件
            sql_file = os.path.join(os.path.dirname(__file__), 'database_design.sql')
            if os.path.exists(sql_file):
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # 执行SQL语句
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(sql_content)
                    conn.commit()
                    
                logger.info("✅ PostgreSQL数据库初始化成功")
            else:
                logger.warning("⚠️ 未找到数据库设计文件，跳过初始化")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            # 不抛出异常，允许程序继续运行
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)
    
    def get_or_create_user(self, wechat_user_id: str, nickname: Optional[str] = None) -> int:
        """
        获取或创建用户
        
        Args:
            wechat_user_id: 微信用户ID
            nickname: 用户昵称
            
        Returns:
            int: 用户ID
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # 尝试获取现有用户
                    cursor.execute(
                        "SELECT id FROM users WHERE wechat_user_id = %s",
                        (wechat_user_id,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        return result['id']
                    
                    # 创建新用户
                    cursor.execute(
                        """
                        INSERT INTO users (wechat_user_id, nickname)
                        VALUES (%s, %s)
                        ON CONFLICT (wechat_user_id) DO UPDATE
                        SET nickname = COALESCE(EXCLUDED.nickname, users.nickname)
                        RETURNING id
                        """,
                        (wechat_user_id, nickname)
                    )
                    result = cursor.fetchone()
                    conn.commit()
                    
                    # 初始化用户配额
                    user_id = result['id']
                    cursor.execute(
                        """
                        INSERT INTO user_quotas (user_id)
                        VALUES (%s)
                        ON CONFLICT (user_id) DO NOTHING
                        """,
                        (user_id,)
                    )
                    conn.commit()
                    
                    logger.info(f"✅ 创建新用户: {wechat_user_id}")
                    return user_id
                    
        except Exception as e:
            logger.error(f"获取或创建用户失败: {e}")
            raise
    
    def save_user_profile(
        self,
        wechat_user_id: str,
        profile_data: Dict[str, Any],
        raw_message: str,
        message_type: str,
        ai_response: Dict[str, Any]
    ) -> Optional[int]:
        """
        保存用户画像
        
        Args:
            wechat_user_id: 微信用户ID
            profile_data: 用户画像数据
            raw_message: 原始消息内容
            message_type: 消息类型
            ai_response: AI原始响应
            
        Returns:
            Optional[int]: 用户画像ID
        """
        try:
            # 获取用户ID
            user_id = self.get_or_create_user(wechat_user_id)
            
            # 检查用户配额
            if not self._check_user_quota(user_id):
                logger.warning(f"用户 {wechat_user_id} 已达到画像数量上限")
                return None
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # 插入或更新用户画像
                    cursor.execute(
                        """
                        INSERT INTO user_profiles (
                            user_id, profile_name, gender, age, phone, location,
                            marital_status, education, company, position, asset_level,
                            personality, ai_summary, source_type, raw_message_content,
                            raw_ai_response, confidence_score
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (user_id, profile_name) DO UPDATE SET
                            gender = EXCLUDED.gender,
                            age = EXCLUDED.age,
                            phone = EXCLUDED.phone,
                            location = EXCLUDED.location,
                            marital_status = EXCLUDED.marital_status,
                            education = EXCLUDED.education,
                            company = EXCLUDED.company,
                            position = EXCLUDED.position,
                            asset_level = EXCLUDED.asset_level,
                            personality = EXCLUDED.personality,
                            ai_summary = EXCLUDED.ai_summary,
                            source_type = EXCLUDED.source_type,
                            raw_message_content = EXCLUDED.raw_message_content,
                            raw_ai_response = EXCLUDED.raw_ai_response,
                            confidence_score = EXCLUDED.confidence_score,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                        """,
                        (
                            user_id,
                            profile_data.get('name', '未知'),
                            profile_data.get('gender'),
                            profile_data.get('age'),
                            profile_data.get('phone'),
                            profile_data.get('location'),
                            profile_data.get('marital_status'),
                            profile_data.get('education'),
                            profile_data.get('company'),
                            profile_data.get('position'),
                            profile_data.get('asset_level'),
                            profile_data.get('personality'),
                            ai_response.get('summary', ''),
                            message_type,
                            raw_message[:5000],  # 限制长度
                            Json(ai_response),
                            self._calculate_confidence_score(profile_data)
                        )
                    )
                    
                    profile_id = cursor.fetchone()[0]
                    
                    # 更新用户配额
                    cursor.execute(
                        """
                        UPDATE user_quotas 
                        SET used_profiles = (
                            SELECT COUNT(DISTINCT id) FROM user_profiles WHERE user_id = %s
                        )
                        WHERE user_id = %s
                        """,
                        (user_id, user_id)
                    )
                    
                    conn.commit()
                    logger.info(f"✅ 保存用户画像成功: {profile_data.get('name', '未知')}")
                    return profile_id
                    
        except Exception as e:
            logger.error(f"保存用户画像失败: {e}")
            return None
    
    def get_user_profiles(
        self,
        wechat_user_id: str,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        获取用户的画像列表
        
        Args:
            wechat_user_id: 微信用户ID
            limit: 每页数量
            offset: 偏移量
            search: 搜索关键词
            
        Returns:
            Tuple[List[Dict], int]: (画像列表, 总数)
        """
        try:
            user_id = self.get_or_create_user(wechat_user_id)
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # 构建查询条件
                    where_clause = "WHERE user_id = %s"
                    params = [user_id]
                    
                    if search:
                        where_clause += """ 
                        AND to_tsvector('chinese', 
                            COALESCE(profile_name, '') || ' ' || 
                            COALESCE(company, '') || ' ' || 
                            COALESCE(position, '') || ' ' || 
                            COALESCE(personality, '')
                        ) @@ to_tsquery('chinese', %s)
                        """
                        params.append(search)
                    
                    # 获取总数
                    cursor.execute(
                        f"SELECT COUNT(*) as total FROM user_profiles {where_clause}",
                        params
                    )
                    total = cursor.fetchone()['total']
                    
                    # 获取数据
                    cursor.execute(
                        f"""
                        SELECT 
                            id, profile_name, gender, age, phone, location,
                            marital_status, education, company, position, 
                            asset_level, personality, ai_summary, source_type,
                            confidence_score, created_at, updated_at
                        FROM user_profiles
                        {where_clause}
                        ORDER BY updated_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        params + [limit, offset]
                    )
                    
                    profiles = cursor.fetchall()
                    
                    # 转换日期时间格式
                    for profile in profiles:
                        profile['created_at'] = profile['created_at'].isoformat() if profile['created_at'] else None
                        profile['updated_at'] = profile['updated_at'].isoformat() if profile['updated_at'] else None
                        profile['confidence_score'] = float(profile['confidence_score']) if profile['confidence_score'] else 0
                    
                    return profiles, total
                    
        except Exception as e:
            logger.error(f"获取用户画像列表失败: {e}")
            return [], 0
    
    def get_user_profile_detail(self, wechat_user_id: str, profile_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户画像详情
        
        Args:
            wechat_user_id: 微信用户ID
            profile_id: 画像ID
            
        Returns:
            Optional[Dict]: 画像详情
        """
        try:
            user_id = self.get_or_create_user(wechat_user_id)
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT * FROM user_profiles
                        WHERE id = %s AND user_id = %s
                        """,
                        (profile_id, user_id)
                    )
                    
                    profile = cursor.fetchone()
                    if profile:
                        # 转换格式
                        profile['created_at'] = profile['created_at'].isoformat() if profile['created_at'] else None
                        profile['updated_at'] = profile['updated_at'].isoformat() if profile['updated_at'] else None
                        profile['confidence_score'] = float(profile['confidence_score']) if profile['confidence_score'] else 0
                    
                    return profile
                    
        except Exception as e:
            logger.error(f"获取用户画像详情失败: {e}")
            return None
    
    def delete_user_profile(self, wechat_user_id: str, profile_id: int) -> bool:
        """
        删除用户画像
        
        Args:
            wechat_user_id: 微信用户ID
            profile_id: 画像ID
            
        Returns:
            bool: 是否成功
        """
        try:
            user_id = self.get_or_create_user(wechat_user_id)
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        DELETE FROM user_profiles
                        WHERE id = %s AND user_id = %s
                        """,
                        (profile_id, user_id)
                    )
                    
                    deleted_count = cursor.rowcount
                    
                    # 更新用户配额
                    cursor.execute(
                        """
                        UPDATE user_quotas 
                        SET used_profiles = (
                            SELECT COUNT(DISTINCT id) FROM user_profiles WHERE user_id = %s
                        )
                        WHERE user_id = %s
                        """,
                        (user_id, user_id)
                    )
                    
                    conn.commit()
                    
                    if deleted_count > 0:
                        logger.info(f"✅ 删除用户画像成功: ID={profile_id}")
                        return True
                    else:
                        logger.warning(f"未找到用户画像: ID={profile_id}")
                        return False
                        
        except Exception as e:
            logger.error(f"删除用户画像失败: {e}")
            return False
    
    def get_user_stats(self, wechat_user_id: str) -> Dict[str, Any]:
        """
        获取用户统计信息
        
        Args:
            wechat_user_id: 微信用户ID
            
        Returns:
            Dict: 统计信息
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # 获取用户画像统计
                    cursor.execute(
                        """
                        SELECT * FROM user_profile_stats
                        WHERE wechat_user_id = %s
                        """,
                        (wechat_user_id,)
                    )
                    
                    stats = cursor.fetchone() or {}
                    
                    # 获取配额信息
                    cursor.execute(
                        """
                        SELECT uq.* FROM user_quotas uq
                        JOIN users u ON uq.user_id = u.id
                        WHERE u.wechat_user_id = %s
                        """,
                        (wechat_user_id,)
                    )
                    
                    quota = cursor.fetchone() or {}
                    
                    return {
                        'total_profiles': stats.get('total_profiles', 0),
                        'unique_names': stats.get('unique_names', 0),
                        'today_profiles': stats.get('today_profiles', 0),
                        'last_profile_at': stats.get('last_profile_at').isoformat() if stats.get('last_profile_at') else None,
                        'max_profiles': quota.get('max_profiles', 1000),
                        'used_profiles': quota.get('used_profiles', 0),
                        'max_daily_messages': quota.get('max_daily_messages', 100)
                    }
                    
        except Exception as e:
            logger.error(f"获取用户统计信息失败: {e}")
            return {}
    
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
        """
        记录消息处理日志
        
        Args:
            wechat_user_id: 微信用户ID
            message_id: 消息ID
            message_type: 消息类型
            success: 是否成功
            error_message: 错误信息
            processing_time_ms: 处理耗时
            profile_id: 关联的画像ID
        """
        try:
            user_id = self.get_or_create_user(wechat_user_id)
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO message_logs (
                            user_id, message_id, message_type, success,
                            error_message, processing_time_ms, profile_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id, message_id, message_type, success,
                            error_message, processing_time_ms, profile_id
                        )
                    )
                    conn.commit()
                    
        except Exception as e:
            logger.error(f"记录消息日志失败: {e}")
    
    def _check_user_quota(self, user_id: int) -> bool:
        """检查用户配额"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT * FROM user_quotas
                        WHERE user_id = %s
                        """,
                        (user_id,)
                    )
                    
                    quota = cursor.fetchone()
                    if not quota:
                        return True
                    
                    return quota['used_profiles'] < quota['max_profiles']
                    
        except Exception as e:
            logger.error(f"检查用户配额失败: {e}")
            return True
    
    def _calculate_confidence_score(self, profile_data: Dict[str, Any]) -> Decimal:
        """计算画像置信度分数"""
        total_fields = 11  # 总字段数
        filled_fields = 0
        
        # 统计非空字段
        for key in ['name', 'gender', 'age', 'phone', 'location', 
                   'marital_status', 'education', 'company', 'position', 
                   'asset_level', 'personality']:
            value = profile_data.get(key, '')
            if value and value != '未知':
                filled_fields += 1
        
        # 计算置信度（0-1）
        score = filled_fields / total_fields
        return Decimal(str(round(score, 2)))
    
    def update_user_profile(
        self, 
        wechat_user_id: str, 
        profile_id: int, 
        update_data: Dict[str, Any]
    ) -> bool:
        """更新用户画像"""
        try:
            # 构建更新SQL
            set_clauses = []
            values = []
            
            for key, value in update_data.items():
                set_clauses.append(f"{key} = %s")
                values.append(value)
            
            # 添加更新时间
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            
            # 添加WHERE条件参数
            values.append(wechat_user_id)
            values.append(profile_id)
            
            sql = f"""
                UPDATE user_profiles
                SET {', '.join(set_clauses)}
                WHERE wechat_user_id = %s AND id = %s
            """
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, values)
                    conn.commit()
                    
                    # 检查是否有更新
                    if cursor.rowcount > 0:
                        logger.info(f"成功更新用户画像 - 用户: {wechat_user_id}, ID: {profile_id}")
                        return True
                    else:
                        logger.warning(f"未找到要更新的画像 - 用户: {wechat_user_id}, ID: {profile_id}")
                        return False
                        
        except Exception as e:
            logger.error(f"更新用户画像失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接池"""
        if hasattr(self, 'pool'):
            self.pool.closeall()
            logger.info("PostgreSQL连接池已关闭")

# 全局数据库实例
pg_database = PostgreSQLDatabase()