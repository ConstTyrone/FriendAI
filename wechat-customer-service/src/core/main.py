# main.py
"""
微信客服用户画像提取系统 - 简化版
只包含微信客服消息处理核心功能
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse
import xml.etree.ElementTree as ET
import urllib.parse
import logging
import sys

from ..services.wework_client import wework_client
from ..handlers.message_handler import classify_and_handle_message, parse_message, handle_wechat_kf_event

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
app = FastAPI(title="微信客服用户画像系统（简化版）", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "微信客服用户画像系统",
        "version": "1.0.0",
        "description": "简化版 - 专注于微信客服消息处理和AI用户画像分析",
        "features": {
            "redis_state_management": "✅ 已启用",
            "async_processing": "✅ 已启用",
            "ai_analysis": "✅ 通义千问"
        }
    }


@app.get("/health")
async def health_check():
    """
    健康检查端点

    检查系统各组件状态：Redis、数据库、AI服务等
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {}
    }

    # 检查Redis连接
    try:
        from ..services.redis_state_manager import state_manager
        redis_health = state_manager.health_check()
        health_status["components"]["redis"] = redis_health
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "message": str(e)
        }

    # 检查数据库连接
    try:
        test_conn = db.get_connection()
        test_conn.__enter__()
        test_conn.__exit__(None, None, None)
        health_status["components"]["database"] = {
            "status": "healthy",
            "type": "sqlite"
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["status"] = "degraded"

    # 整体状态判断
    component_statuses = [c.get("status") for c in health_status["components"].values()]
    if "unhealthy" in component_statuses:
        health_status["status"] = "unhealthy"
        status_code = 503
    elif "degraded" in component_statuses:
        health_status["status"] = "degraded"
        status_code = 200
    else:
        status_code = 200

    return JSONResponse(content=health_status, status_code=status_code)

@app.get("/wework/callback")
async def wework_verify(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    """微信客服/企业微信验证回调"""
    logger.info(f"URL验证请求")
    logger.info(f"参数详情 - msg_signature: {msg_signature}, timestamp: {timestamp}, nonce: {nonce}, echostr: {echostr}")

    try:
        # URL解码echostr
        echostr_decoded = urllib.parse.unquote(echostr)
        logger.info(f"解码后的echostr: {echostr_decoded}")

        # 验证签名 - 微信客服URL验证不包含echostr参数
        # 为了兼容两种平台，我们尝试两种方式
        is_valid = wework_client.verify_signature(msg_signature, timestamp, nonce)
        # 如果标准验证失败，尝试包含echostr的验证（企业微信可能需要）
        if not is_valid:
            is_valid = wework_client.verify_signature(msg_signature, timestamp, nonce, echostr_decoded)

        if not is_valid:
            logger.error("签名验证失败")
            raise HTTPException(status_code=400, detail="签名验证失败")

        # 解密echostr
        decrypted = wework_client.decrypt_message(echostr_decoded)
        logger.info("URL验证成功")

        # 微信客服/企业微信回调验证需要返回解密后的明文
        return PlainTextResponse(decrypted)

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"处理请求时发生错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {e}")


@app.post("/wework/callback")
async def wework_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str,
    timestamp: str,
    nonce: str
):
    """
    微信客服/企业微信消息回调（异步处理版本）

    快速响应微信服务器（<1秒），然后在后台异步处理消息
    解决同步阻塞导致的超时问题
    """
    try:
        # 获取请求体
        body = await request.body()
        logger.info("收到消息回调")

        # 如果请求体为空，记录警告
        if not body:
            logger.warning("收到空的请求体")
            return PlainTextResponse("success")

        root = ET.fromstring(body.decode('utf-8'))
        encrypt_msg = root.find('Encrypt').text

        # 验证签名（快速验证，<100ms）
        is_valid = wework_client.verify_signature(msg_signature, timestamp, nonce, encrypt_msg)

        if not is_valid:
            logger.error("签名验证失败")
            raise HTTPException(status_code=400, detail="签名验证失败")

        # 解密消息（快速解密，<100ms）
        decrypted_xml = wework_client.decrypt_message(encrypt_msg)

        # 解析消息（快速解析，<50ms）
        message = parse_message(decrypted_xml)

        # 添加到后台任务异步处理（不阻塞响应）
        msg_type = message.get('MsgType')
        event = message.get('Event')

        if msg_type == 'event' and event == 'kf_msg_or_event':
            # 异步处理微信客服事件消息
            background_tasks.add_task(handle_wechat_kf_event_async, message)
        else:
            # 异步处理普通消息
            background_tasks.add_task(classify_and_handle_message_async, message)

        # 立即返回成功（总耗时 <200ms）
        logger.info("✅ 消息已接收，正在后台处理")
        return PlainTextResponse("success")

    except ET.ParseError as e:
        logger.error(f"XML解析失败: {e}")
        return PlainTextResponse("fail")
    except Exception as e:
        logger.error(f"消息接收失败: {e}", exc_info=True)
        return PlainTextResponse("fail")


async def handle_wechat_kf_event_async(message: dict):
    """异步处理微信客服事件消息"""
    try:
        logger.info("🔄 开始异步处理微信客服事件")
        # 调用同步处理函数（在后台线程中执行）
        handle_wechat_kf_event(message)
        logger.info("✅ 微信客服事件处理完成")
    except Exception as e:
        logger.error(f"❌ 异步处理微信客服事件失败: {e}", exc_info=True)


async def classify_and_handle_message_async(message: dict):
    """异步处理普通消息"""
    try:
        logger.info("🔄 开始异步处理普通消息")
        # 调用同步处理函数（在后台线程中执行）
        classify_and_handle_message(message)
        logger.info("✅ 普通消息处理完成")
    except Exception as e:
        logger.error(f"❌ 异步处理普通消息失败: {e}", exc_info=True)


@app.get("/wechat/callback")
async def wechat_verify(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    """微信客服/企业微信验证回调 - 兼容路由"""
    return await wework_verify(msg_signature, timestamp, nonce, echostr)


@app.post("/wechat/callback")
async def wechat_callback(request: Request, msg_signature: str, timestamp: str, nonce: str):
    """微信消息回调 - 兼容路由"""
    return await wework_callback(request, msg_signature, timestamp, nonce)


logger.info("FastAPI应用启动完成 - 微信客服用户画像系统（简化版）")
logger.info("已注册端点: GET/POST /wework/callback, GET/POST /wechat/callback")