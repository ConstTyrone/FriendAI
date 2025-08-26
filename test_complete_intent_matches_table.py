#!/usr/bin/env python3
"""
测试完整的intent_matches表结构
"""

import sys
import os
import sqlite3
import json

# 添加src目录到path
sys.path.append('WeiXinKeFu/src')

from database.database_sqlite_v2 import SQLiteDatabase

def test_complete_intent_matches_table():
    """测试完整的intent_matches表结构"""
    print("=== 完整intent_matches表结构测试 ===\n")
    
    try:
        # 创建数据库实例
        print("1. 创建数据库实例...")
        db = SQLiteDatabase()
        print("✅ 数据库实例创建成功")
        
        # 检查完整表结构
        print("\n2. 检查intent_matches表结构...")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取表结构信息
            cursor.execute("PRAGMA table_info(intent_matches)")
            columns_info = cursor.fetchall()
            
            print("intent_matches表完整结构:")
            all_columns = []
            for col_info in columns_info:
                col_id, col_name, col_type, not_null, default_value, pk = col_info
                print(f"  📋 {col_name} ({col_type}) - 默认值: {default_value}")
                all_columns.append(col_name)
            
            # 检查所有必需的列
            required_columns = [
                'id', 'intent_id', 'profile_id', 'user_id',
                'match_score', 'score_details', 'matched_conditions', 'explanation', 
                'match_type', 'extended_info',
                'is_pushed', 'pushed_at', 'push_channel',
                'is_read', 'read_at',
                'user_feedback', 'feedback_at', 'feedback_note',
                'status', 'created_at', 'updated_at'
            ]
            
            print(f"\n3. 必需列完整性检查:")
            missing_columns = []
            for col in required_columns:
                exists = col in all_columns
                status = "✅ 存在" if exists else "❌ 缺失"
                print(f"  {col}: {status}")
                if not exists:
                    missing_columns.append(col)
            
            if missing_columns:
                print(f"\n❌ 缺失列: {', '.join(missing_columns)}")
                return False
            else:
                print(f"\n✅ 所有必需列都存在！")
        
        # 测试完整的插入操作
        print("\n4. 测试完整的数据插入...")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 插入完整测试数据
            test_data = {
                'intent_id': 1,
                'profile_id': 1, 
                'user_id': 'test_user_complete',
                'match_score': 0.85,
                'score_details': '详细分数说明',
                'matched_conditions': json.dumps(['条件1', '条件2']),
                'explanation': '匹配说明',
                'match_type': 'hybrid',
                'extended_info': json.dumps({'confidence': 0.9, 'aspects': ['技能', '经验']}),
                'is_pushed': 0,
                'push_channel': 'wechat',
                'is_read': 0,
                'user_feedback': None,
                'feedback_note': None,
                'status': 'pending'
            }
            
            cursor.execute("""
                INSERT OR REPLACE INTO intent_matches 
                (intent_id, profile_id, user_id, match_score, score_details, 
                 matched_conditions, explanation, match_type, extended_info,
                 is_pushed, push_channel, is_read, user_feedback, feedback_note, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_data['intent_id'], test_data['profile_id'], test_data['user_id'], 
                test_data['match_score'], test_data['score_details'],
                test_data['matched_conditions'], test_data['explanation'], 
                test_data['match_type'], test_data['extended_info'],
                test_data['is_pushed'], test_data['push_channel'], test_data['is_read'],
                test_data['user_feedback'], test_data['feedback_note'], test_data['status']
            ))
            
            conn.commit()
            print("✅ 完整数据插入成功")
            
            # 测试查询所有关键列
            cursor.execute("""
                SELECT id, match_score, match_type, extended_info, is_read, updated_at 
                FROM intent_matches WHERE user_id = ?
            """, (test_data['user_id'],))
            result = cursor.fetchone()
            
            if result:
                match_id, score, match_type, extended_info, is_read, updated_at = result
                print(f"✅ 查询成功:")
                print(f"   ID: {match_id}")
                print(f"   分数: {score}")
                print(f"   匹配类型: {match_type}")
                print(f"   扩展信息: {extended_info}")
                print(f"   已读状态: {is_read}")
                print(f"   更新时间: {updated_at}")
            else:
                print("❌ 未找到测试数据")
                return False
        
        # 测试UPDATE操作中的所有列
        print("\n5. 测试UPDATE操作...")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 测试包含所有新列的UPDATE
            cursor.execute("""
                UPDATE intent_matches 
                SET match_score = ?, matched_conditions = ?, 
                    explanation = ?, match_type = ?, 
                    extended_info = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (
                0.92, json.dumps(['更新条件1', '更新条件2']), 
                '更新说明', 'vector',
                json.dumps({'confidence': 0.95, 'update': True}),
                test_data['user_id']
            ))
            
            # 测试标记已读
            cursor.execute("""
                UPDATE intent_matches 
                SET is_read = 1, read_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (test_data['user_id'],))
            
            conn.commit()
            print("✅ UPDATE操作测试成功")
        
        print(f"\n🎉 intent_matches表结构完整性测试通过！")
        print("   所有必需列都存在，插入和更新操作都正常")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_intent_matches_table()
    if success:
        print("\n🚀 数据库表结构已完全符合代码需求！")
    else:
        print("\n⚠️ 表结构仍有问题，需要进一步修复")