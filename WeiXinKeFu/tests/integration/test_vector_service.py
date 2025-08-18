#!/usr/bin/env python3
"""
测试向量服务和AI匹配功能
"""

import asyncio
import sys
import os
import json
import sqlite3

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_vector_service():
    """测试向量服务"""
    print("=" * 60)
    print("测试向量服务")
    print("=" * 60)
    
    from src.services.vector_service import vector_service
    
    # 检查API密钥
    print(f"\nAPI密钥状态: {'已配置' if vector_service.api_key else '未配置'}")
    if vector_service.api_key:
        print(f"API密钥前10位: {vector_service.api_key[:10]}...")
    print(f"API端点: {vector_service.api_endpoint}")
    print(f"模型: {vector_service.embedding_model}")
    
    if not vector_service.api_key:
        print("\n❌ 未找到QWEN_API_KEY，请检查.env文件")
        return False
    
    # 测试向量化
    print("\n测试文本向量化...")
    test_text = "寻找AI技术专家"
    
    try:
        embedding = await vector_service.get_embedding(test_text)
        if embedding:
            print(f"✅ 向量化成功，维度: {len(embedding)}")
            print(f"   前5个值: {embedding[:5]}")
        else:
            print("❌ 向量化失败，返回None")
    except Exception as e:
        print(f"❌ 向量化出错: {e}")
    
    return True

async def test_intent_matching():
    """测试意图匹配"""
    print("\n" + "=" * 60)
    print("测试意图匹配")
    print("=" * 60)
    
    from src.services.intent_matcher import intent_matcher
    
    print(f"\nAI模式: {'启用' if intent_matcher.use_ai else '禁用'}")
    print(f"向量服务: {'已加载' if intent_matcher.vector_service else '未加载'}")
    
    # 创建测试数据
    test_intent = {
        'id': 1,
        'name': '寻找AI专家',
        'description': '寻找精通人工智能和机器学习的技术专家',
        'conditions': {
            'keywords': ['AI', '人工智能', '技术', '专家']
        },
        'threshold': 0.5
    }
    
    test_profile = {
        'id': 1,
        'profile_name': '张三',
        'company': 'AI科技公司',
        'position': 'AI算法工程师',
        'education': '清华大学计算机系',
        'personality': '技术专家，精通机器学习'
    }
    
    print("\n测试意图:")
    print(f"  名称: {test_intent['name']}")
    print(f"  关键词: {test_intent['conditions']['keywords']}")
    
    print("\n测试联系人:")
    print(f"  姓名: {test_profile['profile_name']}")
    print(f"  公司: {test_profile['company']}")
    print(f"  职位: {test_profile['position']}")
    
    # 计算匹配分数
    print("\n计算匹配分数...")
    try:
        score = await intent_matcher._calculate_match_score(test_intent, test_profile)
        print(f"✅ 匹配分数: {score:.2f}")
        
        # 分析匹配细节
        keywords = test_intent['conditions']['keywords']
        profile_text = f"{test_profile['company']} {test_profile['position']} {test_profile['personality']}".lower()
        
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in profile_text:
                matched_keywords.append(keyword)
        
        print(f"   匹配的关键词: {matched_keywords}")
        print(f"   关键词匹配率: {len(matched_keywords)}/{len(keywords)}")
        
    except Exception as e:
        print(f"❌ 匹配计算失败: {e}")
        import traceback
        traceback.print_exc()

async def test_database_intents():
    """测试数据库中的实际意图"""
    print("\n" + "=" * 60)
    print("测试数据库中的意图")
    print("=" * 60)
    
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    # 查询意图
    cursor.execute("""
        SELECT id, name, description, conditions, threshold 
        FROM user_intents 
        WHERE status = 'active'
        LIMIT 5
    """)
    
    intents = cursor.fetchall()
    print(f"\n找到 {len(intents)} 个活跃意图")
    
    for intent in intents:
        print(f"\n意图 {intent[0]}: {intent[1]}")
        print(f"  描述: {intent[2][:50]}..." if intent[2] else "  描述: 无")
        
        try:
            conditions = json.loads(intent[3]) if intent[3] else {}
            keywords = conditions.get('keywords', [])
            print(f"  关键词: {keywords}")
            print(f"  阈值: {intent[4]}")
        except:
            print(f"  条件解析失败")
    
    # 查询联系人数量
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name LIKE 'profiles_%'
    """)
    
    profile_tables = cursor.fetchall()
    print(f"\n找到 {len(profile_tables)} 个用户的联系人表")
    
    for table in profile_tables[:3]:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  {table[0]}: {count} 个联系人")
    
    conn.close()

async def main():
    """主测试函数"""
    print("\n🔧 开始测试AI意图匹配系统\n")
    
    # 测试向量服务
    success = await test_vector_service()
    
    if success:
        # 测试意图匹配
        await test_intent_matching()
    
    # 测试数据库
    await test_database_intents()
    
    print("\n" + "=" * 60)
    print("🎉 测试完成！")
    print("=" * 60)
    
    print("\n诊断建议:")
    print("1. 确认.env文件中的QWEN_API_KEY是否正确")
    print("2. 确认意图设置了关键词")
    print("3. 确认联系人表中有数据")
    print("4. 检查匹配阈值是否合理（建议0.5-0.7）")

if __name__ == "__main__":
    asyncio.run(main())