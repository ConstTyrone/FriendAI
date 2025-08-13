#!/usr/bin/env python
"""
意图匹配系统 - 数据库表创建脚本
创建意图管理相关的所有数据表
"""

import sqlite3
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_intent_tables(db_path="user_profiles.db"):
    """创建意图匹配系统所需的所有表"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
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
        print("✅ 创建用户意图表成功")
        
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
            
            -- 推送状态
            is_pushed BOOLEAN DEFAULT 0,
            pushed_at TIMESTAMP,
            push_channel TEXT,
            
            -- 用户反馈
            user_feedback TEXT,
            feedback_at TIMESTAMP,
            feedback_note TEXT,
            
            -- 状态
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (intent_id) REFERENCES user_intents(id) ON DELETE CASCADE
        )
        """)
        print("✅ 创建匹配记录表成功")
        
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
        print("✅ 创建向量索引表成功")
        
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
        print("✅ 创建推送历史表成功")
        
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
        print("✅ 创建用户推送偏好表成功")
        
        conn.commit()
        print("\n🎉 所有意图匹配系统表创建成功！")
        
        # 显示创建的表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%intent%' OR name LIKE '%push%' OR name LIKE '%vector%'")
        tables = cursor.fetchall()
        print("\n已创建的相关表：")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"  - {table[0]}: {count} 条记录")
            
    except Exception as e:
        print(f"❌ 创建表时出错: {e}")
        conn.rollback()
    finally:
        conn.close()

def add_sample_intents(db_path="user_profiles.db"):
    """添加示例意图数据"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 添加示例意图
        sample_intents = [
            {
                'user_id': 'dev_user_001',
                'name': '寻找技术合伙人',
                'description': '寻找有AI技术背景，在北京或上海，有创业经验的技术合伙人',
                'type': 'recruitment',
                'conditions': '''{
                    "required": [
                        {"field": "position", "operator": "contains", "value": "CTO"},
                        {"field": "location", "operator": "in", "value": ["北京", "上海"]}
                    ],
                    "keywords": ["AI", "机器学习", "创业", "技术管理"]
                }''',
                'threshold': 0.75,
                'priority': 9
            },
            {
                'user_id': 'dev_user_001',
                'name': '寻找投资人',
                'description': '寻找关注企业服务领域的天使投资人或VC',
                'type': 'business',
                'conditions': '''{
                    "required": [],
                    "keywords": ["投资", "天使", "VC", "企业服务", "SaaS"]
                }''',
                'threshold': 0.7,
                'priority': 8
            }
        ]
        
        for intent in sample_intents:
            cursor.execute("""
                INSERT INTO user_intents (
                    user_id, name, description, type, conditions, threshold, priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                intent['user_id'],
                intent['name'],
                intent['description'],
                intent['type'],
                intent['conditions'],
                intent['threshold'],
                intent['priority']
            ))
        
        conn.commit()
        print(f"\n✅ 添加了 {len(sample_intents)} 个示例意图")
        
    except Exception as e:
        print(f"❌ 添加示例数据时出错: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='创建意图匹配系统数据表')
    parser.add_argument('--db', default='user_profiles.db', help='数据库文件路径')
    parser.add_argument('--sample', action='store_true', help='添加示例数据')
    
    args = parser.parse_args()
    
    # 创建表
    create_intent_tables(args.db)
    
    # 添加示例数据
    if args.sample:
        add_sample_intents(args.db)