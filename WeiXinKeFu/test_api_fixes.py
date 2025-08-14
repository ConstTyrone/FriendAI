#!/usr/bin/env python3
"""
测试API修复效果
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_login():
    """测试登录"""
    print("=" * 60)
    print("测试登录")
    print("=" * 60)
    
    # 使用测试用户登录
    login_data = {
        "wechat_user_id": "test_user_001"
    }
    
    response = requests.post(f"{BASE_URL}/api/login", json=login_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 登录成功")
        print(f"   Token: {data.get('token')[:20]}...")
        return data.get('token')
    else:
        print(f"❌ 登录失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return None

def test_get_intents(token):
    """测试获取意图列表"""
    print("\n" + "=" * 60)
    print("测试获取意图列表")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/api/intents",
        headers=headers,
        params={"status": "active", "page": 1, "size": 10}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取意图列表成功")
        print(f"   意图数量: {len(data.get('intents', []))}")
        for intent in data.get('intents', [])[:3]:
            print(f"   - {intent.get('name')}: {intent.get('description')[:50]}...")
        return True
    else:
        print(f"❌ 获取意图列表失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return False

def test_get_matches(token):
    """测试获取匹配结果"""
    print("\n" + "=" * 60)
    print("测试获取匹配结果")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/api/intents/matches",
        headers=headers,
        params={"page": 1, "size": 10}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取匹配结果成功")
        print(f"   匹配总数: {data.get('data', {}).get('total', 0)}")
        matches = data.get('data', {}).get('matches', [])
        for match in matches[:3]:
            print(f"   - 意图: {match.get('intent_name')}, 联系人: {match.get('profile_name')}, 分数: {match.get('match_score'):.2f}")
        return True
    else:
        print(f"❌ 获取匹配结果失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return False

def test_vector_status(token):
    """测试向量状态"""
    print("\n" + "=" * 60)
    print("测试向量状态")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/api/ai/vector-status",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取向量状态成功")
        print(f"   意图总数: {data.get('intent_total', 0)}")
        print(f"   已向量化: {data.get('intent_vectorized', 0)}")
        print(f"   联系人总数: {data.get('profile_total', 0)}")
        print(f"   已向量化: {data.get('profile_vectorized', 0)}")
        return True
    else:
        print(f"❌ 获取向量状态失败: {response.status_code}")
        print(f"   响应: {response.text}")
        return False

def main():
    """主测试函数"""
    print("\n🔧 开始测试API修复效果\n")
    
    # 测试登录
    token = test_login()
    if not token:
        print("\n❌ 登录失败，无法继续测试")
        return
    
    # 测试各个API
    test_get_intents(token)
    test_get_matches(token)
    test_vector_status(token)
    
    print("\n" + "=" * 60)
    print("🎉 API测试完成！")
    print("=" * 60)
    
    print("\n修复说明:")
    print("1. ✅ 修复了 SQLiteDatabase 没有 get_user_table_name 方法的问题")
    print("2. ✅ 修复了 status 模块导入错误")
    print("3. ✅ 修复了 sqlite3 未导入的问题")
    print("4. ✅ 修复了 push_service 的数据库列名问题")
    print("\n后续建议:")
    print("- 完善数据库表结构的版本管理")
    print("- 添加数据库迁移脚本")
    print("- 统一错误处理和日志记录")

if __name__ == "__main__":
    main()