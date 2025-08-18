#!/usr/bin/env python
"""
初始化推送相关的数据库表
"""

import sqlite3
import os

def init_push_tables():
    """初始化推送相关的数据库表"""
    
    db_path = "user_profiles.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件 {db_path} 不存在")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 创建用户推送偏好表
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
        print("✅ 创建用户推送偏好表成功")
        
        # 创建推送历史表（与create_intent_tables.py保持一致）
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
        print("✅ 创建推送历史表成功")
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_push_user_history ON push_history(user_id, sent_at DESC)")
        
        conn.commit()
        print("\n🎉 推送相关表初始化成功！")
        
        # 显示表信息
        for table in ['user_push_preferences', 'push_history']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} 条记录")
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_push_tables()