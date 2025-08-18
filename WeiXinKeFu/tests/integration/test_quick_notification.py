#!/usr/bin/env python3
"""
快速测试通知系统 - 创建联系人并检查通知
"""

import requests
import json
import time
import base64

# API基础配置
API_BASE = "https://weixin.dataelem.com"  # 使用服务器地址
TEST_USER = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"

def get_token(user_id):
    """获取测试用户的token"""
    token = base64.b64encode(f"user:{user_id}".encode()).decode()
    return f"Bearer {token}"

def create_test_contact():
    """创建一个测试联系人触发意图匹配"""
    print("🔄 创建测试联系人...")
    
    headers = {
        "Authorization": get_token(TEST_USER),
        "Content-Type": "application/json"
    }
    
    # 创建一个符合意图的联系人
    contact_data = {
        "profile_name": f"测试创业者_{int(time.time())}",
        "wechat_id": f"test_{int(time.time())}",
        "tags": ["创业", "技术", "AI"],
        "basic_info": {
            "location": "上海",
            "company": "创业公司",
            "position": "技术合伙人",
            "age": 30,
            "profession": "全栈工程师"
        },
        "recent_activities": [
            {
                "activity": "正在寻找创业合伙人",
                "date": "2025-01-15"
            }
        ],
        "raw_messages": ["我是一个技术创业者，正在寻找合作机会"]
    }
    
    response = requests.post(
        f"{API_BASE}/api/contacts",
        headers=headers,
        json=contact_data
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 联系人创建成功: {data.get('profile_name')} (ID: {data.get('id')})")
        return data.get('id')
    else:
        print(f"❌ 创建失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
        return None

def check_notifications(wait_time=10):
    """检查通知（等待后端处理）"""
    print(f"\n⏳ 等待 {wait_time} 秒让后端完成意图匹配...")
    time.sleep(wait_time)
    
    print("🔍 检查通知...")
    
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
        print(f"✅ 获取通知成功!")
        print(f"   未读数量: {data.get('unread_count', 0)}")
        print(f"   有新匹配: {data.get('has_new', False)}")
        
        matches = data.get('matches', [])
        if matches:
            print(f"\n📋 最新匹配:")
            for i, match in enumerate(matches[:3], 1):
                print(f"\n   {i}. {match.get('intent_name', '未知意图')}")
                print(f"      联系人: {match.get('profile_name', '未知')}")
                print(f"      匹配度: {match.get('match_score', 0):.0%}")
                print(f"      说明: {match.get('explanation', '')[:100]}")
        else:
            print("   暂无新匹配")
        
        return data
    else:
        print(f"❌ 获取通知失败: {response.status_code}")
        print(f"   错误信息: {response.text}")
        return None

def monitor_notifications(duration=30):
    """持续监控通知（模拟小程序轮询）"""
    print(f"\n🔄 开始监控通知（持续 {duration} 秒，每5秒检查一次）...")
    print("=" * 60)
    
    start_time = time.time()
    last_count = 0
    check_count = 0
    
    while time.time() - start_time < duration:
        check_count += 1
        print(f"\n[检查 #{check_count}] {time.strftime('%H:%M:%S')}")
        
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
                print(f"🎯 发现 {new_count} 个新匹配! 📳 叮~")
                print(f"   当前未读总数: {unread_count}")
                
                matches = data.get('matches', [])
                if matches:
                    latest = matches[0]
                    print(f"   最新: {latest.get('intent_name')} - {latest.get('profile_name')}")
                    print(f"   匹配度: {latest.get('match_score', 0):.0%}")
            elif unread_count > 0:
                print(f"   未读匹配: {unread_count} 个")
            else:
                print(f"   暂无未读匹配")
            
            last_count = unread_count
        else:
            print(f"❌ 检查失败: {response.status_code}")
        
        time.sleep(5)  # 5秒轮询一次
    
    print("\n" + "=" * 60)
    print("监控结束")

def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 快速通知系统测试")
    print("=" * 60)
    
    # 1. 创建测试联系人
    contact_id = create_test_contact()
    
    if contact_id:
        # 2. 检查通知
        check_notifications(wait_time=5)
        
        # 3. 持续监控
        print("\n" + "=" * 60)
        choice = input("是否开始持续监控? (y/n): ")
        if choice.lower() == 'y':
            monitor_notifications(duration=30)
    else:
        print("\n❌ 测试失败：无法创建联系人")

if __name__ == "__main__":
    main()