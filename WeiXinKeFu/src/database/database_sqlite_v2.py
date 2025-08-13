# database_sqlite_v2.py
"""
SQLite数据库管理器 - 完整版
每个微信用户拥有独立的用户画像表
"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class SQLiteDatabase:
    """SQLite 数据库管理器 - 支持多用户独立数据存储"""
    
    def __init__(self):
        self.db_path = os.getenv('DATABASE_PATH', 'user_profiles_v2.db')
        self._init_database()
        self.pool = True  # 模拟连接池，用于兼容性检查
    
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
                
                # 创建用户表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        wechat_user_id TEXT UNIQUE NOT NULL,
                        nickname TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active INTEGER DEFAULT 1,
                        metadata TEXT DEFAULT '{}'
                    )
                ''')
                
                # 创建用户统计表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_stats (
                        user_id INTEGER PRIMARY KEY,
                        total_profiles INTEGER DEFAULT 0,
                        unique_names INTEGER DEFAULT 0,
                        last_profile_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                ''')
                
                # 创建消息日志表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS message_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        message_id TEXT,
                        message_type TEXT,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success INTEGER DEFAULT 1,
                        error_message TEXT,
                        processing_time_ms INTEGER,
                        profile_table_name TEXT,
                        profile_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                ''')
                
                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_wechat_id ON users(wechat_user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_message_logs_user_id ON message_logs(user_id)')
                
                conn.commit()
                logger.info("✅ SQLite主数据库初始化成功")
                
        except Exception as e:
            logger.error(f"SQLite数据库初始化失败: {e}")
    
    def _get_user_table_name(self, wechat_user_id: str) -> str:
        """获取用户专属的表名"""
        # 清理用户ID中的特殊字符
        safe_id = ''.join(c if c.isalnum() else '_' for c in wechat_user_id)
        return f"profiles_{safe_id}"
    
    def _create_user_profile_table(self, table_name: str):
        """为用户创建专属的画像表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_name TEXT NOT NULL,
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
                    tags TEXT,  -- 标签字段（JSON数组）
                    
                    -- AI分析元数据
                    ai_summary TEXT,
                    confidence_score REAL,
                    source_type TEXT,
                    
                    -- 原始数据
                    raw_message_content TEXT,
                    raw_ai_response TEXT,
                    
                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(profile_name)
                )
            ''')
            
            # 创建索引
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_name ON {table_name}(profile_name)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_created ON {table_name}(created_at DESC)')
            
            conn.commit()
            logger.info(f"✅ 创建用户画像表: {table_name}")
    
    def get_or_create_user(self, wechat_user_id: str, nickname: Optional[str] = None) -> int:
        """获取或创建用户"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 尝试获取现有用户
                cursor.execute(
                    "SELECT id FROM users WHERE wechat_user_id = ?",
                    (wechat_user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    return result['id']
                
                # 创建新用户
                cursor.execute(
                    "INSERT INTO users (wechat_user_id, nickname) VALUES (?, ?)",
                    (wechat_user_id, nickname)
                )
                user_id = cursor.lastrowid
                
                # 初始化用户统计
                cursor.execute(
                    "INSERT INTO user_stats (user_id) VALUES (?)",
                    (user_id,)
                )
                
                conn.commit()
                
                # 创建用户专属表
                table_name = self._get_user_table_name(wechat_user_id)
                self._create_user_profile_table(table_name)
                
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
        """保存用户画像到用户专属表"""
        try:
            # 获取用户ID
            user_id = self.get_or_create_user(wechat_user_id)
            table_name = self._get_user_table_name(wechat_user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 插入或更新用户画像
                cursor.execute(f'''
                    INSERT OR REPLACE INTO {table_name} (
                        profile_name, gender, age, phone, location,
                        marital_status, education, company, position, asset_level,
                        personality, tags, ai_summary, source_type, raw_message_content,
                        raw_ai_response, confidence_score, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    profile_data.get('profile_name', profile_data.get('name', '未知')),
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
                    json.dumps(profile_data.get('tags', []), ensure_ascii=False),  # 将tags转为JSON字符串
                    ai_response.get('summary', ''),
                    message_type,
                    raw_message[:5000],  # 限制长度
                    json.dumps(ai_response, ensure_ascii=False),
                    self._calculate_confidence_score(profile_data)
                ))
                
                profile_id = cursor.lastrowid
                
                # 更新用户统计
                cursor.execute(f'''
                    UPDATE user_stats 
                    SET total_profiles = (SELECT COUNT(*) FROM {table_name}),
                        unique_names = (SELECT COUNT(DISTINCT profile_name) FROM {table_name}),
                        last_profile_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                logger.info(f"✅ 保存用户画像成功: {profile_data.get('name', '未知')} -> {table_name}")
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
        """获取用户的画像列表"""
        try:
            user_id = self.get_or_create_user(wechat_user_id)
            table_name = self._get_user_table_name(wechat_user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建查询
                if search:
                    where_clause = '''
                        WHERE profile_name LIKE ? 
                        OR company LIKE ? 
                        OR position LIKE ?
                        OR personality LIKE ?
                    '''
                    search_param = f'%{search}%'
                    params = [search_param] * 4
                else:
                    where_clause = ''
                    params = []
                
                # 获取总数
                cursor.execute(f'SELECT COUNT(*) as total FROM {table_name} {where_clause}', params)
                total = cursor.fetchone()['total']
                
                # 获取数据
                cursor.execute(f'''
                    SELECT * FROM {table_name}
                    {where_clause}
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                ''', params + [limit, offset])
                
                profiles = []
                for row in cursor.fetchall():
                    profile = dict(row)
                    # 解析JSON字段
                    if profile.get('raw_ai_response'):
                        try:
                            profile['raw_ai_response'] = json.loads(profile['raw_ai_response'])
                        except:
                            pass
                    # 解析tags字段
                    if profile.get('tags'):
                        try:
                            profile['tags'] = json.loads(profile['tags'])
                        except:
                            profile['tags'] = []
                    else:
                        profile['tags'] = []
                    profiles.append(profile)
                
                return profiles, total
                
        except Exception as e:
            logger.error(f"获取用户画像列表失败: {e}")
            return [], 0
    
    def get_user_profile_detail(self, wechat_user_id: str, profile_id: int) -> Optional[Dict[str, Any]]:
        """获取用户画像详情"""
        try:
            table_name = self._get_user_table_name(wechat_user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'SELECT * FROM {table_name} WHERE id = ?', (profile_id,))
                row = cursor.fetchone()
                
                if row:
                    profile = dict(row)
                    # 解析JSON字段
                    if profile.get('raw_ai_response'):
                        try:
                            profile['raw_ai_response'] = json.loads(profile['raw_ai_response'])
                        except:
                            pass
                    # 解析tags字段
                    if profile.get('tags'):
                        try:
                            profile['tags'] = json.loads(profile['tags'])
                        except:
                            profile['tags'] = []
                    else:
                        profile['tags'] = []
                    return profile
                
                return None
                
        except Exception as e:
            logger.error(f"获取用户画像详情失败: {e}")
            return None
    
    def delete_user_profile(self, wechat_user_id: str, profile_id: int) -> bool:
        """删除用户画像"""
        try:
            user_id = self.get_or_create_user(wechat_user_id)
            table_name = self._get_user_table_name(wechat_user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'DELETE FROM {table_name} WHERE id = ?', (profile_id,))
                deleted_count = cursor.rowcount
                
                # 更新统计
                if deleted_count > 0:
                    cursor.execute(f'''
                        UPDATE user_stats 
                        SET total_profiles = (SELECT COUNT(*) FROM {table_name}),
                            unique_names = (SELECT COUNT(DISTINCT profile_name) FROM {table_name})
                        WHERE user_id = ?
                    ''', (user_id,))
                
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
        """获取用户统计信息"""
        try:
            user_id = self.get_or_create_user(wechat_user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取统计信息
                cursor.execute('''
                    SELECT u.*, s.*
                    FROM users u
                    LEFT JOIN user_stats s ON u.id = s.user_id
                    WHERE u.id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    stats = dict(row)
                    # 获取今日新增
                    table_name = self._get_user_table_name(wechat_user_id)
                    cursor.execute(f'''
                        SELECT COUNT(*) as today_profiles
                        FROM {table_name}
                        WHERE DATE(created_at) = DATE('now')
                    ''')
                    today = cursor.fetchone()
                    stats['today_profiles'] = today['today_profiles'] if today else 0
                    
                    return {
                        'total_profiles': stats.get('total_profiles', 0),
                        'unique_names': stats.get('unique_names', 0),
                        'today_profiles': stats['today_profiles'],
                        'last_profile_at': stats.get('last_profile_at'),
                        'max_profiles': 1000,  # 默认限制
                        'used_profiles': stats.get('total_profiles', 0),
                        'max_daily_messages': 100  # 默认限制
                    }
                
                return {}
                
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
        """记录消息处理日志"""
        try:
            user_id = self.get_or_create_user(wechat_user_id)
            table_name = self._get_user_table_name(wechat_user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO message_logs (
                        user_id, message_id, message_type, success,
                        error_message, processing_time_ms, profile_table_name, profile_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, message_id, message_type, int(success),
                    error_message, processing_time_ms, table_name, profile_id
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"记录消息日志失败: {e}")
    
    def _calculate_confidence_score(self, profile_data: Dict[str, Any]) -> float:
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
        return round(filled_fields / total_fields, 2)
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """获取所有用户列表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT u.*, s.total_profiles
                    FROM users u
                    LEFT JOIN user_stats s ON u.id = s.user_id
                    ORDER BY u.created_at DESC
                    LIMIT 50
                ''')
                
                users = []
                for row in cursor.fetchall():
                    users.append(dict(row))
                
                return users
                
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            return []
    
    def update_user_profile(
        self, 
        wechat_user_id: str, 
        profile_id: int, 
        update_data: Dict[str, Any]
    ) -> bool:
        """更新用户画像"""
        try:
            table_name = self._get_user_table_name(wechat_user_id)
            
            # 构建更新SQL
            set_clauses = []
            values = []
            
            for key, value in update_data.items():
                set_clauses.append(f"{key} = ?")
                # 特殊处理tags字段，转换为JSON字符串
                if key == 'tags' and isinstance(value, list):
                    values.append(json.dumps(value, ensure_ascii=False))
                else:
                    values.append(value)
            
            # 添加更新时间
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            
            # 添加profile_id作为WHERE条件
            values.append(profile_id)
            
            sql = f"""
                UPDATE {table_name}
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, values)
                conn.commit()
                
                # 检查是否有更新
                if cursor.rowcount > 0:
                    logger.info(f"成功更新用户画像 - 表: {table_name}, ID: {profile_id}")
                    return True
                else:
                    logger.warning(f"未找到要更新的画像 - 表: {table_name}, ID: {profile_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"更新用户画像失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接（SQLite不需要）"""
        pass

# 全局数据库实例
database_manager = SQLiteDatabase()