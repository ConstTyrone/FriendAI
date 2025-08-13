"""
直接查询数据库查看详细数据
"""
import sys
import os
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.database_sqlite_v2 import database_manager as db

def check_data_detail(wechat_user_id):
    """查看数据库中的详细数据"""
    print(f"\n=== 查看用户 {wechat_user_id} 的详细数据 ===\n")
    
    table_name = db._get_user_table_name(wechat_user_id)
    print(f"表名: {table_name}")
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 查询所有数据
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            print(f"\n共找到 {len(rows)} 条记录")
            
            # 获取列名
            column_names = [description[0] for description in cursor.description]
            print(f"\n列名: {column_names}")
            
            # 显示每条记录
            for i, row in enumerate(rows):
                print(f"\n--- 记录 {i+1} ---")
                for j, col_name in enumerate(column_names):
                    value = row[j]
                    if value and len(str(value)) > 50:
                        value = str(value)[:50] + "..."
                    print(f"{col_name}: {value}")
        
    except Exception as e:
        print(f"[ERROR] 查询失败: {e}")

if __name__ == "__main__":
    # 查看企业微信用户的数据
    check_data_detail("wm0gZOdQAAZMXhfFKa9kZRMNdRwEVZYQ")