#!/usr/bin/env python
"""
为意图匹配系统添加向量存储支持
更新数据库表结构，添加embedding字段
"""

import sqlite3
import json
import sys
import os
from datetime import datetime

def add_vector_columns(db_path: str = "user_profiles.db"):
    """添加向量相关的列"""
    
    print("=" * 60)
    print("更新数据库以支持向量存储")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 为user_intents表添加向量字段
        print("\n1. 检查并更新user_intents表...")
        
        # 检查embedding列是否存在
        cursor.execute("PRAGMA table_info(user_intents)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'embedding' not in columns:
            print("   添加embedding列...")
            cursor.execute("""
                ALTER TABLE user_intents 
                ADD COLUMN embedding BLOB
            """)
            
        if 'embedding_model' not in columns:
            print("   添加embedding_model列...")
            cursor.execute("""
                ALTER TABLE user_intents 
                ADD COLUMN embedding_model TEXT DEFAULT 'text-embedding-v3'
            """)
            
        if 'embedding_updated_at' not in columns:
            print("   添加embedding_updated_at列...")
            cursor.execute("""
                ALTER TABLE user_intents 
                ADD COLUMN embedding_updated_at TIMESTAMP
            """)
            
        print("   ✓ user_intents表更新完成")
        
        # 2. 获取所有用户表并更新
        print("\n2. 更新用户画像表...")
        
        # 获取所有profiles_开头的表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
        """)
        user_tables = cursor.fetchall()
        
        for (table_name,) in user_tables:
            print(f"\n   处理表: {table_name}")
            
            # 检查表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [col[1] for col in cursor.fetchall()]
            
            # 添加向量相关字段
            if 'embedding' not in columns:
                print(f"      添加embedding列...")
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN embedding BLOB
                """)
                
            if 'embedding_model' not in columns:
                print(f"      添加embedding_model列...")
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN embedding_model TEXT DEFAULT 'text-embedding-v3'
                """)
                
            if 'embedding_updated_at' not in columns:
                print(f"      添加embedding_updated_at列...")
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN embedding_updated_at TIMESTAMP
                """)
                
            print(f"      ✓ {table_name}表更新完成")
        
        # 3. 更新intent_matches表
        print("\n3. 检查并更新intent_matches表...")
        
        cursor.execute("PRAGMA table_info(intent_matches)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'vector_similarity' not in columns:
            print("   添加vector_similarity列...")
            cursor.execute("""
                ALTER TABLE intent_matches 
                ADD COLUMN vector_similarity REAL DEFAULT 0.0
            """)
            
        if 'match_type' not in columns:
            print("   添加match_type列...")
            cursor.execute("""
                ALTER TABLE intent_matches 
                ADD COLUMN match_type TEXT DEFAULT 'rule'
            """)
            # match_type: 'rule'(规则匹配), 'vector'(向量匹配), 'hybrid'(混合匹配)
            
        print("   ✓ intent_matches表更新完成")
        
        # 4. 创建向量索引表（用于快速检索）
        print("\n4. 创建向量索引表...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vector_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,     -- 'intent' 或 'profile'
                entity_id INTEGER NOT NULL,     -- 关联的实体ID
                user_id TEXT NOT NULL,          -- 用户ID
                vector_hash TEXT,               -- 向量的哈希值（用于快速查找）
                dimension INTEGER DEFAULT 1536, -- 向量维度
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(entity_type, entity_id, user_id)
            )
        """)
        
        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vector_entity 
            ON vector_index(entity_type, user_id)
        """)
        
        print("   ✓ 向量索引表创建完成")
        
        # 提交更改
        conn.commit()
        
        # 5. 显示统计信息
        print("\n5. 数据库统计:")
        
        # 统计意图数量
        cursor.execute("SELECT COUNT(*) FROM user_intents")
        intent_count = cursor.fetchone()[0]
        print(f"   - 意图总数: {intent_count}")
        
        # 统计用户表数量
        print(f"   - 用户表数量: {len(user_tables)}")
        
        # 统计匹配记录
        cursor.execute("SELECT COUNT(*) FROM intent_matches")
        match_count = cursor.fetchone()[0]
        print(f"   - 匹配记录总数: {match_count}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ 数据库更新完成！")
        print("=" * 60)
        
        print("\n下一步:")
        print("1. 运行向量化初始化脚本: python scripts/initialize_vectors.py")
        print("2. 重启后端服务以启用AI增强匹配")
        print("3. 在小程序中测试新的匹配功能")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='为意图匹配系统添加向量存储支持')
    parser.add_argument('--db', default='user_profiles.db', help='数据库路径')
    
    args = parser.parse_args()
    
    # 检查数据库是否存在
    if not os.path.exists(args.db):
        print(f"❌ 数据库文件不存在: {args.db}")
        print("请先运行 create_intent_tables.py 创建基础表结构")
        sys.exit(1)
    
    # 执行更新
    success = add_vector_columns(args.db)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()