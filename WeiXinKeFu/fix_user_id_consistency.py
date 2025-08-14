#!/usr/bin/env python3
"""
修复用户ID一致性问题
查看并解释用户ID在不同地方的存储格式
"""

import sqlite3
import json

def analyze_user_id_formats():
    """分析用户ID格式问题"""
    conn = sqlite3.connect('user_profiles.db')
    cursor = conn.cursor()
    
    print("=" * 70)
    print("🔍 用户ID格式分析")
    print("=" * 70)
    
    original_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    clean_id = ''.join(c if c.isalnum() or c == '_' else '_' for c in original_id)
    
    print(f"\n📌 ID格式说明:")
    print(f"   原始ID (从微信): {original_id}")
    print(f"   清理后ID (表名): {clean_id}")
    print(f"   区别: 减号 '-' 被替换为下划线 '_'")
    
    # 1. 检查user_intents表中的用户ID
    print(f"\n1️⃣ user_intents表中的用户ID格式:")
    print("-" * 50)
    
    cursor.execute("""
        SELECT DISTINCT user_id, COUNT(*) as intent_count
        FROM user_intents
        WHERE user_id LIKE '%wm0gZOdQAA%'
        GROUP BY user_id
    """)
    
    results = cursor.fetchall()
    if results:
        for user_id, count in results:
            if '-' in user_id:
                print(f"   ✅ {user_id}")
                print(f"      格式: 原始格式（带减号）")
                print(f"      意图数: {count}")
            else:
                print(f"   ⚠️ {user_id}")
                print(f"      格式: 清理格式（下划线）")
                print(f"      意图数: {count}")
    else:
        print("   没有找到相关用户ID")
    
    # 2. 检查profiles表名
    print(f"\n2️⃣ profiles表名格式:")
    print("-" * 50)
    
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name LIKE 'profiles_%wm0gZOdQAA%'
    """)
    
    tables = cursor.fetchall()
    if tables:
        for table_name, in tables:
            user_part = table_name.replace('profiles_', '')
            if '-' in user_part:
                print(f"   ⚠️ {table_name}")
                print(f"      问题: 表名包含减号（不推荐）")
            else:
                print(f"   ✅ {table_name}")
                print(f"      格式: 正确（使用下划线）")
            
            # 获取表中的记录数
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            count = cursor.fetchone()[0]
            print(f"      记录数: {count}")
    else:
        print("   没有找到相关表")
    
    # 3. 检查intent_matches表
    print(f"\n3️⃣ intent_matches表中的用户ID格式:")
    print("-" * 50)
    
    cursor.execute("""
        SELECT DISTINCT user_id, COUNT(*) as match_count
        FROM intent_matches
        WHERE user_id LIKE '%wm0gZOdQAA%'
        GROUP BY user_id
    """)
    
    results = cursor.fetchall()
    if results:
        for user_id, count in results:
            if '-' in user_id:
                print(f"   ✅ {user_id}")
                print(f"      格式: 原始格式（带减号）")
            else:
                print(f"   ⚠️ {user_id}")
                print(f"      格式: 清理格式（下划线）")
            print(f"      匹配数: {count}")
    else:
        print("   没有找到相关用户ID")
    
    # 建议
    print(f"\n" + "=" * 70)
    print("💡 问题分析与建议:")
    print("=" * 70)
    
    print("""
问题原因:
1. 微信用户ID包含减号: wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q
2. SQLite表名不推荐使用减号，所以转换为下划线
3. 但user_intents表中的user_id字段存储的是原始ID（带减号）

解决方案:
1. user_intents表的user_id字段: 使用原始ID（带减号）
2. profiles表名: 使用清理后的ID（下划线）
3. API调用时: 使用原始ID（带减号）
4. 查询profiles表时: 先清理ID再构建表名

代码示例:
```python
# 原始ID（API传入）
user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"

# 查询意图时使用原始ID
cursor.execute("SELECT * FROM user_intents WHERE user_id = ?", (user_id,))

# 构建表名时清理ID
clean_id = ''.join(c if c.isalnum() or c == '_' else '_' for c in user_id)
table_name = f"profiles_{clean_id}"
```
""")
    
    conn.close()

if __name__ == "__main__":
    print("\n🔧 用户ID一致性分析工具\n")
    analyze_user_id_formats()