#!/usr/bin/env python3
"""
添加反馈相关的数据库列
自动检测并添加缺失的列，确保向后兼容
"""

import sqlite3
import os
import sys
import logging
from pathlib import Path

# 设置Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_feedback_columns(db_path="user_profiles.db"):
    """添加反馈相关的列"""
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有意图匹配表的列信息
        cursor.execute("PRAGMA table_info(intent_matches)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 检查表是否存在
        if not columns:
            logger.warning("intent_matches表不存在，跳过迁移")
            conn.close()
            return True
            
        logger.info(f"当前intent_matches表的列: {columns}")
        
        # 需要添加的列
        columns_to_add = []
        
        # 检查并添加feedback_time列
        if 'feedback_time' not in columns:
            columns_to_add.append(('feedback_time', 'TEXT'))
            
        # 检查并添加user_feedback列（以防万一）
        if 'user_feedback' not in columns:
            columns_to_add.append(('user_feedback', 'TEXT'))
            
        # 检查并添加feedback_confidence列（未来扩展）
        if 'feedback_confidence' not in columns:
            columns_to_add.append(('feedback_confidence', 'REAL'))
            
        # 添加缺失的列
        for column_name, column_type in columns_to_add:
            try:
                logger.info(f"添加列: {column_name} {column_type}")
                cursor.execute(f"""
                    ALTER TABLE intent_matches 
                    ADD COLUMN {column_name} {column_type}
                """)
                conn.commit()
                logger.info(f"✅ 成功添加列: {column_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    logger.info(f"列 {column_name} 已存在，跳过")
                else:
                    logger.error(f"添加列 {column_name} 失败: {e}")
                    
        # 创建反馈时间索引（如果不存在）
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_time 
                ON intent_matches(feedback_time)
            """)
            conn.commit()
            logger.info("✅ 创建feedback_time索引")
        except Exception as e:
            logger.warning(f"创建索引失败（可能已存在）: {e}")
            
        # 验证迁移结果
        cursor.execute("PRAGMA table_info(intent_matches)")
        final_columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"迁移后的列: {final_columns}")
        
        # 统计反馈数据
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(user_feedback) as with_feedback,
                COUNT(CASE WHEN user_feedback = 'positive' THEN 1 END) as positive,
                COUNT(CASE WHEN user_feedback = 'negative' THEN 1 END) as negative,
                COUNT(CASE WHEN user_feedback = 'ignored' THEN 1 END) as ignored
            FROM intent_matches
        """)
        
        stats = cursor.fetchone()
        if stats:
            logger.info(f"""
反馈统计:
- 总匹配数: {stats[0]}
- 有反馈的: {stats[1]}
- 正面反馈: {stats[2]}
- 负面反馈: {stats[3]}
- 忽略反馈: {stats[4]}
            """)
        
        conn.close()
        logger.info("✅ 数据库迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_all_tables(db_path="user_profiles.db"):
    """检查所有相关表的结构"""
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查所有表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%intent%' OR name LIKE '%match%'
        """)
        
        tables = cursor.fetchall()
        logger.info(f"\n找到相关表: {[t[0] for t in tables]}")
        
        for table_name, in tables:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            logger.info(f"\n表 {table_name} 的结构:")
            for col in columns:
                logger.info(f"  - {col[1]} ({col[2]})")
                
        conn.close()
        
    except Exception as e:
        logger.error(f"检查表结构失败: {e}")

if __name__ == "__main__":
    logger.info("=== 开始数据库迁移 ===")
    
    # 检查当前表结构
    logger.info("\n=== 检查当前表结构 ===")
    check_all_tables()
    
    # 执行迁移
    logger.info("\n=== 执行迁移 ===")
    success = migrate_feedback_columns()
    
    if success:
        logger.info("\n✅ 迁移成功！反馈功能已准备就绪")
        
        # 再次检查表结构
        logger.info("\n=== 迁移后表结构 ===")
        check_all_tables()
    else:
        logger.error("\n❌ 迁移失败，请检查错误信息")
        sys.exit(1)