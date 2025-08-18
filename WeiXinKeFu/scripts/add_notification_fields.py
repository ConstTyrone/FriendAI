#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
添加通知相关字段到intent_matches表
"""

import sqlite3
import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def add_notification_fields():
    """添加通知相关字段"""
    
    # 数据库路径
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_profiles.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 获取所有用户的intent_matches表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'intent_matches_%'
        """)
        tables = cursor.fetchall()
        
        if not tables:
            print("⚠️ 没有找到intent_matches表")
            return False
        
        for (table_name,) in tables:
            print(f"\n📊 处理表: {table_name}")
            
            # 检查字段是否已存在
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # 添加缺失的字段
            fields_to_add = [
                ('is_read', 'INTEGER DEFAULT 0'),
                ('is_pushed', 'INTEGER DEFAULT 0'),
                ('pushed_at', 'TIMESTAMP'),
                ('read_at', 'TIMESTAMP'),
                ('push_message_id', 'TEXT'),
                ('push_error', 'TEXT')
            ]
            
            for field_name, field_type in fields_to_add:
                if field_name not in column_names:
                    try:
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {field_name} {field_type}")
                        print(f"  ✅ 添加字段: {field_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            print(f"  ❌ 添加字段 {field_name} 失败: {e}")
                else:
                    print(f"  ℹ️ 字段已存在: {field_name}")
            
            # 为未读的旧记录设置默认值
            cursor.execute(f"""
                UPDATE {table_name} 
                SET is_read = 0, is_pushed = 0
                WHERE is_read IS NULL
            """)
            
            # 创建索引以提高查询性能
            try:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_read_status 
                    ON {table_name}(is_read, created_at DESC)
                """)
                print(f"  ✅ 创建索引: idx_{table_name}_read_status")
            except Exception as e:
                print(f"  ⚠️ 创建索引失败（可能已存在）: {e}")
        
        conn.commit()
        print("\n✅ 所有表更新完成！")
        
        # 显示更新后的表结构
        print("\n📋 验证表结构:")
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"\n{table_name} 字段:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        
        return True
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def check_notification_api():
    """检查通知API所需的表和字段"""
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'user_profiles.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 测试查询
        test_user = 'wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q'
        table_name = f'intent_matches_{test_user}'
        
        cursor.execute(f"""
            SELECT 
                m.id,
                m.intent_id,
                m.profile_id,
                m.match_score,
                m.explanation,
                m.is_read,
                m.is_pushed,
                m.created_at
            FROM {table_name} m
            WHERE m.is_read = 0
            ORDER BY m.created_at DESC
            LIMIT 5
        """)
        
        results = cursor.fetchall()
        print(f"\n✅ API查询测试成功！找到 {len(results)} 条未读记录")
        
        if results:
            print("\n最近的未读匹配:")
            for r in results:
                print(f"  - ID: {r[0]}, 分数: {r[3]:.2f}, 已推送: {'是' if r[6] else '否'}")
        
    except Exception as e:
        print(f"\n❌ API查询测试失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔧 开始添加通知相关字段...")
    print("=" * 50)
    
    if add_notification_fields():
        print("\n" + "=" * 50)
        check_notification_api()
        print("\n✨ 更新完成！现在可以使用通知功能了")
    else:
        print("\n❌ 更新失败，请检查错误信息")