#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：为所有已存在的用户表添加tags字段
"""
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """为所有用户表添加tags字段"""
    
    # 数据库路径
    db_path = os.getenv('DATABASE_PATH', 'user_profiles_v2.db')
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有以profiles_开头的表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
        """)
        
        tables = cursor.fetchall()
        logger.info(f"找到 {len(tables)} 个用户表需要迁移")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for (table_name,) in tables:
            try:
                # 检查表是否已有tags字段
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                if 'tags' in column_names:
                    logger.info(f"表 {table_name} 已有tags字段，跳过")
                    skip_count += 1
                    continue
                
                # 添加tags字段
                logger.info(f"为表 {table_name} 添加tags字段...")
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN tags TEXT DEFAULT '[]'
                """)
                
                success_count += 1
                logger.info(f"✅ 表 {table_name} 迁移成功")
                
            except Exception as e:
                error_count += 1
                logger.error(f"❌ 表 {table_name} 迁移失败: {e}")
        
        # 提交更改
        conn.commit()
        conn.close()
        
        # 输出统计
        logger.info("=" * 60)
        logger.info("迁移完成统计：")
        logger.info(f"  成功迁移: {success_count} 个表")
        logger.info(f"  已存在跳过: {skip_count} 个表")
        logger.info(f"  迁移失败: {error_count} 个表")
        logger.info("=" * 60)
        
        return error_count == 0
        
    except Exception as e:
        logger.error(f"迁移过程出错: {e}")
        return False

def verify_migration():
    """验证迁移结果"""
    db_path = os.getenv('DATABASE_PATH', 'user_profiles_v2.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有以profiles_开头的表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
        """)
        
        tables = cursor.fetchall()
        
        logger.info("\n验证迁移结果：")
        all_good = True
        
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            if 'tags' in column_names:
                logger.info(f"  ✅ {table_name}: tags字段存在")
            else:
                logger.error(f"  ❌ {table_name}: tags字段缺失")
                all_good = False
        
        conn.close()
        
        if all_good:
            logger.info("\n✅ 所有表都已成功添加tags字段！")
        else:
            logger.error("\n❌ 部分表仍缺少tags字段")
        
        return all_good
        
    except Exception as e:
        logger.error(f"验证过程出错: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("数据库迁移：添加tags字段")
    print("=" * 60)
    
    # 执行迁移
    if migrate_database():
        # 验证结果
        verify_migration()
    else:
        logger.error("迁移失败！")