#!/usr/bin/env python3
"""
检查数据库中的所有表
"""

import sqlite3
import os

def check_tables():
    """检查数据库中的所有表"""
    db_path = "user_profiles.db"
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return
    
    print(f"✅ 数据库文件存在: {db_path}")
    print(f"   文件大小: {os.path.getsize(db_path) / 1024:.2f} KB")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取所有表
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    
    tables = cursor.fetchall()
    
    print(f"\n📋 数据库中的表 (共 {len(tables)} 个):")
    print("-" * 60)
    
    for table_name, in tables:
        # 获取表的行数
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count} 行")
            
            # 如果是profiles开头的表，显示更多信息
            if table_name.startswith("profiles_"):
                user_id = table_name.replace("profiles_", "")
                print(f"    用户ID: {user_id}")
                
                # 检查是否是我们要找的用户
                if "wm0gZOdQAA" in user_id:
                    print(f"    ⭐ 这可能是目标用户表!")
                    
                    # 显示前3条记录
                    cursor.execute(f"SELECT id, profile_name, company FROM `{table_name}` LIMIT 3")
                    profiles = cursor.fetchall()
                    if profiles:
                        print(f"    示例联系人:")
                        for p_id, name, company in profiles:
                            print(f"      - ID {p_id}: {name} ({company})")
        except Exception as e:
            print(f"  - {table_name}: 读取失败 ({e})")
    
    # 特别查找目标用户
    print("\n🔍 查找目标用户表:")
    print("-" * 60)
    
    target_user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    # 尝试不同的表名格式
    possible_table_names = [
        f"profiles_{target_user_id}",
        f"profiles_{target_user_id.replace('-', '_')}",
        f"profiles_wm0gZOdQAAv_phiLJWS77wmzQQSOrL1Q",
        "profiles_wm0gZOdQAAvphiLJWS77wmzQQSOrL1Q"
    ]
    
    for table_name in possible_table_names:
        cursor.execute("""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        
        exists = cursor.fetchone()[0] > 0
        print(f"  {table_name}: {'✅ 存在' if exists else '❌ 不存在'}")
    
    # 查找相似的表名
    print("\n🔍 包含 'wm0gZOdQAA' 的表:")
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE '%wm0gZOdQAA%'
    """)
    
    similar_tables = cursor.fetchall()
    if similar_tables:
        for table_name, in similar_tables:
            print(f"  ✅ 找到: {table_name}")
    else:
        print("  ❌ 没有找到包含 'wm0gZOdQAA' 的表")
    
    conn.close()

if __name__ == "__main__":
    print("\n🗄️ 数据库表检查工具\n")
    print("=" * 60)
    check_tables()
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)