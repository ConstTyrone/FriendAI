"""
为用户添加测试数据
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.database_sqlite_v2 import database_manager as db
from datetime import datetime

def add_test_profiles(wechat_user_id):
    """为用户添加测试画像数据"""
    print(f"\n=== 为用户 {wechat_user_id} 添加测试数据 ===\n")
    
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
            "ai_summary": "高净值客户，科技行业中层管理者，有投资理财需求",
            "source_type": "chat_record",
            "raw_message_content": "测试消息内容"
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
            "ai_summary": "年轻有为的职场精英，注重生活品质",
            "source_type": "text",
            "raw_message_content": "测试消息内容"
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
            "ai_summary": "资深金融从业者，高净值人群，投资经验丰富",
            "source_type": "voice",
            "raw_message_content": "测试语音转文字内容"
        }
    ]
    
    for i, profile in enumerate(test_profiles):
        try:
            profile_id = db.save_user_profile(
                wechat_user_id=wechat_user_id,
                profile_data=profile,
                raw_message=profile.get("raw_message_content", "测试消息"),
                message_type=profile.get("source_type", "text"),
                ai_response={"success": True, "profile": profile}
            )
            print(f"[OK] 添加画像成功: {profile['profile_name']} (ID: {profile_id})")
        except Exception as e:
            print(f"[ERROR] 添加画像失败: {profile['profile_name']} - {e}")
    
    # 检查结果
    print("\n=== 检查添加结果 ===")
    profiles, total = db.get_user_profiles(wechat_user_id, limit=10, offset=0)
    print(f"画像总数: {total}")
    
    if total > 0:
        print("\n画像列表:")
        for i, profile in enumerate(profiles):
            print(f"  {i+1}. {profile.get('profile_name')} - {profile.get('company')} - {profile.get('position')}")

if __name__ == "__main__":
    # 为企业微信用户添加测试数据
    add_test_profiles("wm0gZOdQAAZMXhfFKa9kZRMNdRwEVZYQ")
    
    # 也为test_user_001添加一些数据
    print("\n" + "="*50)
    add_test_profiles("test_user_001")