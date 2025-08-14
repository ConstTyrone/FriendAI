#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试创建和更新联系人功能
"""

import requests
import json
import base64
import sys

# 配置
BASE_URL = "http://localhost:8000"  # 修改为你的服务器地址
TEST_USER_ID = "test_user_001"  # 测试用户ID

# 生成简单token
token = base64.b64encode(TEST_USER_ID.encode('utf-8')).decode('utf-8')
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

def test_login():
    """测试登录"""
    print("1. 测试登录...")
    url = f"{BASE_URL}/api/login"
    data = {
        "wechat_user_id": TEST_USER_ID
    }
    
    response = requests.post(url, json=data)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   登录成功: {result.get('wechat_user_id')}")
        return result.get('token')
    else:
        print(f"   登录失败: {response.text}")
        return None

def test_create_contact(token):
    """测试创建联系人"""
    print("\n2. 测试创建联系人...")
    url = f"{BASE_URL}/api/profiles"
    
    # 准备测试数据
    contact_data = {
        "name": "张三",
        "phone": "13800138000",
        "wechat_id": "zhangsan_wx",
        "email": "zhangsan@example.com",
        "company": "科技有限公司",
        "position": "产品经理",
        "address": "北京市朝阳区",
        "notes": "这是通过API创建的测试联系人",
        "tags": ["朋友", "同事"],
        # 额外字段
        "gender": "男",
        "age": "30",
        "marital_status": "已婚已育",
        "education": "硕士-清华大学",
        "asset_level": "中",
        "personality": "外向开朗，善于沟通"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=contact_data, headers=headers)
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   创建成功!")
        print(f"   联系人ID: {result.get('profile_id')}")
        print(f"   联系人信息: {json.dumps(result.get('profile'), ensure_ascii=False, indent=2)}")
        return result.get('profile_id')
    else:
        print(f"   创建失败: {response.text}")
        return None

def test_update_contact(token, profile_id):
    """测试更新联系人"""
    if not profile_id:
        print("\n3. 跳过更新测试（没有可更新的联系人）")
        return
        
    print(f"\n3. 测试更新联系人 (ID: {profile_id})...")
    url = f"{BASE_URL}/api/profiles/{profile_id}"
    
    # 准备更新数据
    update_data = {
        "name": "张三（已更新）",
        "phone": "13900139000",
        "company": "新科技有限公司",
        "position": "高级产品经理",
        "age": "31",
        "asset_level": "高",
        "notes": "通过API更新了联系人信息"
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.put(url, json=update_data, headers=headers)
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   更新成功!")
        print(f"   更新后信息: {json.dumps(result.get('profile'), ensure_ascii=False, indent=2)}")
        return True
    else:
        print(f"   更新失败: {response.text}")
        return False

def test_get_contacts(token):
    """测试获取联系人列表"""
    print("\n4. 测试获取联系人列表...")
    url = f"{BASE_URL}/api/profiles?page=1&page_size=10"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(url, headers=headers)
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"   获取成功!")
        print(f"   总数: {result.get('total')}")
        print(f"   当前页联系人数: {len(result.get('profiles', []))}")
        
        # 显示前3个联系人
        profiles = result.get('profiles', [])[:3]
        for i, profile in enumerate(profiles, 1):
            print(f"\n   联系人 {i}:")
            print(f"     姓名: {profile.get('profile_name')}")
            print(f"     公司: {profile.get('company')}")
            print(f"     职位: {profile.get('position')}")
    else:
        print(f"   获取失败: {response.text}")

def main():
    """主测试流程"""
    print("=" * 50)
    print("联系人管理API测试")
    print("=" * 50)
    
    # 1. 登录获取token
    token = test_login()
    if not token:
        print("\n登录失败，测试中止")
        sys.exit(1)
    
    # 2. 创建联系人
    profile_id = test_create_contact(token)
    
    # 3. 更新联系人
    test_update_contact(token, profile_id)
    
    # 4. 获取联系人列表
    test_get_contacts(token)
    
    print("\n" + "=" * 50)
    print("测试完成!")
    print("=" * 50)

if __name__ == "__main__":
    main()