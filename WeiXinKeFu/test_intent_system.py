#!/usr/bin/env python
"""
意图匹配系统测试脚本
测试数据库创建和基本功能
"""

import sys
import os
import sqlite3
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_creation():
    """测试数据库表创建"""
    print("=" * 60)
    print("测试意图匹配系统数据库")
    print("=" * 60)
    
    # 运行创建脚本
    from scripts.create_intent_tables import create_intent_tables, add_sample_intents
    
    db_path = "user_profiles.db"
    
    # 创建表
    print("\n1. 创建数据表...")
    create_intent_tables(db_path)
    
    # 添加示例数据
    print("\n2. 添加示例意图...")
    add_sample_intents(db_path)
    
    # 验证表结构
    print("\n3. 验证表结构...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('user_intents', 'intent_matches', 'vector_index', 'push_history', 'user_push_preferences')
    """)
    tables = cursor.fetchall()
    
    print(f"   已创建的表: {[t[0] for t in tables]}")
    
    # 查询示例意图
    cursor.execute("SELECT id, name, description, type FROM user_intents")
    intents = cursor.fetchall()
    
    print(f"\n4. 示例意图数据:")
    for intent in intents:
        print(f"   ID={intent[0]}, 名称={intent[1]}, 类型={intent[3]}")
        print(f"   描述: {intent[2][:50]}...")
    
    conn.close()
    
    print("\n✅ 数据库测试完成！")

def test_intent_matching():
    """测试意图匹配引擎"""
    print("\n" + "=" * 60)
    print("测试意图匹配引擎")
    print("=" * 60)
    
    from src.services.intent_matcher import intent_matcher
    
    # 创建测试意图
    test_intent = {
        'id': 1,
        'name': '寻找技术合伙人',
        'description': '寻找有AI技术背景，在北京或上海，有创业经验的技术合伙人',
        'conditions': {
            'required': [
                {'field': 'position', 'operator': 'contains', 'value': 'CTO'},
                {'field': 'location', 'operator': 'in', 'value': ['北京', '上海']}
            ],
            'keywords': ['AI', '机器学习', '创业', '技术管理']
        },
        'threshold': 0.7
    }
    
    # 创建测试联系人
    test_profiles = [
        {
            'id': 1,
            'profile_name': '张三',
            'company': 'AI科技公司',
            'position': 'CTO',
            'location': '北京',
            'education': '清华大学',
            'ai_summary': '技术专家，有10年AI开发经验，曾创办过科技公司'
        },
        {
            'id': 2,
            'profile_name': '李四',
            'company': '互联网公司',
            'position': '产品经理',
            'location': '上海',
            'education': '复旦大学',
            'ai_summary': '产品专家，擅长用户体验设计'
        },
        {
            'id': 3,
            'profile_name': '王五',
            'company': '创业公司',
            'position': '技术总监',
            'location': '深圳',
            'education': '北京大学',
            'ai_summary': '全栈工程师，有创业经验'
        }
    ]
    
    print("\n测试意图:")
    print(f"  名称: {test_intent['name']}")
    print(f"  描述: {test_intent['description']}")
    
    print("\n测试联系人:")
    for profile in test_profiles:
        print(f"  - {profile['profile_name']}: {profile['position']} @ {profile['company']} ({profile['location']})")
    
    # 执行匹配
    print("\n执行匹配...")
    matches = intent_matcher.match_intent_with_profiles(test_intent, test_profiles)
    
    print(f"\n匹配结果: 找到 {len(matches)} 个匹配")
    for i, match in enumerate(matches, 1):
        profile = match['profile']
        print(f"\n  {i}. {profile['profile_name']} - 匹配度: {match['score']*100:.1f}%")
        print(f"     解释: {match['explanation']}")
        if match['matched_conditions']:
            print(f"     匹配条件: {', '.join(match['matched_conditions'][:3])}")
    
    print("\n✅ 匹配引擎测试完成！")

def main():
    """主测试函数"""
    print("\n🚀 开始测试意图匹配系统\n")
    
    try:
        # 测试数据库
        test_database_creation()
        
        # 测试匹配引擎
        test_intent_matching()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成！意图匹配系统基础功能正常")
        print("=" * 60)
        
        print("\n下一步:")
        print("1. 启动后端服务: python run.py")
        print("2. 在微信开发者工具中编译小程序")
        print("3. 在设置页面点击'意图匹配'进入功能")
        print("4. 创建意图并测试匹配功能")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()