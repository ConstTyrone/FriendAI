#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试标签功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database.database_sqlite_v2 import database_manager as db

def test_tags():
    """测试标签功能"""
    print("=" * 60)
    print("测试标签功能")
    print("=" * 60)
    
    # 测试用户
    test_user = "test_tags_user"
    
    # 1. 创建带标签的联系人
    print("\n1. 创建带标签的联系人")
    profile_data = {
        "name": "测试标签",
        "phone": "13800138000",
        "company": "测试公司",
        "tags": ["重要客户", "互联网", "北京"]
    }
    
    profile_id = db.save_user_profile(
        wechat_user_id=test_user,
        profile_data=profile_data,
        raw_message="测试创建带标签的联系人",
        message_type="test",
        ai_response={"summary": "测试"}
    )
    
    if profile_id:
        print(f"   ✅ 创建成功，ID: {profile_id}")
    else:
        print("   ❌ 创建失败")
        return
    
    # 2. 获取联系人详情，验证标签
    print("\n2. 获取联系人详情")
    detail = db.get_user_profile_detail(test_user, profile_id)
    
    if detail:
        tags = detail.get("tags", [])
        print(f"   姓名: {detail.get('profile_name')}")
        print(f"   标签: {tags}")
        
        if tags == profile_data["tags"]:
            print("   ✅ 标签保存和读取正确")
        else:
            print(f"   ❌ 标签不匹配")
            print(f"      期望: {profile_data['tags']}")
            print(f"      实际: {tags}")
    else:
        print("   ❌ 获取详情失败")
    
    # 3. 更新标签
    print("\n3. 更新标签")
    new_tags = ["VIP客户", "技术大牛", "上海"]
    
    success = db.update_user_profile(
        test_user,
        profile_id,
        {"tags": new_tags}
    )
    
    if success:
        print("   ✅ 更新成功")
        
        # 再次获取验证
        detail = db.get_user_profile_detail(test_user, profile_id)
        if detail:
            updated_tags = detail.get("tags", [])
            print(f"   更新后的标签: {updated_tags}")
            
            if updated_tags == new_tags:
                print("   ✅ 标签更新正确")
            else:
                print("   ❌ 标签更新失败")
    else:
        print("   ❌ 更新失败")
    
    # 4. 获取列表，验证标签
    print("\n4. 获取联系人列表")
    profiles, total = db.get_user_profiles(test_user, limit=10, offset=0)
    
    print(f"   共 {total} 个联系人")
    for profile in profiles[:3]:
        name = profile.get("profile_name", "未知")
        tags = profile.get("tags", [])
        print(f"   - {name}: {tags}")
    
    # 5. 清理测试数据
    print("\n5. 清理测试数据")
    if db.delete_user_profile(test_user, profile_id):
        print("   ✅ 测试数据已清理")
    else:
        print("   ❌ 清理失败")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_tags()