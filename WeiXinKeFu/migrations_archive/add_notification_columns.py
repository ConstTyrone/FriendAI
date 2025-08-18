#!/usr/bin/env python3
"""
为intent_matches表添加通知相关字段
"""

import sqlite3
import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'WeiXinKeFu'))

def add_notification_columns():
    """添加通知相关字段"""
    
    db_path = "WeiXinKeFu/user_profiles.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查字段是否存在
        cursor.execute("PRAGMA table_info(intent_matches)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 添加is_read字段
        if 'is_read' not in columns:
            cursor.execute("""
                ALTER TABLE intent_matches 
                ADD COLUMN is_read INTEGER DEFAULT 0
            """)
            print("✅ 添加is_read字段成功")
        else:
            print("ℹ️ is_read字段已存在")
        
        # 添加read_at字段
        if 'read_at' not in columns:
            cursor.execute("""
                ALTER TABLE intent_matches 
                ADD COLUMN read_at TIMESTAMP
            """)
            print("✅ 添加read_at字段成功")
        else:
            print("ℹ️ read_at字段已存在")
        
        # 添加pushed_at字段（记录推送时间）
        if 'pushed_at' not in columns:
            cursor.execute("""
                ALTER TABLE intent_matches 
                ADD COLUMN pushed_at TIMESTAMP
            """)
            print("✅ 添加pushed_at字段成功")
        else:
            print("ℹ️ pushed_at字段已存在")
        
        conn.commit()
        print("\n✅ 数据库更新完成")
        
        # 查看更新后的表结构
        cursor.execute("PRAGMA table_info(intent_matches)")
        columns = cursor.fetchall()
        print("\n当前intent_matches表结构：")
        for col in columns:
            print(f"  {col[1]} - {col[2]}")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_notification_columns()