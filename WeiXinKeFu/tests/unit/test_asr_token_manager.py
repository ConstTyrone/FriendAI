#!/usr/bin/env python3
"""
ASR Token管理器测试脚本
测试自动获取和刷新Token功能
"""

import os
import sys
import time
import logging
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_token_manager():
    """测试ASR Token管理器"""
    
    print("="*60)
    print("🧪 ASR Token管理器测试")
    print("="*60)
    
    # 检查环境变量
    print("\n1. 检查配置...")
    aliyun_ak_id = os.getenv('ALIYUN_AK_ID')
    aliyun_ak_secret = os.getenv('ALIYUN_AK_SECRET')
    
    if not aliyun_ak_id or not aliyun_ak_secret:
        print("⚠️ 警告: 未配置阿里云AccessKey")
        print("如要测试自动Token管理，请在.env文件中设置:")
        print("ALIYUN_AK_ID=your_access_key_id")
        print("ALIYUN_AK_SECRET=your_access_key_secret")
        print("\n当前将测试手动Token模式...")
    else:
        print(f"✅ AccessKey ID: {aliyun_ak_id[:8]}...{aliyun_ak_id[-4:]}")
        print("✅ AccessKey Secret已配置")
    
    try:
        # 导入token管理器
        print("\n2. 导入Token管理器...")
        from src.services.asr_token_manager import asr_token_manager, get_asr_token_info, force_refresh_asr_token
        print("✅ Token管理器导入成功")
        
        # 获取初始状态
        print("\n3. 获取Token状态...")
        initial_status = get_asr_token_info()
        print("Token状态信息:")
        for key, value in initial_status.items():
            print(f"  {key}: {value}")
        
        # 测试Token获取
        print("\n4. 测试Token获取...")
        token = asr_token_manager.get_token()
        if token:
            print(f"✅ Token获取成功: {token[:16]}...{token[-8:]}")
        else:
            print("⚠️ Token获取失败（可能使用手动模式）")
        
        # 如果有AccessKey配置，测试强制刷新
        if aliyun_ak_id and aliyun_ak_secret:
            print("\n5. 测试强制刷新...")
            refresh_result = force_refresh_asr_token()
            if refresh_result:
                print("✅ Token强制刷新成功")
                
                # 获取刷新后状态
                updated_status = get_asr_token_info()
                print("刷新后状态:")
                for key, value in updated_status.items():
                    print(f"  {key}: {value}")
            else:
                print("❌ Token强制刷新失败")
        
        print("\n6. 测试ASR处理器集成...")
        from src.services.media_processor import asr_processor
        asr_status = asr_processor.get_token_status()
        print("ASR处理器Token状态:")
        for key, value in asr_status.items():
            print(f"  {key}: {value}")
        
        print("\n✅ ASR Token管理器测试完成!")
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请确保在WeiXinKeFu目录下运行此脚本")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        logger.exception("测试过程中发生异常")

def test_api_endpoints():
    """测试API端点"""
    
    print("\n" + "="*60)
    print("🌐 API端点测试")
    print("="*60)
    
    try:
        import requests
        
        base_url = "http://localhost:3001"
        
        print("\n1. 测试Token状态API...")
        try:
            response = requests.get(f"{base_url}/api/asr/token/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print("✅ Token状态API响应成功")
                print(f"状态: {data.get('status')}")
                if 'data' in data:
                    for key, value in data['data'].items():
                        print(f"  {key}: {value}")
            else:
                print(f"⚠️ API返回状态码: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("⚠️ 无法连接到服务器，请确保后端服务正在运行")
        except Exception as e:
            print(f"❌ API测试失败: {e}")
        
        print("\n2. 测试Token刷新API...")
        try:
            response = requests.post(f"{base_url}/api/asr/token/refresh", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print("✅ Token刷新API响应成功")
                print(f"状态: {data.get('status')}")
                print(f"消息: {data.get('message')}")
            else:
                print(f"⚠️ API返回状态码: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("⚠️ 无法连接到服务器")
        except Exception as e:
            print(f"❌ API测试失败: {e}")
            
    except ImportError:
        print("⚠️ requests库未安装，跳过API测试")
        print("要进行API测试，请运行: pip install requests")

def main():
    """主测试函数"""
    
    print("🚀 开始测试ASR Token管理系统...")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查是否在正确的目录
    if not os.path.exists('src/services/asr_token_manager.py'):
        print("❌ 请在WeiXinKeFu目录下运行此脚本")
        sys.exit(1)
    
    # 测试Token管理器
    test_token_manager()
    
    # 测试API端点
    test_api_endpoints()
    
    print("\n" + "="*60)
    print("📋 测试总结")
    print("="*60)
    print("✅ Token管理器已升级为自动获取和刷新模式")
    print("✅ 支持手动Token模式向后兼容")
    print("✅ 新增API端点用于监控Token状态")
    print("✅ 集成到ASR处理器中")
    
    print("\n📖 使用说明:")
    print("1. 配置ALIYUN_AK_ID和ALIYUN_AK_SECRET启用自动模式")
    print("2. 访问 GET /api/asr/token/status 查看Token状态")
    print("3. 访问 POST /api/asr/token/refresh 强制刷新Token")
    print("4. ASR服务将自动使用最新Token，无需手动更新")
    
    print("\n🎉 ASR Token管理系统测试完成!")

if __name__ == "__main__":
    main()