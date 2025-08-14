#!/usr/bin/env python3
"""
微信客服用户画像系统启动脚本
"""
import sys
import os
import uvicorn
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 加载环境变量
load_dotenv()

# 显示AI配置状态
print("\n" + "="*60)
print("🌏 启动微信客服用户画像系统")
print("="*60)

# 检查AI配置
qwen_key = os.getenv('QWEN_API_KEY')
if qwen_key:
    print(f"✅ QWEN API密钥已配置: {qwen_key[:10]}...{qwen_key[-5:]}")
else:
    print("⚠️  QWEN API密钥未配置，将使用基础匹配模式")
    print("   要启用AI功能，请在.env文件中设置: QWEN_API_KEY=你的密钥")

# 检查依赖
try:
    import numpy
    print("✅ NumPy已安装")
except ImportError:
    print("❌ NumPy未安装 - 请运行: pip install numpy")

try:
    import aiohttp
    print("✅ AioHTTP已安装")
except ImportError:
    print("❌ AioHTTP未安装 - 请运行: pip install aiohttp")

print("="*60 + "\n")

# 导入应用
from src.core.main import app

def main():
    """启动应用"""
    port = int(os.getenv('LOCAL_SERVER_PORT', 3001))
    
    print(f"""
    🚀 微信客服用户画像系统启动中...
    
    📋 服务信息:
    - 端口: {port}
    - 环境: {'生产' if os.getenv('ENVIRONMENT') == 'production' else '开发'}
    - API文档: http://localhost:{port}/docs
    - 前端测试: frontend-test/index.html
    
    💡 提示:
    - 按 Ctrl+C 停止服务
    - 查看 docs/ 目录获取完整API文档
    """)
    
    uvicorn.run(
        "src.core.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[project_root],
        log_level="info"
    )

if __name__ == "__main__":
    main()