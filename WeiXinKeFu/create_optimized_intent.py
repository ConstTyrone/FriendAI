#!/usr/bin/env python3
"""
创建优化的测试意图，提高匹配分数
"""

import sqlite3
import json
from datetime import datetime

def create_optimized_intent():
    """创建优化的测试意图"""
    conn = sqlite3.connect('user_profiles.db')
    cursor = conn.cursor()
    
    test_user = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    print("=" * 60)
    print("🎯 创建优化的测试意图")
    print("=" * 60)
    
    # 创建优化的意图 - 更少但更精准的关键词
    intent_name = "寻找科技行业决策者"
    intent_desc = "寻找在科技公司担任高级管理职位的决策者"
    
    # 优化的条件配置
    conditions = {
        # 减少关键词数量，提高匹配概率
        "keywords": ["科技", "总监", "AI"],  # 从7个减少到3个
        
        # 不设置必要条件（避免严格匹配失败）
        "required": [],
        
        # 设置更容易匹配的优选条件
        "preferred": [
            {"field": "position", "operator": "contains", "value": "总监"},
            {"field": "company", "operator": "contains", "value": "科"}  # 更宽泛的匹配
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
            0.3,  # 保持较低阈值
            'active',
            1,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        intent_id = cursor.lastrowid
        conn.commit()
        
        print(f"\n✅ 成功创建优化的测试意图!")
        print(f"   ID: {intent_id}")
        print(f"   名称: {intent_name}")
        print(f"   用户: {test_user}")
        print(f"   阈值: 0.3")
        print(f"   关键词: {conditions['keywords']} (只有3个)")
        
        print(f"\n📈 优化说明:")
        print("   1. 减少关键词数量（7→3），提高单个匹配的权重")
        print("   2. 使用更通用的关键词，增加匹配概率")
        print("   3. 不设必要条件，避免严格匹配失败")
        print("   4. 优选条件更宽泛，容易部分匹配")
        
        print(f"\n💡 预期效果:")
        print("   - 张里辰: 关键词匹配2/3（科技、AI），分数约0.5-0.6")
        print("   - 有'总监'职位的: 额外加分")
        print("   - 语义相似度会更高")
        
    except sqlite3.IntegrityError as e:
        print(f"\n❌ 创建失败: {e}")
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
        LIMIT 5
    """, (test_user,))
    
    intents = cursor.fetchall()
    if intents:
        for intent_id, name, status, threshold in intents:
            print(f"  - ID {intent_id}: {name} ({status}, 阈值: {threshold})")
    
    conn.close()

def analyze_matching_formula():
    """分析匹配公式"""
    print("\n" + "=" * 60)
    print("📊 匹配分数计算公式分析")
    print("=" * 60)
    
    print("""
AI模式下的权重分配:
- 语义相似度: 30%
- 关键词匹配: 30%  
- 必要条件: 25%
- 优选条件: 15%

问题分析:
1. 关键词太多时，匹配率低
   - 7个关键词，只匹配1个 = 14% × 30% = 4.2%贡献
   
2. 语义相似度有上限
   - 即使100%相似，也只贡献30%
   
优化策略:
1. 减少关键词数量（3-4个最佳）
2. 使用更通用的关键词
3. 合理设置优选条件
4. 避免设置过多必要条件
""")

if __name__ == "__main__":
    print("\n🚀 创建优化的意图\n")
    analyze_matching_formula()
    create_optimized_intent()
    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)