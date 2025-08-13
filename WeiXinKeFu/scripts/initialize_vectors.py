#!/usr/bin/env python
"""
向量化初始化脚本
为现有的意图和联系人生成向量
"""

import asyncio
import sqlite3
import json
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def initialize_vectors(db_path: str = "user_profiles.db", force_update: bool = False):
    """初始化所有向量"""
    
    print("=" * 60)
    print("AI增强匹配 - 向量化初始化")
    print("=" * 60)
    
    try:
        from src.services.vector_service import VectorService
    except ImportError as e:
        print(f"❌ 无法导入向量服务: {e}")
        print("请确保已安装所有依赖: pip install -r requirements.txt")
        return False
    
    # 检查API密钥
    import os
    if not os.getenv('QWEN_API_KEY'):
        print("❌ 未设置QWEN_API_KEY环境变量")
        print("请在.env文件中设置您的通义千问API密钥")
        return False
    
    async with VectorService() as vector_service:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. 向量化所有意图
            print("\n1. 向量化用户意图...")
            
            # 获取所有意图（或需要更新的意图）
            if force_update:
                cursor.execute("SELECT * FROM user_intents")
            else:
                cursor.execute("SELECT * FROM user_intents WHERE embedding IS NULL")
            
            intent_rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            print(f"   找到 {len(intent_rows)} 个需要向量化的意图")
            
            success_count = 0
            for i, row in enumerate(intent_rows, 1):
                intent = dict(zip(columns, row))
                print(f"   处理意图 {i}/{len(intent_rows)}: {intent['name']}")
                
                try:
                    # 生成向量
                    embedding = await vector_service.vectorize_intent(intent)
                    
                    if embedding:
                        # 转换为bytes存储
                        import pickle
                        embedding_bytes = pickle.dumps(embedding)
                        
                        # 更新数据库
                        cursor.execute("""
                            UPDATE user_intents 
                            SET embedding = ?, 
                                embedding_model = 'text-embedding-v3',
                                embedding_updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (embedding_bytes, intent['id']))
                        
                        # 更新向量索引表
                        cursor.execute("""
                            INSERT OR REPLACE INTO vector_index 
                            (entity_type, entity_id, user_id, vector_hash, dimension)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            'intent',
                            intent['id'], 
                            intent['user_id'],
                            str(hash(str(embedding))),
                            len(embedding)
                        ))
                        
                        success_count += 1
                        print(f"      ✓ 成功")
                        
                        # 每处理5个意图提交一次，避免丢失数据
                        if i % 5 == 0:
                            conn.commit()
                    else:
                        print(f"      ❌ 向量化失败")
                        
                except Exception as e:
                    print(f"      ❌ 错误: {e}")
                    
                # 添加延迟避免API限流
                await asyncio.sleep(0.5)
            
            print(f"   ✓ 意图向量化完成: {success_count}/{len(intent_rows)}")
            
            # 2. 向量化所有联系人
            print("\n2. 向量化用户联系人...")
            
            # 获取所有用户表
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE 'profiles_%'
            """)
            user_tables = cursor.fetchall()
            
            total_profiles = 0
            total_success = 0
            
            for (table_name,) in user_tables:
                print(f"\n   处理表: {table_name}")
                
                # 获取需要向量化的联系人
                if force_update:
                    cursor.execute(f"SELECT * FROM {table_name}")
                else:
                    cursor.execute(f"SELECT * FROM {table_name} WHERE embedding IS NULL")
                
                profile_rows = cursor.fetchall()
                if not profile_rows:
                    print("      无需处理的联系人")
                    continue
                
                columns = [desc[0] for desc in cursor.description]
                print(f"      找到 {len(profile_rows)} 个需要向量化的联系人")
                
                table_success = 0
                for i, row in enumerate(profile_rows, 1):
                    profile = dict(zip(columns, row))
                    name = profile.get('profile_name', profile.get('name', f'ID-{profile["id"]}'))
                    print(f"      处理联系人 {i}/{len(profile_rows)}: {name}")
                    
                    try:
                        # 生成向量
                        embedding = await vector_service.vectorize_profile(profile)
                        
                        if embedding:
                            # 转换为bytes存储
                            embedding_bytes = pickle.dumps(embedding)
                            
                            # 更新数据库
                            cursor.execute(f"""
                                UPDATE {table_name}
                                SET embedding = ?, 
                                    embedding_model = 'text-embedding-v3',
                                    embedding_updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """, (embedding_bytes, profile['id']))
                            
                            # 提取用户ID
                            user_id = table_name.replace('profiles_', '')\n                            \n                            # 更新向量索引表\n                            cursor.execute(\"\"\"\n                                INSERT OR REPLACE INTO vector_index \n                                (entity_type, entity_id, user_id, vector_hash, dimension)\n                                VALUES (?, ?, ?, ?, ?)\n                            \"\"\", (\n                                'profile',\n                                profile['id'], \n                                user_id,\n                                str(hash(str(embedding))),\n                                len(embedding)\n                            ))\n                            \n                            table_success += 1\n                            total_success += 1\n                            print(f\"         ✓ 成功\")\n                            \n                            # 每处理5个联系人提交一次\n                            if i % 5 == 0:\n                                conn.commit()\n                        else:\n                            print(f\"         ❌ 向量化失败\")\n                            \n                    except Exception as e:\n                        print(f\"         ❌ 错误: {e}\")\n                        \n                    # 添加延迟避免API限流\n                    await asyncio.sleep(0.3)\n                \n                total_profiles += len(profile_rows)\n                print(f\"      ✓ 表 {table_name} 完成: {table_success}/{len(profile_rows)}\")\n            \n            print(f\"   ✓ 联系人向量化完成: {total_success}/{total_profiles}\")\n            \n            # 提交所有更改\n            conn.commit()\n            \n            # 3. 显示统计信息\n            print(\"\\n3. 向量化统计:\")\n            \n            # 意图向量统计\n            cursor.execute(\"SELECT COUNT(*) FROM user_intents WHERE embedding IS NOT NULL\")\n            vectorized_intents = cursor.fetchone()[0]\n            cursor.execute(\"SELECT COUNT(*) FROM user_intents\")\n            total_intents = cursor.fetchone()[0]\n            print(f\"   - 已向量化意图: {vectorized_intents}/{total_intents}\")\n            \n            # 联系人向量统计\n            cursor.execute(\"SELECT COUNT(*) FROM vector_index WHERE entity_type = 'profile'\")\n            vectorized_profiles = cursor.fetchone()[0]\n            print(f\"   - 已向量化联系人: {vectorized_profiles}\")\n            \n            # 向量索引统计\n            cursor.execute(\"SELECT COUNT(*) FROM vector_index\")\n            total_vectors = cursor.fetchone()[0]\n            print(f\"   - 向量索引总数: {total_vectors}\")\n            \n            conn.close()\n            \n            print(\"\\n\" + \"=\" * 60)\n            print(\"✅ 向量化初始化完成！\")\n            print(\"=\" * 60)\n            \n            print(\"\\n下一步:\")\n            print(\"1. 重启后端服务: python run.py\")\n            print(\"2. 在小程序中创建新意图测试AI匹配\")\n            print(\"3. 查看匹配结果页面的语义相似度评分\")\n            \n            return True\n            \n        except Exception as e:\n            print(f\"\\n❌ 向量化失败: {e}\")\n            import traceback\n            traceback.print_exc()\n            return False\n\ndef main():\n    \"\"\"主函数\"\"\"\n    import argparse\n    \n    parser = argparse.ArgumentParser(description='初始化向量化数据')\n    parser.add_argument('--db', default='user_profiles.db', help='数据库路径')\n    parser.add_argument('--force', action='store_true', help='强制重新生成所有向量')\n    \n    args = parser.parse_args()\n    \n    # 检查数据库是否存在\n    if not os.path.exists(args.db):\n        print(f\"❌ 数据库文件不存在: {args.db}\")\n        print(\"请先运行 create_intent_tables.py 创建基础表结构\")\n        sys.exit(1)\n    \n    # 检查是否已添加向量字段\n    conn = sqlite3.connect(args.db)\n    cursor = conn.cursor()\n    cursor.execute(\"PRAGMA table_info(user_intents)\")\n    columns = [col[1] for col in cursor.fetchall()]\n    conn.close()\n    \n    if 'embedding' not in columns:\n        print(\"❌ 数据库尚未支持向量存储\")\n        print(\"请先运行: python scripts/add_vector_columns.py\")\n        sys.exit(1)\n    \n    # 执行向量化\n    success = asyncio.run(initialize_vectors(args.db, args.force))\n    \n    if not success:\n        sys.exit(1)\n\nif __name__ == \"__main__\":\n    main()