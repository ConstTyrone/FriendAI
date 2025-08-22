#!/usr/bin/env python3
"""
快速配置验证脚本
验证阿里云AccessKey配置是否正确读取
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_config():
    """检查配置"""
    
    print("🔍 检查环境变量配置...")
    print("=" * 50)
    
    # 检查所有可能的环境变量名
    print("\n📋 原始环境变量检查:")
    
    aliyun_ak_id_1 = os.getenv('ALIYUN_AK_ID')
    aliyun_ak_secret_1 = os.getenv('ALIYUN_AK_SECRET')
    
    accesskey_id = os.getenv('accessKeyId')
    accesskey_secret = os.getenv('accessKeySecret')
    
    print(f"ALIYUN_AK_ID: {aliyun_ak_id_1[:10] + '...' if aliyun_ak_id_1 else 'None'}")
    print(f"ALIYUN_AK_SECRET: {aliyun_ak_secret_1[:10] + '...' if aliyun_ak_secret_1 else 'None'}")
    print(f"accessKeyId: {accesskey_id[:10] + '...' if accesskey_id else 'None'}")
    print(f"accessKeySecret: {accesskey_secret[:10] + '...' if accesskey_secret else 'None'}")
    
    # 测试配置类
    print("\n🔧 配置类读取测试:")
    try:
        # 导入配置
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from src.config.config import config
        
        print(f"config.aliyun_ak_id: {config.aliyun_ak_id[:10] + '...' if config.aliyun_ak_id else 'None'}")
        print(f"config.aliyun_ak_secret: {config.aliyun_ak_secret[:10] + '...' if config.aliyun_ak_secret else 'None'}")
        
        if config.aliyun_ak_id and config.aliyun_ak_secret:
            print("✅ AccessKey配置读取成功！")
            return True
        else:
            print("❌ AccessKey配置读取失败！")
            return False
            
    except Exception as e:
        print(f"❌ 配置导入失败: {e}")
        return False

def main():
    """主函数"""
    
    print("🚀 阿里云AccessKey配置验证")
    print(f"当前目录: {os.getcwd()}")
    print(f"脚本位置: {os.path.abspath(__file__)}")
    
    # 检查.env文件是否存在
    env_file = ".env"
    if os.path.exists(env_file):
        print(f"✅ 找到环境变量文件: {env_file}")
    else:
        print(f"⚠️ 未找到环境变量文件: {env_file}")
        print("请创建.env文件并添加AccessKey配置")
    
    # 检查配置
    success = check_config()
    
    if success:
        print("\n🎉 配置验证成功！可以启用ASR自动Token管理。")
    else:
        print("\n📝 配置指南:")
        print("请在.env文件中添加以下任一组配置:")
        print("方式1:")
        print("ALIYUN_AK_ID=your_access_key_id")
        print("ALIYUN_AK_SECRET=your_access_key_secret")
        print("\n方式2:")
        print("accessKeyId=your_access_key_id")
        print("accessKeySecret=your_access_key_secret")

if __name__ == "__main__":
    main()