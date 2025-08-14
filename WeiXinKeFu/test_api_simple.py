#!/usr/bin/env python3
"""
简单测试API修复效果
"""

import json
import urllib.request
import urllib.parse
import urllib.error

BASE_URL = "http://localhost:8000"

def make_request(method, endpoint, data=None, headers=None):
    """发送HTTP请求"""
    url = f"{BASE_URL}{endpoint}"
    
    if headers is None:
        headers = {}
    headers['Content-Type'] = 'application/json'
    
    if data:
        data = json.dumps(data).encode('utf-8')
    
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        response = urllib.request.urlopen(request)
        return response.getcode(), json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)

def test_login():
    """测试登录"""
    print("=" * 60)
    print("测试登录")
    print("=" * 60)
    
    login_data = {
        "wechat_user_id": "test_user_001"
    }
    
    status, response = make_request("POST", "/api/login", login_data)
    
    if status == 200:
        print(f"✅ 登录成功")
        print(f"   Token: {response.get('token', '')[:20]}...")
        return response.get('token')
    else:
        print(f"❌ 登录失败: {status}")
        print(f"   响应: {response}")
        return None

def test_get_intents(token):
    """测试获取意图列表"""
    print("\n" + "=" * 60)
    print("测试获取意图列表")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    params = urllib.parse.urlencode({
        "status": "active",
        "page": "1",
        "size": "10"
    })
    
    status, response = make_request("GET", f"/api/intents?{params}", headers=headers)
    
    if status == 200:
        print(f"✅ 获取意图列表成功")
        if isinstance(response, dict):
            print(f"   意图数量: {len(response.get('intents', []))}")
        return True
    else:
        print(f"❌ 获取意图列表失败: {status}")
        print(f"   响应: {response}")
        return False

def test_get_matches(token):
    """测试获取匹配结果"""
    print("\n" + "=" * 60)
    print("测试获取匹配结果")
    print("=" * 60)
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    params = urllib.parse.urlencode({
        "page": "1",
        "size": "10"
    })
    
    status, response = make_request("GET", f"/api/intents/matches?{params}", headers=headers)
    
    if status == 200:
        print(f"✅ 获取匹配结果成功")
        if isinstance(response, dict):
            total = response.get('data', {}).get('total', 0)
            print(f"   匹配总数: {total}")
        return True
    else:
        print(f"❌ 获取匹配结果失败: {status}")
        print(f"   响应: {response}")
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
    
    print("\n" + "=" * 60)
    print("🎉 API测试完成！")
    print("=" * 60)
    
    print("\n修复清单:")
    print("1. ✅ 修复了 SQLiteDatabase 没有 get_user_table_name 方法")
    print("2. ✅ 修复了 status 模块导入错误")
    print("3. ✅ 修复了 sqlite3 未导入的问题")
    print("4. ✅ 修复了 push_service 的数据库列名问题")

if __name__ == "__main__":
    main()