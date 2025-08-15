#!/usr/bin/env python3
"""
测试数据库插入功能
验证ai_summary字段是否能正常保存
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.database_sqlite_v2 import SQLiteDatabase
import json

def test_save_profile():
    """测试保存用户画像功能"""
    
    # 初始化数据库
    db = SQLiteDatabase()
    
    # 测试用户ID
    test_user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    # 测试数据
    profile_data = {
        'name': '赵翊辰',
        'profile_name': '赵翊辰',
        'gender': '男',
        'age': '36 岁',
        'phone': '137-0000-1999',
        'location': '合肥高新区量子大道',
        'marital_status': '已婚已育',
        'education': '中国科学技术大学 量子信息博士',
        'company': 'QuantumLeap（量子机器学习）',
        'position': '数据与合规总监',
        'asset_level': '高',
        'personality': 'MBTI 测评为 INFJ-A，外表温和，内心有一把"量子尺"'
    }
    
    # AI响应数据
    ai_response = {
        'summary': '赵翊辰介绍了个人基本信息，包括职业、家庭及性格。',
        'user_profiles': [profile_data]
    }
    
    raw_message = '能把隐私计算和量子加密写成童话讲给女儿听；在公司推行"数据伦理三会签"制度，被同事戏称"温柔的守门人"。'
    message_type = "general_text"
    
    print("开始测试数据库插入功能...")
    print(f"用户ID: {test_user_id}")
    print(f"用户画像: {profile_data['profile_name']}")
    print(f"AI摘要: {ai_response['summary']}")
    print(f"消息类型: {message_type}")
    
    try:
        # 保存用户画像
        result = db.save_user_profile(
            wechat_user_id=test_user_id,
            profile_data=profile_data,
            raw_message=raw_message,
            message_type=message_type,
            ai_response=ai_response
        )
        
        if result:
            print(f"✅ 成功保存用户画像，ID: {result}")
            
            # 验证数据是否正确保存
            profiles, total = db.get_user_profiles(test_user_id, limit=1)
            if profiles:
                saved_profile = profiles[0]
                print(f"✅ 验证成功，已保存的ai_summary: {saved_profile.get('ai_summary')}")
                print(f"   保存的姓名: {saved_profile.get('profile_name')}")
                print(f"   保存的公司: {saved_profile.get('company')}")
            else:
                print("❌ 验证失败：无法读取已保存的数据")
                
        else:
            print("❌ 保存失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_save_profile()