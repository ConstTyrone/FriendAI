#!/usr/bin/env python
"""
添加推送通知所需的数据库字段
"""
import sqlite3
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def add_push_fields(db_path="user_profiles.db"):
    """添加推送通知所需的字段"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("=" * 60)
        print("添加推送通知字段")
        print("=" * 60)
        
        # 1. 为user_push_preferences表添加open_kfid字段
        print("\n1. 检查user_push_preferences表...")
        cursor.execute("PRAGMA table_info(user_push_preferences)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'open_kfid' not in column_names:
            cursor.execute("""
                ALTER TABLE user_push_preferences 
                ADD COLUMN open_kfid TEXT
            """)
            print("   ✅ 添加open_kfid字段")
        else:
            print("   ℹ️ open_kfid字段已存在")
        
        if 'external_userid' not in column_names:
            cursor.execute("""
                ALTER TABLE user_push_preferences 
                ADD COLUMN external_userid TEXT
            """)
            print("   ✅ 添加external_userid字段")
        else:
            print("   ℹ️ external_userid字段已存在")
            
        if 'last_message_time' not in column_names:
            cursor.execute("""
                ALTER TABLE user_push_preferences 
                ADD COLUMN last_message_time TIMESTAMP
            """)
            print("   ✅ 添加last_message_time字段（用于48小时限制）")
        else:
            print("   ℹ️ last_message_time字段已存在")
            
        if 'push_count_48h' not in column_names:
            cursor.execute("""
                ALTER TABLE user_push_preferences 
                ADD COLUMN push_count_48h INTEGER DEFAULT 0
            """)
            print("   ✅ 添加push_count_48h字段（48小时内推送计数）")
        else:
            print("   ℹ️ push_count_48h字段已存在")
        
        # 2. 创建微信客服会话表（存储用户和客服账号的关系）
        print("\n2. 创建微信客服会话表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wechat_kf_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                external_userid TEXT NOT NULL,
                open_kfid TEXT NOT NULL,
                last_message_time TIMESTAMP,
                message_count_48h INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, open_kfid)
            )
        """)
        print("   ✅ 微信客服会话表创建/已存在")
        
        # 3. 为push_history表添加更多字段
        print("\n3. 检查push_history表...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='push_history'
        """)
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(push_history)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'open_kfid' not in column_names:
                cursor.execute("""
                    ALTER TABLE push_history 
                    ADD COLUMN open_kfid TEXT
                """)
                print("   ✅ 添加open_kfid字段到push_history")
            
            if 'external_userid' not in column_names:
                cursor.execute("""
                    ALTER TABLE push_history 
                    ADD COLUMN external_userid TEXT
                """)
                print("   ✅ 添加external_userid字段到push_history")
                
            if 'push_channel' not in column_names:
                cursor.execute("""
                    ALTER TABLE push_history 
                    ADD COLUMN push_channel TEXT DEFAULT 'wechat_kf'
                """)
                print("   ✅ 添加push_channel字段到push_history")
        
        # 4. 创建推送模板表
        print("\n4. 创建推送模板表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS push_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT NOT NULL UNIQUE,
                template_type TEXT NOT NULL,  -- text, miniprogram, link
                title_template TEXT,
                content_template TEXT NOT NULL,
                detail_template TEXT,
                miniprogram_config TEXT,  -- JSON格式的小程序配置
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ 推送模板表创建/已存在")
        
        # 5. 插入默认推送模板
        print("\n5. 插入默认推送模板...")
        cursor.execute("""
            INSERT OR IGNORE INTO push_templates (
                template_name, template_type, title_template, 
                content_template, detail_template
            ) VALUES 
            (
                'match_notification_text',
                'text',
                '🎯 找到匹配的联系人',
                '【{profile_name}】符合您的意图【{intent_name}】\n匹配度：{score}%\n{explanation}\n\n回复"查看{profile_id}"了解详情',
                '{matched_conditions}'
            ),
            (
                'match_notification_simple',
                'text',
                '发现新匹配',
                '{profile_name} 符合 [{intent_name}]，匹配度{score}%',
                NULL
            )
        """)
        print("   ✅ 默认推送模板已插入")
        
        conn.commit()
        print("\n✅ 所有字段添加成功！")
        
        # 显示更新后的表结构
        print("\n" + "=" * 60)
        print("更新后的表结构")
        print("=" * 60)
        
        cursor.execute("PRAGMA table_info(user_push_preferences)")
        columns = cursor.fetchall()
        print("\nuser_push_preferences表字段：")
        for col in columns:
            print(f"  - {col[1]}: {col[2]}")
            
        cursor.execute("PRAGMA table_info(wechat_kf_sessions)")
        columns = cursor.fetchall()
        print("\nwechat_kf_sessions表字段：")
        for col in columns:
            print(f"  - {col[1]}: {col[2]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 添加字段失败: {e}")
        return False

if __name__ == "__main__":
    add_push_fields()