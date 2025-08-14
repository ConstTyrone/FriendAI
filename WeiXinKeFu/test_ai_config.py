#!/usr/bin/env python3
"""
测试AI配置和环境变量
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_env_config():
    """测试环境配置"""
    print("=" * 60)
    print("测试AI配置")
    print("=" * 60)
    
    # 检查QWEN API配置
    api_key = os.getenv('QWEN_API_KEY')
    api_endpoint = os.getenv('QWEN_API_ENDPOINT', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    
    print(f"\nQWEN_API_KEY: {'已配置' if api_key else '未配置'}")
    if api_key:
        print(f"  密钥长度: {len(api_key)} 字符")
        print(f"  前10位: {api_key[:10]}...")
        print(f"  后5位: ...{api_key[-5:]}")
    else:
        print("  ❌ 请在.env文件中设置QWEN_API_KEY")
    
    print(f"\nQWEN_API_ENDPOINT: {api_endpoint}")
    
    # 检查其他配置
    print("\n其他配置:")
    print(f"  DATABASE_PATH: {os.getenv('DATABASE_PATH', 'user_profiles.db')}")
    print(f"  WEWORK_CORP_ID: {'已配置' if os.getenv('WEWORK_CORP_ID') else '未配置'}")
    
    # 检查.env文件
    env_file = '.env'
    if os.path.exists(env_file):
        print(f"\n.env文件: 存在")
        with open(env_file, 'r') as f:
            lines = f.readlines()
            qwen_line = None
            for line in lines:
                if 'QWEN_API_KEY' in line and not line.strip().startswith('#'):
                    qwen_line = line.strip()
                    break
            
            if qwen_line:
                print(f"  找到QWEN_API_KEY配置行")
                if '=' in qwen_line:
                    key_part = qwen_line.split('=', 1)[1].strip()
                    if key_part:
                        print(f"  配置值长度: {len(key_part)} 字符")
                    else:
                        print(f"  ⚠️ 配置值为空")
            else:
                print(f"  ❌ 未找到QWEN_API_KEY配置")
    else:
        print(f"\n❌ .env文件不存在")
    
    return api_key is not None

def test_simple_matching():
    """测试简单的规则匹配"""
    print("\n" + "=" * 60)
    print("测试规则匹配（不使用AI）")
    print("=" * 60)
    
    # 模拟意图
    keywords = ['AI', '技术', '专家']
    
    # 模拟联系人
    profiles = [
        {
            'name': '张三',
            'company': 'AI科技公司',
            'position': '技术总监',
            'text': 'AI科技公司 技术总监'
        },
        {
            'name': '李四',
            'company': '传统制造业',
            'position': '销售经理',
            'text': '传统制造业 销售经理'
        },
        {
            'name': '王五',
            'company': '人工智能研究院',
            'position': 'AI专家',
            'text': '人工智能研究院 AI专家'
        }
    ]
    
    print(f"\n关键词: {keywords}")
    print("\n联系人匹配结果:")
    
    for profile in profiles:
        profile_text = profile['text'].lower()
        matched = []
        for keyword in keywords:
            if keyword.lower() in profile_text:
                matched.append(keyword)
        
        score = len(matched) / len(keywords) if keywords else 0
        print(f"\n  {profile['name']} ({profile['company']} - {profile['position']})")
        print(f"    匹配关键词: {matched}")
        print(f"    匹配分数: {score:.2f}")
        if score >= 0.5:
            print(f"    ✅ 符合条件")
        else:
            print(f"    ❌ 不符合")

def main():
    """主函数"""
    print("\n🔧 开始测试AI配置\n")
    
    # 测试环境配置
    has_api_key = test_env_config()
    
    # 测试规则匹配
    test_simple_matching()
    
    print("\n" + "=" * 60)
    print("诊断结果")
    print("=" * 60)
    
    if has_api_key:
        print("\n✅ API密钥已配置")
        print("如果AI匹配仍不工作，可能的原因：")
        print("1. API密钥无效或过期")
        print("2. 网络连接问题")
        print("3. numpy等依赖未安装（pip install numpy）")
        print("4. 向量服务初始化失败")
    else:
        print("\n❌ API密钥未配置")
        print("系统将使用基于规则的匹配（关键词匹配）")
        print("要启用AI匹配，请在.env文件中设置：")
        print("QWEN_API_KEY=你的API密钥")
    
    print("\n建议的下一步：")
    print("1. 确认.env文件中QWEN_API_KEY的值正确")
    print("2. 安装依赖：pip install -r requirements.txt")
    print("3. 重启服务：python run.py")
    print("4. 检查后端日志中的错误信息")

if __name__ == "__main__":
    main()