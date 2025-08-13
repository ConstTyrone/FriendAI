# binding_db.py
"""
用户绑定关系数据库操作
支持PostgreSQL和SQLite
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class BindingDatabase:
    """绑定关系数据库操作类"""
    
    def __init__(self, db_instance):
        """
        初始化
        :param db_instance: 数据库实例（PostgreSQL或SQLite）
        """
        self.db = db_instance
        # 检查是否为PostgreSQL（pool是对象）还是SQLite（pool是True）
        self.is_postgres = hasattr(db_instance, 'pool') and db_instance.pool != True
        
    def create_binding_table(self):
        """创建绑定关系表"""
        if self.is_postgres:
            # PostgreSQL
            query = """
            CREATE TABLE IF NOT EXISTS user_binding (
                id SERIAL PRIMARY KEY,
                openid VARCHAR(64) UNIQUE NOT NULL,
                external_userid VARCHAR(64) UNIQUE,
                unionid VARCHAR(64),
                bind_status SMALLINT DEFAULT 0,
                bind_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_openid ON user_binding(openid);
            CREATE INDEX IF NOT EXISTS idx_external_userid ON user_binding(external_userid);
            """
        else:
            # SQLite
            query = """
            CREATE TABLE IF NOT EXISTS user_binding (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                openid TEXT UNIQUE NOT NULL,
                external_userid TEXT UNIQUE,
                unionid TEXT,
                bind_status INTEGER DEFAULT 0,
                bind_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_openid ON user_binding(openid);
            CREATE INDEX IF NOT EXISTS idx_external_userid ON user_binding(external_userid);
            """
        
        try:
            if self.is_postgres:
                with self.db.pool.connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query)
                        conn.commit()
            else:
                # SQLite - 使用 get_connection 方法
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    # SQLite 不支持在一个 execute 中执行多条语句
                    for statement in query.split(';'):
                        if statement.strip():
                            cursor.execute(statement)
                    conn.commit()
            
            logger.info("绑定关系表创建成功")
            return True
        except Exception as e:
            logger.error(f"创建绑定关系表失败: {e}")
            return False
    
    def get_user_binding(self, openid: str) -> Optional[Dict[str, Any]]:
        """
        获取用户绑定信息
        :param openid: 微信openid
        :return: 绑定信息字典或None
        """
        try:
            if self.is_postgres:
                query = """
                SELECT id, openid, external_userid, unionid, bind_status, 
                       bind_time, last_login, created_at, updated_at
                FROM user_binding
                WHERE openid = %s
                """
                with self.db.pool.connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query, (openid,))
                        row = cursor.fetchone()
                        if row:
                            return {
                                'id': row[0],
                                'openid': row[1],
                                'external_userid': row[2],
                                'unionid': row[3],
                                'bind_status': row[4],
                                'bind_time': row[5].isoformat() if row[5] else None,
                                'last_login': row[6].isoformat() if row[6] else None,
                                'created_at': row[7].isoformat() if row[7] else None,
                                'updated_at': row[8].isoformat() if row[8] else None
                            }
            else:
                # SQLite
                query = """
                SELECT id, openid, external_userid, unionid, bind_status, 
                       bind_time, last_login, created_at, updated_at
                FROM user_binding
                WHERE openid = ?
                """
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (openid,))
                    row = cursor.fetchone()
                    if row:
                        return {
                            'id': row[0],
                            'openid': row[1],
                            'external_userid': row[2],
                            'unionid': row[3],
                            'bind_status': row[4],
                            'bind_time': row[5],
                            'last_login': row[6],
                            'created_at': row[7],
                            'updated_at': row[8]
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"获取用户绑定信息失败: {e}")
            return None
    
    def save_user_binding(self, openid: str, external_userid: str) -> bool:
        """
        保存用户绑定关系
        :param openid: 微信openid
        :param external_userid: 企微客服用户ID
        :return: 是否成功
        """
        try:
            now = datetime.now()
            
            if self.is_postgres:
                # PostgreSQL - UPSERT操作
                query = """
                INSERT INTO user_binding (openid, external_userid, bind_status, bind_time, updated_at)
                VALUES (%s, %s, 1, %s, %s)
                ON CONFLICT (openid) 
                DO UPDATE SET 
                    external_userid = EXCLUDED.external_userid,
                    bind_status = 1,
                    bind_time = EXCLUDED.bind_time,
                    updated_at = EXCLUDED.updated_at
                """
                with self.db.pool.connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query, (openid, external_userid, now, now))
                        conn.commit()
            else:
                # SQLite - REPLACE操作
                query = """
                INSERT OR REPLACE INTO user_binding 
                (openid, external_userid, bind_status, bind_time, updated_at)
                VALUES (?, ?, 1, ?, ?)
                """
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (openid, external_userid, now, now))
                    conn.commit()
            
            logger.info(f"保存绑定关系成功: openid={openid}, external_userid={external_userid}")
            return True
            
        except Exception as e:
            logger.error(f"保存绑定关系失败: {e}")
            return False
    
    def remove_user_binding(self, openid: str) -> bool:
        """
        删除用户绑定关系
        :param openid: 微信openid
        :return: 是否成功
        """
        try:
            if self.is_postgres:
                query = """
                UPDATE user_binding 
                SET bind_status = 0, external_userid = NULL, updated_at = %s
                WHERE openid = %s
                """
                with self.db.pool.connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query, (datetime.now(), openid))
                        conn.commit()
            else:
                # SQLite
                query = """
                UPDATE user_binding 
                SET bind_status = 0, external_userid = NULL, updated_at = ?
                WHERE openid = ?
                """
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (datetime.now(), openid))
                    conn.commit()
            
            logger.info(f"删除绑定关系成功: openid={openid}")
            return True
            
        except Exception as e:
            logger.error(f"删除绑定关系失败: {e}")
            return False
    
    def get_openid_by_external_userid(self, external_userid: str) -> Optional[str]:
        """
        通过企微用户ID获取openid
        :param external_userid: 企微客服用户ID
        :return: openid或None
        """
        try:
            if self.is_postgres:
                query = "SELECT openid FROM user_binding WHERE external_userid = %s AND bind_status = 1"
                with self.db.pool.connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query, (external_userid,))
                        row = cursor.fetchone()
                        return row[0] if row else None
            else:
                # SQLite
                query = "SELECT openid FROM user_binding WHERE external_userid = ? AND bind_status = 1"
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (external_userid,))
                    row = cursor.fetchone()
                    return row[0] if row else None
                
        except Exception as e:
            logger.error(f"通过external_userid获取openid失败: {e}")
            return None
    
    def update_last_login(self, openid: str) -> bool:
        """
        更新最后登录时间
        :param openid: 微信openid
        :return: 是否成功
        """
        try:
            now = datetime.now()
            
            if self.is_postgres:
                query = "UPDATE user_binding SET last_login = %s WHERE openid = %s"
                with self.db.pool.connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query, (now, openid))
                        conn.commit()
            else:
                # SQLite
                query = "UPDATE user_binding SET last_login = ? WHERE openid = ?"
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (now, openid))
                    conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"更新最后登录时间失败: {e}")
            return False

# 创建全局实例
def get_binding_db():
    """获取绑定数据库实例"""
    try:
        from .database_pg import pg_database
        if pg_database.pool:
            return BindingDatabase(pg_database)
    except:
        pass
    
    try:
        from .database_sqlite_v2 import database_manager
        return BindingDatabase(database_manager)
    except:
        pass
    
    logger.error("无法创建绑定数据库实例")
    return None

# 导出
binding_db = get_binding_db()