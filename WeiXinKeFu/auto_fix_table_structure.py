#!/usr/bin/env python3
"""
自动检查和修复所有用户profiles表的结构
确保所有必需的列都存在
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定义profiles表应该有的完整列结构
REQUIRED_COLUMNS = {
    'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
    'profile_name': 'TEXT',
    'gender': 'TEXT DEFAULT "未知"',
    'age': 'TEXT DEFAULT "未知"',
    'phone': 'TEXT DEFAULT "未知"',
    'location': 'TEXT DEFAULT "未知"',
    'marital_status': 'TEXT DEFAULT "未知"',
    'education': 'TEXT DEFAULT "未知"',
    'company': 'TEXT DEFAULT "未知"',
    'position': 'TEXT DEFAULT "未知"',
    'asset_level': 'TEXT DEFAULT "未知"',
    'personality': 'TEXT DEFAULT "未知"',
    'wechat_id': 'TEXT',
    'basic_info': 'TEXT',
    'ai_summary': 'TEXT',
    'recent_activities': 'TEXT',
    'tags': 'TEXT DEFAULT "[]"',  # 新增的tags列
    'source': 'TEXT DEFAULT "微信"',
    'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
    'message_count': 'INTEGER DEFAULT 0',
    'raw_messages': 'TEXT',
    'profile_picture': 'TEXT',
    'industry': 'TEXT',
    'school': 'TEXT',
    'confidence_score': 'REAL DEFAULT 0.0',
    'last_message_time': 'TEXT',
    'embedding': 'BLOB'  # 向量数据
}

# 可以安全添加的列（带默认值）
SAFE_TO_ADD_COLUMNS = {
    'tags': 'TEXT DEFAULT "[]"',
    'source': 'TEXT DEFAULT "微信"',
    'message_count': 'INTEGER DEFAULT 0',
    'confidence_score': 'REAL DEFAULT 0.0',
    'embedding': 'BLOB',
    'industry': 'TEXT',
    'school': 'TEXT',
    'profile_picture': 'TEXT',
    'last_message_time': 'TEXT'
}


class TableStructureFixer:
    """表结构修复器"""
    
    def __init__(self, db_path: str = "user_profiles.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()
    
    def get_all_profile_tables(self) -> List[str]:
        """获取所有profiles表"""
        self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
        """)
        return [row[0] for row in self.cursor.fetchall()]
    
    def get_table_columns(self, table_name: str) -> List[str]:
        """获取表的所有列名"""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in self.cursor.fetchall()]
    
    def add_missing_column(self, table_name: str, column_name: str, column_type: str) -> bool:
        """为表添加缺失的列"""
        try:
            # 构建ALTER TABLE语句
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            self.cursor.execute(sql)
            
            # 如果是tags列，设置默认值
            if column_name == 'tags':
                self.cursor.execute(f"""
                    UPDATE {table_name} 
                    SET tags = '[]' 
                    WHERE tags IS NULL
                """)
            
            logger.info(f"✅ 成功为 {table_name} 添加列: {column_name}")
            return True
            
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                logger.debug(f"列 {column_name} 已存在于 {table_name}")
            else:
                logger.error(f"添加列 {column_name} 到 {table_name} 失败: {e}")
            return False
    
    def fix_table_structure(self, table_name: str) -> Tuple[int, int]:
        """修复单个表的结构"""
        existing_columns = self.get_table_columns(table_name)
        added_count = 0
        failed_count = 0
        
        for column_name, column_type in SAFE_TO_ADD_COLUMNS.items():
            if column_name not in existing_columns:
                if self.add_missing_column(table_name, column_name, column_type):
                    added_count += 1
                else:
                    failed_count += 1
        
        return added_count, failed_count
    
    def fix_all_tables(self):
        """修复所有表的结构"""
        tables = self.get_all_profile_tables()
        
        if not tables:
            print("❌ 没有找到任何profiles表")
            return
        
        print(f"\n📊 找到 {len(tables)} 个用户表需要检查")
        print("=" * 60)
        
        total_added = 0
        total_failed = 0
        tables_fixed = 0
        
        for table_name in tables:
            print(f"\n检查表: {table_name}")
            existing_columns = self.get_table_columns(table_name)
            missing_columns = []
            
            # 检查缺失的列
            for column_name in SAFE_TO_ADD_COLUMNS.keys():
                if column_name not in existing_columns:
                    missing_columns.append(column_name)
            
            if missing_columns:
                print(f"  缺失的列: {', '.join(missing_columns)}")
                added, failed = self.fix_table_structure(table_name)
                total_added += added
                total_failed += failed
                if added > 0:
                    tables_fixed += 1
            else:
                print(f"  ✅ 表结构完整")
        
        # 打印统计
        print("\n" + "=" * 60)
        print("📊 修复统计")
        print("=" * 60)
        print(f"✅ 修复的表数: {tables_fixed}")
        print(f"✅ 添加的列数: {total_added}")
        print(f"❌ 失败的操作: {total_failed}")
        print(f"📋 总计检查: {len(tables)} 个表")
        
        if total_added > 0:
            print("\n✨ 修复完成！数据库结构已更新")
    
    def verify_all_tables(self):
        """验证所有表的结构"""
        tables = self.get_all_profile_tables()
        
        print("\n" + "=" * 60)
        print("🔍 验证表结构完整性")
        print("=" * 60)
        
        all_complete = True
        
        for table_name in tables:
            existing_columns = self.get_table_columns(table_name)
            missing_columns = []
            
            for column_name in SAFE_TO_ADD_COLUMNS.keys():
                if column_name not in existing_columns:
                    missing_columns.append(column_name)
            
            if missing_columns:
                print(f"❌ {table_name}: 缺失 {', '.join(missing_columns)}")
                all_complete = False
            else:
                print(f"✅ {table_name}: 结构完整")
        
        if all_complete:
            print("\n🎉 所有表结构都已完整！")
        else:
            print("\n⚠️ 仍有表结构不完整，请运行修复")
        
        return all_complete


def create_sample_profile_with_tags(db_path: str = "user_profiles.db"):
    """创建一个带标签的示例联系人（用于测试）"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 使用第一个找到的表
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
        
        # 创建示例数据
        sample_data = {
            'profile_name': '测试用户_标签功能',
            'gender': '男',
            'age': '30',
            'phone': '13800138000',
            'location': '北京',
            'company': 'AI科技公司',
            'position': 'CTO',
            'tags': json.dumps(['AI专家', '创业者', '技术大牛', '北京'], ensure_ascii=False),
            'ai_summary': '资深AI技术专家，有多年创业经验',
            'source': '测试创建',
            'confidence_score': 0.95
        }
        
        # 构建插入语句
        columns = ', '.join(sample_data.keys())
        placeholders = ', '.join(['?' for _ in sample_data])
        values = list(sample_data.values())
        
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        
        conn.commit()
        print(f"\n✅ 成功创建测试联系人，包含标签: {sample_data['tags']}")
        print(f"   表名: {table_name}")
        print(f"   姓名: {sample_data['profile_name']}")
        
    except Exception as e:
        print(f"创建测试数据失败: {e}")
        conn.rollback()
    finally:
        conn.close()


def main():
    """主函数"""
    import sys
    
    # 默认数据库路径
    db_path = "user_profiles.db"
    
    # 如果提供了命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("""
用法: python auto_fix_table_structure.py [选项]

选项:
    --help          显示帮助信息
    --verify        仅验证表结构，不修复
    --test          创建测试数据
    [db_path]       指定数据库文件路径（默认: user_profiles.db）

示例:
    python auto_fix_table_structure.py                    # 修复默认数据库
    python auto_fix_table_structure.py --verify           # 仅验证
    python auto_fix_table_structure.py my_database.db     # 修复指定数据库
            """)
            return
        elif sys.argv[1] == '--verify':
            with TableStructureFixer(db_path) as fixer:
                fixer.verify_all_tables()
            return
        elif sys.argv[1] == '--test':
            create_sample_profile_with_tags(db_path)
            return
        else:
            db_path = sys.argv[1]
    
    print("=" * 60)
    print("🔧 自动修复数据库表结构")
    print("=" * 60)
    print(f"数据库: {db_path}")
    
    try:
        with TableStructureFixer(db_path) as fixer:
            # 1. 修复所有表
            fixer.fix_all_tables()
            
            # 2. 验证结果
            fixer.verify_all_tables()
            
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()