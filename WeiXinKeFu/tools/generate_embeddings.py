#!/usr/bin/env python3
"""
生成测试数据的向量embeddings
使向量匹配功能正常工作
"""

import asyncio
import json
import sqlite3
import pickle
import logging
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.vector_service import vector_service
from src.config.config import config

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def generate_intent_embeddings():
    """为所有意图生成向量embeddings"""
    
    print("\n" + "="*60)
    print("📝 生成意图向量embeddings")
    print("="*60)
    
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    # 获取所有意图
    cursor.execute("""
        SELECT id, user_id, name, description, conditions 
        FROM user_intents 
        WHERE status = 'active'
    """)
    
    intents = cursor.fetchall()
    print(f"找到 {len(intents)} 个活跃意图")
    
    success_count = 0
    for intent in intents:
        intent_id, user_id, name, description, conditions_str = intent
        
        try:
            # 解析条件
            conditions = json.loads(conditions_str) if conditions_str else {}
            
            # 构建意图文本表示
            intent_text = f"{name} {description or ''}"
            
            # 添加关键词
            keywords = conditions.get('keywords', [])
            if keywords:
                intent_text += " " + " ".join(keywords)
            
            # 添加条件描述
            required = conditions.get('required', [])
            for req in required:
                if 'value' in req:
                    intent_text += f" {req['value']}"
            
            preferred = conditions.get('preferred', [])
            for pref in preferred:
                if 'value' in pref:
                    intent_text += f" {pref['value']}"
            
            print(f"\n处理意图 {intent_id}: {name}")
            print(f"  文本: {intent_text[:100]}...")
            
            # 生成embedding
            embedding = await vector_service.generate_embedding(intent_text)
            
            if embedding and len(embedding) > 0:
                # 序列化embedding
                embedding_blob = pickle.dumps(embedding)
                
                # 更新数据库
                cursor.execute("""
                    UPDATE user_intents 
                    SET embedding = ? 
                    WHERE id = ?
                """, (embedding_blob, intent_id))
                
                print(f"  ✅ 向量生成成功 (维度: {len(embedding)})")
                success_count += 1
            else:
                print(f"  ❌ 向量生成失败")
                
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 成功生成 {success_count}/{len(intents)} 个意图的向量")
    return success_count

async def generate_profile_embeddings():
    """为所有联系人生成向量embeddings"""
    
    print("\n" + "="*60)
    print("👥 生成联系人向量embeddings")
    print("="*60)
    
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    # 真实用户ID
    user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    clean_user = ''.join(c if c.isalnum() or c == '_' else '_' for c in user_id)
    user_table = f"profiles_{clean_user}"
    
    # 获取所有联系人
    cursor.execute(f"""
        SELECT id, profile_name, gender, age, location, 
               education, company, position, tags, basic_info
        FROM {user_table}
    """)
    
    profiles = cursor.fetchall()
    print(f"找到 {len(profiles)} 个联系人")
    
    success_count = 0
    for profile in profiles:
        profile_id = profile[0]
        profile_name = profile[1]
        
        try:
            # 构建联系人文本表示
            profile_text_parts = []
            
            # 基本信息
            for value in profile[1:8]:  # profile_name到position
                if value and value != '未知':
                    profile_text_parts.append(str(value))
            
            # 标签
            if profile[8]:  # tags
                try:
                    tags = json.loads(profile[8])
                    if isinstance(tags, list):
                        profile_text_parts.extend(tags)
                except:
                    pass
            
            # basic_info
            if profile[9]:
                try:
                    basic_info = json.loads(profile[9])
                    if isinstance(basic_info, dict):
                        # 添加技能信息
                        if '技能' in basic_info:
                            skills = basic_info['技能']
                            if isinstance(skills, list):
                                profile_text_parts.extend(skills)
                        # 添加项目信息
                        if '项目' in basic_info:
                            profile_text_parts.append(str(basic_info['项目']))
                        # 添加经验信息
                        if '经验' in basic_info:
                            profile_text_parts.append(f"{basic_info['经验']}年经验")
                except:
                    pass
            
            profile_text = " ".join(profile_text_parts)
            
            print(f"\n处理联系人 {profile_id}: {profile_name}")
            print(f"  文本: {profile_text[:100]}...")
            
            # 生成embedding
            embedding = await vector_service.generate_embedding(profile_text)
            
            if embedding and len(embedding) > 0:
                # 序列化embedding
                embedding_blob = pickle.dumps(embedding)
                
                # 更新数据库
                cursor.execute(f"""
                    UPDATE {user_table}
                    SET embedding = ? 
                    WHERE id = ?
                """, (embedding_blob, profile_id))
                
                print(f"  ✅ 向量生成成功 (维度: {len(embedding)})")
                success_count += 1
            else:
                print(f"  ❌ 向量生成失败")
                
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 成功生成 {success_count}/{len(profiles)} 个联系人的向量")
    return success_count

async def verify_embeddings():
    """验证向量embeddings是否正确生成"""
    
    print("\n" + "="*60)
    print("🔍 验证向量embeddings")
    print("="*60)
    
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    # 检查意图embeddings
    cursor.execute("""
        SELECT COUNT(*), 
               COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END)
        FROM user_intents
        WHERE status = 'active'
    """)
    total_intents, intents_with_embedding = cursor.fetchone()
    
    print(f"\n意图向量状态:")
    print(f"  总数: {total_intents}")
    print(f"  有向量: {intents_with_embedding}")
    print(f"  覆盖率: {intents_with_embedding/total_intents*100:.1f}%")
    
    # 检查联系人embeddings
    user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    clean_user = ''.join(c if c.isalnum() or c == '_' else '_' for c in user_id)
    user_table = f"profiles_{clean_user}"
    
    cursor.execute(f"""
        SELECT COUNT(*), 
               COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END)
        FROM {user_table}
    """)
    total_profiles, profiles_with_embedding = cursor.fetchone()
    
    print(f"\n联系人向量状态:")
    print(f"  总数: {total_profiles}")
    print(f"  有向量: {profiles_with_embedding}")
    print(f"  覆盖率: {profiles_with_embedding/total_profiles*100:.1f}%")
    
    # 测试向量相似度计算
    if intents_with_embedding > 0 and profiles_with_embedding > 0:
        print("\n测试向量相似度计算...")
        
        # 获取一个意图和一个联系人的embedding
        cursor.execute("""
            SELECT id, name, embedding 
            FROM user_intents 
            WHERE embedding IS NOT NULL 
            LIMIT 1
        """)
        intent_data = cursor.fetchone()
        
        cursor.execute(f"""
            SELECT id, profile_name, embedding 
            FROM {user_table}
            WHERE embedding IS NOT NULL 
            LIMIT 1
        """)
        profile_data = cursor.fetchone()
        
        if intent_data and profile_data:
            intent_embedding = pickle.loads(intent_data[2])
            profile_embedding = pickle.loads(profile_data[2])
            
            # 计算相似度
            similarity = await vector_service.calculate_similarity(
                intent_embedding, 
                profile_embedding
            )
            
            print(f"  意图: {intent_data[1]}")
            print(f"  联系人: {profile_data[1]}")
            print(f"  相似度: {similarity:.3f}")
            
            if similarity > 0:
                print("  ✅ 向量相似度计算正常")
            else:
                print("  ⚠️ 相似度较低，可能需要优化")
    
    conn.close()

async def main():
    """主函数"""
    
    print("🚀 向量Embedding生成工具")
    print("="*60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key: {'✅ 已配置' if config.qwen_api_key else '❌ 未配置'}")
    
    if not config.qwen_api_key:
        print("\n❌ 错误: QWEN_API_KEY未配置")
        print("请设置环境变量: export QWEN_API_KEY=your_key")
        return
    
    # 初始化向量服务
    if not vector_service:
        print("\n❌ 错误: 向量服务未初始化")
        return
    
    print("\n开始生成向量embeddings...")
    
    # 1. 生成意图embeddings
    intent_count = await generate_intent_embeddings()
    
    # 2. 生成联系人embeddings
    profile_count = await generate_profile_embeddings()
    
    # 3. 验证embeddings
    await verify_embeddings()
    
    print("\n" + "="*60)
    print("✅ 向量生成完成！")
    print("="*60)
    print(f"""
总结:
  - 意图向量: {intent_count} 个
  - 联系人向量: {profile_count} 个
  
现在可以运行测试:
  python test_with_real_data.py
  
预期结果:
  - 传统向量模式应该能找到匹配
  - 可以对比向量vs混合匹配的效果
""")

if __name__ == "__main__":
    asyncio.run(main())