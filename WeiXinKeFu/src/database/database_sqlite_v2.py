# database_sqlite_v2.py
"""
SQLite数据库管理器 - 完整版
每个微信用户拥有独立的用户画像表
"""
import os
import json
import sqlite3
import logging
import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class SQLiteDatabase:
    """SQLite 数据库管理器 - 支持多用户独立数据存储"""
    
    def __init__(self):
        self.db_path = os.getenv('DATABASE_PATH', 'user_profiles.db')  # 统一使用 user_profiles.db
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
                
                # 创建意图匹配系统相关表
                self._create_intent_tables()
                
                # 升级数据库结构（添加缺失的列）
                self._upgrade_database_schema()
                
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
                    
                    -- 信息来源字段
                    source VARCHAR(20) DEFAULT 'manual',  -- 'wechat_message' | 'manual' | 'import'
                    source_messages TEXT,                 -- JSON数组存储原始消息详情
                    source_timestamp TIMESTAMP,           -- 最后一次从消息更新的时间
                    
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
    
    def _create_intent_tables(self):
        """创建意图匹配系统所需的所有表"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. 用户意图表
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_intents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    type TEXT DEFAULT 'general',
                    
                    -- 条件存储（JSON格式）
                    conditions TEXT DEFAULT '{}',
                    
                    -- 向量数据
                    embedding BLOB,
                    embedding_model TEXT DEFAULT 'qwen-v2',
                    
                    -- 配置项
                    threshold REAL DEFAULT 0.7,
                    priority INTEGER DEFAULT 5,
                    max_push_per_day INTEGER DEFAULT 5,
                    
                    -- 状态控制
                    status TEXT DEFAULT 'active',
                    expire_at TIMESTAMP,
                    
                    -- 统计数据
                    match_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    last_match_at TIMESTAMP,
                    
                    -- 时间戳
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_intents_status ON user_intents(user_id, status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_intents_expire ON user_intents(expire_at)")
                
                # 2. 匹配记录表
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS intent_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    intent_id INTEGER NOT NULL,
                    profile_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    
                    -- 匹配详情
                    match_score REAL NOT NULL,
                    score_details TEXT,
                    matched_conditions TEXT,
                    explanation TEXT,
                    match_type TEXT DEFAULT 'rule',
                    extended_info TEXT,
                    
                    -- 推送状态
                    is_pushed BOOLEAN DEFAULT 0,
                    pushed_at TIMESTAMP,
                    push_channel TEXT,
                    
                    -- 阅读状态
                    is_read BOOLEAN DEFAULT 0,
                    read_at TIMESTAMP,
                    
                    -- 用户反馈
                    user_feedback TEXT,
                    feedback_at TIMESTAMP,
                    feedback_note TEXT,
                    
                    -- 状态
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (intent_id) REFERENCES user_intents(id) ON DELETE CASCADE
                )
                """)
                
                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_matches ON intent_matches(user_id, status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_intent_matches ON intent_matches(intent_id, match_score DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_profile_matches ON intent_matches(profile_id)")
                cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_match ON intent_matches(intent_id, profile_id)")
                
                # 3. 向量索引表
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_index (
                    id TEXT PRIMARY KEY,
                    vector_type TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_vector_type ON vector_index(vector_type, user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_vector_entity ON vector_index(entity_id)")
                
                # 4. 推送历史表
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS push_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    match_ids TEXT NOT NULL,
                    push_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'sent',
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_at TIMESTAMP
                )
                """)
                
                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_push_user_history ON push_history(user_id, sent_at DESC)")
                
                # 5. 用户推送偏好表
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_push_preferences (
                    user_id TEXT PRIMARY KEY,
                    enable_push BOOLEAN DEFAULT 1,
                    daily_limit INTEGER DEFAULT 10,
                    quiet_hours TEXT,
                    batch_mode TEXT DEFAULT 'smart',
                    min_score REAL DEFAULT 0.7,
                    preferred_time TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                conn.commit()
                logger.info("✅ 创建意图匹配系统表成功")
                
        except Exception as e:
            logger.error(f"创建意图表失败: {e}")
            raise
    
    def ensure_intent_tables_exist(self):
        """确保意图表存在，如果不存在则创建"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 检查 user_intents 表是否存在
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='user_intents'
                """)
                if not cursor.fetchone():
                    logger.info("意图表不存在，正在创建...")
                    self._create_intent_tables()
                    logger.info("✅ 意图表创建完成")
        except Exception as e:
            logger.error(f"检查/创建意图表失败: {e}")
            # 如果检查失败，尝试重新创建
            try:
                self._create_intent_tables()
                logger.info("✅ 强制重新创建意图表成功")
            except Exception as create_error:
                logger.error(f"强制创建意图表也失败: {create_error}")
                raise
    
    def _upgrade_database_schema(self):
        """升级数据库结构，添加缺失的列"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查 intent_matches 表的所有缺失列
                cursor.execute("PRAGMA table_info(intent_matches)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # 定义所有需要的列及其定义
                # 注意：SQLite的ALTER TABLE ADD COLUMN不支持复杂的默认值
                required_columns = {
                    'is_read': 'BOOLEAN DEFAULT 0',
                    'read_at': 'TIMESTAMP',
                    'match_type': 'TEXT DEFAULT \'rule\'',
                    'extended_info': 'TEXT',
                    'updated_at': 'TIMESTAMP'  # SQLite ALTER TABLE不支持CURRENT_TIMESTAMP默认值
                }
                
                # 添加缺失的列
                added_columns = []
                for column_name, column_def in required_columns.items():
                    if column_name not in columns:
                        logger.info(f"添加缺失的{column_name}列到intent_matches表...")
                        cursor.execute(f"ALTER TABLE intent_matches ADD COLUMN {column_name} {column_def}")
                        added_columns.append(column_name)
                        logger.info(f"✅ 添加{column_name}列成功")
                
                if added_columns:
                    conn.commit()
                    logger.info(f"✅ 数据库结构升级完成，新增列: {', '.join(added_columns)}")
                else:
                    logger.info("✅ 数据库结构已是最新，无需升级")
                
                # 升级用户画像表，添加信息来源字段
                self._upgrade_profile_tables()
                
        except Exception as e:
            logger.error(f"数据库结构升级失败: {e}")
            # 升级失败不影响系统正常运行，仅记录错误
    
    def _upgrade_profile_tables(self):
        """升级所有用户画像表，添加信息来源字段"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取所有用户
                cursor.execute("SELECT wechat_user_id FROM users")
                users = cursor.fetchall()
                
                for user_row in users:
                    wechat_user_id = user_row['wechat_user_id']
                    table_name = self._get_user_table_name(wechat_user_id)
                    
                    try:
                        # 检查表是否存在
                        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                        if not cursor.fetchone():
                            continue
                        
                        # 检查表的列结构
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = [row[1] for row in cursor.fetchall()]
                        
                        # 添加缺失的信息来源字段
                        source_columns = {
                            'source': 'VARCHAR(20) DEFAULT \'manual\'',
                            'source_messages': 'TEXT',
                            'source_timestamp': 'TIMESTAMP'
                        }
                        
                        added_to_table = []
                        for column_name, column_def in source_columns.items():
                            if column_name not in columns:
                                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
                                added_to_table.append(column_name)
                        
                        if added_to_table:
                            logger.info(f"✅ 为表 {table_name} 添加字段: {', '.join(added_to_table)}")
                        
                    except Exception as table_error:
                        logger.error(f"升级表 {table_name} 失败: {table_error}")
                        continue
                
                conn.commit()
                logger.info("✅ 用户画像表升级完成")
                
        except Exception as e:
            logger.error(f"升级用户画像表失败: {e}")
    
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
        ai_response: Dict[str, Any],
        original_message: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """保存用户画像到用户专属表"""
        try:
            # 获取用户ID
            user_id = self.get_or_create_user(wechat_user_id)
            table_name = self._get_user_table_name(wechat_user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                profile_name = profile_data.get('profile_name', profile_data.get('name', '未知'))
                
                # 检查是否已存在此联系人
                cursor.execute(f'SELECT id, source_messages FROM {table_name} WHERE profile_name = ?', (profile_name,))
                existing_profile = cursor.fetchone()
                
                # 处理信息来源数据
                source = 'wechat_message' if original_message else 'manual'
                source_messages = []
                
                if original_message:
                    # 创建新的原始消息记录
                    new_message = {
                        'id': f"msg_{int(time.time() * 1000)}",
                        'timestamp': datetime.now().isoformat(),
                        'message_type': message_type,
                        'wechat_msg_id': original_message.get('MsgId', ''),
                        'raw_content': str(original_message)[:1000],  # 限制长度
                        'processed_content': raw_message[:1000],
                        'media_url': original_message.get('PicUrl') or original_message.get('MediaId'),
                        'action': 'updated' if existing_profile else 'created'
                    }
                    
                    if existing_profile:
                        # 如果联系人已存在，追加到现有消息列表
                        try:
                            existing_messages = json.loads(existing_profile['source_messages'] or '[]')
                            source_messages = existing_messages + [new_message]
                        except:
                            source_messages = [new_message]
                    else:
                        # 新建联系人
                        source_messages = [new_message]
                
                # 插入或更新用户画像
                if existing_profile:
                    # 更新现有联系人
                    cursor.execute(f'''
                        UPDATE {table_name} SET
                            gender = ?, age = ?, phone = ?, location = ?,
                            marital_status = ?, education = ?, company = ?, position = ?, asset_level = ?,
                            personality = ?, tags = ?, ai_summary = ?, source_type = ?, raw_message_content = ?,
                            raw_ai_response = ?, confidence_score = ?, source_messages = ?, source_timestamp = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE profile_name = ?
                    ''', (
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
                        json.dumps(profile_data.get('tags', []), ensure_ascii=False),
                        ai_response.get('summary', ''),
                        message_type,
                        raw_message[:5000],
                        json.dumps(ai_response, ensure_ascii=False),
                        self._calculate_confidence_score(profile_data),
                        json.dumps(source_messages, ensure_ascii=False),
                        profile_name
                    ))
                    profile_id = existing_profile['id']
                else:
                    # 创建新联系人
                    cursor.execute(f'''
                        INSERT INTO {table_name} (
                            profile_name, gender, age, phone, location,
                            marital_status, education, company, position, asset_level,
                            personality, tags, ai_summary, source_type, raw_message_content,
                            raw_ai_response, confidence_score, source, source_messages, source_timestamp,
                            updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ''', (
                        profile_name,
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
                        json.dumps(profile_data.get('tags', []), ensure_ascii=False),
                        ai_response.get('summary', ''),
                        message_type,
                        raw_message[:5000],
                        json.dumps(ai_response, ensure_ascii=False),
                        self._calculate_confidence_score(profile_data),
                        source,
                        json.dumps(source_messages, ensure_ascii=False),
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
        search: Optional[str] = None,
        age_min: Optional[int] = None,
        age_max: Optional[int] = None,
        gender: Optional[str] = None,
        location: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取用户的画像列表"""
        try:
            user_id = self.get_or_create_user(wechat_user_id)
            table_name = self._get_user_table_name(wechat_user_id)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 构建动态查询条件
                where_conditions = []
                params = []
                
                # 1. 文本搜索条件
                if search:
                    text_conditions = [
                        'profile_name LIKE ?',
                        'company LIKE ?', 
                        'position LIKE ?',
                        'personality LIKE ?',
                        'location LIKE ?',
                        'education LIKE ?'
                    ]
                    search_param = f'%{search}%'
                    where_conditions.append(f'({" OR ".join(text_conditions)})')
                    params.extend([search_param] * 6)
                
                # 2. 年龄范围条件
                if age_min is not None:
                    where_conditions.append('CAST(age AS INTEGER) >= ?')
                    params.append(age_min)
                
                if age_max is not None:
                    where_conditions.append('CAST(age AS INTEGER) <= ?')
                    params.append(age_max)
                
                # 3. 性别精确匹配
                if gender:
                    where_conditions.append('gender = ?')
                    params.append(gender)
                
                # 4. 地域匹配
                if location:
                    where_conditions.append('location LIKE ?')
                    params.append(f'%{location}%')
                
                # 构建最终的WHERE子句
                if where_conditions:
                    where_clause = 'WHERE ' + ' AND '.join(where_conditions)
                else:
                    where_clause = ''
                
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
                    
                    # 解析source_messages字段
                    if profile.get('source_messages'):
                        try:
                            profile['source_messages'] = json.loads(profile['source_messages'])
                        except:
                            profile['source_messages'] = []
                    else:
                        profile['source_messages'] = []
                    
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
                    profile = {}
                    # 逐个处理字段，避免二进制数据问题
                    for key in row.keys():
                        value = row[key]
                        # 如果是二进制数据，跳过或转换
                        if isinstance(value, bytes):
                            try:
                                # 尝试解码为字符串
                                profile[key] = value.decode('utf-8')
                            except UnicodeDecodeError:
                                # 如果无法解码，可能是二进制数据（如embedding）
                                # 跳过这个字段或转换为base64
                                profile[key] = None  # 或者 base64.b64encode(value).decode('ascii')
                        else:
                            profile[key] = value
                    
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
                    # 解析source_messages字段
                    if profile.get('source_messages'):
                        try:
                            profile['source_messages'] = json.loads(profile['source_messages'])
                        except:
                            profile['source_messages'] = []
                    else:
                        profile['source_messages'] = []
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