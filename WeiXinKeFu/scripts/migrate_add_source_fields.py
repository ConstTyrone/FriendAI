#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本：添加信息来源字段
用于为现有的用户画像表添加source、source_messages、source_timestamp字段
"""

import os
import sys
import sqlite3
import json
import logging
from datetime import datetime

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.database.database_sqlite_v2 import database_manager
except ImportError:
    print("错误：无法导入数据库模块")
    print("请确保在WeiXinKeFu目录下运行此脚本")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SourceFieldsMigration:
    """信息来源字段迁移类"""
    
    def __init__(self):
        self.db_manager = database_manager
        self.backup_file = None
        
    def backup_database(self):
        """备份数据库"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.backup_file = f"{self.db_manager.db_path}.backup_{timestamp}"
            
            # 复制数据库文件
            import shutil
            shutil.copy2(self.db_manager.db_path, self.backup_file)
            
            logger.info(f"数据库备份完成：{self.backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"数据库备份失败：{e}")
            return False
    
    def get_all_profile_tables(self):
        """获取所有用户画像表"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 查找所有profiles_*表
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name LIKE 'profiles_%'
                    ORDER BY name
                """)
                
                tables = [row[0] for row in cursor.fetchall()]
                logger.info(f"找到 {len(tables)} 个用户画像表")
                
                return tables
                
        except Exception as e:
            logger.error(f"获取画像表列表失败：{e}")
            return []
    
    def check_table_structure(self, table_name):
        """检查表结构，确定需要添加的字段"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取表结构
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                
                # 检查需要添加的字段
                required_fields = ['source', 'source_messages', 'source_timestamp']
                missing_fields = [field for field in required_fields if field not in columns]
                
                return missing_fields, len(columns)
                
        except Exception as e:
            logger.error(f"检查表结构失败 {table_name}：{e}")
            return [], 0
    
    def add_source_fields_to_table(self, table_name):
        """为单个表添加信息来源字段"""
        try:
            missing_fields, total_columns = self.check_table_structure(table_name)
            
            if not missing_fields:
                logger.info(f"表 {table_name} 已包含所有必要字段，跳过")
                return True
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 添加缺失的字段
                for field in missing_fields:
                    if field == 'source':
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN source VARCHAR(20) DEFAULT 'manual'")
                        logger.info(f"为表 {table_name} 添加 source 字段")
                        
                    elif field == 'source_messages':
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN source_messages TEXT")
                        logger.info(f"为表 {table_name} 添加 source_messages 字段")
                        
                    elif field == 'source_timestamp':
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN source_timestamp TIMESTAMP")
                        logger.info(f"为表 {table_name} 添加 source_timestamp 字段")
                
                # 为现有记录设置默认值
                cursor.execute(f"""
                    UPDATE {table_name} 
                    SET source = 'manual' 
                    WHERE source IS NULL
                """)
                
                conn.commit()
                
                # 获取更新的记录数量
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                record_count = cursor.fetchone()[0]
                
                logger.info(f"表 {table_name} 迁移完成，影响 {record_count} 条记录")
                return True
                
        except Exception as e:
            logger.error(f"为表 {table_name} 添加字段失败：{e}")
            return False
    
    def verify_migration(self, table_name):
        """验证迁移结果"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查字段是否存在
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                
                required_fields = ['source', 'source_messages', 'source_timestamp']
                missing_fields = [field for field in required_fields if field not in columns]
                
                if missing_fields:
                    logger.error(f"表 {table_name} 验证失败，缺少字段：{missing_fields}")
                    return False
                
                # 检查数据完整性
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {table_name} 
                    WHERE source IS NULL
                """)
                null_source_count = cursor.fetchone()[0]
                
                if null_source_count > 0:
                    logger.warning(f"表 {table_name} 有 {null_source_count} 条记录的source字段为空")
                
                logger.info(f"表 {table_name} 验证通过")
                return True
                
        except Exception as e:
            logger.error(f"验证表 {table_name} 失败：{e}")
            return False
    
    def run_migration(self):
        """执行完整的迁移流程"""
        logger.info("开始信息来源字段迁移...")
        
        # 1. 备份数据库
        if not self.backup_database():
            logger.error("数据库备份失败，中止迁移")
            return False
        
        try:
            # 2. 获取所有画像表
            profile_tables = self.get_all_profile_tables()
            
            if not profile_tables:
                logger.warning("未找到用户画像表")
                return True
            
            # 3. 逐个处理每张表
            success_count = 0
            failed_tables = []
            
            for table_name in profile_tables:
                logger.info(f"处理表：{table_name}")
                
                if self.add_source_fields_to_table(table_name):
                    if self.verify_migration(table_name):
                        success_count += 1
                    else:
                        failed_tables.append(table_name)
                else:
                    failed_tables.append(table_name)
            
            # 4. 输出迁移结果
            logger.info(f"迁移完成：成功 {success_count}/{len(profile_tables)} 张表")
            
            if failed_tables:
                logger.error(f"失败的表：{failed_tables}")
                return False
            
            logger.info("所有表迁移成功！")
            return True
            
        except Exception as e:
            logger.error(f"迁移过程出错：{e}")
            return False
    
    def rollback_migration(self):
        """回滚迁移（从备份恢复）"""
        if not self.backup_file or not os.path.exists(self.backup_file):
            logger.error("未找到备份文件，无法回滚")
            return False
        
        try:
            import shutil
            shutil.copy2(self.backup_file, self.db_manager.db_path)
            logger.info(f"从备份文件恢复数据库：{self.backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"回滚失败：{e}")
            return False
    
    def show_migration_status(self):
        """显示迁移状态"""
        logger.info("检查信息来源字段迁移状态...")
        
        profile_tables = self.get_all_profile_tables()
        
        if not profile_tables:
            logger.info("未找到用户画像表")
            return
        
        migrated_tables = []
        pending_tables = []
        
        for table_name in profile_tables:
            missing_fields, total_columns = self.check_table_structure(table_name)
            
            if not missing_fields:
                migrated_tables.append(table_name)
            else:
                pending_tables.append((table_name, missing_fields))
        
        logger.info(f"已迁移的表：{len(migrated_tables)}/{len(profile_tables)}")
        for table in migrated_tables:
            logger.info(f"  ✅ {table}")
        
        if pending_tables:
            logger.info("待迁移的表：")
            for table, missing in pending_tables:
                logger.info(f"  ❌ {table} (缺少字段: {missing})")
        else:
            logger.info("所有表已完成迁移 🎉")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='信息来源字段迁移脚本')
    parser.add_argument('action', choices=['migrate', 'rollback', 'status'], 
                       help='操作类型：migrate(迁移)、rollback(回滚)、status(状态)')
    
    args = parser.parse_args()
    
    migration = SourceFieldsMigration()
    
    if args.action == 'migrate':
        logger.info("执行信息来源字段迁移...")
        if migration.run_migration():
            logger.info("迁移成功完成！")
            sys.exit(0)
        else:
            logger.error("迁移失败！")
            sys.exit(1)
            
    elif args.action == 'rollback':
        logger.info("执行迁移回滚...")
        if migration.rollback_migration():
            logger.info("回滚成功！")
            sys.exit(0)
        else:
            logger.error("回滚失败！")
            sys.exit(1)
            
    elif args.action == 'status':
        migration.show_migration_status()

if __name__ == '__main__':
    main()