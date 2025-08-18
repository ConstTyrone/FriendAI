#!/usr/bin/env python3
"""
AI匹配诊断脚本
用于检查为什么AI匹配返回0结果
"""

import os
import sys
import json
import sqlite3
import asyncio
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 加载环境变量
load_dotenv()

async def test_ai_matching():
    """测试AI匹配功能"""
    print("\n" + "="*60)
    print("🔍 AI匹配诊断工具")
    print("="*60)
    
    # 1. 检查环境配置
    print("\n1️⃣ 检查环境配置")
    print("-" * 40)
    
    api_key = os.getenv('QWEN_API_KEY')
    if api_key:
        print(f"✅ QWEN_API_KEY已配置: {api_key[:10]}...{api_key[-5:]}")
    else:
        print("❌ QWEN_API_KEY未配置")
        print("   请在.env文件中设置: QWEN_API_KEY=你的密钥")
        return
    
    # 2. 检查依赖
    print("\n2️⃣ 检查依赖包")
    print("-" * 40)
    
    try:
        import numpy
        print("✅ NumPy已安装")
    except ImportError:
        print("❌ NumPy未安装 - 请运行: pip install numpy")
        return
    
    try:
        import aiohttp
        print("✅ AioHTTP已安装")
    except ImportError:
        print("❌ AioHTTP未安装 - 请运行: pip install aiohttp")
        return
    
    # 3. 初始化匹配引擎
    print("\n3️⃣ 初始化匹配引擎")
    print("-" * 40)
    
    try:
        from src.services.intent_matcher import IntentMatcher
        matcher = IntentMatcher(use_ai=True)
        
        if matcher.use_ai and matcher.vector_service:
            print("✅ AI匹配引擎已启用")
            print(f"   向量服务: {matcher.vector_service.__class__.__name__}")
        else:
            print("❌ AI匹配引擎未启用")
            print(f"   use_ai={matcher.use_ai}")
            print(f"   vector_service={matcher.vector_service}")
            return
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. 检查意图的详情
    print("\n4️⃣ 检查意图配置")
    print("-" * 40)
    
    # 使用新创建的意图12
    intent_id = 12  # 可以通过参数传入
    
    try:
        conn = sqlite3.connect('user_profiles.db')
        cursor = conn.cursor()
        
        # 查询意图
        cursor.execute("""
            SELECT id, name, description, conditions, status, threshold, user_id
            FROM user_intents 
            WHERE id = ?
        """, (intent_id,))
        
        intent_row = cursor.fetchone()
        if intent_row:
            intent_id, name, desc, conditions_str, status, threshold, intent_user_id = intent_row
            print(f"✅ 找到意图{intent_id}: {name}")
            print(f"   所属用户: {intent_user_id}")
            print(f"   状态: {status}")
            print(f"   阈值: {threshold}")
            print(f"   描述: {desc[:50]}..." if desc and len(desc) > 50 else f"   描述: {desc}")
            
            # 解析条件
            try:
                conditions = json.loads(conditions_str) if conditions_str else {}
                keywords = conditions.get('keywords', [])
                required = conditions.get('required', [])
                preferred = conditions.get('preferred', [])
                
                print(f"\n   条件配置:")
                print(f"   - 关键词: {keywords}")
                print(f"   - 必要条件: {len(required)} 个")
                print(f"   - 优选条件: {len(preferred)} 个")
                
                if not keywords and not required and not preferred:
                    print("   ⚠️ 警告: 没有配置任何匹配条件!")
            except Exception as e:
                print(f"   ❌ 解析条件失败: {e}")
        else:
            print(f"❌ 意图{intent_id}不存在")
            
            # 列出所有意图
            cursor.execute("SELECT id, name, status FROM user_intents ORDER BY id")
            intents = cursor.fetchall()
            if intents:
                print("\n可用的意图:")
                for intent_id, name, status in intents:
                    print(f"   - ID {intent_id}: {name} ({status})")
            conn.close()
            return
        
        # 5. 检查用户联系人
        print("\n5️⃣ 检查用户联系人")
        print("-" * 40)
        
        # 使用指定的测试用户ID
        user_id = 'wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q'
        # 清理用户ID中的特殊字符（与intent_matcher一致）
        clean_id = ''.join(c if c.isalnum() or c == '_' else '_' for c in user_id)
        user_table = f"profiles_{clean_id}"
        
        print(f"   原始用户ID: {user_id}")
        print(f"   清理后ID: {clean_id}")
        print(f"   表名: {user_table}")
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (user_table,))
        
        if cursor.fetchone()[0] > 0:
            cursor.execute(f"SELECT COUNT(*) FROM {user_table}")
            count = cursor.fetchone()[0]
            print(f"✅ 用户表存在: {user_table}")
            print(f"   联系人数量: {count}")
            
            if count > 0:
                # 显示前3个联系人
                cursor.execute(f"SELECT id, profile_name, company, position FROM {user_table} LIMIT 3")
                profiles = cursor.fetchall()
                print("\n   示例联系人:")
                for p_id, p_name, company, position in profiles:
                    print(f"   - {p_name}: {company} {position}")
        else:
            print(f"❌ 用户表不存在: {user_table}")
            conn.close()
            return
        
        conn.close()
        
        # 6. 测试AI向量服务
        print("\n6️⃣ 测试AI向量服务")
        print("-" * 40)
        
        from src.services.vector_service import VectorService
        vector_service = VectorService()
        
        if not vector_service.api_key:
            print("❌ 向量服务未配置API密钥")
            return
        
        print("测试文本向量化...")
        test_text = "AI技术专家，需要有深度学习经验"
        
        try:
            embedding = await vector_service.get_embedding(test_text)
            if embedding:
                print(f"✅ 向量化成功")
                print(f"   向量维度: {len(embedding)}")
                print(f"   前5个值: {embedding[:5]}")
            else:
                print("❌ 向量化失败，返回None")
                print("   可能原因:")
                print("   1. API密钥无效")
                print("   2. 网络连接问题")
                print("   3. API配额用完")
        except Exception as e:
            print(f"❌ 向量化出错: {e}")
            import traceback
            traceback.print_exc()
        
        # 7. 执行完整匹配测试
        print("\n7️⃣ 执行完整匹配测试")
        print("-" * 40)
        
        print(f"开始匹配意图{intent_id}与用户 {user_id} 的联系人...")
        
        try:
            matches = await matcher.match_intent_with_profiles(intent_id, user_id)
            
            print(f"\n匹配结果: 找到 {len(matches)} 个匹配")
            
            if matches:
                print("\n匹配详情:")
                for i, match in enumerate(matches[:3], 1):
                    print(f"\n  匹配 {i}:")
                    print(f"    联系人: {match.get('profile_name')}")
                    print(f"    分数: {match.get('score', 0):.2f}")
                    print(f"    条件: {match.get('matched_conditions')}")
                    print(f"    解释: {match.get('explanation')}")
            else:
                print("\n⚠️ 没有找到匹配的联系人")
                print("\n可能的原因:")
                print("1. 意图没有配置关键词或条件")
                print("2. 联系人信息不满足条件")
                print("3. 匹配阈值设置过高")
                print("4. AI向量化失败，且规则匹配也失败")
                
        except Exception as e:
            print(f"❌ 匹配执行失败: {e}")
            import traceback
            traceback.print_exc()
    
    except Exception as e:
        print(f"❌ 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理向量服务的session
        if 'vector_service' in locals():
            if hasattr(vector_service, 'session') and vector_service.session:
                await vector_service.session.close()

def main():
    """主函数"""
    print("\n🚀 启动AI匹配诊断...\n")
    
    # 运行异步测试
    asyncio.run(test_ai_matching())
    
    print("\n" + "="*60)
    print("诊断完成")
    print("="*60)
    
    print("\n📋 建议的修复步骤:")
    print("1. 确保意图配置了关键词或条件")
    print("2. 确保联系人信息完整")
    print("3. 检查匹配阈值是否合理（建议0.3-0.7）")
    print("4. 查看后端日志了解详细错误")
    print("5. 如果API调用失败，检查网络和API密钥")

if __name__ == "__main__":
    main()