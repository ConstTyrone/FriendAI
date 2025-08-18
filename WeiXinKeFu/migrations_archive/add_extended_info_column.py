#!/usr/bin/env python3
"""
添加extended_info字段到intent_matches表
"""

import sqlite3

def add_extended_info_column():
    """添加extended_info字段"""
    
    print("="*60)
    print("🔧 添加extended_info字段")
    print("="*60)
    
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    try:
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(intent_matches)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'extended_info' not in column_names:
            print("⚠️ extended_info字段不存在，正在添加...")
            cursor.execute("""
                ALTER TABLE intent_matches 
                ADD COLUMN extended_info TEXT
            """)
            conn.commit()
            print("✅ extended_info字段已添加")
        else:
            print("✅ extended_info字段已存在")
        
        # 显示表结构
        print("\n当前intent_matches表结构：")
        cursor.execute("PRAGMA table_info(intent_matches)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
    except Exception as e:
        print(f"❌ 添加字段失败: {e}")
    finally:
        conn.close()
    
    print("\n✅ 完成！")

if __name__ == "__main__":
    add_extended_info_column()