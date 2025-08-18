#!/usr/bin/env python3
"""
检查意图的所属用户
"""

import sqlite3

def check_intent_ownership():
    """检查意图的所属用户"""
    conn = sqlite3.connect('user_profiles.db')
    cursor = conn.cursor()
    
    print("=" * 60)
    print("🔍 检查意图所属用户")
    print("=" * 60)
    
    # 查询意图11的详情
    cursor.execute("""
        SELECT id, name, user_id, status, created_at
        FROM user_intents 
        WHERE id = 11
    """)
    
    result = cursor.fetchone()
    if result:
        intent_id, name, user_id, status, created_at = result
        print(f"\n✅ 找到意图11:")
        print(f"   名称: {name}")
        print(f"   所属用户: {user_id}")
        print(f"   状态: {status}")
        print(f"   创建时间: {created_at}")
        
        if user_id != "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q":
            print(f"\n⚠️ 意图11不属于测试用户!")
            print(f"   意图所属: {user_id}")
            print(f"   测试用户: wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q")
    else:
        print("\n❌ 意图11不存在")
    
    # 查询测试用户的所有意图
    print("\n" + "-" * 60)
    print("📋 测试用户的意图列表:")
    print("-" * 60)
    
    test_user = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    cursor.execute("""
        SELECT id, name, status, threshold
        FROM user_intents 
        WHERE user_id = ?
        ORDER BY id
    """, (test_user,))
    
    intents = cursor.fetchall()
    if intents:
        print(f"\n用户 {test_user} 的意图:")
        for intent_id, name, status, threshold in intents:
            print(f"  - ID {intent_id}: {name} ({status}, 阈值: {threshold})")
    else:
        print(f"\n❌ 用户 {test_user} 没有任何意图")
        print("\n建议: 为测试用户创建一个新的意图")
    
    # 查询所有用户及其意图数量
    print("\n" + "-" * 60)
    print("📊 所有用户的意图统计:")
    print("-" * 60)
    
    cursor.execute("""
        SELECT user_id, COUNT(*) as intent_count
        FROM user_intents
        GROUP BY user_id
        ORDER BY intent_count DESC
    """)
    
    users = cursor.fetchall()
    for user_id, count in users:
        display_id = user_id[:20] + "..." if len(user_id) > 20 else user_id
        print(f"  - {display_id}: {count} 个意图")
    
    conn.close()

if __name__ == "__main__":
    print("\n🎯 意图所属用户检查工具\n")
    check_intent_ownership()
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)