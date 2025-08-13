"""
查看数据库中的用户列表
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.database_sqlite_v2 import database_manager as db

def list_all_users():
    """列出所有用户"""
    print("=== 数据库中的所有用户 ===\n")
    
    # 获取所有表名
    tables = db.get_all_tables()
    user_count = 0
    
    for table in tables:
        if table.startswith('user_') and table.endswith('_profiles'):
            # 从表名提取用户ID
            user_id = table.replace('user_', '').replace('_profiles', '')
            
            # 获取该用户的画像数量
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                print(f"用户ID: {user_id}")
                print(f"画像数量: {count}")
                print(f"表名: {table}")
                print("-" * 50)
                
                user_count += 1
                
            except Exception as e:
                print(f"读取表 {table} 失败: {e}")
            finally:
                conn.close()
    
    print(f"\n总用户数: {user_count}")
    
    # 如果有测试用户，列出来
    print("\n=== 可用的测试用户 ===")
    test_users = [
        "test_user_001",
        "test_user_002", 
        "demo_user_001",
        "dev_user_001"
    ]
    
    for user in test_users:
        table_name = f"user_{user}_profiles"
        if table_name in tables:
            print(f"✓ {user} - 可用")
        else:
            print(f"✗ {user} - 不存在")

if __name__ == "__main__":
    list_all_users()