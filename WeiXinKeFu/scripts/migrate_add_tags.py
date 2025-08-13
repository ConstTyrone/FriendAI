#!/usr/bin/env python3
"""
数据库迁移脚本 - 为现有表添加 tags 列
"""
import sqlite3
import logging
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

def add_tags_column_to_tables():
    """为所有用户画像表添加 tags 列"""
    
    # 获取数据库路径
    db_path = os.getenv('DATABASE_PATH', 'user_profiles.db')
    
    # 如果是相对路径，转换为绝对路径
    if not os.path.isabs(db_path):
        db_path = os.path.join(project_root, db_path)
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return
    
    logger.info(f"开始迁移数据库: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        # 计数器
        migrated_count = 0
        skipped_count = 0
        
        for table_tuple in tables:
            table_name = table_tuple[0]
            
            # 只处理用户画像表（以 profiles_ 或 user_ 开头的表）
            if table_name.startswith('profiles_') or table_name.startswith('user_'):
                # 检查表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                # 检查是否已有 tags 列
                if 'tags' in column_names:
                    logger.info(f"表 {table_name} 已有 tags 列，跳过")
                    skipped_count += 1
                    continue
                
                # 添加 tags 列
                try:
                    cursor.execute(f'''
                        ALTER TABLE {table_name} 
                        ADD COLUMN tags TEXT DEFAULT '[]'
                    ''')
                    logger.info(f"✅ 成功添加 tags 列到表: {table_name}")
                    migrated_count += 1
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        logger.info(f"表 {table_name} 已有 tags 列")
                        skipped_count += 1
                    else:
                        logger.error(f"添加 tags 列到表 {table_name} 失败: {e}")
        
        # 提交更改
        conn.commit()
        
        logger.info(f"""
        ========================================
        数据库迁移完成！
        ----------------------------------------
        成功迁移: {migrated_count} 个表
        跳过（已有tags列）: {skipped_count} 个表
        ========================================
        """)
        
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def verify_migration():
    """验证迁移结果"""
    db_path = os.getenv('DATABASE_PATH', 'user_profiles.db')
    
    # 如果是相对路径，转换为绝对路径
    if not os.path.isabs(db_path):
        db_path = os.path.join(project_root, db_path)
    
    logger.info("开始验证迁移结果...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 获取所有用户画像表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND (name LIKE 'profiles_%' OR name LIKE 'user_%')
        """)
        tables = cursor.fetchall()
        
        missing_tags = []
        has_tags = []
        
        for table_tuple in tables:
            table_name = table_tuple[0]
            
            # 检查表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'tags' not in column_names:
                missing_tags.append(table_name)
                logger.warning(f"❌ 表 {table_name} 缺少 tags 列")
            else:
                has_tags.append(table_name)
                logger.info(f"✅ 表 {table_name} 包含 tags 列")
        
        logger.info(f"""
        ========================================
        验证结果
        ----------------------------------------
        包含 tags 列的表: {len(has_tags)} 个
        缺少 tags 列的表: {len(missing_tags)} 个
        ========================================
        """)
        
        if missing_tags:
            logger.error(f"以下表仍缺少 tags 列: {', '.join(missing_tags)}")
            return False
        else:
            logger.info("✅ 所有表都已成功添加 tags 列")
            return True
            
    finally:
        conn.close()

def show_table_structure(table_name):
    """显示表结构"""
    db_path = os.getenv('DATABASE_PATH', 'user_profiles.db')
    
    # 如果是相对路径，转换为绝对路径
    if not os.path.isabs(db_path):
        db_path = os.path.join(project_root, db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        logger.info(f"\n表 {table_name} 的结构:")
        logger.info("-" * 60)
        for col in columns:
            logger.info(f"  {col[1]:20} {col[2]:15} {'NOT NULL' if col[3] else 'NULL':10} DEFAULT: {col[4]}")
        logger.info("-" * 60)
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("""
    ========================================
    数据库迁移工具 - 添加 tags 列
    ========================================
    此脚本将为所有用户画像表添加 tags 列
    """)
    
    # 执行迁移
    add_tags_column_to_tables()
    
    # 验证结果
    if verify_migration():
        logger.info("🎉 迁移成功完成！")
        
        # 显示一个表的结构作为示例
        db_path = os.getenv('DATABASE_PATH', 'user_profiles.db')
        if not os.path.isabs(db_path):
            db_path = os.path.join(project_root, db_path)
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'profiles_%' LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        
        if result:
            show_table_structure(result[0])
    else:
        logger.error("⚠️ 迁移可能未完全成功，请检查日志")