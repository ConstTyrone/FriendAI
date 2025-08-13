#!/usr/bin/env python3
"""
向量化初始化脚本
用于初始化意图和联系人的向量化数据
"""

import os
import sys
import sqlite3
import asyncio
import json
import pickle
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_embedding(text: str) -> Optional[List[float]]:
    """
    获取文本的向量表示
    
    Args:
        text: 要向量化的文本
        
    Returns:
        向量列表或None
    """
    try:
        from src.services.vector_service import vector_service
        return await vector_service.get_embedding(text)
    except Exception as e:
        logger.error(f"向量化失败: {e}")
        return None

async def initialize_vectors(db_path: str = "user_profiles.db", force: bool = False) -> bool:
    """
    初始化向量化数据
    
    Args:
        db_path: 数据库路径
        force: 是否强制重新生成所有向量
        
    Returns:
        是否成功
    """
    try:
        print("=" * 60)
        print("初始化向量化数据")
        print("=" * 60)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 向量化意图数据
        print("\n1. 向量化意图数据:")
        
        # 获取所有意图
        if force:
            cursor.execute("SELECT * FROM user_intents")
        else:
            cursor.execute("SELECT * FROM user_intents WHERE embedding IS NULL OR embedding_updated_at IS NULL")
        
        intent_rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        intent_success = 0
        for i, row in enumerate(intent_rows, 1):
            intent = dict(zip(columns, row))
            intent_id = intent['id']
            intent_name = intent['name']
            
            print(f"   处理意图 {i}/{len(intent_rows)}: {intent_name}")
            
            # 构建向量化文本
            vectorize_text = f"{intent['name']} {intent.get('description', '')}"
            if intent.get('conditions'):
                conditions = json.loads(intent['conditions'])
                if 'keywords' in conditions:
                    vectorize_text += " " + " ".join(conditions['keywords'])
            
            print(f"      向量化文本: {vectorize_text[:100]}...")
            
            # 获取向量
            embedding = await get_embedding(vectorize_text)
            if embedding:
                # 将向量序列化为二进制
                embedding_bytes = pickle.dumps(embedding)
                
                # 更新数据库
                cursor.execute("""
                    UPDATE user_intents 
                    SET embedding = ?, embedding_updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (embedding_bytes, intent_id))
                
                intent_success += 1
                print(f"      ✓ 成功")
            else:
                print(f"      ❌ 向量化失败")
                
            # 添加延迟避免API限流
            await asyncio.sleep(0.3)
        
        print(f"   ✓ 意图向量化完成: {intent_success}/{len(intent_rows)}")
        
        # 2. 向量化联系人数据
        print("\n2. 向量化联系人数据:")
        
        # 获取所有用户表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
        """)
        
        user_tables = [row[0] for row in cursor.fetchall()]
        total_profiles = 0
        total_success = 0
        
        for table_name in user_tables:
            print(f"   处理表: {table_name}")
            
            # 获取联系人数据
            if force:
                cursor.execute(f"SELECT * FROM {table_name}")
            else:
                cursor.execute(f"SELECT * FROM {table_name} WHERE embedding IS NULL OR embedding_updated_at IS NULL")
            
            profile_rows = cursor.fetchall()
            if not profile_rows:
                print(f"      无需向量化的联系人")
                continue
                
            # 获取列名
            cursor.execute(f"PRAGMA table_info({table_name})")
            profile_columns = [col[1] for col in cursor.fetchall()]
            
            table_success = 0
            for i, row in enumerate(profile_rows, 1):
                profile = dict(zip(profile_columns, row))
                profile_name = profile.get('profile_name', '未知')
                
                print(f"      联系人 {i}/{len(profile_rows)}: {profile_name}")
                
                try:
                    # 构建向量化文本
                    vectorize_parts = []
                    if profile.get('profile_name'):
                        vectorize_parts.append(profile['profile_name'])
                    
                    # 解析JSON字段
                    for json_field in ['basic_info', 'tags']:
                        if profile.get(json_field):
                            try:
                                data = json.loads(profile[json_field])
                                if isinstance(data, dict):
                                    vectorize_parts.extend([str(v) for v in data.values() if v])
                                elif isinstance(data, list):
                                    vectorize_parts.extend([str(item) for item in data if item])
                            except:
                                vectorize_parts.append(str(profile[json_field]))
                    
                    vectorize_text = " ".join(vectorize_parts)
                    if not vectorize_text.strip():
                        print(f"         ❌ 无有效文本")
                        continue
                    
                    print(f"         向量化文本: {vectorize_text[:50]}...")
                    
                    # 获取向量
                    embedding = await get_embedding(vectorize_text)
                    if embedding:
                        # 将向量序列化为二进制
                        embedding_bytes = pickle.dumps(embedding)
                        
                        # 更新联系人表
                        cursor.execute(f"""
                            UPDATE {table_name}
                            SET embedding = ?, 
                                embedding_model = 'text-embedding-v3',
                                embedding_updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (embedding_bytes, profile['id']))
                        
                        # 提取用户ID
                        user_id = table_name.replace('profiles_', '')
                        
                        # 更新向量索引表
                        cursor.execute("""
                            INSERT OR REPLACE INTO vector_index 
                            (entity_type, entity_id, user_id, vector_hash, dimension)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            'profile',
                            profile['id'], 
                            user_id,
                            str(hash(str(embedding))),
                            len(embedding)
                        ))
                        
                        table_success += 1
                        total_success += 1
                        print(f"         ✓ 成功")
                        
                        # 每处理5个联系人提交一次
                        if i % 5 == 0:
                            conn.commit()
                    else:
                        print(f"         ❌ 向量化失败")
                        
                except Exception as e:
                    print(f"         ❌ 错误: {e}")
                    
                # 添加延迟避免API限流
                await asyncio.sleep(0.3)
            
            total_profiles += len(profile_rows)
            print(f"      ✓ 表 {table_name} 完成: {table_success}/{len(profile_rows)}")
        
        print(f"   ✓ 联系人向量化完成: {total_success}/{total_profiles}")
        
        # 提交所有更改
        conn.commit()
        
        # 3. 显示统计信息
        print("\n3. 向量化统计:")
        
        # 意图向量统计
        cursor.execute("SELECT COUNT(*) FROM user_intents WHERE embedding IS NOT NULL")
        vectorized_intents = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM user_intents")
        total_intents = cursor.fetchone()[0]
        print(f"   - 已向量化意图: {vectorized_intents}/{total_intents}")
        
        # 联系人向量统计
        cursor.execute("SELECT COUNT(*) FROM vector_index WHERE entity_type = 'profile'")
        vectorized_profiles = cursor.fetchone()[0]
        print(f"   - 已向量化联系人: {vectorized_profiles}")
        
        # 向量索引统计
        cursor.execute("SELECT COUNT(*) FROM vector_index")
        total_vectors = cursor.fetchone()[0]
        print(f"   - 向量索引总数: {total_vectors}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ 向量化初始化完成！")
        print("=" * 60)
        
        print("\n下一步:")
        print("1. 重启后端服务: python run.py")
        print("2. 在小程序中创建新意图测试AI匹配")
        print("3. 查看匹配结果页面的语义相似度评分")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 向量化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='初始化向量化数据')
    parser.add_argument('--db', default='user_profiles.db', help='数据库路径')
    parser.add_argument('--force', action='store_true', help='强制重新生成所有向量')
    
    args = parser.parse_args()
    
    # 检查数据库是否存在
    if not os.path.exists(args.db):
        print(f"❌ 数据库文件不存在: {args.db}")
        print("请先运行 create_intent_tables.py 创建基础表结构")
        sys.exit(1)
    
    # 检查是否已添加向量字段
    conn = sqlite3.connect(args.db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(user_intents)")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()
    
    if 'embedding' not in columns:
        print("❌ 数据库尚未支持向量存储")
        print("请先运行: python scripts/add_vector_columns.py")
        sys.exit(1)
    
    # 执行向量化
    success = asyncio.run(initialize_vectors(args.db, args.force))
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()