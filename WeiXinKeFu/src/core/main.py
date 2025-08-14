# main.py
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import xml.etree.ElementTree as ET
import logging
import sys
import json
import time
import sqlite3
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
    """获取用于查询画像的用户ID（优先使用external_userid）"""
    try:
        from ..database.binding_db import binding_db
        
        if binding_db:
            binding_info = binding_db.get_user_binding(openid)
            if binding_info and binding_info.get('bind_status') == 1:
                external_userid = binding_info.get('external_userid')
                if external_userid:
                    logger.info(f"使用绑定的external_userid查询画像: {external_userid}")
                    return external_userid
        
        logger.info(f"用户未绑定或绑定无效，使用openid查询画像: {openid}")
        return openid
    except Exception as e:
        logger.error(f"获取查询用户ID时出错: {e}")
        return openid

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
    current_user: str = Depends(verify_user_token)
):
    """搜索用户画像"""
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
            offset=0
        )
        
        return {
            "success": True,
            "total": total,
            "profiles": profiles,
            "query": q.strip()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索画像失败: {e}")
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

# ======================== 联系人管理API ========================

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
            "name": request.name.strip(),
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
            
            # 触发意图匹配（异步执行，不阻塞返回）
            try:
                from src.services.intent_matcher import intent_matcher
                # 在后台异步执行匹配
                matches = intent_matcher.match_profile_with_intents(profile_id, query_user_id)
                if matches:
                    logger.info(f"新联系人{profile_id}匹配到{len(matches)}个意图")
            except Exception as e:
                logger.error(f"触发意图匹配失败: {e}")
                # 不影响主流程，继续返回成功
            
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
        
        # 准备更新数据
        update_data = {}
        
        # 只更新提供的字段
        if request.name is not None:
            update_data["profile_name"] = request.name.strip()
        if request.gender is not None:
            update_data["gender"] = request.gender
        if request.age is not None:
            update_data["age"] = request.age
        if request.phone is not None:
            update_data["phone"] = request.phone
        if request.location is not None:
            update_data["location"] = request.location
        elif request.address is not None:
            update_data["location"] = request.address
        if request.marital_status is not None:
            update_data["marital_status"] = request.marital_status
        if request.education is not None:
            update_data["education"] = request.education
        if request.company is not None:
            update_data["company"] = request.company
        if request.position is not None:
            update_data["position"] = request.position
        if request.asset_level is not None:
            update_data["asset_level"] = request.asset_level
        if request.personality is not None:
            update_data["personality"] = request.personality
        if request.tags is not None:
            update_data["tags"] = request.tags  # 添加tags字段更新
        
        # 更新AI摘要（如果有备注）
        if request.notes is not None:
            update_data["ai_summary"] = request.notes
        
        # 调用数据库更新方法
        success = db.update_user_profile(query_user_id, profile_id, update_data)
        
        if success:
            logger.info(f"成功更新联系人画像：{profile_id}")
            
            # 获取更新后的画像详情
            updated_profile = db.get_user_profile_detail(query_user_id, profile_id)
            
            # 触发意图匹配（异步执行，不阻塞返回）
            try:
                from src.services.intent_matcher import intent_matcher
                # 在后台异步执行匹配
                matches = intent_matcher.match_profile_with_intents(profile_id, query_user_id)
                if matches:
                    logger.info(f"更新的联系人{profile_id}匹配到{len(matches)}个意图")
            except Exception as e:
                logger.error(f"触发意图匹配失败: {e}")
                # 不影响主流程，继续返回成功
            
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
    status: Optional[str] = "active",
    page: int = 1,
    size: int = 10,
    current_user: str = Depends(verify_user_token)
):
    """获取用户意图列表"""
    try:
        import json
        import sqlite3
        
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 查询意图
        offset = (page - 1) * size
        
        if status:
            cursor.execute("""
                SELECT * FROM user_intents 
                WHERE user_id = ? AND status = ?
                ORDER BY priority DESC, created_at DESC
                LIMIT ? OFFSET ?
            """, (query_user_id, status, size, offset))
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
            intents.append(intent)
        
        # 获取总数
        if status:
            cursor.execute(
                "SELECT COUNT(*) FROM user_intents WHERE user_id = ? AND status = ?",
                (query_user_id, status)
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
        
        # 获取用户ID
        query_user_id = get_query_user_id(current_user)
        
        # 连接数据库
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        
        # 检查意图是否存在
        cursor.execute(
            "SELECT id FROM user_intents WHERE id = ? AND user_id = ?",
            (intent_id, query_user_id)
        )
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="意图不存在"
            )
        
        # 构建更新语句
        update_fields = []
        update_values = []
        
        if request.name is not None:
            update_fields.append("name = ?")
            update_values.append(request.name)
        if request.description is not None:
            update_fields.append("description = ?")
            update_values.append(request.description)
        if request.conditions is not None:
            update_fields.append("conditions = ?")
            update_values.append(json.dumps(request.conditions, ensure_ascii=False))
        if request.threshold is not None:
            update_fields.append("threshold = ?")
            update_values.append(request.threshold)
        if request.priority is not None:
            update_fields.append("priority = ?")
            update_values.append(request.priority)
        if request.max_push_per_day is not None:
            update_fields.append("max_push_per_day = ?")
            update_values.append(request.max_push_per_day)
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
        
        return {
            "success": True,
            "message": "意图更新成功"
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
        
        # 执行匹配
        matches = intent_matcher.match_intent_with_profiles(intent_id, query_user_id)
        
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