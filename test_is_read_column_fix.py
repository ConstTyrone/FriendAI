#!/usr/bin/env python3
"""
测试is_read列修复
"""

import sys
import os
import sqlite3

# 添加src目录到path
sys.path.append('WeiXinKeFu/src')

from database.database_sqlite_v2 import SQLiteDatabase

def test_is_read_column_fix():
    """测试is_read列修复"""
    print("=== is_read列修复测试 ===\n")
    
    try:
        # 创建数据库实例
        print("1. 创建数据库实例...")
        db = SQLiteDatabase()
        print("✅ 数据库实例创建成功")
        
        # 检查intent_matches表结构
        print("\n2. 检查intent_matches表结构...")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取表结构信息
            cursor.execute("PRAGMA table_info(intent_matches)")
            columns_info = cursor.fetchall()
            
            print("intent_matches表列信息:")
            required_columns = ['is_read', 'read_at']
            found_columns = []
            
            for col_info in columns_info:
                col_id, col_name, col_type, not_null, default_value, pk = col_info
                print(f"  📋 {col_name} ({col_type}) - 默认值: {default_value}")
                found_columns.append(col_name)
            
            print(f"\n必需列检查:")
            for col in required_columns:
                exists = col in found_columns
                status = "✅ 存在" if exists else "❌ 缺失"
                print(f"  {col}: {status}")
        
        # 测试插入数据
        print("\n3. 测试插入匹配记录...")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 插入测试数据
            test_data = {
                'intent_id': 1,
                'profile_id': 1, 
                'user_id': 'test_user',
                'match_score': 0.85,
                'explanation': '测试匹配',
                'is_read': 0
            }
            
            cursor.execute("""
                INSERT OR REPLACE INTO intent_matches 
                (intent_id, profile_id, user_id, match_score, explanation, is_read)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (test_data['intent_id'], test_data['profile_id'], test_data['user_id'], 
                  test_data['match_score'], test_data['explanation'], test_data['is_read']))
            
            conn.commit()
            print("✅ 插入测试数据成功")
            
            # 测试查询is_read列
            cursor.execute("SELECT id, match_score, is_read FROM intent_matches WHERE user_id = ?", 
                         (test_data['user_id'],))
            result = cursor.fetchone()
            
            if result:
                match_id, score, is_read = result
                print(f"✅ 查询成功: id={match_id}, score={score}, is_read={is_read}")
            else:
                print("❌ 未找到测试数据")
        
        print(f"\n🎉 is_read列修复测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_is_read_column_fix()