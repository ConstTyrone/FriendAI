#!/usr/bin/env python3
"""
清理数据库中多余的列，只保留v2版本定义的标准列
"""

import sqlite3
import sys
from datetime import datetime

# v2版本定义的标准列
V2_STANDARD_COLUMNS = {
    'id', 'profile_name', 'gender', 'age', 'phone', 'location',
    'marital_status', 'education', 'company', 'position', 
    'asset_level', 'personality', 'tags', 'ai_summary',
    'confidence_score', 'source_type', 'raw_message_content',
    'raw_ai_response', 'created_at', 'updated_at'
}

# 要删除的多余列
COLUMNS_TO_REMOVE = [
    'wechat_id', 'basic_info', 'recent_activities', 'raw_messages',
    'source', 'message_count', 'industry', 'school', 
    'profile_picture', 'last_message_time',
    'embedding', 'embedding_model', 'embedding_updated_at'  # 向量搜索相关列
]

def clean_database(db_path="user_profiles.db", dry_run=False):
    """清理数据库中的多余列"""
    print("=" * 60)
    print(f"🧹 清理数据库多余列")
    print(f"数据库: {db_path}")
    print(f"模式: {'模拟运行' if dry_run else '实际执行'}")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有profiles表
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'profiles_%'
        """)
        tables = cursor.fetchall()
        
        print(f"\n找到 {len(tables)} 个profiles表")
        
        for (table_name,) in tables:
            print(f"\n处理表: {table_name}")
            print("-" * 50)
            
            # 获取当前表的所有列
            cursor.execute(f"PRAGMA table_info({table_name})")
            current_columns = [(row[1], row[2]) for row in cursor.fetchall()]
            current_column_names = {col[0] for col in current_columns}
            
            # 找出要删除的列
            columns_to_delete = []
            for col_name in COLUMNS_TO_REMOVE:
                if col_name in current_column_names:
                    columns_to_delete.append(col_name)
            
            if not columns_to_delete:
                print("  ✅ 没有多余的列需要删除")
                continue
            
            print(f"  发现 {len(columns_to_delete)} 个多余的列:")
            for col in columns_to_delete:
                print(f"    - {col}")
            
            if dry_run:
                print("  🔍 模拟运行：不执行实际删除")
                continue
            
            # SQLite不支持直接删除列，需要重建表
            print("  🔄 重建表以删除多余列...")
            
            # 1. 创建新表（只包含标准列）
            temp_table = f"{table_name}_new"
            
            # 构建只包含标准列的CREATE TABLE语句
            create_columns = []
            for col_name, col_type in current_columns:
                if col_name in V2_STANDARD_COLUMNS:
                    if col_name == 'id':
                        create_columns.append(f"{col_name} INTEGER PRIMARY KEY AUTOINCREMENT")
                    elif col_name == 'created_at' or col_name == 'updated_at':
                        create_columns.append(f"{col_name} TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                    else:
                        create_columns.append(f"{col_name} {col_type}")
            
            # 添加UNIQUE约束
            create_sql = f"""
                CREATE TABLE {temp_table} (
                    {', '.join(create_columns)},
                    UNIQUE(profile_name)
                )
            """
            
            cursor.execute(create_sql)
            
            # 2. 复制数据（只复制标准列）
            standard_cols = [col for col, _ in current_columns if col in V2_STANDARD_COLUMNS]
            cols_str = ', '.join(standard_cols)
            
            cursor.execute(f"""
                INSERT INTO {temp_table} ({cols_str})
                SELECT {cols_str} FROM {table_name}
            """)
            
            # 3. 删除旧表
            cursor.execute(f"DROP TABLE {table_name}")
            
            # 4. 重命名新表
            cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
            
            # 5. 重建索引
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_name ON {table_name}(profile_name)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_created ON {table_name}(created_at DESC)')
            
            print(f"  ✅ 成功删除 {len(columns_to_delete)} 个多余的列")
        
        if not dry_run:
            conn.commit()
            print("\n✅ 数据库清理完成")
        
        # 验证结果
        print("\n" + "=" * 60)
        print("🔍 验证清理结果")
        print("=" * 60)
        
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            
            extra_cols = set(columns) - V2_STANDARD_COLUMNS
            missing_cols = V2_STANDARD_COLUMNS - set(columns)
            
            if extra_cols:
                print(f"⚠️ {table_name}: 仍有多余列 {extra_cols}")
            elif missing_cols:
                print(f"⚠️ {table_name}: 缺少标准列 {missing_cols}")
            else:
                print(f"✅ {table_name}: 结构符合v2标准")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def backup_database(db_path="user_profiles.db"):
    """备份数据库"""
    import shutil
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"✅ 数据库已备份到: {backup_path}")
    return backup_path


if __name__ == "__main__":
    db_path = "user_profiles.db"
    
    # 检查命令行参数
    dry_run = "--dry-run" in sys.argv
    no_backup = "--no-backup" in sys.argv
    
    if "--help" in sys.argv:
        print("""
用法: python clean_extra_columns.py [选项]

选项:
    --dry-run       模拟运行，不实际删除
    --no-backup     不创建备份（不推荐）
    --help          显示帮助信息

示例:
    python clean_extra_columns.py                # 备份并清理
    python clean_extra_columns.py --dry-run      # 仅查看要删除的列
    python clean_extra_columns.py --no-backup    # 清理但不备份（危险）
        """)
        sys.exit(0)
    
    # 创建备份
    if not dry_run and not no_backup:
        backup_path = backup_database(db_path)
        print()
    
    # 执行清理
    success = clean_database(db_path, dry_run=dry_run)
    
    if dry_run:
        print("\n💡 这是模拟运行。要实际删除列，请运行：")
        print("   python clean_extra_columns.py")
    
    sys.exit(0 if success else 1)