#!/usr/bin/env python3
"""
修复所有用户profiles表中缺少tags列的问题
"""

import sqlite3
import json
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_missing_tags_column(db_path: str = "user_profiles.db"):
    """
    为所有用户的profiles表添加缺失的tags列
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("🔧 修复数据库中缺少tags列的问题")
    print("=" * 60)
    
    try:
        # 1. 获取所有的profiles表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
        """)
        
        tables = cursor.fetchall()
        
        if not tables:
            print("❌ 没有找到任何profiles表")
            return
        
        print(f"\n📊 找到 {len(tables)} 个用户表需要检查")
        
        fixed_count = 0
        skipped_count = 0
        error_count = 0
        
        for (table_name,) in tables:
            try:
                # 检查表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                # 检查是否已有tags列
                if 'tags' in column_names:
                    logger.info(f"✓ {table_name} 已有tags列，跳过")
                    skipped_count += 1
                    continue
                
                # 添加tags列
                logger.info(f"🔧 为 {table_name} 添加tags列...")
                
                # 添加tags列（JSON数组格式）
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN tags TEXT DEFAULT '[]'
                """)
                
                # 验证添加成功
                cursor.execute(f"PRAGMA table_info({table_name})")
                new_columns = cursor.fetchall()
                new_column_names = [col[1] for col in new_columns]
                
                if 'tags' in new_column_names:
                    logger.info(f"✅ {table_name} 成功添加tags列")
                    fixed_count += 1
                    
                    # 为现有记录设置默认值
                    cursor.execute(f"""
                        UPDATE {table_name} 
                        SET tags = '[]' 
                        WHERE tags IS NULL
                    """)
                else:
                    logger.error(f"❌ {table_name} 添加tags列失败")
                    error_count += 1
                    
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    logger.info(f"ℹ️ {table_name} 已有tags列（检测到重复列）")
                    skipped_count += 1
                else:
                    logger.error(f"❌ 处理 {table_name} 时出错: {e}")
                    error_count += 1
            except Exception as e:
                logger.error(f"❌ 处理 {table_name} 时出现未知错误: {e}")
                error_count += 1
        
        # 提交更改
        conn.commit()
        
        # 打印统计
        print("\n" + "=" * 60)
        print("📊 修复统计")
        print("=" * 60)
        print(f"✅ 成功修复: {fixed_count} 个表")
        print(f"⏭️ 跳过（已有tags列）: {skipped_count} 个表")
        print(f"❌ 失败: {error_count} 个表")
        print(f"📋 总计处理: {len(tables)} 个表")
        
        if fixed_count > 0:
            print("\n✨ 修复完成！现在可以正常使用标签功能了")
            
            # 示例：展示如何使用tags
            print("\n💡 使用示例:")
            print("   tags可以存储联系人的标签，格式为JSON数组")
            print('   例如: ["投资人", "AI领域", "北京"]')
            
    except Exception as e:
        logger.error(f"修复过程中出现错误: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def verify_tags_column(db_path: str = "user_profiles.db"):
    """
    验证所有profiles表都有tags列
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("🔍 验证tags列状态")
    print("=" * 60)
    
    try:
        # 获取所有profiles表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
        """)
        
        tables = cursor.fetchall()
        
        all_have_tags = True
        
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'tags' in column_names:
                print(f"✅ {table_name}: 有tags列")
            else:
                print(f"❌ {table_name}: 缺少tags列")
                all_have_tags = False
        
        if all_have_tags:
            print("\n🎉 所有表都已正确配置tags列！")
        else:
            print("\n⚠️ 仍有表缺少tags列，请运行修复程序")
            
    finally:
        conn.close()


def add_sample_tags(db_path: str = "user_profiles.db"):
    """
    为一些联系人添加示例标签（用于测试）
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("🏷️ 添加示例标签")
    print("=" * 60)
    
    try:
        # 找一个有数据的表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
            LIMIT 1
        """)
        
        table = cursor.fetchone()
        if not table:
            print("没有找到profiles表")
            return
            
        table_name = table[0]
        
        # 获取前3个联系人
        cursor.execute(f"""
            SELECT id, profile_name FROM {table_name} 
            LIMIT 3
        """)
        
        contacts = cursor.fetchall()
        
        if not contacts:
            print(f"{table_name} 中没有联系人数据")
            return
        
        # 示例标签
        sample_tags = [
            ["投资人", "天使投资", "TMT领域"],
            ["创业者", "AI技术", "连续创业者"],
            ["高管", "互联网", "产品专家"]
        ]
        
        for i, (contact_id, name) in enumerate(contacts):
            if i < len(sample_tags):
                tags = json.dumps(sample_tags[i], ensure_ascii=False)
                cursor.execute(f"""
                    UPDATE {table_name} 
                    SET tags = ? 
                    WHERE id = ?
                """, (tags, contact_id))
                
                print(f"✅ 为 {name} 添加标签: {sample_tags[i]}")
        
        conn.commit()
        print("\n✨ 示例标签添加完成！")
        
    finally:
        conn.close()


if __name__ == "__main__":
    import sys
    
    # 默认数据库路径
    db_path = "user_profiles.db"
    
    # 如果提供了命令行参数，使用指定的数据库
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    try:
        # 1. 修复缺失的tags列
        fix_missing_tags_column(db_path)
        
        # 2. 验证修复结果
        verify_tags_column(db_path)
        
        # 3. 可选：添加示例标签
        # add_sample_tags(db_path)
        
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()