"""
检查用户数据是否存在
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.database_sqlite_v2 import database_manager as db

def check_user_data(wechat_user_id):
    """检查指定用户的数据"""
    print(f"\n=== 检查用户: {wechat_user_id} ===\n")
    
    # 1. 检查用户是否存在
    try:
        user_id = db.get_or_create_user(wechat_user_id)
        print(f"[OK] 用户存在，ID: {user_id}")
    except Exception as e:
        print(f"[ERROR] 获取用户失败: {e}")
        return
    
    # 2. 获取表名
    table_name = db._get_user_table_name(wechat_user_id)
    print(f"[OK] 用户表名: {table_name}")
    
    # 3. 获取用户画像
    try:
        profiles, total = db.get_user_profiles(wechat_user_id, limit=10, offset=0)
        print(f"[OK] 画像总数: {total}")
        
        if total > 0:
            print("\n前5个画像:")
            for i, profile in enumerate(profiles[:5]):
                print(f"  {i+1}. {profile.get('profile_name', '未知')} - {profile.get('company', '未知公司')}")
        else:
            print("\n[WARNING] 该用户没有任何画像数据")
            
    except Exception as e:
        print(f"[ERROR] 获取画像失败: {e}")
    
    # 4. 获取统计信息
    try:
        stats = db.get_user_stats(wechat_user_id)
        print(f"\n用户统计:")
        print(f"  - 总画像数: {stats.get('total_profiles', 0)}")
        print(f"  - 今日新增: {stats.get('today_profiles', 0)}")
        print(f"  - 最后更新: {stats.get('last_profile_at', '未知')}")
    except Exception as e:
        print(f"[ERROR] 获取统计失败: {e}")

if __name__ == "__main__":
    # 检查新的企业微信用户
    check_user_data("wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q")
    
    # 检查之前的用户
    print("\n" + "="*50 + "\n")
    check_user_data("wm0gZOdQAAZMXhfFKa9kZRMNdRwEVZYQ")