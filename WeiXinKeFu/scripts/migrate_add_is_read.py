#!/usr/bin/env python3
"""
数据库迁移脚本：为 intent_matches 表添加 is_read 列
"""

import sqlite3
import os
import sys
from datetime import datetime

def migrate_database():
    """为 intent_matches 表添加 is_read 列"""
    
    # 数据库路径
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_profiles.db')
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='intent_matches'
        """)
        
        if not cursor.fetchone():
            print("❌ intent_matches 表不存在")
            conn.close()
            return False
        
        # 检查是否已有 is_read 列
        cursor.execute("PRAGMA table_info(intent_matches)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'is_read' in column_names:
            print("✅ is_read 列已存在，无需迁移")
            conn.close()
            return True
        
        print("📦 开始数据库迁移...")
        
        # 添加 is_read 列
        cursor.execute("""
            ALTER TABLE intent_matches 
            ADD COLUMN is_read BOOLEAN DEFAULT 0
        """)
        
        print("✅ 成功添加 is_read 列")
        
        # 添加 read_at 列（记录阅读时间）
        if 'read_at' not in column_names:
            cursor.execute("""
                ALTER TABLE intent_matches 
                ADD COLUMN read_at TIMESTAMP
            """)
            print("✅ 成功添加 read_at 列")
        
        # 更新现有记录：将已推送的设为已读
        cursor.execute("""
            UPDATE intent_matches 
            SET is_read = 1, read_at = pushed_at
            WHERE is_pushed = 1 AND is_read IS NULL
        """)
        
        affected_rows = cursor.rowcount
        print(f"✅ 更新了 {affected_rows} 条已推送记录为已读")
        
        # 提交更改
        conn.commit()
        
        # 验证迁移结果
        cursor.execute("PRAGMA table_info(intent_matches)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print("\n📊 迁移后的表结构:")
        for col in columns:
            print(f"  - {col[1]}: {col[2]}")
        
        if 'is_read' in column_names and 'read_at' in column_names:
            print("\n✅ 数据库迁移成功完成！")
            success = True
        else:
            print("\n❌ 迁移验证失败")
            success = False
        
        conn.close()
        return success
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("Intent Matches 表迁移脚本")
    print("=" * 50)
    print(f"迁移时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = migrate_database()
    
    if success:
        print("\n🎉 迁移完成！")
        sys.exit(0)
    else:
        print("\n❌ 迁移失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()