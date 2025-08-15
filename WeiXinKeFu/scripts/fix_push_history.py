#!/usr/bin/env python3
"""
修复push_history表结构
"""

import sqlite3
import os
from pathlib import Path

# 获取数据库路径
db_path = Path(__file__).parent.parent / "user_profiles.db"

def fix_push_history_table():
    """修复push_history表，添加缺失的列"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 获取所有用户表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'push_history_%'
        """)
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            print(f"检查表: {table_name}")
            
            # 检查表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            print(f"  当前列: {column_names}")
            
            # 添加缺失的列
            if 'intent_id' not in column_names:
                print(f"  添加 intent_id 列...")
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN intent_id INTEGER
                """)
                print(f"  ✅ intent_id 列已添加")
            
            if 'profile_id' not in column_names:
                print(f"  添加 profile_id 列...")
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN profile_id INTEGER
                """)
                print(f"  ✅ profile_id 列已添加")
            
            if 'match_id' not in column_names:
                print(f"  添加 match_id 列...")
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN match_id INTEGER
                """)
                print(f"  ✅ match_id 列已添加")
        
        conn.commit()
        print("\n✅ 所有push_history表已修复")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        conn.rollback()
    finally:
        conn.close()

def check_push_history():
    """检查push_history表内容"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 获取所有push_history表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'push_history_%'
        """)
        tables = cursor.fetchall()
        
        for (table_name,) in tables:
            print(f"\n📊 {table_name}:")
            
            # 显示表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print("  表结构:")
            for col in columns:
                print(f"    - {col[1]} ({col[2]})")
            
            # 显示最新记录
            cursor.execute(f"""
                SELECT * FROM {table_name} 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            records = cursor.fetchall()
            
            if records:
                print(f"  最新 {len(records)} 条记录:")
                for record in records:
                    print(f"    {record}")
            else:
                print("  暂无记录")
                
    except Exception as e:
        print(f"❌ 检查失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("修复 push_history 表结构")
    print("=" * 60)
    
    fix_push_history_table()
    print("\n" + "=" * 60)
    print("检查 push_history 表内容")
    print("=" * 60)
    check_push_history()