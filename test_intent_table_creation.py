#!/usr/bin/env python3
"""
测试意图表自动创建功能
"""

import sys
import os
import sqlite3

# 添加src目录到path
sys.path.append('WeiXinKeFu/src')

from database.database_sqlite_v2 import SQLiteDatabase

def test_intent_table_creation():
    """测试意图表自动创建"""
    print("=== 意图表自动创建测试 ===\n")
    
    try:
        # 创建数据库实例
        print("1. 创建数据库实例...")
        db = SQLiteDatabase()
        print("✅ 数据库实例创建成功")
        
        # 检查表是否存在
        print("\n2. 检查意图表是否存在...")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查所有表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall()]
            
            intent_tables = ['user_intents', 'intent_matches', 'vector_index', 'push_history', 'user_push_preferences']
            
            print("所有表:")
            for table in sorted(tables):
                print(f"  📋 {table}")
            
            print(f"\n意图相关表检查:")
            for table in intent_tables:
                exists = table in tables
                status = "✅ 存在" if exists else "❌ 不存在"
                print(f"  {table}: {status}")
        
        # 手动触发表创建检查
        print("\n3. 手动触发意图表创建检查...")
        db.ensure_intent_tables_exist()
        print("✅ 意图表创建检查完成")
        
        # 再次检查表
        print("\n4. 检查表创建结果...")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables_after = [table[0] for table in cursor.fetchall()]
            
            intent_tables_after = [table for table in tables_after if table in intent_tables]
            print(f"意图表创建结果: {len(intent_tables_after)}/{len(intent_tables)} 个表存在")
            for table in intent_tables:
                exists = table in tables_after
                status = "✅" if exists else "❌"
                print(f"  {status} {table}")
        
        print(f"\n🎉 测试完成！意图表应该可以正常自动创建")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_intent_table_creation()