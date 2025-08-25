#!/usr/bin/env python3
"""
完整验证和修复数据库表结构
确保所有profiles表都有正确的列
"""

import sqlite3
import json
import sys
from datetime import datetime

def verify_and_fix_database(db_path="user_profiles.db"):
    """验证和修复数据库"""
    print("=" * 60)
    print(f"🔍 验证数据库: {db_path}")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 获取所有profiles表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
        """)
        
        tables = cursor.fetchall()
        print(f"\n找到 {len(tables)} 个profiles表")
        
        # 定义必需的列
        required_columns = {
            'tags': 'TEXT DEFAULT "[]"',
            'source': 'TEXT DEFAULT "微信"',
            'message_count': 'INTEGER DEFAULT 0',
            'industry': 'TEXT',
            'school': 'TEXT',
            'profile_picture': 'TEXT',
            'last_message_time': 'TEXT',
            'wechat_id': 'TEXT',
            'basic_info': 'TEXT',
            'recent_activities': 'TEXT',
            'raw_messages': 'TEXT'
        }
        
        total_fixed = 0
        
        for (table_name,) in tables:
            print(f"\n检查表: {table_name}")
            
            # 获取当前列
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # 检查缺失的列
            missing_columns = []
            for col_name, col_type in required_columns.items():
                if col_name not in existing_columns:
                    missing_columns.append((col_name, col_type))
            
            if missing_columns:
                print(f"  缺失 {len(missing_columns)} 个列:")
                for col_name, col_type in missing_columns:
                    try:
                        # 添加缺失的列
                        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                        cursor.execute(sql)
                        print(f"    ✅ 添加: {col_name}")
                        total_fixed += 1
                    except sqlite3.OperationalError as e:
                        if "duplicate column" in str(e):
                            print(f"    ⏭️ 跳过: {col_name} (已存在)")
                        else:
                            print(f"    ❌ 失败: {col_name} - {e}")
            else:
                print("  ✅ 表结构完整")
        
        # 提交更改
        conn.commit()
        
        print("\n" + "=" * 60)
        print("📊 修复统计")
        print("=" * 60)
        print(f"✅ 添加了 {total_fixed} 个列")
        print(f"📋 检查了 {len(tables)} 个表")
        
        # 2. 验证修复结果
        print("\n" + "=" * 60)
        print("🔍 验证修复结果")
        print("=" * 60)
        
        all_ok = True
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            
            missing = []
            for col_name in required_columns.keys():
                if col_name not in columns:
                    missing.append(col_name)
            
            if missing:
                print(f"❌ {table_name}: 仍缺失 {', '.join(missing)}")
                all_ok = False
            else:
                print(f"✅ {table_name}: 结构完整")
        
        if all_ok:
            print("\n🎉 所有表结构都已完整!")
        else:
            print("\n⚠️ 仍有表结构不完整")
        
        conn.close()
        return all_ok
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_create_profile(db_path="user_profiles.db"):
    """测试创建带tags的联系人"""
    print("\n" + "=" * 60)
    print("🧪 测试创建带tags的联系人")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 找一个表来测试
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
            LIMIT 1
        """)
        
        table = cursor.fetchone()
        if not table:
            print("❌ 没有找到profiles表")
            return False
        
        table_name = table[0]
        print(f"使用表: {table_name}")
        
        # 创建测试数据
        test_data = {
            'profile_name': f'测试用户_{datetime.now().strftime("%H%M%S")}',
            'gender': '男',
            'tags': json.dumps(['测试', 'API', '标签'], ensure_ascii=False),
            'company': '测试公司',
            'source': 'API测试'
        }
        
        # 插入数据
        columns = ', '.join(test_data.keys())
        placeholders = ', '.join(['?' for _ in test_data])
        values = list(test_data.values())
        
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        
        profile_id = cursor.lastrowid
        conn.commit()
        
        # 验证插入成功
        cursor.execute(f"SELECT * FROM {table_name} WHERE id = ?", (profile_id,))
        row = cursor.fetchone()
        
        if row:
            print(f"✅ 成功创建测试联系人 (ID: {profile_id})")
            print(f"   姓名: {test_data['profile_name']}")
            print(f"   标签: {test_data['tags']}")
            conn.close()
            return True
        else:
            print("❌ 创建失败")
            conn.close()
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 获取数据库路径
    db_path = sys.argv[1] if len(sys.argv) > 1 else "user_profiles.db"
    
    # 1. 验证和修复
    success = verify_and_fix_database(db_path)
    
    # 2. 测试创建
    if success:
        test_create_profile(db_path)
    
    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)