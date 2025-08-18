#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化意图匹配系统的所有表
"""

import sqlite3
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_intent_tables(user_id):
    """为用户创建意图相关的表"""
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_profiles.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. 创建用户意图表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_intents_{user_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                type TEXT DEFAULT 'general',
                conditions TEXT,
                threshold REAL DEFAULT 0.7,
                priority INTEGER DEFAULT 5,
                status TEXT DEFAULT 'active',
                embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)
        print(f"  ✅ 创建表: user_intents_{user_id}")
        
        # 2. 创建意图匹配记录表（包含通知字段）
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS intent_matches_{user_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent_id INTEGER NOT NULL,
                profile_id INTEGER NOT NULL,
                match_score REAL NOT NULL,
                vector_score REAL,
                keyword_score REAL,
                condition_score REAL,
                matched_conditions TEXT,
                explanation TEXT,
                user_feedback TEXT,
                is_read INTEGER DEFAULT 0,
                is_pushed INTEGER DEFAULT 0,
                pushed_at TIMESTAMP,
                read_at TIMESTAMP,
                push_message_id TEXT,
                push_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (intent_id) REFERENCES user_intents_{user_id}(id),
                FOREIGN KEY (profile_id) REFERENCES profiles_{user_id}(id)
            )
        """)
        print(f"  ✅ 创建表: intent_matches_{user_id}")
        
        # 创建索引
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_intent_matches_{user_id}_read 
            ON intent_matches_{user_id}(is_read, created_at DESC)
        """)
        
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_intent_matches_{user_id}_intent 
            ON intent_matches_{user_id}(intent_id, match_score DESC)
        """)
        
        # 3. 创建推送历史表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS push_history_{user_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                message_type TEXT NOT NULL,
                message_content TEXT NOT NULL,
                message_id TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES intent_matches_{user_id}(id)
            )
        """)
        print(f"  ✅ 创建表: push_history_{user_id}")
        
        # 4. 创建用户推送偏好表（如果不存在）
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_push_preferences_{user_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL UNIQUE,
                enable_push INTEGER DEFAULT 1,
                push_channel TEXT DEFAULT 'wechat_kf',
                quiet_hours TEXT DEFAULT '22:00-08:00',
                daily_limit INTEGER DEFAULT 10,
                min_score REAL DEFAULT 0.7,
                push_types TEXT DEFAULT 'all',
                last_push_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print(f"  ✅ 创建表: user_push_preferences_{user_id}")
        
        # 插入默认推送偏好
        cursor.execute(f"""
            INSERT OR IGNORE INTO user_push_preferences_{user_id} (user_id)
            VALUES (?)
        """, (user_id,))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"  ❌ 创建表失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def initialize_all_users():
    """为所有用户初始化意图系统"""
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_profiles.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        print("  创建新的数据库...")
        conn = sqlite3.connect(db_path)
        conn.close()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 获取所有用户的profiles表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
        """)
        profile_tables = cursor.fetchall()
        
        if not profile_tables:
            print("⚠️ 没有找到用户profiles表，创建测试用户...")
            # 创建测试用户
            test_users = [
                'wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q',  # 主测试用户
                'test_user_001',
                'dev_user_001'
            ]
            
            for user_id in test_users:
                print(f"\n📊 初始化用户: {user_id}")
                
                # 创建profiles表
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS profiles_{user_id} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        profile_name TEXT NOT NULL,
                        wechat_id TEXT,
                        phone TEXT,
                        tags TEXT,
                        basic_info TEXT,
                        interests TEXT,
                        personality TEXT,
                        values TEXT,
                        lifestyle TEXT,
                        social_style TEXT,
                        communication TEXT,
                        goals TEXT,
                        challenges TEXT,
                        preferences TEXT,
                        recent_activities TEXT,
                        topics_discussed TEXT,
                        interaction_style TEXT,
                        raw_messages TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_analysis_at TIMESTAMP,
                        message_count INTEGER DEFAULT 0,
                        analysis_version TEXT DEFAULT '1.0',
                        confidence_score REAL DEFAULT 0.0,
                        profile_completeness REAL DEFAULT 0.0,
                        embedding BLOB
                    )
                """)
                print(f"  ✅ 创建表: profiles_{user_id}")
                
                # 创建意图系统表
                create_intent_tables(user_id)
        else:
            # 为现有用户创建意图表
            for (table_name,) in profile_tables:
                user_id = table_name.replace('profiles_', '')
                print(f"\n📊 处理用户: {user_id}")
                create_intent_tables(user_id)
        
        # 创建全局表
        print("\n📊 创建全局表...")
        
        # 微信客服会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wechat_kf_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                external_userid TEXT NOT NULL,
                open_kfid TEXT NOT NULL,
                last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, external_userid)
            )
        """)
        print("  ✅ 创建表: wechat_kf_sessions")
        
        # 推送模板表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS push_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT NOT NULL UNIQUE,
                template_type TEXT DEFAULT 'text',
                content_template TEXT NOT NULL,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  ✅ 创建表: push_templates")
        
        # 插入默认模板
        cursor.execute("""
            INSERT OR IGNORE INTO push_templates (template_name, content_template, description)
            VALUES 
            ('default_match', '【FriendAI】发现新匹配：{profile_name}符合您的意图"{intent_name}"，匹配度{score}%', '默认匹配通知模板'),
            ('high_score_match', '【FriendAI】高度匹配！{profile_name}与您的意图"{intent_name}"匹配度高达{score}%：{explanation}', '高分匹配模板'),
            ('batch_match', '【FriendAI】您有{count}个新匹配：\n{matches}', '批量匹配模板')
        """)
        
        conn.commit()
        print("\n✅ 所有表初始化完成！")
        
        # 显示统计信息
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = cursor.fetchone()[0]
        print(f"\n📊 数据库统计:")
        print(f"  - 总表数: {table_count}")
        print(f"  - 用户数: {len(profile_tables) if profile_tables else len(test_users)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def verify_tables():
    """验证表结构"""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_profiles.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("\n📋 验证表结构...")
        
        # 测试用户
        test_user = 'wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q'
        
        # 检查意图匹配表
        cursor.execute(f"PRAGMA table_info(intent_matches_{test_user})")
        columns = cursor.fetchall()
        
        if columns:
            required_fields = ['is_read', 'is_pushed', 'pushed_at', 'read_at']
            column_names = [col[1] for col in columns]
            
            print(f"\n意图匹配表字段检查:")
            for field in required_fields:
                if field in column_names:
                    print(f"  ✅ {field} - 存在")
                else:
                    print(f"  ❌ {field} - 缺失")
        else:
            print(f"  ⚠️ 表 intent_matches_{test_user} 不存在")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔧 初始化意图匹配系统...")
    print("=" * 50)
    
    if initialize_all_users():
        print("\n" + "=" * 50)
        verify_tables()
        print("\n✨ 初始化完成！意图匹配系统已准备就绪")
    else:
        print("\n❌ 初始化失败，请检查错误信息")