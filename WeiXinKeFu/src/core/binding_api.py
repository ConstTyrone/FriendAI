# binding_api.py
"""
企微客服与小程序用户绑定API
实现openid与external_userid的绑定关系管理
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import json
import time
import random
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 创建路由
router = APIRouter(prefix="/api/binding", tags=["binding"])

# 导入数据库
from ..database.binding_db import binding_db as db

# 初始化数据库表
if db:
    db.create_binding_table()
    logger.info("绑定数据库初始化成功")
else:
    logger.error("绑定数据库初始化失败")

# Redis连接（用于临时存储绑定会话）
try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
    logger.info("Redis连接成功")
except:
    redis_client = None
    logger.warning("Redis不可用，使用内存缓存")
    # 简单的内存缓存作为Redis的替代
    memory_cache = {}

# Pydantic模型
class CreateBindingSessionRequest(BaseModel):
    openid: str

class UpdateBindingSessionRequest(BaseModel):
    token: str
    verify_code: Optional[str] = None

class CheckBindingStatusRequest(BaseModel):
    token: str

class CompleteBindingRequest(BaseModel):
    verify_code: str
    external_userid: str

class UnbindRequest(BaseModel):
    openid: str

# 辅助函数
def generate_verify_code() -> str:
    """生成6位数字验证码"""
    return str(random.randint(100000, 999999))

def generate_token() -> str:
    """生成唯一的绑定会话token"""
    import uuid
    return str(uuid.uuid4())

def set_cache(key: str, value: dict, expire_seconds: int = 300):
    """设置缓存"""
    if redis_client:
        redis_client.setex(key, expire_seconds, json.dumps(value))
    else:
        # 使用内存缓存
        memory_cache[key] = {
            'data': value,
            'expire_at': time.time() + expire_seconds
        }

def get_cache(key: str) -> Optional[dict]:
    """获取缓存"""
    if redis_client:
        data = redis_client.get(key)
        return json.loads(data) if data else None
    else:
        # 使用内存缓存
        if key in memory_cache:
            item = memory_cache[key]
            if time.time() < item['expire_at']:
                return item['data']
            else:
                del memory_cache[key]
        return None

def delete_cache(key: str):
    """删除缓存"""
    if redis_client:
        redis_client.delete(key)
    else:
        if key in memory_cache:
            del memory_cache[key]

# API端点
@router.post("/create-session")
async def create_binding_session(request: CreateBindingSessionRequest):
    """
    创建绑定会话
    1. 生成唯一的token和验证码
    2. 存储到缓存中（5分钟有效期）
    3. 返回token和验证码给前端
    """
    try:
        openid = request.openid
        if not openid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing openid"
            )
        
        # 检查是否已经绑定
        existing_binding = db.get_user_binding(openid)
        if existing_binding and existing_binding.get('bind_status') == 1:
            return {
                "success": False,
                "message": "用户已绑定",
                "isBound": True,
                "external_userid": existing_binding.get('external_userid')
            }
        
        # 生成token和验证码
        bind_token = generate_token()
        verify_code = generate_verify_code()
        
        # 存储到缓存
        session_data = {
            "openid": openid,
            "verify_code": verify_code,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        # 存储会话数据
        set_cache(f"bind_session:{bind_token}", session_data, 300)
        logger.info(f"存储会话数据: bind_session:{bind_token}")
        
        # 同时存储验证码映射（方便通过验证码查找）
        set_cache(f"verify_code:{verify_code}", bind_token, 300)
        logger.info(f"存储验证码映射: verify_code:{verify_code} -> {bind_token}")
        
        # 验证存储是否成功
        test_token = get_cache(f"verify_code:{verify_code}")
        logger.info(f"验证存储结果: verify_code:{verify_code} -> {test_token}")
        
        logger.info(f"创建绑定会话: token={bind_token}, verify_code={verify_code}, openid={openid}")
        
        return {
            "success": True,
            "token": bind_token,
            "verify_code": verify_code,
            "expires_in": 300
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建绑定会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建绑定会话失败: {str(e)}"
        )

@router.get("/check-status")
async def check_binding_status(token: str):
    """
    检查绑定状态
    返回: pending（等待中）、bound（已绑定）、expired（已过期）、failed（失败）
    """
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing token"
            )
        
        # 获取会话数据
        session_data = get_cache(f"bind_session:{token}")
        
        if not session_data:
            return {
                "status": "expired",
                "message": "绑定会话已过期"
            }
        
        # 检查是否已完成绑定
        if session_data.get('status') == 'bound':
            return {
                "status": "bound",
                "external_userid": session_data.get('external_userid'),
                "message": "绑定成功"
            }
        
        # 检查数据库中是否已经绑定（防止缓存丢失）
        openid = session_data.get('openid')
        if openid:
            binding_info = db.get_user_binding(openid)
            if binding_info and binding_info.get('bind_status') == 1:
                # 更新缓存状态
                session_data['status'] = 'bound'
                session_data['external_userid'] = binding_info.get('external_userid')
                set_cache(f"bind_session:{token}", session_data, 60)
                
                return {
                    "status": "bound",
                    "external_userid": binding_info.get('external_userid'),
                    "message": "绑定成功"
                }
        
        return {
            "status": "pending",
            "message": "等待用户确认"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查绑定状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查状态失败: {str(e)}"
        )

@router.post("/complete")
async def complete_binding(request: CompleteBindingRequest):
    """
    完成绑定（由企微消息处理器调用）
    当用户在企微客服中发送验证码时，调用此接口完成绑定
    """
    try:
        verify_code = request.verify_code
        external_userid = request.external_userid
        
        if not verify_code or not external_userid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameters"
            )
        
        # 通过验证码查找会话token
        bind_token = get_cache(f"verify_code:{verify_code}")
        
        if not bind_token:
            return {
                "success": False,
                "message": "验证码无效或已过期"
            }
        
        # 获取会话数据
        session_data = get_cache(f"bind_session:{bind_token}")
        
        if not session_data:
            return {
                "success": False,
                "message": "绑定会话已过期"
            }
        
        openid = session_data.get('openid')
        
        # 保存绑定关系到数据库
        success = db.save_user_binding(openid, external_userid)
        
        if success:
            # 更新会话状态
            session_data['status'] = 'bound'
            session_data['external_userid'] = external_userid
            session_data['bound_at'] = datetime.now().isoformat()
            set_cache(f"bind_session:{bind_token}", session_data, 60)
            
            # 清除验证码映射
            delete_cache(f"verify_code:{verify_code}")
            
            logger.info(f"绑定成功: openid={openid}, external_userid={external_userid}")
            
            return {
                "success": True,
                "message": "绑定成功",
                "openid": openid,
                "external_userid": external_userid
            }
        else:
            return {
                "success": False,
                "message": "保存绑定关系失败"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"完成绑定失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"完成绑定失败: {str(e)}"
        )

@router.post("/unbind")
async def unbind_account(request: UnbindRequest):
    """
    解除绑定
    """
    try:
        openid = request.openid
        
        if not openid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing openid"
            )
        
        # 删除绑定关系
        success = db.remove_user_binding(openid)
        
        if success:
            logger.info(f"解除绑定成功: openid={openid}")
            return {
                "success": True,
                "message": "解除绑定成功"
            }
        else:
            return {
                "success": False,
                "message": "解除绑定失败"
            }
        
    except Exception as e:
        logger.error(f"解除绑定失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"解除绑定失败: {str(e)}"
        )

@router.get("/info")
async def get_binding_info(openid: str):
    """
    获取绑定信息
    """
    try:
        if not openid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing openid"
            )
        
        binding_info = db.get_user_binding(openid)
        
        if binding_info:
            return {
                "success": True,
                "isBound": binding_info.get('bind_status') == 1,
                "external_userid": binding_info.get('external_userid'),
                "bind_time": binding_info.get('bind_time')
            }
        else:
            return {
                "success": True,
                "isBound": False,
                "external_userid": None,
                "bind_time": None
            }
        
    except Exception as e:
        logger.error(f"获取绑定信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取绑定信息失败: {str(e)}"
        )

# 企微消息处理（当收到客服消息时调用）
async def handle_wechat_work_message(message_data: dict):
    """
    处理企微客服消息
    当用户发送验证码时，完成绑定
    """
    try:
        content = message_data.get('content', '')
        external_userid = message_data.get('external_userid')
        
        # 检查是否是6位数字验证码
        if len(content) == 6 and content.isdigit():
            logger.info(f"收到验证码: {content} from {external_userid}")
            
            # 调用完成绑定接口
            await complete_binding(CompleteBindingRequest(
                verify_code=content,
                external_userid=external_userid
            ))
            
            # 发送成功消息给用户（需要实现企微消息发送）
            # await send_kf_message(external_userid, "绑定成功！请返回小程序查看。")
            
    except Exception as e:
        logger.error(f"处理企微消息失败: {e}")