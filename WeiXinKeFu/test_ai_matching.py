#!/usr/bin/env python
"""
AI增强匹配功能测试脚本
验证向量化和语义相似度匹配
"""

import asyncio
import sqlite3
import json
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_setup():
    """测试基础设置和数据库结构"""
    print("=" * 60)
    print("测试AI增强匹配系统")
    print("=" * 60)
    
    # 检查数据库
    db_path = "user_profiles.db"
    if not os.path.exists(db_path):
        print("❌ 数据库文件不存在，请先运行 create_intent_tables.py")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n1. 检查数据库表结构...")
    
    # 检查user_intents表
    cursor.execute("PRAGMA table_info(user_intents)")
    columns = [col[1] for col in cursor.fetchall()]
    
    required_columns = ['embedding', 'embedding_model', 'embedding_updated_at']
    missing_columns = [col for col in required_columns if col not in columns]
    
    if missing_columns:
        print(f"❌ user_intents表缺少向量字段: {missing_columns}")
        print("请运行: python scripts/add_vector_columns.py")
        conn.close()
        return False
    
    print("   ✓ user_intents表结构正确")
    
    # 检查向量索引表
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='vector_index'
    """)
    
    if not cursor.fetchone():
        print("❌ vector_index表不存在")
        print("请运行: python scripts/add_vector_columns.py")
        conn.close()
        return False
    
    print("   ✓ vector_index表存在")
    
    # 检查API密钥
    if not os.getenv('QWEN_API_KEY'):
        print("❌ 未设置QWEN_API_KEY环境变量")
        print("请在.env文件中设置您的通义千问API密钥")
        conn.close()
        return False
    
    print("   ✓ API密钥已配置")
    
    conn.close()
    return True

async def test_vector_service():
    """测试向量服务"""
    print("\n2. 测试向量服务...")
    
    try:
        from src.services.vector_service import VectorService
        
        async with VectorService() as vector_service:
            # 测试简单文本向量化
            test_text = "寻找AI技术专家，擅长机器学习，有创业经验"
            embedding = await vector_service.get_embedding(test_text)
            
            if embedding and len(embedding) > 0:
                print(f"   ✓ 文本向量化成功，维度: {len(embedding)}")
                
                # 测试相似度计算
                test_text2 = "需要机器学习专家，有人工智能背景"
                embedding2 = await vector_service.get_embedding(test_text2)
                
                if embedding2:
                    similarity = vector_service.calculate_similarity(embedding, embedding2)
                    print(f"   ✓ 相似度计算成功: {similarity:.3f}")
                    
                    if similarity > 0.5:
                        print(f"   ✓ 相似文本检测正确 (相似度: {similarity:.1%})")
                    else:
                        print(f"   ⚠️ 相似度偏低: {similarity:.1%}")
                else:
                    print("   ❌ 第二个文本向量化失败")
                    return False
            else:
                print("   ❌ 文本向量化失败")
                return False
                
        return True
        
    except ImportError as e:
        print(f"   ❌ 无法导入向量服务: {e}")
        return False
    except Exception as e:
        print(f"   ❌ 向量服务测试失败: {e}")
        return False

async def test_intent_vectorization():
    """测试意图向量化"""
    print("\n3. 测试意图向量化...")
    
    try:
        from src.services.vector_service import VectorService
        
        # 创建测试意图
        test_intent = {
            'id': 999,
            'name': '寻找技术合伙人',
            'description': '寻找有AI技术背景的创业合伙人，最好在北京或上海',
            'conditions': {
                'keywords': ['AI', '人工智能', '机器学习', '创业'],
                'required': [
                    {'field': 'position', 'operator': 'contains', 'value': 'CTO'}
                ],
                'preferred': [
                    {'field': 'location', 'operator': 'in', 'value': ['北京', '上海']}
                ]
            }
        }
        
        async with VectorService() as vector_service:
            embedding = await vector_service.vectorize_intent(test_intent)
            
            if embedding and len(embedding) > 0:
                print(f"   ✓ 意图向量化成功，维度: {len(embedding)}")
                return True
            else:
                print("   ❌ 意图向量化失败")
                return False
                
    except Exception as e:
        print(f"   ❌ 意图向量化测试失败: {e}")
        return False

async def test_profile_vectorization():
    """测试联系人画像向量化"""
    print("\n4. 测试联系人画像向量化...")
    
    try:
        from src.services.vector_service import VectorService
        
        # 创建测试联系人
        test_profile = {
            'id': 999,
            'profile_name': '张三',
            'gender': '男',
            'age': '30',
            'company': 'AI科技公司',
            'position': 'CTO',
            'location': '北京',
            'education': '清华大学',
            'ai_summary': '技术专家，有10年AI开发经验，曾创办过科技公司'
        }
        
        async with VectorService() as vector_service:
            embedding = await vector_service.vectorize_profile(test_profile)
            
            if embedding and len(embedding) > 0:
                print(f"   ✓ 联系人向量化成功，维度: {len(embedding)}")
                return True
            else:
                print("   ❌ 联系人向量化失败")
                return False
                
    except Exception as e:
        print(f"   ❌ 联系人向量化测试失败: {e}")
        return False

async def test_semantic_matching():
    """测试语义匹配"""
    print("\n5. 测试语义匹配...")
    
    try:
        from src.services.vector_service import VectorService
        
        # 创建测试数据
        intent = {
            'name': '寻找技术合伙人',
            'description': '需要有AI技术背景的创业伙伴',
            'conditions': {
                'keywords': ['AI', '机器学习', '创业']
            }
        }
        
        profile = {
            'profile_name': '李四',
            'company': '人工智能研究院',
            'position': '研究员',
            'ai_summary': '专注机器学习算法研究，有创业想法'
        }
        
        async with VectorService() as vector_service:
            similarity, explanation = await vector_service.calculate_semantic_similarity(
                intent, profile, use_cache=False
            )
            
            if similarity > 0:
                print(f"   ✓ 语义匹配成功，相似度: {similarity:.1%}")
                print(f"   解释: {explanation}")
                return True
            else:
                print(f"   ❌ 语义匹配失败: {explanation}")
                return False
                
    except Exception as e:
        print(f"   ❌ 语义匹配测试失败: {e}")
        return False

def test_ai_enhanced_matcher():
    """测试AI增强匹配引擎"""
    print("\n6. 测试AI增强匹配引擎...")
    
    try:
        from src.services.intent_matcher import IntentMatcher
        
        # 创建AI增强匹配器
        matcher = IntentMatcher(use_ai=True)
        
        # 检查AI是否启用
        if matcher.use_ai and matcher.vector_service:
            print("   ✓ AI增强匹配引擎已启用")
            print(f"   向量服务: {type(matcher.vector_service).__name__}")
            return True
        else:
            print("   ❌ AI增强匹配引擎未启用，使用基础模式")
            return False
            
    except Exception as e:
        print(f"   ❌ AI增强匹配引擎测试失败: {e}")
        return False

async def test_full_matching_pipeline():
    """测试完整匹配流程"""
    print("\n7. 测试完整匹配流程...")
    
    try:
        conn = sqlite3.connect("user_profiles.db")
        cursor = conn.cursor()
        
        # 创建测试用户数据
        test_user_id = "test_ai_user"
        test_table = f"profiles_{test_user_id}"
        
        # 清理之前的测试数据
        cursor.execute(f"DROP TABLE IF EXISTS {test_table}")
        cursor.execute("DELETE FROM user_intents WHERE user_id = ?", (test_user_id,))
        
        # 创建测试用户表
        cursor.execute(f"""
            CREATE TABLE {test_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT NOT NULL,
                company TEXT,
                position TEXT,
                location TEXT,
                ai_summary TEXT,
                embedding BLOB,
                embedding_model TEXT DEFAULT 'text-embedding-v3',
                embedding_updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 插入测试联系人
        cursor.execute(f"""
            INSERT INTO {test_table} 
            (profile_name, company, position, location, ai_summary)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "张三", "AI科技公司", "CTO", "北京", 
            "技术专家，有10年AI开发经验，曾创办过科技公司"
        ))
        
        profile_id = cursor.lastrowid
        
        # 创建测试意图
        cursor.execute("""
            INSERT INTO user_intents 
            (user_id, name, description, conditions, threshold)
            VALUES (?, ?, ?, ?, ?)
        """, (
            test_user_id,
            "寻找技术合伙人",
            "寻找有AI技术背景的创业合伙人",
            json.dumps({
                'keywords': ['AI', '技术', '创业', 'CTO'],
                'required': [
                    {'field': 'position', 'operator': 'contains', 'value': 'CTO'}
                ]
            }, ensure_ascii=False),
            0.6
        ))
        
        intent_id = cursor.lastrowid
        conn.commit()
        
        # 导入AI增强匹配引擎
        from src.services.intent_matcher import intent_matcher
        
        # 执行匹配
        matches = intent_matcher.match_intent_with_profiles(intent_id, test_user_id)
        
        if matches and len(matches) > 0:
            match = matches[0]
            print(f"   ✓ 匹配成功，找到 {len(matches)} 个结果")
            print(f"   最佳匹配: {match['profile_name']}")
            print(f"   匹配分数: {match['score']:.1%}")
            print(f"   解释: {match['explanation']}")
            
            # 检查是否使用了AI
            if hasattr(intent_matcher, 'use_ai') and intent_matcher.use_ai:
                print("   ✓ 使用了AI增强匹配")
            else:
                print("   ⚠️ 使用了基础匹配模式")
            
            success = True
        else:
            print("   ❌ 匹配失败，未找到结果")
            success = False
        
        # 清理测试数据
        cursor.execute(f"DROP TABLE IF EXISTS {test_table}")
        cursor.execute("DELETE FROM user_intents WHERE user_id = ?", (test_user_id,))
        cursor.execute("DELETE FROM intent_matches WHERE user_id = ?", (test_user_id,))
        conn.commit()
        conn.close()
        
        return success
        
    except Exception as e:
        print(f"   ❌ 完整匹配流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("\n🚀 开始AI增强匹配功能测试\n")
    
    test_results = []
    
    # 基础设置测试
    test_results.append(("基础设置", test_basic_setup()))
    
    # 异步测试
    async_tests = [
        ("向量服务", test_vector_service()),
        ("意图向量化", test_intent_vectorization()),
        ("联系人向量化", test_profile_vectorization()),
        ("语义匹配", test_semantic_matching()),
        ("完整匹配流程", test_full_matching_pipeline())
    ]
    
    for name, coro in async_tests:
        try:
            result = await coro
            test_results.append((name, result))
        except Exception as e:
            print(f"   ❌ {name}测试异常: {e}")
            test_results.append((name, False))
    
    # 同步测试
    test_results.append(("AI增强引擎", test_ai_enhanced_matcher()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:<15} {status}")
        if result:
            passed += 1
    
    print(f"\n总结: {passed}/{total} 项测试通过 ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 所有测试通过！AI增强匹配功能正常工作")
        print("\n下一步:")
        print("1. 运行数据库迁移: python scripts/add_vector_columns.py")
        print("2. 初始化向量数据: python scripts/initialize_vectors.py")
        print("3. 启动后端服务: python run.py")
        print("4. 在小程序中测试AI增强匹配功能")
    else:
        print("\n⚠️ 部分测试失败，请检查配置和环境")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)