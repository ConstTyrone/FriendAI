#!/usr/bin/env python3
"""
检查当前的未读通知
"""

import urllib.request
import json
import base64
from datetime import datetime

# API基础配置
API_BASE = "https://weixin.dataelem.com"
TEST_USER = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"

def get_token(user_id):
    """获取测试用户的token"""
    token = base64.b64encode(f"user:{user_id}".encode()).decode()
    return f"Bearer {token}"

def check_notifications():
    """检查未读通知"""
    print(f"🔍 检查用户 {TEST_USER} 的未读通知...")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 构建请求
    url = f"{API_BASE}/api/notifications/matches?unread_only=true&limit=10"
    headers = {
        "Authorization": get_token(TEST_USER),
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            print(f"✅ API调用成功!")
            print(f"\n📊 通知统计:")
            print(f"   未读数量: {data.get('unread_count', 0)}")
            print(f"   有新匹配: {data.get('has_new', False)}")
            
            matches = data.get('matches', [])
            if matches:
                print(f"\n📋 未读匹配列表 (共 {len(matches)} 个):")
                for i, match in enumerate(matches, 1):
                    print(f"\n   [{i}] {match.get('intent_name', '未知意图')}")
                    print(f"       联系人: {match.get('profile_name', '未知')}")
                    print(f"       匹配度: {match.get('match_score', 0)*100:.0f}%")
                    print(f"       匹配ID: {match.get('id')}")
                    print(f"       创建时间: {match.get('created_at', '')}")
                    print(f"       是否已读: {match.get('is_read', False)}")
                    
                    explanation = match.get('explanation', '')
                    if explanation:
                        print(f"       说明: {explanation[:100]}...")
            else:
                print("\n   ℹ️ 暂无未读匹配")
                
            return data
            
    except urllib.error.HTTPError as e:
        print(f"❌ API调用失败: HTTP {e.code}")
        print(f"   错误信息: {e.read().decode()}")
        return None
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

def check_all_matches():
    """检查所有匹配（包括已读）"""
    print(f"\n\n🔍 检查所有匹配记录...")
    print("=" * 60)
    
    # 构建请求（不限制unread_only）
    url = f"{API_BASE}/api/notifications/matches?unread_only=false&limit=20"
    headers = {
        "Authorization": get_token(TEST_USER),
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            matches = data.get('matches', [])
            if matches:
                print(f"📋 所有匹配记录 (最新 {len(matches)} 个):")
                for i, match in enumerate(matches[:5], 1):  # 只显示前5个
                    print(f"\n   [{i}] {match.get('intent_name', '未知意图')}")
                    print(f"       联系人: {match.get('profile_name', '未知')}")
                    print(f"       匹配度: {match.get('match_score', 0)*100:.0f}%")
                    print(f"       状态: {'已读' if match.get('is_read') else '未读'}")
                    print(f"       创建时间: {match.get('created_at', '')}")
            else:
                print("   ℹ️ 暂无任何匹配记录")
                
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("🧪 通知系统检查")
    print("=" * 60)
    
    # 检查未读通知
    result = check_notifications()
    
    # 检查所有匹配
    check_all_matches()
    
    print("\n" + "=" * 60)
    print("提示:")
    print("1. 如果有未读通知，小程序应该会在5秒内检测到")
    print("2. 小程序会振动提醒并显示弹窗")
    print("3. Tab栏会显示未读数量的红点")
    print("=" * 60)

if __name__ == "__main__":
    main()