#!/usr/bin/env python3
"""
为测试用户创建测试意图
"""

import sqlite3
import json
from datetime import datetime

def create_test_intent():
    """为测试用户创建测试意图"""
    conn = sqlite3.connect('user_profiles.db')
    cursor = conn.cursor()
    
    test_user = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    print("=" * 60)
    print("🎯 创建测试意图")
    print("=" * 60)
    
    # 检查表是否存在
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='user_intents'
    """)
    
    if not cursor.fetchone():
        print("❌ user_intents表不存在，需要先创建表")
        conn.close()
        return
    
    # 创建测试意图
    intent_name = "寻找AI技术专家"
    intent_desc = "寻找有AI和机器学习背景的技术专家，最好有大型项目经验"
    
    # 配置条件
    conditions = {
        "keywords": ["AI", "人工智能", "机器学习", "深度学习", "技术", "专家", "算法"],
        "required": [],
        "preferred": [
            {"field": "position", "operator": "contains", "value": "技术"},
            {"field": "company", "operator": "contains", "value": "科技"}
        ]
    }
    
    # 插入意图
    try:
        cursor.execute("""
            INSERT INTO user_intents (
                user_id, name, description, conditions, 
                threshold, status, priority, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_user,
            intent_name,
            intent_desc,
            json.dumps(conditions, ensure_ascii=False),
            0.3,  # 较低的阈值以便更容易匹配
            'active',
            1,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        intent_id = cursor.lastrowid
        conn.commit()
        
        print(f"\n✅ 成功创建测试意图!")
        print(f"   ID: {intent_id}")
        print(f"   名称: {intent_name}")
        print(f"   用户: {test_user}")
        print(f"   阈值: 0.3")
        print(f"   关键词: {conditions['keywords']}")
        
        # 验证创建
        cursor.execute("""
            SELECT id, name FROM user_intents 
            WHERE user_id = ? AND id = ?
        """, (test_user, intent_id))
        
        if cursor.fetchone():
            print(f"\n✅ 验证成功: 意图已创建")
            print(f"\n📝 使用说明:")
            print(f"   1. 使用意图ID {intent_id} 进行匹配测试")
            print(f"   2. 运行: python check_ai.py")
            print(f"   3. 或在API中调用: POST /api/intents/{intent_id}/match")
        else:
            print(f"\n❌ 验证失败: 无法找到创建的意图")
            
    except sqlite3.IntegrityError as e:
        print(f"\n❌ 创建失败: {e}")
        print("   可能已经存在相同的意图")
    except Exception as e:
        print(f"\n❌ 创建失败: {e}")
    
    # 列出用户的所有意图
    print("\n" + "-" * 60)
    print("📋 用户的所有意图:")
    print("-" * 60)
    
    cursor.execute("""
        SELECT id, name, status, threshold
        FROM user_intents 
        WHERE user_id = ?
        ORDER BY id DESC
    """, (test_user,))
    
    intents = cursor.fetchall()
    if intents:
        for intent_id, name, status, threshold in intents:
            print(f"  - ID {intent_id}: {name} ({status}, 阈值: {threshold})")
    
    conn.close()

if __name__ == "__main__":
    print("\n🚀 为测试用户创建意图\n")
    create_test_intent()
    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)