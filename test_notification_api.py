#!/usr/bin/env python3
"""
测试小程序通知API
"""

import requests
import json
import time

# API基础配置
API_BASE = "https://weixin.dataelem.com"  # 服务器地址
TEST_USER = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"

def get_token(user_id):
    """获取测试用户的token"""
    import base64
    # 简单的Base64 token（生产环境应该用JWT）
    token = base64.b64encode(f"user:{user_id}".encode()).decode()
    return f"Bearer {token}"

def test_get_notifications():
    """测试获取未读通知"""
    print("🔍 测试获取未读通知...")
    
    headers = {
        "Authorization": get_token(TEST_USER),
        "Content-Type": "application/json"
    }
    
    # 获取未读通知
    response = requests.get(
        f"{API_BASE}/api/notifications/matches",
        headers=headers,
        params={"unread_only": True, "limit": 10}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 获取成功!")
        print(f"   未读数量: {data.get('unread_count', 0)}")
        print(f"   有新匹配: {data.get('has_new', False)}")
        
        matches = data.get('matches', [])
        if matches:
            print(f"\n📋 最新匹配列表:")
            for i, match in enumerate(matches[:3], 1):
                print(f"\n   {i}. {match.get('intent_name', '未知意图')}")
                print(f"      联系人: {match.get('profile_name', '未知')}")
                print(f"      匹配度: {match.get('match_score', 0):.0%}")
                print(f"      说明: {match.get('explanation', '')[:50]}...")
                print(f"      创建时间: {match.get('created_at', '')}")
                print(f"      匹配ID: {match.get('id')}")
        else:
            print("   暂无未读匹配")
            
        return matches
    else:
        print(f"❌ 获取失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
        return []

def test_mark_as_read(match_id):
    """测试标记已读"""
    print(f"\n📝 测试标记匹配 {match_id} 为已读...")
    
    headers = {
        "Authorization": get_token(TEST_USER),
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_BASE}/api/notifications/matches/{match_id}/read",
        headers=headers
    )
    
    if response.status_code == 200:
        print("✅ 标记成功!")
        return True
    else:
        print(f"❌ 标记失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
        return False

def simulate_polling():
    """模拟小程序轮询"""
    print("\n🔄 模拟小程序轮询（每10秒检查一次）...")
    print("按 Ctrl+C 停止\n")
    
    last_count = 0
    
    try:
        while True:
            headers = {
                "Authorization": get_token(TEST_USER),
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{API_BASE}/api/notifications/matches",
                headers=headers,
                params={"unread_only": True, "limit": 10}
            )
            
            if response.status_code == 200:
                data = response.json()
                unread_count = data.get('unread_count', 0)
                
                if unread_count > last_count:
                    new_count = unread_count - last_count
                    print(f"🎯 发现 {new_count} 个新匹配!")
                    print(f"   当前未读总数: {unread_count}")
                    
                    # 显示最新的匹配
                    matches = data.get('matches', [])
                    if matches:
                        latest = matches[0]
                        print(f"   最新匹配: {latest.get('intent_name')} - {latest.get('profile_name')}")
                        print(f"   匹配度: {latest.get('match_score', 0):.0%}")
                    
                    # 模拟振动提醒
                    print("   📳 叮~ （振动提醒）")
                    
                elif unread_count == 0 and last_count > 0:
                    print("✅ 所有匹配已读")
                else:
                    print(f"⏳ 轮询中... 未读数: {unread_count}")
                
                last_count = unread_count
            else:
                print(f"❌ 轮询失败: {response.status_code}")
            
            time.sleep(10)  # 10秒轮询一次
            
    except KeyboardInterrupt:
        print("\n\n👋 停止轮询")

def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 小程序通知API测试")
    print("=" * 60)
    
    # 1. 获取未读通知
    matches = test_get_notifications()
    
    # 2. 如果有未读，标记第一个为已读
    if matches:
        first_match_id = matches[0].get('id')
        if first_match_id:
            time.sleep(2)
            test_mark_as_read(first_match_id)
            
            # 3. 再次获取，验证已读状态
            time.sleep(2)
            print("\n🔍 验证已读状态...")
            test_get_notifications()
    
    # 4. 模拟轮询
    print("\n" + "=" * 60)
    choice = input("是否开始模拟轮询? (y/n): ")
    if choice.lower() == 'y':
        simulate_polling()

if __name__ == "__main__":
    main()