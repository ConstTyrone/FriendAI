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