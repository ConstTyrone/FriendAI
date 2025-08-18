#!/usr/bin/env python
"""
测试意图匹配修复
"""

import sys
import os
import sqlite3
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_user_isolation():
    """测试用户数据隔离"""
    print("=" * 60)
    print("测试用户数据隔离")
    print("=" * 60)
    
    from src.services.intent_matcher import intent_matcher
    
    # 测试用户ID处理
    test_user_id = "test_user_001"
    table_name = intent_matcher._get_user_table_name(test_user_id)
    
    print(f"\n用户ID: {test_user_id}")
    print(f"用户表名: {table_name}")
    
    # 检查数据库中的表
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    # 列出所有用户表
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE 'profiles_%'
    """)
    tables = cursor.fetchall()
    
    print(f"\n数据库中的用户表:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # 检查意图表中的用户隔离
    cursor.execute("""
        SELECT user_id, COUNT(*) as intent_count 
        FROM user_intents 
        GROUP BY user_id
    """)
    user_intents = cursor.fetchall()
    
    print(f"\n各用户的意图数量:")
    for user_id, count in user_intents:
        print(f"  - {user_id}: {count}个意图")
    
    conn.close()
    
    print("\n✅ 用户数据隔离测试完成")

def test_async_fix():
    """测试异步修复"""
    print("\n" + "=" * 60)
    print("测试异步修复")
    print("=" * 60)
    
    from src.services.intent_matcher import intent_matcher
    
    print(f"\nAI增强状态: {intent_matcher.use_ai}")
    
    if not intent_matcher.use_ai:
        print("✅ AI增强已禁用，避免异步冲突")
    else:
        print("⚠️ AI增强仍然启用，可能导致异步冲突")
    
    # 测试基础匹配功能
    test_intent = {
        'id': 1,
        'name': '测试意图',
        'conditions': {
            'keywords': ['技术', 'AI']
        },
        'threshold': 0.5
    }
    
    test_profile = {
        'id': 1,
        'profile_name': '测试联系人',
        'company': 'AI公司',
        'position': '技术总监'
    }
    
    # 计算匹配分数
    score = intent_matcher._calculate_match_score(test_intent, test_profile)
    
    print(f"\n测试匹配分数: {score:.2f}")
    
    if score > 0:
        print("✅ 基础匹配功能正常")
    else:
        print("❌ 基础匹配功能异常")

def main():
    """主测试函数"""
    print("\n🔧 开始测试意图匹配修复\n")
    
    try:
        # 测试用户隔离
        test_user_isolation()
        
        # 测试异步修复
        test_async_fix()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成！")
        print("=" * 60)
        
        print("\n修复说明:")
        print("1. 暂时禁用了AI增强功能，避免异步事件循环冲突")
        print("2. 用户数据隔离通过表名前缀 profiles_{user_id} 实现")
        print("3. 基础的规则匹配功能仍然可用")
        print("\n后续优化:")
        print("- 将整个匹配流程改为异步，支持AI增强")
        print("- 或使用线程池来处理异步调用")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()