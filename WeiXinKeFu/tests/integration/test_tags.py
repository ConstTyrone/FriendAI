#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试标签功能的完整流程
"""
import requests
import json
import base64
import time

# API配置
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_001"
TOKEN = base64.b64encode(TEST_USER_ID.encode()).decode()

# 请求头
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_create_contact_with_tags():
    """测试创建带标签的联系人"""
    print("\n=== 测试创建带标签的联系人 ===")
    
    # 准备测试数据
    contact_data = {
        "name": "测试标签功能",
        "phone": "13800138000",
        "company": "测试公司",
        "tags": ["重要客户", "互联网", "北京"]
    }
    
    # 创建联系人
    response = requests.post(
        f"{BASE_URL}/api/profiles",
        headers=headers,
        json=contact_data
    )
    
    if response.status_code == 200:
        result = response.json()
        profile_id = result.get("profile_id")
        print(f"✅ 联系人创建成功，ID: {profile_id}")
        
        # 验证标签是否保存
        detail = result.get("profile", {})
        saved_tags = detail.get("tags", [])
        print(f"   保存的标签: {saved_tags}")
        
        if saved_tags == contact_data["tags"]:
            print("   ✅ 标签保存正确")
        else:
            print(f"   ❌ 标签保存错误，期望: {contact_data['tags']}, 实际: {saved_tags}")
        
        return profile_id
    else:
        print(f"❌ 创建失败: {response.status_code} - {response.text}")
        return None

def test_get_contact_with_tags(profile_id):
    """测试获取联系人时是否包含标签"""
    print(f"\n=== 测试获取联系人详情（ID: {profile_id}） ===")
    
    response = requests.get(
        f"{BASE_URL}/api/profiles/{profile_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        profile = result.get("profile", {})
        tags = profile.get("tags", [])
        
        print(f"✅ 获取成功")
        print(f"   姓名: {profile.get('profile_name')}")
        print(f"   标签: {tags}")
        
        if isinstance(tags, list) and len(tags) > 0:
            print("   ✅ 标签正确返回")
        else:
            print("   ❌ 标签数据异常")
        
        return True
    else:
        print(f"❌ 获取失败: {response.status_code} - {response.text}")
        return False

def test_update_contact_tags(profile_id):
    """测试更新联系人标签"""
    print(f"\n=== 测试更新联系人标签（ID: {profile_id}） ===")
    
    # 准备更新数据
    update_data = {
        "tags": ["VIP客户", "技术大牛", "上海", "新标签"]
    }
    
    response = requests.put(
        f"{BASE_URL}/api/profiles/{profile_id}",
        headers=headers,
        json=update_data
    )
    
    if response.status_code == 200:
        result = response.json()
        profile = result.get("profile", {})
        updated_tags = profile.get("tags", [])
        
        print(f"✅ 更新成功")
        print(f"   更新后的标签: {updated_tags}")
        
        if updated_tags == update_data["tags"]:
            print("   ✅ 标签更新正确")
        else:
            print(f"   ❌ 标签更新错误，期望: {update_data['tags']}, 实际: {updated_tags}")
        
        return True
    else:
        print(f"❌ 更新失败: {response.status_code} - {response.text}")
        return False

def test_list_contacts_with_tags():
    """测试列表中的标签显示"""
    print("\n=== 测试联系人列表中的标签 ===")
    
    response = requests.get(
        f"{BASE_URL}/api/profiles?page=1&page_size=5",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        profiles = result.get("profiles", [])
        
        print(f"✅ 获取列表成功，共 {len(profiles)} 个联系人")
        
        for profile in profiles:
            name = profile.get("profile_name", "未知")
            tags = profile.get("tags", [])
            print(f"   - {name}: 标签 {tags}")
            
            if not isinstance(tags, list):
                print(f"     ❌ 标签格式错误，应该是数组，实际是 {type(tags)}")
        
        return True
    else:
        print(f"❌ 获取列表失败: {response.status_code} - {response.text}")
        return False

def test_cleanup(profile_id):
    """清理测试数据"""
    print(f"\n=== 清理测试数据（ID: {profile_id}） ===")
    
    if profile_id:
        response = requests.delete(
            f"{BASE_URL}/api/profiles/{profile_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            print("✅ 测试数据已清理")
        else:
            print(f"❌ 清理失败: {response.status_code}")

def main():
    """主测试流程"""
    print("=" * 60)
    print("标签功能完整测试")
    print("=" * 60)
    
    try:
        # 1. 创建带标签的联系人
        profile_id = test_create_contact_with_tags()
        if not profile_id:
            print("\n测试中止：无法创建联系人")
            return
        
        # 等待一下确保数据已保存
        time.sleep(1)
        
        # 2. 获取联系人验证标签
        if not test_get_contact_with_tags(profile_id):
            print("\n测试中止：无法获取联系人")
            return
        
        # 3. 更新标签
        test_update_contact_tags(profile_id)
        
        # 等待一下
        time.sleep(1)
        
        # 4. 再次获取验证更新
        test_get_contact_with_tags(profile_id)
        
        # 5. 列表中的标签显示
        test_list_contacts_with_tags()
        
        # 6. 清理测试数据
        test_cleanup(profile_id)
        
        print("\n" + "=" * 60)
        print("✅ 标签功能测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()