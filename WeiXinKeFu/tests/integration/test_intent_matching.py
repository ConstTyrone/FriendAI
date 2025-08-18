#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试意图匹配系统
"""

import json
import sqlite3
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.intent_matcher import intent_matcher

def test_intent_matching():
    """测试意图匹配功能"""
    
    # 测试用户ID
    test_user_id = "test_user_001"
    
    # 连接数据库
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    try:
        # 1. 创建测试意图
        print("1. 创建测试意图...")
        cursor.execute("""
            INSERT OR REPLACE INTO user_intents (
                user_id, name, description, type, 
                conditions, threshold, priority, 
                max_push_per_day, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            test_user_id,
            "寻找技术合作伙伴",
            "寻找有技术背景的创业者或技术专家进行合作",
            "collaboration",
            json.dumps({
                "keywords": ["技术", "程序员", "工程师", "开发", "AI", "创业"],
                "required": [
                    {"field": "position", "operator": "contains", "value": "技术"},
                    {"field": "company", "operator": "contains", "value": "科技"}
                ],
                "preferred": [
                    {"field": "location", "operator": "contains", "value": "北京"}
                ]
            }, ensure_ascii=False),
            0.6,  # 匹配阈值
            8,    # 优先级
            5,    # 每日推送上限
            "active"
        ))
        
        intent_id = cursor.lastrowid
        conn.commit()
        print(f"创建意图成功，ID: {intent_id}")
        
        # 2. 获取测试用户的联系人数量
        user_table = f"profiles_{test_user_id}"
        cursor.execute(f"""
            SELECT COUNT(*) FROM {user_table}
        """)
        count = cursor.fetchone()[0]
        print(f"\n2. 用户 {test_user_id} 有 {count} 个联系人")
        
        # 3. 执行意图匹配
        print(f"\n3. 执行意图匹配...")
        matches = intent_matcher.match_intent_with_profiles(intent_id, test_user_id)
        
        print(f"找到 {len(matches)} 个匹配的联系人:")
        for match in matches[:5]:  # 显示前5个
            print(f"  - {match['profile_name']} (匹配度: {match['score']:.2%})")
            print(f"    匹配条件: {', '.join(match['matched_conditions'][:3])}")
            print(f"    解释: {match['explanation']}")
        
        # 4. 测试反向匹配（联系人匹配所有意图）
        if count > 0:
            print(f"\n4. 测试联系人匹配所有意图...")
            cursor.execute(f"SELECT id FROM {user_table} LIMIT 1")
            profile_id = cursor.fetchone()[0]
            
            profile_matches = intent_matcher.match_profile_with_intents(profile_id, test_user_id)
            print(f"联系人 {profile_id} 匹配到 {len(profile_matches)} 个意图")
            for pm in profile_matches:
                print(f"  - 意图: {pm['intent_name']} (匹配度: {pm['score']:.2%})")
        
        # 5. 查看数据库中的匹配记录
        print(f"\n5. 查看保存的匹配记录...")
        cursor.execute("""
            SELECT COUNT(*) FROM intent_matches 
            WHERE user_id = ?
        """, (test_user_id,))
        match_count = cursor.fetchone()[0]
        print(f"数据库中保存了 {match_count} 条匹配记录")
        
        # 显示几条匹配记录
        cursor.execute("""
            SELECT m.*, i.name as intent_name
            FROM intent_matches m
            JOIN user_intents i ON m.intent_id = i.id
            WHERE m.user_id = ?
            ORDER BY m.match_score DESC
            LIMIT 5
        """, (test_user_id,))
        
        columns = [desc[0] for desc in cursor.description]
        for row in cursor.fetchmany(5):
            record = dict(zip(columns, row))
            print(f"  - 意图: {record['intent_name']}, 分数: {record['match_score']:.2%}")
        
        print("\n✅ 意图匹配系统测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    test_intent_matching()