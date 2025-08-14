#!/usr/bin/env python3
"""
API接口测试脚本
用于测试前端API接口的基本功能
"""

import requests
import json
import base64
import time

class APITester:
    def __init__(self, base_url="http://localhost:3001"):
        self.base_url = base_url
        self.token = None
        self.wechat_user_id = "test_user_001"
    
    def print_response(self, response, title):
        """打印响应结果"""
        print(f"\n{'='*50}")
        print(f"📋 {title}")
        print(f"{'='*50}")
        print(f"状态码: {response.status_code}")
        try:
            data = response.json()
            print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        except:
            print(f"响应内容: {response.text}")
        print("-" * 50)
    
    def test_login(self):
        """测试登录接口"""
        url = f"{self.base_url}/api/login"
        data = {"wechat_user_id": self.wechat_user_id}
        
        response = requests.post(url, json=data)
        self.print_response(response, "用户登录测试")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                self.token = result.get('token')
                print(f"✅ 登录成功，Token: {self.token}")
                return True
        
        print("❌ 登录失败")
        return False
    
    def get_headers(self):
        """获取认证头"""
        if not self.token:
            raise Exception("请先登录获取Token")
        return {"Authorization": f"Bearer {self.token}"}
    
    def test_get_profiles(self):
        """测试获取画像列表"""
        url = f"{self.base_url}/api/profiles"
        params = {"page": 1, "page_size": 10}
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        self.print_response(response, "获取画像列表测试")
        
        return response.status_code == 200
    
    def test_get_stats(self):
        """测试获取统计信息"""
        url = f"{self.base_url}/api/stats"
        
        response = requests.get(url, headers=self.get_headers())
        self.print_response(response, "获取统计信息测试")
        
        return response.status_code == 200
    
    def test_get_user_info(self):
        """测试获取用户信息"""
        url = f"{self.base_url}/api/user/info"
        
        response = requests.get(url, headers=self.get_headers())
        self.print_response(response, "获取用户信息测试")
        
        return response.status_code == 200
    
    def test_search_profiles(self):
        """测试搜索功能"""
        url = f"{self.base_url}/api/search"
        params = {"q": "测试", "limit": 5}
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        self.print_response(response, "搜索画像测试")
        
        return response.status_code == 200
    
    def test_get_recent(self):
        """测试获取最近画像"""
        url = f"{self.base_url}/api/recent"
        params = {"limit": 5}
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        self.print_response(response, "获取最近画像测试")
        
        return response.status_code == 200
    
    def test_check_updates(self):
        """测试检查更新"""
        url = f"{self.base_url}/api/updates/check"
        
        response = requests.get(url, headers=self.get_headers())
        self.print_response(response, "检查更新测试")
        
        return response.status_code == 200
    
    def test_server_status(self):
        """测试服务器状态"""
        url = f"{self.base_url}/"
        
        try:
            response = requests.get(url, timeout=5)
            self.print_response(response, "服务器状态测试")
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            print(f"❌ 无法连接到服务器: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始API接口测试")
        print(f"测试服务器: {self.base_url}")
        print(f"测试用户: {self.wechat_user_id}")
        
        # 测试服务器状态
        if not self.test_server_status():
            print("❌ 服务器未启动，请先启动服务器")
            return
        
        # 测试登录
        if not self.test_login():
            print("❌ 登录失败，跳过后续测试")
            return
        
        # 测试其他接口
        tests = [
            ("获取画像列表", self.test_get_profiles),
            ("获取统计信息", self.test_get_stats),
            ("获取用户信息", self.test_get_user_info),
            ("搜索画像", self.test_search_profiles),
            ("获取最近画像", self.test_get_recent),
            ("检查更新", self.test_check_updates),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    print(f"✅ {test_name} - 通过")
                    passed += 1
                else:
                    print(f"❌ {test_name} - 失败")
                    failed += 1
            except Exception as e:
                print(f"❌ {test_name} - 异常: {e}")
                failed += 1
            
            time.sleep(0.5)  # 避免请求过快
        
        print(f"\n{'='*50}")
        print(f"📊 测试结果总结")
        print(f"{'='*50}")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"📈 成功率: {passed/(passed+failed)*100:.1f}%")

def main():
    """主函数"""
    print("微信客服用户画像系统 - API接口测试工具")
    
    # 检查服务器地址
    base_url = input("请输入服务器地址 (默认: http://localhost:3001): ").strip()
    if not base_url:
        base_url = "http://localhost:3001"
    
    # 检查用户ID
    user_id = input("请输入测试用户微信ID (默认: test_user_001): ").strip()
    if not user_id:
        user_id = "test_user_001"
    
    # 创建测试器并运行测试
    tester = APITester(base_url)
    tester.wechat_user_id = user_id
    tester.run_all_tests()

if __name__ == "__main__":
    main()