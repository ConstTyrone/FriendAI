"""
清理并重新添加测试数据
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.database_sqlite_v2 import database_manager as db
import sqlite3

def reset_user_data(wechat_user_id):
    """清理用户数据并重新添加"""
    print(f"\n=== 重置用户 {wechat_user_id} 的数据 ===\n")
    
    # 清理现有数据
    table_name = db._get_user_table_name(wechat_user_id)
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table_name}")
            conn.commit()
            print(f"[OK] 清理表 {table_name} 完成")
    except Exception as e:
        print(f"[ERROR] 清理数据失败: {e}")
        return
    
    # 添加新的测试数据
    test_profiles = [
        {
            "profile_name": "张三",
            "gender": "男",
            "age": "35",
            "phone": "138****1234",
            "location": "上海市浦东新区",
            "marital_status": "已婚",
            "education": "复旦大学 MBA",
            "company": "某科技公司",
            "position": "产品总监",
            "asset_level": "100-500万",
            "personality": "性格开朗，善于沟通，对新技术很感兴趣",
            "ai_summary": "高净值客户，科技行业中层管理者，有投资理财需求"
        },
        {
            "profile_name": "李四",
            "gender": "女",
            "age": "28",
            "phone": "139****5678",
            "location": "北京市朝阳区",
            "marital_status": "未婚",
            "education": "北京大学 本科",
            "company": "互联网公司",
            "position": "市场经理",
            "asset_level": "50-100万",
            "personality": "工作认真负责，追求完美主义",
            "ai_summary": "年轻有为的职场精英，注重生活品质"
        },
        {
            "profile_name": "王五",
            "gender": "男",
            "age": "42",
            "phone": "137****9012",
            "location": "深圳市南山区",
            "marital_status": "已婚",
            "education": "清华大学 硕士",
            "company": "金融投资公司",
            "position": "投资总监",
            "asset_level": "500万以上",
            "personality": "沉稳内敛，善于分析，决策果断",
            "ai_summary": "资深金融从业者，高净值人群，投资经验丰富"
        },
        {
            "profile_name": "赵六",
            "gender": "女",
            "age": "33",
            "phone": "186****3456",
            "location": "广州市天河区",
            "marital_status": "已婚",
            "education": "中山大学 本科",
            "company": "医药公司",
            "position": "销售总监",
            "asset_level": "100-500万",
            "personality": "热情开朗，善于交际，目标导向",
            "ai_summary": "医药行业销售精英，人脉广泛"
        },
        {
            "profile_name": "钱七",
            "gender": "男",
            "age": "45",
            "phone": "135****7890",
            "location": "杭州市西湖区",
            "marital_status": "已婚",
            "education": "浙江大学 EMBA",
            "company": "电商平台",
            "position": "运营副总裁",
            "asset_level": "500万以上",
            "personality": "思维敏捷，创新能力强，注重团队建设",
            "ai_summary": "电商行业高管，经验丰富，有创业背景"
        },
        {
            "profile_name": "孙八",
            "gender": "女",
            "age": "38",
            "phone": "158****2468",
            "location": "成都市高新区",
            "marital_status": "已婚",
            "education": "四川大学 硕士",
            "company": "游戏开发公司",
            "position": "技术总监",
            "asset_level": "100-500万",
            "personality": "技术精湛，追求极致，善于带团队",
            "ai_summary": "游戏行业技术专家，有丰富的项目管理经验"
        }
    ]
    
    # 添加数据
    success_count = 0
    for profile in test_profiles:
        try:
            profile_id = db.save_user_profile(
                wechat_user_id=wechat_user_id,
                profile_data=profile,
                raw_message=f"这是{profile['profile_name']}的测试消息内容",
                message_type="text",
                ai_response={
                    "success": True, 
                    "profile": profile,
                    "summary": profile.get("ai_summary", "")
                }
            )
            print(f"[OK] 添加画像成功: {profile['profile_name']} (ID: {profile_id})")
            success_count += 1
        except Exception as e:
            print(f"[ERROR] 添加画像失败: {profile['profile_name']} - {e}")
    
    # 验证结果
    profiles, total = db.get_user_profiles(wechat_user_id, limit=10)
    print(f"\n[结果] 成功添加 {success_count} 条画像，数据库中共有 {total} 条记录")
    
    if total > 0:
        print("\n画像列表:")
        for i, p in enumerate(profiles[:5]):
            print(f"  {i+1}. {p.get('profile_name')} - {p.get('company')} - {p.get('position')}")

if __name__ == "__main__":
    # 为新用户添加测试数据
    reset_user_data("wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q")