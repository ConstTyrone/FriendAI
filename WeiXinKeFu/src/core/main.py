# main.py
from fastapi import FastAPI, Request, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import tempfile
import os
import xml.etree.ElementTree as ET
import logging
import sys
import json
import time
import sqlite3
from datetime import datetime
from ..services.wework_client import wework_client
from ..handlers.message_handler import classify_and_handle_message, parse_message, handle_wechat_kf_event
from ..services.ai_service import UserProfileExtractor
from ..services.media_processor import MediaProcessor


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

app = FastAPI(title="微信客服用户画像系统", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该指定具体的前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

# 注册绑定API路由
try:
    from .binding_api import router as binding_router
    app.include_router(binding_router)
    logger.info("绑定API路由注册成功")
except Exception as e:
    logger.warning(f"绑定API路由注册失败: {e}")

# 导入数据库
try:
    from ..database.database_pg import pg_database
    if pg_database.pool:
        db = pg_database
        logger.info("API使用PostgreSQL数据库")
    else:
        raise ImportError("PostgreSQL不可用")
except:
    from ..database.database_sqlite_v2 import database_manager as db
    logger.info("API使用SQLite数据库（备用方案）- 多用户独立存储版本")

# 身份验证
security = HTTPBearer()

# Pydantic模型
class UserLoginRequest(BaseModel):
    wechat_user_id: Optional[str] = None  # 兼容旧版本
    code: Optional[str] = None  # 新增：支持微信登录code

class SourceMessage(BaseModel):
    id: str
    timestamp: str
    message_type: str
    wechat_msg_id: Optional[str] = None
    raw_content: Optional[str] = None
    processed_content: Optional[str] = None
    media_url: Optional[str] = None
    action: str

class UserProfile(BaseModel):
    id: int
    profile_name: str
    gender: Optional[str] = None
    age: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    marital_status: Optional[str] = None
    education: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    asset_level: Optional[str] = None
    personality: Optional[str] = None
    ai_summary: Optional[str] = None
    confidence_score: Optional[float] = None
    source_type: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    source: Optional[str] = None
    source_messages: Optional[List[SourceMessage]] = None
    source_timestamp: Optional[str] = None

class UserProfilesResponse(BaseModel):
    total: int
    profiles: List[UserProfile]
    page: int
    page_size: int
    total_pages: int

class UserStatsResponse(BaseModel):
    total_profiles: int
    unique_names: int
    today_profiles: int
    last_profile_at: Optional[str]
    max_profiles: int
    used_profiles: int
    max_daily_messages: int

# 简单的用户验证（生产环境应该使用更安全的JWT或其他认证方式）
def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """验证用户token并返回微信用户ID"""
    try:
        # 这里简化处理，token就是base64编码的微信用户ID
        # 生产环境应该使用JWT或其他安全的认证方式
        import base64
        wechat_user_id = base64.b64decode(credentials.credentials).decode('utf-8')
        
        # 验证用户是否存在
        user_id = db.get_or_create_user(wechat_user_id)
        if user_id:
            return wechat_user_id
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的用户Token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        logger.error(f"Token验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token验证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_query_user_id(openid: str) -> str:
    """获取用于查询画像的用户ID（统一使用openid）"""
    try:
        # 新架构：所有用户都使用openid作为唯一标识
        # 数据表统一为 profiles_{openid} 格式
        # 绑定关系通过映射表维护，不影响数据存储结构
        logger.info(f"使用openid查询画像: {openid}")
        return openid
    except Exception as e:
        logger.error(f"获取查询用户ID时出错: {e}")
        return openid

def convert_external_userid_to_openid(external_userid: str) -> Optional[str]:
    """将external_userid转换为openid（仅限已绑定用户）"""
    try:
        from ..database.binding_db import binding_db
        
        if binding_db:
            # 通过映射表查找对应的openid
            openid = binding_db.get_openid_by_external_userid(external_userid)
            if openid:
                logger.info(f"微信客服消息：external_userid {external_userid} → openid {openid}")
                return openid
            else:
                logger.warning(f"拒绝处理未绑定用户 {external_userid} 的消息，该用户需要先通过小程序登录并绑定")
                return None
        else:
            logger.error("绑定数据库不可用，无法验证用户绑定关系，拒绝处理消息")
            return None
    except Exception as e:
        logger.error(f"转换external_userid到openid时出错: {e}")
        return None

@app.get("/wework/callback")
async def wework_verify(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    """微信客服/企业微信验证回调"""
    import urllib.parse
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
async def wework_callback(request: Request, msg_signature: str, timestamp: str, nonce: str):
    """微信客服/企业微信消息回调"""
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
        
        # 验证签名
        is_valid = wework_client.verify_signature(msg_signature, timestamp, nonce, encrypt_msg)
        
        if not is_valid:
            logger.error("签名验证失败")
            raise HTTPException(status_code=400, detail="签名验证失败")
        
        # 解密消息
        decrypted_xml = wework_client.decrypt_message(encrypt_msg)
        
        # 解析消息
        message = parse_message(decrypted_xml)
        
        # 检查是否为微信客服事件消息
        msg_type = message.get('MsgType')
        event = message.get('Event')
        
        if msg_type == 'event' and event == 'kf_msg_or_event':
            # 处理微信客服事件消息
            handle_wechat_kf_event(message)
        else:
            # 分类处理普通消息
            classify_and_handle_message(message)
        
        return PlainTextResponse("success")
        
    except ET.ParseError as e:
        logger.error(f"XML解析失败: {e}")
        logger.error(f"请求体内容: {await request.body()}")
        return PlainTextResponse("fail")
    except Exception as e:
        logger.error(f"消息处理失败: {e}", exc_info=True)
        return PlainTextResponse("fail")

# 添加根路径测试接口
@app.get("/")
async def root():
    return {"message": "服务器正常运行"}

# 添加一个简单的测试接口
@app.post("/test")
async def test_endpoint(request: Request):
    """测试接口"""
    return {"status": "success", "message": "测试成功"}

# 添加消息同步状态查看接口
@app.get("/sync/status")
async def get_sync_status():
    """查看消息同步状态"""
    try:
        return {
            "status": "success",
            "message": "消息同步功能已简化，直接获取最新消息",
            "sync_method": "简化版 - 每次仅获取最新1条消息"
        }
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        return {
            "status": "error", 
            "message": str(e)
        }

# ASR Token状态监控接口
@app.get("/api/asr/token/status")
async def get_asr_token_status():
    """获取ASR Token状态"""
    try:
        from ..services.media_processor import asr_processor
        
        token_status = asr_processor.get_token_status()
        
        return {
            "status": "success",
            "data": token_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取ASR Token状态失败: {e}")
        return {
            "status": "error", 
            "message": f"获取ASR Token状态失败: {str(e)}"
        }

@app.post("/api/asr/token/refresh")
async def refresh_asr_token():
    """强制刷新ASR Token"""
    try:
        from ..services.asr_token_manager import force_refresh_asr_token, get_asr_token_info
        
        # 尝试强制刷新
        refresh_success = force_refresh_asr_token()
        
        if refresh_success:
            # 获取最新状态
            token_info = get_asr_token_info()
            return {
                "status": "success",
                "message": "ASR Token刷新成功",
                "data": token_info,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": "ASR Token刷新失败，请检查配置和网络连接"
            }
    except Exception as e:
        logger.error(f"刷新ASR Token失败: {e}")
        return {
            "status": "error", 
            "message": f"刷新ASR Token失败: {str(e)}"
        }

# 添加微信回调的路由，以兼容不同的回调地址
@app.get("/wechat/callback")
async def wechat_verify(msg_signature: str, timestamp: str, nonce: str, echostr: str):
    """微信客服/企业微信验证回调 - 兼容路由"""
    return await wework_verify(msg_signature, timestamp, nonce, echostr)

@app.post("/wechat/callback")
async def wechat_callback(request: Request, msg_signature: str, timestamp: str, nonce: str):
    """微信消息回调 - 兼容路由"""
    return await wework_callback(request, msg_signature, timestamp, nonce)

# ======================== 前端API接口 ========================

@app.post("/api/login")
async def login(request: UserLoginRequest):
    """用户登录，获取访问token"""
    try:
        import requests
        from ..config.config import config
        
        # 优先使用code进行微信登录
        if request.code:
            logger.info(f"使用微信code登录: {request.code}")
            
            # 检查小程序secret配置
            if not config.wechat_mini_secret:
                logger.warning("微信小程序Secret未配置，尝试使用code作为用户ID（仅限开发环境）")
                # 开发环境：如果没有配置secret，将code作为用户ID使用
                wechat_user_id = f"dev_{request.code[:10]}"
            else:
                # 调用微信API获取openid
                wx_api_url = "https://api.weixin.qq.com/sns/jscode2session"
                params = {
                    "appid": config.wechat_mini_appid,
                    "secret": config.wechat_mini_secret,
                    "js_code": request.code,
                    "grant_type": "authorization_code"
                }
                
                try:
                    response = requests.get(wx_api_url, params=params, timeout=5)
                    wx_data = response.json()
                    
                    if "openid" in wx_data:
                        wechat_user_id = wx_data["openid"]
                        logger.info(f"微信登录成功，获取到openid: {wechat_user_id}")
                        
                        # 可以保存session_key和unionid供后续使用
                        session_key = wx_data.get("session_key")
                        unionid = wx_data.get("unionid")
                    else:
                        # 微信API返回错误
                        error_code = wx_data.get("errcode", -1)
                        error_msg = wx_data.get("errmsg", "未知错误")
                        logger.error(f"微信API错误: {error_msg} (code: {error_code})")
                        
                        # 如果是开发环境的模拟code，使用特殊处理
                        if error_code == 40029 and request.code.startswith("0"):
                            logger.info("检测到开发环境模拟code，使用测试用户ID")
                            wechat_user_id = "dev_user_001"
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"微信登录失败: {error_msg}"
                            )
                except requests.exceptions.RequestException as e:
                    logger.error(f"调用微信API失败: {e}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="调用微信服务失败"
                    )
        
        # 兼容旧版本：直接使用wechat_user_id
        elif request.wechat_user_id:
            wechat_user_id = request.wechat_user_id
            logger.info(f"使用微信用户ID直接登录: {wechat_user_id}")
            
            # 验证用户ID格式（简单验证）
            if not wechat_user_id or len(wechat_user_id) < 3:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的微信用户ID"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供code或wechat_user_id"
            )
        
        # 创建或获取用户
        user_id = db.get_or_create_user(wechat_user_id)
        
        if user_id:
            # 生成简单token（生产环境应使用JWT）
            import base64
            token = base64.b64encode(wechat_user_id.encode('utf-8')).decode('utf-8')
            
            # 获取用户统计信息
            stats = db.get_user_stats(wechat_user_id)
            
            # 检查绑定状态
            from ..database.binding_db import binding_db
            isBound = False
            external_userid = None
            
            if binding_db:
                binding_info = binding_db.get_user_binding(wechat_user_id)
                if binding_info:
                    isBound = binding_info.get('bind_status') == 1
                    external_userid = binding_info.get('external_userid')
                    # 更新最后登录时间
                    binding_db.update_last_login(wechat_user_id)
            
            return {
                "success": True,
                "token": token,
                "wechat_user_id": wechat_user_id,
                "user_id": user_id,
                "stats": stats,
                "openid": wechat_user_id,  # 为了兼容前端
                "isBound": isBound,
                "external_userid": external_userid
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="用户创建失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )

@app.get("/api/profiles", response_model=UserProfilesResponse)
async def get_user_profiles(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    current_user: str = Depends(verify_user_token)
):
    """获取用户的画像列表（分页）"""
    try:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
            
        offset = (page - 1) * page_size
        
        # 获取查询用户ID（优先使用external_userid）
        query_user_id = get_query_user_id(current_user)
        
        profiles, total = db.get_user_profiles(
            wechat_user_id=query_user_id,
            limit=page_size,
            offset=offset,
            search=search
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        return UserProfilesResponse(
            total=total,
            profiles=[UserProfile(**profile) for profile in profiles],
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"获取用户画像列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取画像列表失败"
        )

@app.get("/api/profiles/{profile_id}")
async def get_profile_detail(
    profile_id: int,
    current_user: str = Depends(verify_user_token)
):
    """获取用户画像详情"""
    try:
        query_user_id = get_query_user_id(current_user)
        profile = db.get_user_profile_detail(query_user_id, profile_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="画像不存在"
            )
        
        return {
            "success": True,
            "profile": profile
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取画像详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取画像详情失败"
        )

@app.delete("/api/profiles/{profile_id}")
async def delete_profile(
    profile_id: int,
    current_user: str = Depends(verify_user_token)
):
    """删除用户画像"""
    try:
        query_user_id = get_query_user_id(current_user)
        success = db.delete_user_profile(query_user_id, profile_id)
        
        if success:
            return {"success": True, "message": "画像删除成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="画像不存在或删除失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除画像失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除画像失败"
        )

@app.get("/api/stats", response_model=UserStatsResponse)
async def get_user_stats(current_user: str = Depends(verify_user_token)):
    """获取用户统计信息"""
    try:
        query_user_id = get_query_user_id(current_user)
        stats = db.get_user_stats(query_user_id)
        return UserStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"获取用户统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取统计信息失败"
        )

@app.get("/api/search")
async def search_profiles(
    q: str,
    limit: int = 20,
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    gender: Optional[str] = None,
    location: Optional[str] = None,
    current_user: str = Depends(verify_user_token)
):
    """智能搜索用户画像 - 支持多维度条件"""
    try:
        if not q or len(q.strip()) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="搜索关键词不能为空"
            )
        
        query_user_id = get_query_user_id(current_user)
        profiles, total = db.get_user_profiles(
            wechat_user_id=query_user_id,
            search=q.strip(),
            limit=limit,
            offset=0,
            age_min=age_min,
            age_max=age_max,
            gender=gender,
            location=location
        )
        
        return {
            "success": True,
            "total": total,
            "profiles": profiles,
            "query": q.strip(),
            "filters": {
                "age_min": age_min,
                "age_max": age_max,
                "gender": gender,
                "location": location
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"智能搜索失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索失败"
        )

@app.get("/api/recent")
async def get_recent_profiles(
    limit: int = 10,
    current_user: str = Depends(verify_user_token)
):
    """获取最近的用户画像"""
    try:
        if limit < 1 or limit > 50:
            limit = 10
            
        query_user_id = get_query_user_id(current_user)
        profiles, total = db.get_user_profiles(
            wechat_user_id=query_user_id,
            limit=limit,
            offset=0
        )
        
        return {
            "success": True,
            "profiles": profiles,
            "total": total
        }
        
    except Exception as e:
        logger.error(f"获取最近画像失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取最近画像失败"
        )

@app.get("/api/user/info")
async def get_user_info(current_user: str = Depends(verify_user_token)):
    """获取当前用户信息"""
    try:
        query_user_id = get_query_user_id(current_user)
        stats = db.get_user_stats(query_user_id)
        table_name = db._get_user_table_name(query_user_id)
        
        return {
            "success": True,
            "wechat_user_id": current_user,
            "table_name": table_name,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )

# 实时数据更新相关接口
@app.get("/api/updates/check")
async def check_for_updates(
    last_check: Optional[str] = None,
    current_user: str = Depends(verify_user_token)
):
    """检查是否有新的画像数据"""
    try:
        # 获取最新的画像（最近1分钟内）
        query_user_id = get_query_user_id(current_user)
        profiles, total = db.get_user_profiles(
            wechat_user_id=query_user_id,
            limit=5,
            offset=0
        )
        
        # 简单检查是否有更新（生产环境可以用更精确的时间戳对比）
        has_updates = total > 0
        
        return {
            "success": True,
            "has_updates": has_updates,
            "latest_profiles": profiles[:3] if has_updates else [],
            "total_profiles": total,
            "check_time": "2025-08-04T" + str(time.time())
        }
        
    except Exception as e:
        logger.error(f"检查更新失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="检查更新失败"
        )

# ======================== 匹配通知API ========================

@app.get("/api/notifications/matches")
async def get_match_notifications(
    unread_only: bool = True,
    limit: int = 10,
    current_user: str = Depends(verify_user_token)
):
    """获取匹配通知（供小程序轮询）"""
    try:
        # 确保意图表存在
        db.ensure_intent_tables_exist()
        
        query_user_id = get_query_user_id(current_user)
        
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 查询最新的匹配记录
        if unread_only:
            # 只获取未读的（24小时内的新匹配）
            cursor.execute("""
                SELECT 
                    m.id,
                    m.intent_id,
                    m.profile_id,
                    m.match_score,
                    m.explanation,
                    m.created_at,
                    i.name as intent_name,
                    i.type as intent_type
                FROM intent_matches m
                LEFT JOIN user_intents i ON m.intent_id = i.id
                WHERE m.user_id = ? 
                AND datetime(m.created_at) > datetime('now', '-24 hours')
                AND (m.is_read IS NULL OR m.is_read = 0)
                ORDER BY m.created_at DESC
                LIMIT ?
            """, (query_user_id, limit))
        else:
            # 获取所有最近的匹配
            cursor.execute("""
                SELECT 
                    m.id,
                    m.intent_id,
                    m.profile_id,
                    m.match_score,
                    m.explanation,
                    m.created_at,
                    i.name as intent_name,
                    i.type as intent_type
                FROM intent_matches m
                LEFT JOIN user_intents i ON m.intent_id = i.id
                WHERE m.user_id = ?
                ORDER BY m.created_at DESC
                LIMIT ?
            """, (query_user_id, limit))
        
        matches = []
        columns = [desc[0] for desc in cursor.description]
        
        for row in cursor.fetchall():
            match = dict(zip(columns, row))
            
            # 获取联系人信息
            user_table = f"profiles_{query_user_id.replace('-', '_')}"
            cursor.execute(f"""
                SELECT profile_name, company, position, phone 
                FROM {user_table} 
                WHERE id = ?
            """, (match['profile_id'],))
            
            profile_row = cursor.fetchone()
            if profile_row:
                match['profile_name'] = profile_row[0]
                match['company'] = profile_row[1]
                match['position'] = profile_row[2]
                match['phone'] = profile_row[3]
            
            matches.append(match)
        
        # 获取未读数量
        cursor.execute("""
            SELECT COUNT(*) FROM intent_matches 
            WHERE user_id = ? 
            AND datetime(created_at) > datetime('now', '-24 hours')
            AND (is_read IS NULL OR is_read = 0)
        """, (query_user_id,))
        
        unread_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "matches": matches,
            "unread_count": unread_count,
            "has_new": unread_count > 0
        }
        
    except Exception as e:
        logger.error(f"获取匹配通知失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取匹配通知失败"
        )

@app.post("/api/notifications/matches/{match_id}/read")
async def mark_match_as_read(
    match_id: int,
    current_user: str = Depends(verify_user_token)
):
    """标记匹配通知为已读"""
    try:
        query_user_id = get_query_user_id(current_user)
        
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 更新已读状态
        cursor.execute("""
            UPDATE intent_matches 
            SET is_read = 1, read_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (match_id, query_user_id))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "已标记为已读"}
        
    except Exception as e:
        logger.error(f"标记已读失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="标记已读失败"
        )

# ======================== 联系人管理API ========================

class ParseVoiceTextRequest(BaseModel):
    """解析语音文本请求模型"""
    text: str  # 语音识别后的文本内容
    merge_mode: bool = False  # 是否为合并模式（用于编辑现有联系人）

class ParseVoiceTextResponse(BaseModel):
    """解析语音文本响应模型"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

@app.post("/api/profiles/parse-voice")
async def parse_voice_text(
    request: ParseVoiceTextRequest,
    current_user: str = Depends(verify_user_token)
):
    """解析语音文本，提取用户画像信息"""
    try:
        # 初始化AI服务
        ai_service = UserProfileExtractor()
        
        # 使用AI服务解析文本
        result = ai_service.extract_user_profile(request.text, is_chat_record=False)
        
        # AI服务返回的格式是 {"success": True, "data": {"user_profiles": [...]}, "error": None}
        # 需要从嵌套的data字段中获取user_profiles
        if not result or not result.get("data"):
            return ParseVoiceTextResponse(
                success=False,
                message="无法从文本中提取有效信息"
            )
        
        ai_data = result.get("data", {})
        if "user_profiles" not in ai_data:
            return ParseVoiceTextResponse(
                success=False,
                message="无法从文本中提取有效信息"
            )
        
        user_profiles = ai_data.get("user_profiles", [])
        
        if not user_profiles:
            return ParseVoiceTextResponse(
                success=False,
                message="未能识别出联系人信息"
            )
        
        # 取第一个识别到的用户画像
        profile = user_profiles[0]
        
        # 转换字段名以匹配前端表单
        parsed_data = {
            "name": profile.get("name", "") if profile.get("name") != "未知" else "",
            "gender": profile.get("gender", "") if profile.get("gender") != "未知" else "",
            "age": profile.get("age", "") if profile.get("age") != "未知" else "",
            "phone": profile.get("phone", "") if profile.get("phone") != "未知" else "",
            "wechat_id": "",  # AI通常不能识别微信号
            "email": "",  # AI通常不能识别邮箱
            "location": profile.get("location", "") if profile.get("location") != "未知" else "",
            "address": profile.get("location", "") if profile.get("location") != "未知" else "",
            "marital_status": profile.get("marital_status", "") if profile.get("marital_status") != "未知" else "",
            "education": profile.get("education", "") if profile.get("education") != "未知" else "",
            "company": profile.get("company", "") if profile.get("company") != "未知" else "",
            "position": profile.get("position", "") if profile.get("position") != "未知" else "",
            "asset_level": profile.get("asset_level", "") if profile.get("asset_level") != "未知" else "",
            "personality": profile.get("personality", "") if profile.get("personality") != "未知" else "",
            "notes": result.get("summary", "")  # 使用AI的总结作为备注
        }
        
        # 如果是合并模式，只返回非空字段
        if request.merge_mode:
            parsed_data = {k: v for k, v in parsed_data.items() if v and v != ""}
        
        return ParseVoiceTextResponse(
            success=True,
            data=parsed_data,
            message="解析成功"
        )
        
    except Exception as e:
        logger.error(f"解析语音文本失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return ParseVoiceTextResponse(
            success=False,
            message=f"解析失败: {str(e)}"
        )

@app.post("/api/profiles/parse-voice-audio")
async def parse_voice_audio(
    audio_file: UploadFile = File(...),
    merge_mode: str = Form("false"),  # 接收字符串形式的布尔值
    contact_id: Optional[str] = Form(None),  # 编辑模式下的联系人ID
    current_user: str = Depends(verify_user_token)
):
    """接收音频文件，进行ASR识别后解析用户画像"""
    logger.info(f"收到语音上传请求，用户: {current_user}")
    logger.info(f"音频文件名: {audio_file.filename}, 大小: {audio_file.size if hasattr(audio_file, 'size') else '未知'}")
    logger.info(f"合并模式: {merge_mode}")
    logger.info(f"联系人ID: {contact_id}")
    
    # 将字符串转换为布尔值
    merge_mode = merge_mode.lower() == "true"
    
    temp_file_path = None
    try:
        # 保存上传的音频文件到临时目录
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            temp_file_path = tmp_file.name
            content = await audio_file.read()
            tmp_file.write(content)
            tmp_file.flush()
            
        logger.info(f"音频文件已保存到: {temp_file_path}")
        
        # 初始化媒体处理器
        media_processor = MediaProcessor()
        
        # 使用ASR进行语音识别
        logger.info("开始语音识别...")
        recognized_text = None
        intermediate_results = []
        
        try:
            # 尝试使用阿里云ASR
            from ..services.media_processor import AliyunASRProcessor
            asr_processor = AliyunASRProcessor()
            # 请求返回中间结果
            asr_result = asr_processor.recognize_speech(temp_file_path, return_intermediate=True)
            
            if isinstance(asr_result, dict):
                recognized_text = asr_result.get('final_text')
                intermediate_results = asr_result.get('intermediate_results', [])
                logger.info(f"ASR识别成功: {recognized_text[:100] if recognized_text else '无内容'}...")
                logger.info(f"中间结果数量: {len(intermediate_results)}")
            else:
                # 兼容旧版本返回格式
                recognized_text = asr_result
                logger.info(f"ASR识别成功: {recognized_text[:100] if recognized_text else '无内容'}...")
        except Exception as asr_error:
            logger.error(f"ASR识别出错: {str(asr_error)}")
            recognized_text = None
        
        if not recognized_text:
            logger.warning("ASR识别失败，返回错误提示")
            # 如果ASR失败，可以返回错误或使用其他备用方案
            return ParseVoiceTextResponse(
                success=False,
                message="语音识别失败，请重试或使用文字输入"
            )
        
        logger.info(f"语音识别结果: {recognized_text}")
        
        # 如果是编辑模式且有contact_id，获取现有联系人数据并与新识别的文本合并
        if merge_mode and contact_id:
            logger.info(f"编辑模式，获取现有联系人数据: {contact_id}")
            try:
                # 获取查询用户ID
                query_user_id = get_query_user_id(current_user)
                
                # 获取现有联系人数据 - 使用统一的数据库实例
                existing_profile = db.get_user_profile_detail(query_user_id, int(contact_id))
                
                if existing_profile:
                    logger.info(f"找到现有联系人: {existing_profile.get('profile_name', '')}")
                    
                    # 构建合并提示，让AI整合新旧数据 - 使用正确的字段访问方式
                    merge_prompt = f"""你需要智能整合以下两部分信息：

【现有联系人信息】
姓名: {existing_profile.get('profile_name', '未知')}
性别: {existing_profile.get('gender', '未知')}
年龄: {existing_profile.get('age', '未知')}
电话: {existing_profile.get('phone', '未知')}
微信号: {existing_profile.get('wechat_id', '未知')}
邮箱: {existing_profile.get('email', '未知')}
所在地: {existing_profile.get('location', '未知')}
婚育: {existing_profile.get('marital_status', '未知')}
学历: {existing_profile.get('education', '未知')}
公司: {existing_profile.get('company', '未知')}
职位: {existing_profile.get('position', '未知')}
资产水平: {existing_profile.get('asset_level', '未知')}
性格: {existing_profile.get('personality', '未知')}
备注: {existing_profile.get('ai_summary', '无')}

【新语音输入的信息】
{recognized_text}

请智能整合上述信息，生成一个更完整的用户画像。整合规则：
1. 如果新信息中有更具体、更准确的数据，使用新信息替换旧信息
2. 如果新信息是对现有信息的补充，将两者合并
3. 如果新信息中没有提到某个字段，保留现有的有效信息（不要输出"未知"）
4. 如果旧信息为"未知"而新信息有值，使用新信息
5. 对于备注字段，如果两者都有内容，将新的备注追加到原有备注后
6. 输出完整的用户画像，所有有效字段都要包含"""
                    
                    # 使用AI服务解析整合后的文本
                    ai_service = UserProfileExtractor()
                    result = ai_service.extract_user_profile(merge_prompt, is_chat_record=False)
                else:
                    logger.warning(f"未找到联系人: {contact_id}")
                    # 如果没找到现有联系人，直接使用新识别的文本
                    ai_service = UserProfileExtractor()
                    result = ai_service.extract_user_profile(recognized_text, is_chat_record=False)
            except Exception as e:
                logger.error(f"获取现有联系人数据失败: {e}")
                logger.error(f"错误详情: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                # 出错时直接使用新识别的文本
                ai_service = UserProfileExtractor()
                result = ai_service.extract_user_profile(recognized_text, is_chat_record=False)
        else:
            # 新建模式，直接使用识别的文本
            ai_service = UserProfileExtractor()
            result = ai_service.extract_user_profile(recognized_text, is_chat_record=False)
        
        if not result:
            logger.warning(f"AI解析失败，无返回结果。识别文本: {recognized_text}")
            return ParseVoiceTextResponse(
                success=False,
                message="AI解析失败，请重试",
                data={"recognized_text": recognized_text}  # 返回识别的原始文本
            )
        
        # AI服务返回的格式是 {"success": True, "data": {"user_profiles": [...]}, "error": None}
        # 需要从嵌套的data字段中获取user_profiles
        ai_data = result.get("data", {})
        
        if not ai_data or "user_profiles" not in ai_data:
            logger.warning(f"AI解析结果缺少user_profiles。识别文本: {recognized_text}")
            logger.warning(f"AI返回结果: {result}")
            return ParseVoiceTextResponse(
                success=False,
                message="无法从语音中提取有效信息",
                data={"recognized_text": recognized_text}
            )
        
        user_profiles = ai_data.get("user_profiles", [])
        
        if not user_profiles:
            logger.warning(f"AI解析结果为空。识别文本: {recognized_text}")
            return ParseVoiceTextResponse(
                success=False,
                message="未能识别出联系人信息",
                data={"recognized_text": recognized_text}
            )
        
        # 取第一个识别到的用户画像
        profile = user_profiles[0]
        
        # 转换字段名以匹配前端表单
        parsed_data = {
            "name": profile.get("name", "") if profile.get("name") != "未知" else "",
            "gender": profile.get("gender", "") if profile.get("gender") != "未知" else "",
            "age": profile.get("age", "") if profile.get("age") != "未知" else "",
            "phone": profile.get("phone", "") if profile.get("phone") != "未知" else "",
            "wechat_id": "",
            "email": "",
            "location": profile.get("location", "") if profile.get("location") != "未知" else "",
            "address": profile.get("location", "") if profile.get("location") != "未知" else "",
            "marital_status": profile.get("marital_status", "") if profile.get("marital_status") != "未知" else "",
            "education": profile.get("education", "") if profile.get("education") != "未知" else "",
            "company": profile.get("company", "") if profile.get("company") != "未知" else "",
            "position": profile.get("position", "") if profile.get("position") != "未知" else "",
            "asset_level": profile.get("asset_level", "") if profile.get("asset_level") != "未知" else "",
            "personality": profile.get("personality", "") if profile.get("personality") != "未知" else "",
            "notes": result.get("summary", ""),
            "recognized_text": recognized_text  # 返回识别的原始文本供参考
        }
        
        # 在编辑模式下，AI已经整合了完整数据，不需要前端再合并
        # 所以直接返回完整数据即可
        
        # 添加识别的原始文本和中间结果到返回数据中
        parsed_data['recognized_text'] = recognized_text
        parsed_data['intermediate_results'] = intermediate_results  # 添加中间结果数组
        
        return ParseVoiceTextResponse(
            success=True,
            data=parsed_data,
            message="语音解析成功"
        )
        
    except Exception as e:
        logger.error(f"解析语音文件失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return ParseVoiceTextResponse(
            success=False,
            message=f"解析失败: {str(e)}"
        )
    
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"临时文件已删除: {temp_file_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {e}")

class CreateProfileRequest(BaseModel):
    """创建联系人请求模型"""
    name: str  # 必填
    phone: Optional[str] = None
    wechat_id: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = []
    # 额外的画像字段
    gender: Optional[str] = None
    age: Optional[str] = None
    location: Optional[str] = None
    marital_status: Optional[str] = None
    education: Optional[str] = None
    asset_level: Optional[str] = None
    personality: Optional[str] = None

class UpdateProfileRequest(BaseModel):
    """更新联系人请求模型"""
    name: Optional[str] = None
    phone: Optional[str] = None
    wechat_id: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    # 额外的画像字段
    gender: Optional[str] = None
    age: Optional[str] = None
    location: Optional[str] = None
    marital_status: Optional[str] = None
    education: Optional[str] = None
    asset_level: Optional[str] = None
    personality: Optional[str] = None

class BatchImportRequest(BaseModel):
    """批量导入联系人请求模型"""
    profiles: List[CreateProfileRequest]
    import_mode: str = "create"  # create, merge, skip_duplicate

class BatchImportResult(BaseModel):
    """批量导入结果模型"""
    success: bool
    total_count: int
    success_count: int
    failed_count: int
    skipped_count: int
    errors: List[Dict[str, Any]] = []
    created_profiles: List[Dict[str, Any]] = []

@app.post("/api/profiles")
async def create_profile(
    request: CreateProfileRequest,
    current_user: str = Depends(verify_user_token)
):
    """创建新的联系人画像"""
    try:
        # 验证必填字段
        if not request.name or not request.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="联系人姓名不能为空"
            )
        
        # 获取查询用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 准备画像数据
        profile_data = {
            "profile_name": request.name.strip(),  # 修正字段名
            "name": request.name.strip(),  # 保留兼容性
            "gender": request.gender or "未知",
            "age": request.age or "未知",
            "phone": request.phone or "未知",
            "location": request.location or request.address or "未知",
            "marital_status": request.marital_status or "未知",
            "education": request.education or "未知",
            "company": request.company or "未知",
            "position": request.position or "未知",
            "asset_level": request.asset_level or "未知",
            "personality": request.personality or "未知",
            "tags": request.tags or []  # 添加tags字段
        }
        
        # 准备AI响应数据（模拟AI分析结果）
        ai_response = {
            "summary": f"手动创建的联系人：{request.name.strip()}",
            "user_profiles": [profile_data]
        }
        
        # 保存到数据库
        profile_id = db.save_user_profile(
            wechat_user_id=query_user_id,
            profile_data=profile_data,
            raw_message=request.notes or f"手动创建联系人：{request.name.strip()}",
            message_type="manual_create",
            ai_response=ai_response
        )
        
        if profile_id:
            logger.info(f"成功创建联系人画像：{profile_id}")
            
            # 获取创建的画像详情
            created_profile = db.get_user_profile_detail(query_user_id, profile_id)
            
            # 触发意图匹配（真正的异步执行，不阻塞返回）
            import asyncio
            async def run_intent_matching():
                try:
                    from src.services.intent_matcher import intent_matcher
                    matches = await intent_matcher.match_profile_with_intents(profile_id, query_user_id)
                    if matches:
                        logger.info(f"新联系人{profile_id}匹配到{len(matches)}个意图")
                except Exception as e:
                    logger.error(f"触发意图匹配失败: {e}")
            
            # 创建后台任务，不等待完成
            asyncio.create_task(run_intent_matching())
            
            return {
                "success": True,
                "message": "联系人创建成功",
                "profile_id": profile_id,
                "profile": created_profile
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建联系人失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建联系人失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建联系人失败: {str(e)}"
        )

@app.put("/api/profiles/{profile_id}")
async def update_profile(
    profile_id: int,
    request: UpdateProfileRequest,
    current_user: str = Depends(verify_user_token)
):
    """更新联系人画像"""
    try:
        # 获取查询用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 先检查画像是否存在
        existing_profile = db.get_user_profile_detail(query_user_id, profile_id)
        if not existing_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="联系人不存在"
            )
        
        # 准备更新数据 - 过滤空值，避免覆盖有效数据
        update_data = {}
        
        # 辅助函数：检查值是否有效（非空且有意义）
        def is_valid_value(value):
            if value is None:
                return False
            if isinstance(value, str):
                return value.strip() != ''
            if isinstance(value, list):
                return len(value) > 0
            return True
        
        # 只更新提供的且有效的字段
        if is_valid_value(request.name):
            update_data["profile_name"] = request.name.strip()
            
        # 处理字符串字段 - 只更新非空字符串
        string_fields = [
            ('phone', 'phone'),
            ('age', 'age'),
            ('education', 'education'),
            ('company', 'company'),
            ('position', 'position'),
            ('personality', 'personality'),
            ('wechat_id', 'wechat_id'),
            ('email', 'email')
        ]
        
        for request_field, db_field in string_fields:
            value = getattr(request, request_field, None)
            if is_valid_value(value):
                update_data[db_field] = value.strip() if isinstance(value, str) else value
        
        # 处理位置字段（支持location和address两个字段名）
        if is_valid_value(request.location):
            update_data["location"] = request.location.strip()
        elif is_valid_value(request.address):
            update_data["location"] = request.address.strip()
            
        # 处理选择器字段 - 避免设置为"未知"
        if is_valid_value(request.gender) and request.gender != '未知':
            update_data["gender"] = request.gender
        if is_valid_value(request.marital_status) and request.marital_status != '未知':
            update_data["marital_status"] = request.marital_status
        if is_valid_value(request.asset_level) and request.asset_level != '未知':
            update_data["asset_level"] = request.asset_level
            
        # 处理标签字段
        if is_valid_value(request.tags):
            update_data["tags"] = request.tags
        
        # 更新AI摘要（如果有备注）
        if is_valid_value(request.notes):
            update_data["ai_summary"] = request.notes.strip()
        
        # 调用数据库更新方法
        success = db.update_user_profile(query_user_id, profile_id, update_data)
        
        if success:
            logger.info(f"成功更新联系人画像：{profile_id}")
            
            # 获取更新后的画像详情
            updated_profile = db.get_user_profile_detail(query_user_id, profile_id)
            
            # 触发意图匹配（真正的异步执行，不阻塞返回）
            import asyncio
            async def run_intent_matching():
                try:
                    from src.services.intent_matcher import intent_matcher
                    matches = await intent_matcher.match_profile_with_intents(profile_id, query_user_id)
                    if matches:
                        logger.info(f"更新的联系人{profile_id}匹配到{len(matches)}个意图")
                except Exception as e:
                    logger.error(f"触发意图匹配失败: {e}")
            
            # 创建后台任务，不等待完成
            asyncio.create_task(run_intent_matching())
            
            return {
                "success": True,
                "message": "联系人更新成功",
                "profile": updated_profile
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新联系人失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新联系人失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新联系人失败: {str(e)}"
        )

@app.post("/api/profiles/parse-file")
async def parse_import_file(
    file: UploadFile = File(...),
    current_user: str = Depends(verify_user_token)
):
    """解析导入文件并返回预览数据"""
    try:
        # 验证文件类型
        allowed_types = ['text/csv', 'application/vnd.ms-excel', 
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持CSV和Excel文件格式"
            )
        
        # 读取文件内容
        contents = await file.read()
        
        # 根据文件类型解析数据
        import pandas as pd
        import io
        
        try:
            if file.content_type == 'text/csv':
                df = pd.read_csv(io.BytesIO(contents), encoding='utf-8')
            else:
                df = pd.read_excel(io.BytesIO(contents))
        except UnicodeDecodeError:
            # 尝试GBK编码
            if file.content_type == 'text/csv':
                df = pd.read_csv(io.BytesIO(contents), encoding='gbk')
            else:
                raise
        
        # 字段映射配置
        field_mapping = {
            '姓名': 'name', '联系人': 'name', '名字': 'name', 'name': 'name',
            '手机': 'phone', '电话': 'phone', '手机号': 'phone', 'phone': 'phone',
            '微信': 'wechat_id', '微信号': 'wechat_id', 'wechat': 'wechat_id',
            '邮箱': 'email', '邮件': 'email', 'email': 'email',
            '公司': 'company', '单位': 'company', 'company': 'company',
            '职位': 'position', '岗位': 'position', 'position': 'position',
            '地址': 'address', '住址': 'address', '地区': 'address', 'address': 'address',
            '备注': 'notes', '说明': 'notes', 'notes': 'notes',
            '性别': 'gender', 'gender': 'gender',
            '年龄': 'age', 'age': 'age',
            '婚姻状况': 'marital_status', '婚姻': 'marital_status',
            '学历': 'education', 'education': 'education',
            '资产水平': 'asset_level', '资产': 'asset_level',
            '性格': 'personality', 'personality': 'personality'
        }
        
        # 解析数据
        parsed_data = []
        errors = []
        
        for index, row in df.iterrows():
            try:
                contact = {}
                
                # 映射字段
                for col in df.columns:
                    col_name = str(col).strip()
                    if col_name in field_mapping:
                        field_name = field_mapping[col_name]
                        value = str(row[col]) if pd.notna(row[col]) else ""
                        if value and value != 'nan':
                            contact[field_name] = value.strip()
                
                # 验证必填字段
                if not contact.get('name'):
                    errors.append({
                        'row': index + 2,  # Excel行号从1开始，加上表头
                        'error': '缺少姓名字段'
                    })
                    continue
                
                # 处理标签（如果有）
                if 'tags' in contact:
                    tags_str = contact['tags']
                    if tags_str:
                        contact['tags'] = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
                    else:
                        contact['tags'] = []
                else:
                    contact['tags'] = []
                
                parsed_data.append({
                    'row': index + 2,
                    'data': contact,
                    'valid': True
                })
                
            except Exception as e:
                errors.append({
                    'row': index + 2,
                    'error': f'解析失败: {str(e)}'
                })
        
        return {
            "success": True,
            "total_rows": len(df),
            "valid_count": len(parsed_data),
            "error_count": len(errors),
            "data": parsed_data,
            "errors": errors,
            "field_mapping": {v: k for k, v in field_mapping.items() if any(k in str(col) for col in df.columns)}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解析导入文件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件解析失败: {str(e)}"
        )

@app.post("/api/profiles/batch")
async def batch_import_profiles(
    request: BatchImportRequest,
    current_user: str = Depends(verify_user_token)
) -> BatchImportResult:
    """批量导入联系人"""
    try:
        query_user_id = get_query_user_id(current_user)
        
        total_count = len(request.profiles)
        success_count = 0
        failed_count = 0
        skipped_count = 0
        errors = []
        created_profiles = []
        
        for i, profile_request in enumerate(request.profiles):
            try:
                # 验证必填字段
                if not profile_request.name or not profile_request.name.strip():
                    errors.append({
                        'index': i,
                        'name': profile_request.name or '未知',
                        'error': '联系人姓名不能为空'
                    })
                    failed_count += 1
                    continue
                
                # 检查重复（如果设置了跳过重复）
                if request.import_mode == "skip_duplicate":
                    existing = db.search_user_profiles(query_user_id, profile_request.name.strip())
                    if existing and len(existing) > 0:
                        skipped_count += 1
                        continue
                
                # 准备画像数据
                profile_data = {
                    "profile_name": profile_request.name.strip(),
                    "name": profile_request.name.strip(),
                    "gender": profile_request.gender or "未知",
                    "age": profile_request.age or "未知",
                    "phone": profile_request.phone or "未知",
                    "location": profile_request.location or profile_request.address or "未知",
                    "marital_status": profile_request.marital_status or "未知",
                    "education": profile_request.education or "未知",
                    "company": profile_request.company or "未知",
                    "position": profile_request.position or "未知",
                    "asset_level": profile_request.asset_level or "未知",
                    "personality": profile_request.personality or "未知",
                    "tags": profile_request.tags or []
                }
                
                # 准备AI响应数据
                ai_response = {
                    "summary": f"批量导入的联系人：{profile_request.name.strip()}",
                    "user_profiles": [profile_data]
                }
                
                # 保存到数据库
                profile_id = db.save_user_profile(
                    wechat_user_id=query_user_id,
                    profile_data=profile_data,
                    raw_message=profile_request.notes or f"批量导入联系人：{profile_request.name.strip()}",
                    message_type="batch_import",
                    ai_response=ai_response
                )
                
                if profile_id:
                    success_count += 1
                    created_profile = db.get_user_profile_detail(query_user_id, profile_id)
                    created_profiles.append(created_profile)
                    
                    # 异步触发意图匹配
                    import asyncio
                    async def run_intent_matching():
                        try:
                            from src.services.intent_matcher import intent_matcher
                            await intent_matcher.match_profile_with_intents(profile_id, query_user_id)
                        except Exception as e:
                            logger.error(f"批量导入触发意图匹配失败: {e}")
                    
                    asyncio.create_task(run_intent_matching())
                    
                else:
                    failed_count += 1
                    errors.append({
                        'index': i,
                        'name': profile_request.name,
                        'error': '数据库保存失败'
                    })
                    
            except Exception as e:
                failed_count += 1
                errors.append({
                    'index': i,
                    'name': getattr(profile_request, 'name', '未知'),
                    'error': str(e)
                })
        
        logger.info(f"批量导入完成: 总计{total_count}，成功{success_count}，失败{failed_count}，跳过{skipped_count}")
        
        return BatchImportResult(
            success=success_count > 0,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            errors=errors,
            created_profiles=created_profiles
        )
        
    except Exception as e:
        logger.error(f"批量导入联系人失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量导入失败: {str(e)}"
        )

# ===================== 意图匹配系统 API =====================

class CreateIntentRequest(BaseModel):
    """创建意图请求模型"""
    name: str
    description: str
    type: Optional[str] = "general"
    conditions: Optional[dict] = {}
    threshold: Optional[float] = 0.7
    priority: Optional[int] = 5
    max_push_per_day: Optional[int] = 5

class UpdateIntentRequest(BaseModel):
    """更新意图请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[dict] = None
    threshold: Optional[float] = None
    priority: Optional[int] = None
    max_push_per_day: Optional[int] = None
    status: Optional[str] = None

@app.post("/api/intents")
async def create_intent(
    request: CreateIntentRequest,
    current_user: str = Depends(verify_user_token)
):
    """创建新的用户意图"""
    try:
        import json
        import sqlite3
        
        # 确保意图表存在
        db.ensure_intent_tables_exist()
        
        # 验证必填字段
        if not request.name or not request.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="意图名称不能为空"
            )
        
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 插入意图
        cursor.execute("""
            INSERT INTO user_intents (
                user_id, name, description, type, conditions, 
                threshold, priority, max_push_per_day
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            query_user_id,
            request.name.strip(),
            request.description,
            request.type,
            json.dumps(request.conditions, ensure_ascii=False),
            request.threshold,
            request.priority,
            request.max_push_per_day
        ))
        
        intent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"成功创建意图：{intent_id}")
        
        # TODO: 触发全量匹配
        # await trigger_full_match(intent_id, query_user_id)
        
        return {
            "success": True,
            "message": "意图创建成功",
            "data": {
                "intentId": intent_id,
                "message": "意图创建成功，正在进行匹配分析"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建意图失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建意图失败: {str(e)}"
        )

@app.get("/api/intents")
async def get_intents(
    intent_status: Optional[str] = None,
    page: int = 1,
    size: int = 10,
    current_user: str = Depends(verify_user_token)
):
    """获取用户意图列表"""
    try:
        import json
        import sqlite3
        
        # 确保意图表存在
        db.ensure_intent_tables_exist()
        
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 查询意图
        offset = (page - 1) * size
        
        if intent_status:
            cursor.execute("""
                SELECT * FROM user_intents 
                WHERE user_id = ? AND status = ?
                ORDER BY priority DESC, created_at DESC
                LIMIT ? OFFSET ?
            """, (query_user_id, intent_status, size, offset))
        else:
            cursor.execute("""
                SELECT * FROM user_intents 
                WHERE user_id = ?
                ORDER BY priority DESC, created_at DESC
                LIMIT ? OFFSET ?
            """, (query_user_id, size, offset))
        
        columns = [desc[0] for desc in cursor.description]
        intents = []
        
        for row in cursor.fetchall():
            intent = dict(zip(columns, row))
            # 解析JSON字段
            if intent.get('conditions'):
                try:
                    intent['conditions'] = json.loads(intent['conditions'])
                except:
                    intent['conditions'] = {}
            
            # 获取该意图的匹配数量
            cursor.execute("""
                SELECT COUNT(*) FROM intent_matches 
                WHERE intent_id = ? AND user_id = ?
            """, (intent['id'], query_user_id))
            match_count = cursor.fetchone()[0]
            intent['match_count'] = match_count
            
            intents.append(intent)
        
        # 获取总数
        if intent_status:
            cursor.execute(
                "SELECT COUNT(*) FROM user_intents WHERE user_id = ? AND status = ?",
                (query_user_id, intent_status)
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM user_intents WHERE user_id = ?",
                (query_user_id,)
            )
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "intents": intents,
                "total": total,
                "page": page,
                "size": size
            }
        }
        
    except Exception as e:
        logger.error(f"获取意图列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取意图列表失败: {str(e)}"
        )

@app.get("/api/intents/{intent_id}")
async def get_intent_detail(
    intent_id: int,
    current_user: str = Depends(verify_user_token)
):
    """获取意图详情"""
    try:
        import json
        import sqlite3
        
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 查询意图
        cursor.execute("""
            SELECT * FROM user_intents 
            WHERE id = ? AND user_id = ?
        """, (intent_id, query_user_id))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="意图不存在"
            )
        
        columns = [desc[0] for desc in cursor.description]
        intent = dict(zip(columns, row))
        
        # 解析JSON字段
        if intent.get('conditions'):
            try:
                intent['conditions'] = json.loads(intent['conditions'])
            except:
                intent['conditions'] = {}
        
        # 获取匹配统计
        cursor.execute("""
            SELECT COUNT(*) as total_matches,
                   COUNT(CASE WHEN user_feedback = 'positive' THEN 1 END) as positive_matches,
                   COUNT(CASE WHEN is_pushed = 1 THEN 1 END) as pushed_matches
            FROM intent_matches 
            WHERE intent_id = ?
        """, (intent_id,))
        
        stats = cursor.fetchone()
        intent['stats'] = {
            'total_matches': stats[0],
            'positive_matches': stats[1],
            'pushed_matches': stats[2]
        }
        
        conn.close()
        
        return {
            "success": True,
            "data": intent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取意图详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取意图详情失败: {str(e)}"
        )

@app.put("/api/intents/{intent_id}")
async def update_intent(
    intent_id: int,
    request: UpdateIntentRequest,
    current_user: str = Depends(verify_user_token)
):
    """更新意图"""
    try:
        import json
        import sqlite3
        import asyncio
        
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 获取原始意图数据，用于比较变化
        cursor.execute(
            "SELECT id, description, conditions, threshold FROM user_intents WHERE id = ? AND user_id = ?",
            (intent_id, query_user_id)
        )
        original_intent = cursor.fetchone()
        if not original_intent:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="意图不存在"
            )
        
        # 解析原始数据
        original_description = original_intent[1]
        original_conditions = json.loads(original_intent[2]) if original_intent[2] else {}
        original_threshold = original_intent[3]
        
        # 检测是否需要重新匹配
        need_full_rematch = False  # 需要完全重新匹配（description或conditions变化）
        need_threshold_reeval = False  # 只需要重新评估阈值
        
        # 构建更新语句
        update_fields = []
        update_values = []
        
        if request.name is not None:
            update_fields.append("name = ?")
            update_values.append(request.name)
            # 名称变化不需要重新匹配
            
        if request.description is not None:
            update_fields.append("description = ?")
            update_values.append(request.description)
            # 检查描述是否真的变化了
            if request.description != original_description:
                need_full_rematch = True
                logger.info(f"意图{intent_id}的描述发生变化，需要重新匹配")
                
        if request.conditions is not None:
            update_fields.append("conditions = ?")
            conditions_json = json.dumps(request.conditions, ensure_ascii=False)
            update_values.append(conditions_json)
            # 检查条件是否真的变化了
            if request.conditions != original_conditions:
                need_full_rematch = True
                logger.info(f"意图{intent_id}的条件发生变化，需要重新匹配")
                
        if request.threshold is not None:
            update_fields.append("threshold = ?")
            update_values.append(request.threshold)
            # 检查阈值是否真的变化了
            if abs(request.threshold - original_threshold) > 0.001:
                need_threshold_reeval = True
                logger.info(f"意图{intent_id}的阈值发生变化: {original_threshold:.2f} -> {request.threshold:.2f}")
                
        if request.priority is not None:
            update_fields.append("priority = ?")
            update_values.append(request.priority)
            # 优先级变化不需要重新匹配
            
        if request.max_push_per_day is not None:
            update_fields.append("max_push_per_day = ?")
            update_values.append(request.max_push_per_day)
            # 推送次数变化不需要重新匹配
            
        if request.status is not None:
            update_fields.append("status = ?")
            update_values.append(request.status)
        
        if update_fields:
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.extend([intent_id, query_user_id])
            
            cursor.execute(f"""
                UPDATE user_intents 
                SET {', '.join(update_fields)}
                WHERE id = ? AND user_id = ?
            """, update_values)
            
            conn.commit()
        
        conn.close()
        
        # 根据变化情况触发重新匹配（异步执行）
        if need_full_rematch:
            # 描述或条件变化，需要完全重新匹配
            async def run_full_rematch():
                try:
                    from src.services.intent_matcher import intent_matcher
                    # 重新生成embedding并进行全量匹配
                    matches = await intent_matcher.match_intent_with_profiles(intent_id, query_user_id, regenerate_embedding=True)
                    logger.info(f"意图{intent_id}重新匹配完成，找到{len(matches)}个匹配")
                except Exception as e:
                    logger.error(f"意图{intent_id}重新匹配失败: {e}")
            
            # 创建后台任务
            asyncio.create_task(run_full_rematch())
            message = "意图更新成功，正在后台重新匹配"
            
        elif need_threshold_reeval:
            # 只是阈值变化，重新评估现有匹配
            async def run_threshold_reeval():
                try:
                    from src.services.intent_matcher import intent_matcher
                    # 只重新评估阈值，不重新计算匹配分数
                    updated_count = await intent_matcher.reevaluate_intent_threshold(intent_id, query_user_id, request.threshold)
                    logger.info(f"意图{intent_id}阈值重新评估完成，更新了{updated_count}个匹配")
                except Exception as e:
                    logger.error(f"意图{intent_id}阈值重新评估失败: {e}")
            
            # 创建后台任务
            asyncio.create_task(run_threshold_reeval())
            message = "意图更新成功，正在重新评估匹配阈值"
        else:
            # 其他字段变化，不需要重新匹配
            message = "意图更新成功"
        
        return {
            "success": True,
            "message": message,
            "need_rematch": need_full_rematch,
            "need_threshold_reeval": need_threshold_reeval
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新意图失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新意图失败: {str(e)}"
        )

@app.delete("/api/intents/{intent_id}")
async def delete_intent(
    intent_id: int,
    current_user: str = Depends(verify_user_token)
):
    """删除意图"""
    try:
        import sqlite3
        
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 删除意图（级联删除匹配记录）
        cursor.execute(
            "DELETE FROM user_intents WHERE id = ? AND user_id = ?",
            (intent_id, query_user_id)
        )
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="意图不存在"
            )
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "意图删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除意图失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除意图失败: {str(e)}"
        )

@app.post("/api/intents/{intent_id}/match")
async def trigger_intent_match(
    intent_id: int,
    current_user: str = Depends(verify_user_token)
):
    """手动触发意图匹配（AI增强）"""
    try:
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 导入匹配引擎（AI增强版）
        from src.services.intent_matcher import intent_matcher
        
        # 执行匹配（异步调用）
        matches = await intent_matcher.match_intent_with_profiles(intent_id, query_user_id)
        
        # 增强匹配信息
        enhanced_matches = []
        for match in matches[:10]:
            enhanced_match = match.copy()
            # 添加匹配类型标识
            enhanced_match['match_type'] = 'hybrid' if hasattr(intent_matcher, 'use_ai') and intent_matcher.use_ai else 'rule'
            # 格式化分数为百分比
            enhanced_match['score_percent'] = round(match['score'] * 100, 1)
            enhanced_matches.append(enhanced_match)
        
        return {
            "success": True,
            "message": f"AI增强匹配完成，找到{len(matches)}个潜在联系人",
            "data": {
                "intentId": intent_id,
                "matchesFound": len(matches),
                "matches": enhanced_matches,
                "aiEnabled": hasattr(intent_matcher, 'use_ai') and intent_matcher.use_ai
            }
        }
        
    except Exception as e:
        logger.error(f"触发匹配失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"触发匹配失败: {str(e)}"
        )

@app.get("/api/matches")
async def get_matches(
    intent_id: Optional[int] = None,
    status: Optional[str] = "pending",
    min_score: Optional[float] = None,
    page: int = 1,
    size: int = 20,
    current_user: str = Depends(verify_user_token)
):
    """获取匹配结果列表"""
    try:
        import json
        import sqlite3
        
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 构建查询条件
        where_clauses = ["m.user_id = ?"]
        params = [query_user_id]
        
        if intent_id:
            where_clauses.append("m.intent_id = ?")
            params.append(intent_id)
        if status:
            where_clauses.append("m.status = ?")
            params.append(status)
        if min_score is not None:
            where_clauses.append("m.match_score >= ?")
            params.append(min_score)
        
        # 查询匹配结果
        offset = (page - 1) * size
        params.extend([size, offset])
        
        # 获取用户表名 - 使用intent_matcher的方法
        from src.services.intent_matcher import intent_matcher
        user_table = intent_matcher._get_user_table_name(query_user_id)
        
        query = f"""
            SELECT 
                m.*,
                i.name as intent_name,
                i.description as intent_description,
                p.profile_name,
                p.company,
                p.position,
                p.location
            FROM intent_matches m
            LEFT JOIN user_intents i ON m.intent_id = i.id
            LEFT JOIN {user_table} p ON m.profile_id = p.id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY m.match_score DESC, m.created_at DESC
            LIMIT ? OFFSET ?
        """
        
        cursor.execute(query, params)
        
        columns = [desc[0] for desc in cursor.description]
        matches = []
        
        for row in cursor.fetchall():
            match = dict(zip(columns, row))
            # 解析JSON字段
            for field in ['score_details', 'matched_conditions']:
                if match.get(field):
                    try:
                        match[field] = json.loads(match[field])
                    except:
                        pass
            matches.append(match)
        
        # 获取总数
        count_params = params[:-2]  # 去掉LIMIT和OFFSET参数
        count_query = f"""
            SELECT COUNT(*) 
            FROM intent_matches m
            WHERE {' AND '.join(where_clauses)}
        """
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "matches": matches,
                "total": total,
                "page": page,
                "size": size
            }
        }
        
    except Exception as e:
        logger.error(f"获取匹配结果失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取匹配结果失败: {str(e)}"
        )

@app.put("/api/matches/{match_id}/feedback")
async def update_match_feedback(
    match_id: int,
    feedback_data: dict,
    current_user: str = Depends(verify_user_token)
):
    """更新匹配结果的用户反馈"""
    try:
        import json
        import sqlite3
        from datetime import datetime
        
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 验证反馈值
        feedback_value = feedback_data.get("feedback")
        if feedback_value not in ["positive", "negative", "ignored", None]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="反馈值必须是: positive, negative, ignored 或 null"
            )
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 验证匹配记录属于该用户
        cursor.execute("""
            SELECT m.*, i.user_id, i.name as intent_name, i.conditions
            FROM intent_matches m
            JOIN user_intents i ON m.intent_id = i.id
            WHERE m.id = ? AND i.user_id = ?
        """, (match_id, query_user_id))
        
        match_row = cursor.fetchone()
        if not match_row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="匹配记录不存在"
            )
        
        # 获取匹配记录详情
        columns = [desc[0] for desc in cursor.description]
        match_data = dict(zip(columns, match_row))
        
        # 获取旧反馈值
        old_feedback = match_data.get('user_feedback')
        
        # 更新反馈（使用已有的feedback_at列）
        cursor.execute("""
            UPDATE intent_matches
            SET user_feedback = ?, feedback_at = ?
            WHERE id = ?
        """, (feedback_value, datetime.now().isoformat() if feedback_value else None, match_id))
        
        conn.commit()
        
        # 记录到数据分析系统
        try:
            from src.services.scoring_analytics import scoring_analytics
            
            # 准备评分事件数据
            # 安全地解析JSON字段
            score_details = match_data.get('score_details')
            if score_details and isinstance(score_details, str):
                try:
                    score_details = json.loads(score_details)
                except:
                    score_details = {}
            else:
                score_details = {}
                
            conditions = match_data.get('conditions')
            if conditions and isinstance(conditions, str):
                try:
                    conditions = json.loads(conditions)
                except:
                    conditions = {}
            else:
                conditions = {}
            
            scoring_event = {
                "user_id": query_user_id,
                "intent_id": match_data['intent_id'],
                "profile_id": match_data['profile_id'],
                "match_score": match_data.get('match_score', 0),
                "score_details": score_details,
                "user_feedback": feedback_value,
                "old_feedback": old_feedback,
                "intent_name": match_data.get('intent_name', ''),
                "conditions": conditions,
                "timestamp": datetime.now().isoformat()
            }
            
            # 记录评分事件
            await scoring_analytics.record_scoring_event(scoring_event)
            
            # 如果积累了足够反馈，触发校准
            feedback_count = await scoring_analytics.get_user_feedback_count(query_user_id)
            if feedback_count >= 10 and feedback_count % 5 == 0:  # 每5个反馈触发一次校准
                calibration_params = await scoring_analytics.calculate_calibration(query_user_id)
                if calibration_params:
                    logger.info(f"用户 {query_user_id} 触发自动校准: {calibration_params}")
                    # 这里可以自动应用校准参数
                    from src.config.scoring_config import scoring_config_manager
                    scoring_config_manager.update_config({
                        'calibration': calibration_params
                    })
        except Exception as e:
            # 分析系统错误不影响反馈更新
            logger.warning(f"记录到分析系统失败: {e}")
        
        conn.close()
        
        return {
            "success": True,
            "message": f"反馈已更新为: {feedback_value or '无'}",
            "data": {
                "matchId": match_id,
                "feedback": feedback_value,
                "oldFeedback": old_feedback
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新反馈失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新反馈失败: {str(e)}"
        )

# ========== AI增强功能API ==========

@app.post("/api/ai/vectorize-intent/{intent_id}")
async def vectorize_intent(
    intent_id: int,
    current_user: str = Depends(verify_user_token)
):
    """为指定意图生成向量（手动触发）"""
    try:
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 获取意图详情
        cursor.execute("""
            SELECT * FROM user_intents 
            WHERE id = ? AND user_id = ?
        """, (intent_id, query_user_id))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="意图不存在"
            )
        
        columns = [desc[0] for desc in cursor.description]
        intent = dict(zip(columns, row))
        
        # 解析条件
        try:
            intent['conditions'] = json.loads(intent['conditions']) if intent['conditions'] else {}
        except:
            intent['conditions'] = {}
        
        # 导入并使用向量服务
        try:
            from src.services.vector_service import VectorService
            
            async with VectorService() as vector_service:
                # 生成向量
                embedding = await vector_service.vectorize_intent(intent)
                
                if embedding:
                    # 存储向量
                    import pickle
                    embedding_bytes = pickle.dumps(embedding)
                    
                    cursor.execute("""
                        UPDATE user_intents 
                        SET embedding = ?, 
                            embedding_model = 'text-embedding-v3',
                            embedding_updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (embedding_bytes, intent_id))
                    
                    # 更新向量索引
                    cursor.execute("""
                        INSERT OR REPLACE INTO vector_index 
                        (entity_type, entity_id, user_id, vector_hash, dimension)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        'intent', intent_id, query_user_id,
                        str(hash(str(embedding))), len(embedding)
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                    return {
                        "success": True,
                        "message": "意图向量化成功",
                        "data": {
                            "intentId": intent_id,
                            "vectorDimension": len(embedding),
                            "model": "text-embedding-v3"
                        }
                    }
                else:
                    conn.close()
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="向量生成失败"
                    )
                    
        except ImportError:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="向量服务不可用，请检查QWEN_API_KEY配置"
            )
        
    except Exception as e:
        logger.error(f"向量化失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"向量化失败: {str(e)}"
        )

@app.get("/api/ai/vector-status")
async def get_vector_status(
    current_user: str = Depends(verify_user_token)
):
    """获取向量化状态统计"""
    try:
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 统计意图向量化情况
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(embedding) as vectorized
            FROM user_intents 
            WHERE user_id = ?
        """, (query_user_id,))
        
        intent_stats = cursor.fetchone()
        
        # 统计联系人向量化情况
        from src.services.intent_matcher import intent_matcher
        user_table = intent_matcher._get_user_table_name(query_user_id)
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name = ?
        """, (user_table,))
        
        profile_total = 0
        profile_vectorized = 0
        
        if cursor.fetchone():
            # 检查是否有embedding字段
            cursor.execute(f"PRAGMA table_info({user_table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'embedding' in columns:
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(embedding) as vectorized
                    FROM {user_table}
                """)
                profile_stats = cursor.fetchone()
                profile_total = profile_stats[0]
                profile_vectorized = profile_stats[1]
            else:
                cursor.execute(f"SELECT COUNT(*) FROM {user_table}")
                profile_total = cursor.fetchone()[0]
        
        # 检查AI功能可用性
        ai_available = False
        try:
            from src.services.vector_service import vector_service
            ai_available = bool(vector_service.api_key)
        except:
            pass
        
        conn.close()
        
        return {
            "success": True,
            "data": {
                "aiEnabled": ai_available,
                "intents": {
                    "total": intent_stats[0],
                    "vectorized": intent_stats[1],
                    "percentage": round(intent_stats[1] / intent_stats[0] * 100, 1) if intent_stats[0] > 0 else 0
                },
                "profiles": {
                    "total": profile_total,
                    "vectorized": profile_vectorized,
                    "percentage": round(profile_vectorized / profile_total * 100, 1) if profile_total > 0 else 0
                },
                "lastUpdated": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"获取向量状态失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取向量状态失败: {str(e)}"
        )

@app.post("/api/ai/batch-vectorize")
async def batch_vectorize(
    current_user: str = Depends(verify_user_token)
):
    """批量向量化用户的意图和联系人"""
    try:
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 检查AI服务可用性
        try:
            from src.services.vector_service import VectorService
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="向量服务不可用，请检查配置"
            )
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        async with VectorService() as vector_service:
            vectorized_intents = 0
            vectorized_profiles = 0
            
            # 1. 向量化意图
            cursor.execute("""
                SELECT * FROM user_intents 
                WHERE user_id = ? AND embedding IS NULL
            """, (query_user_id,))
            
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                intent = dict(zip(columns, row))
                try:
                    intent['conditions'] = json.loads(intent['conditions']) if intent['conditions'] else {}
                except:
                    intent['conditions'] = {}
                
                embedding = await vector_service.vectorize_intent(intent)
                if embedding:
                    import pickle
                    embedding_bytes = pickle.dumps(embedding)
                    
                    cursor.execute("""
                        UPDATE user_intents 
                        SET embedding = ?, embedding_model = 'text-embedding-v3', 
                            embedding_updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (embedding_bytes, intent['id']))
                    
                    vectorized_intents += 1
            
            # 2. 向量化联系人
            user_table = db.get_user_table_name(query_user_id)
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name = ?
            """, (user_table,))
            
            if cursor.fetchone():
                cursor.execute(f"PRAGMA table_info({user_table})")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'embedding' in columns:
                    cursor.execute(f"""
                        SELECT * FROM {user_table} 
                        WHERE embedding IS NULL
                        LIMIT 20
                    """)  # 限制批量数量避免超时
                    
                    columns = [desc[0] for desc in cursor.description]
                    for row in cursor.fetchall():
                        profile = dict(zip(columns, row))
                        
                        embedding = await vector_service.vectorize_profile(profile)
                        if embedding:
                            import pickle
                            embedding_bytes = pickle.dumps(embedding)
                            
                            cursor.execute(f"""
                                UPDATE {user_table}
                                SET embedding = ?, embedding_model = 'text-embedding-v3', 
                                    embedding_updated_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            """, (embedding_bytes, profile['id']))
                            
                            vectorized_profiles += 1
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": f"批量向量化完成：意图{vectorized_intents}个，联系人{vectorized_profiles}个",
                "data": {
                    "vectorizedIntents": vectorized_intents,
                    "vectorizedProfiles": vectorized_profiles
                }
            }
        
    except Exception as e:
        logger.error(f"批量向量化失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量向量化失败: {str(e)}"
        )