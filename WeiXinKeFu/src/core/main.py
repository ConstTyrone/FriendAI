# main_new.py - 重构后的主应用文件
"""
重构后的FastAPI主应用文件
将原main.py中的路由按功能域拆分到不同模块
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

# 导入路由模块
from .routes.wechat import router as wechat_router
from .routes.auth import router as auth_router
from .routes.utils import router as utils_router
from .routes.profiles import router as profiles_router
from .routes.intents import router as intents_router
from .routes.relationships import router as relationships_router
from .routes.ai_services import router as ai_services_router
from .routes.notifications import router as notifications_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="微信客服用户画像系统", version="2.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该指定具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(wechat_router, tags=["微信回调"])
app.include_router(auth_router, tags=["用户认证"])
app.include_router(utils_router, tags=["工具和监控"])
app.include_router(profiles_router, tags=["用户画像"])
app.include_router(intents_router, tags=["意图管理"])
app.include_router(relationships_router, tags=["关系管理"])
app.include_router(ai_services_router, tags=["AI服务"])
app.include_router(notifications_router, tags=["通知管理"])

# 注册绑定API路由
try:
    from .binding_api import router as binding_router
    app.include_router(binding_router, tags=["微信绑定"])
    logger.info("绑定API路由注册成功")
except Exception as e:
    logger.warning(f"绑定API路由注册失败: {e}")

logger.info("FastAPI应用启动完成 - 重构版本")
logger.info("已注册路由模块: wechat, auth, utils, profiles, intents, relationships, ai_services, notifications")