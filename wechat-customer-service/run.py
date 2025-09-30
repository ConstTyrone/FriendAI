#!/usr/bin/env python
# run.py
"""
微信客服用户画像系统启动脚本
"""
import uvicorn
import os

if __name__ == "__main__":
    # 从环境变量获取端口，默认3001
    port = int(os.getenv('LOCAL_SERVER_PORT', '3001'))

    print(f"🚀 启动微信客服用户画像系统...")
    print(f"📡 监听端口: {port}")
    print(f"🌐 访问地址: http://0.0.0.0:{port}")
    print(f"📝 API文档: http://0.0.0.0:{port}/docs")
    print("")

    uvicorn.run(
        "src.core.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )