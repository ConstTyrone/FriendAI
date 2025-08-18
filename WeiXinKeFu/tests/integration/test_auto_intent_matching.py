#!/usr/bin/env python3
"""
测试新联系人自动触发意图匹配功能
"""

import sys
import os
import asyncio
import json

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'WeiXinKeFu'))

from src.database.database_sqlite_v2 import database_manager as db
from src.handlers.message_handler import process_message
from src.services.intent_matcher import intent_matcher

def create_test_intent(user_id: str) -> int:
    """创建测试意图"""
    import sqlite3
    
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # 创建一个测试意图
    test_intent = {
        "user_id": user_id,
        "name": "寻找技术人才",
        "description": "寻找Python开发工程师，要求有AI背景，年龄25-35岁",
        "type": "recruitment",
        "conditions": {
            "required": {
                "company": ["技术", "AI", "Python", "开发", "工程师"],
                "position": ["开发", "工程师", "技术", "程序员"],
                "age_range": {"min": 25, "max": 35}
            },
            "preferred": {
                "education": ["本科", "硕士", "计算机"],
                "skills": ["Python", "AI", "机器学习", "深度学习"]
            }
        },
        "threshold": 0.6,
        "priority": 8,
        "max_push_per_day": 3
    }
    
    cursor.execute("""
        INSERT INTO user_intents (
            user_id, name, description, type, conditions, 
            threshold, priority, max_push_per_day
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        test_intent["user_id"],
        test_intent["name"],
        test_intent["description"],
        test_intent["type"],
        json.dumps(test_intent["conditions"], ensure_ascii=False),
        test_intent["threshold"],
        test_intent["priority"],
        test_intent["max_push_per_day"]
    ))
    
    intent_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"✅ 创建测试意图成功 (ID: {intent_id})")
    return intent_id

def simulate_new_contact_message(user_id: str):
    """模拟收到新联系人消息"""
    # 模拟一个包含联系人信息的消息
    test_message = {
        'FromUserName': user_id,
        'MsgType': 'text',
        'Content': '''
        李明，男，28岁，Python开发工程师
        公司：阿里巴巴AI实验室
        职位：高级算法工程师
        学历：清华大学计算机科学硕士
        电话：13888888888
        地址：杭州市西湖区
        技能：Python、机器学习、深度学习、TensorFlow
        ''',
        'CreateTime': '1703123456',
        'MsgId': 'test_msg_001'
    }
    
    print(f"📨 模拟收到新联系人消息...")
    print(f"消息内容预览: {test_message['Content'][:100]}...")
    
    # 处理消息 - 这会自动触发意图匹配
    process_message(test_message)

async def check_matches(user_id: str, intent_id: int):
    """检查匹配结果"""
    import sqlite3
    
    # 等待一下，让异步匹配完成
    print("⏳ 等待意图匹配完成...")
    await asyncio.sleep(3)
    
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    # 查询匹配结果
    cursor.execute("""
        SELECT 
            m.id,
            m.profile_id,
            m.match_score,
            m.explanation,
            p.profile_name,
            p.company,
            p.position
        FROM intent_matches m
        LEFT JOIN profiles_{} p ON m.profile_id = p.id
        WHERE m.intent_id = ? AND m.user_id = ?
        ORDER BY m.match_score DESC
    """.format(user_id.replace('-', '_')), (intent_id, user_id))
    
    matches = cursor.fetchall()
    conn.close()
    
    if matches:
        print(f"\n🎯 找到 {len(matches)} 个匹配结果:")
        for i, match in enumerate(matches, 1):
            match_id, profile_id, score, explanation, name, company, position = match
            print(f"\n=== 匹配结果 {i} ===")
            print(f"匹配ID: {match_id}")
            print(f"联系人: {name}")
            print(f"公司: {company}")
            print(f"职位: {position}")
            print(f"匹配分数: {score:.2%}")
            if explanation:
                print(f"AI解释: {explanation}")
    else:
        print("❌ 未找到匹配结果")

async def main():
    """主测试函数"""
    print("🧪 开始测试新联系人自动触发意图匹配功能\n")
    
    # 测试用户ID
    test_user_id = "test-auto-intent-user"
    
    try:
        # 1. 创建测试意图
        print("步骤1: 创建测试意图")
        intent_id = create_test_intent(test_user_id)
        
        # 2. 模拟新联系人消息
        print("\n步骤2: 模拟收到新联系人消息")
        simulate_new_contact_message(test_user_id)
        
        # 3. 检查匹配结果
        print("\n步骤3: 检查意图匹配结果")
        await check_matches(test_user_id, intent_id)
        
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())