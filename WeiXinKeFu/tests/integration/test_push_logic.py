#!/usr/bin/env python3
"""
测试推送逻辑修复
"""

import sys
import os
import asyncio
import sqlite3
import json
from datetime import datetime

# 添加项目路径到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量避免numpy导入
os.environ['NO_NUMPY'] = '1'

from src.services.intent_matcher import IntentMatcher

# 测试用户ID
TEST_USER_ID = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"

async def test_push_logic():
    """测试推送逻辑"""
    print("=" * 60)
    print("测试推送逻辑修复")
    print("=" * 60)
    
    # 初始化匹配器
    matcher = IntentMatcher(use_ai=False)  # 使用规则匹配测试
    
    # 连接数据库
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    # 获取用户的第一个意图
    cursor.execute("""
        SELECT id, name FROM user_intents 
        WHERE user_id = ? AND status = 'active' 
        LIMIT 1
    """, (TEST_USER_ID,))
    
    intent_row = cursor.fetchone()
    if not intent_row:
        print("❌ 没有找到活跃的意图")
        return
    
    intent_id, intent_name = intent_row
    print(f"✅ 找到意图: {intent_name} (ID: {intent_id})")
    
    # 获取已存在的匹配记录数
    cursor.execute("""
        SELECT COUNT(*) FROM intent_matches 
        WHERE intent_id = ? AND user_id = ?
    """, (intent_id, TEST_USER_ID))
    
    before_count = cursor.fetchone()[0]
    print(f"📊 当前匹配记录数: {before_count}")
    
    # 执行第一次匹配
    print("\n🔄 执行第一次匹配...")
    matches1 = await matcher.match_intent_with_profiles(intent_id, TEST_USER_ID)
    print(f"✅ 第一次匹配结果: {len(matches1)} 个匹配")
    
    # 检查匹配记录数
    cursor.execute("""
        SELECT COUNT(*) FROM intent_matches 
        WHERE intent_id = ? AND user_id = ?
    """, (intent_id, TEST_USER_ID))
    
    after_count1 = cursor.fetchone()[0]
    print(f"📊 第一次后匹配记录数: {after_count1}")
    
    # 执行第二次匹配（不应该产生新的推送）
    print("\n🔄 执行第二次匹配（模拟重复触发）...")
    matches2 = await matcher.match_intent_with_profiles(intent_id, TEST_USER_ID)
    print(f"✅ 第二次匹配结果: {len(matches2)} 个匹配（应该为0，因为没有新匹配）")
    
    # 检查匹配记录数
    cursor.execute("""
        SELECT COUNT(*) FROM intent_matches 
        WHERE intent_id = ? AND user_id = ?
    """, (intent_id, TEST_USER_ID))
    
    after_count2 = cursor.fetchone()[0]
    print(f"📊 第二次后匹配记录数: {after_count2}")
    
    # 验证结果
    print("\n" + "=" * 60)
    print("测试结果:")
    if len(matches2) == 0:
        print("✅ 成功：第二次匹配没有产生新的推送")
    else:
        print(f"❌ 失败：第二次匹配产生了 {len(matches2)} 个推送")
    
    if after_count2 == after_count1:
        print("✅ 成功：匹配记录数没有增加")
    else:
        print(f"❌ 失败：匹配记录数从 {after_count1} 增加到 {after_count2}")
    
    # 查看最近的匹配记录
    print("\n📋 最近的匹配记录:")
    cursor.execute("""
        SELECT id, profile_id, match_score, created_at, is_read
        FROM intent_matches 
        WHERE intent_id = ? AND user_id = ?
        ORDER BY created_at DESC
        LIMIT 5
    """, (intent_id, TEST_USER_ID))
    
    for row in cursor.fetchall():
        match_id, profile_id, score, created_at, is_read = row
        read_status = "已读" if is_read else "未读"
        print(f"  - ID: {match_id}, Profile: {profile_id}, Score: {score:.2f}, "
              f"Time: {created_at}, Status: {read_status}")
    
    conn.close()
    print("\n测试完成！")

if __name__ == "__main__":
    asyncio.run(test_push_logic())