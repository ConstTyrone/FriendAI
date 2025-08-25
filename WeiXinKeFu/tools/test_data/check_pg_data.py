"""
检查PostgreSQL数据库中的用户数据
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from src.database.database_pg import pg_database as db
    
    def check_pg_user_data(wechat_user_id):
        """检查PostgreSQL中的用户数据"""
        print(f"\n=== 检查PostgreSQL中用户: {wechat_user_id} ===\n")
        
        try:
            # 获取用户画像
            profiles, total = db.get_user_profiles(wechat_user_id, limit=10, offset=0)
            print(f"[OK] 画像总数: {total}")
            
            if total > 0:
                print("\n画像列表:")
                for i, profile in enumerate(profiles[:6]):
                    print(f"  {i+1}. {profile.get('profile_name', '未知')} - {profile.get('company', '未知公司')} - {profile.get('position', '未知职位')}")
            else:
                print("\n[WARNING] 该用户没有任何画像数据")
                
        except Exception as e:
            print(f"[ERROR] 获取画像失败: {e}")
    
    if __name__ == "__main__":
        # 检查PostgreSQL中的数据
        check_pg_user_data("wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q")
        
except ImportError as e:
    print(f"[ERROR] 无法导入PostgreSQL数据库模块: {e}")
    print("可能需要安装 psycopg2: pip install psycopg2-binary")