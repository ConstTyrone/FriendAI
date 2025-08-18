"""
微信小程序订阅消息API端点
处理订阅保存和推送触发
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import requests

from ..services.miniprogram_push_service import miniprogram_push_service
from ..config.config import config

logger = logging.getLogger(__name__)
router = APIRouter()

class SubscriptionRequest(BaseModel):
    """订阅请求模型"""
    code: Optional[str] = None
    openid: Optional[str] = None
    template_id: str
    status: str  # accept, reject, ban

class PushTestRequest(BaseModel):
    """推送测试请求"""
    user_id: str
    profile_name: str
    intent_name: str
    score: float

def get_openid_from_code(code: str) -> Optional[str]:
    """
    通过code获取openid
    
    Args:
        code: 微信登录code
        
    Returns:
        openid或None
    """
    try:
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": config.wechat_mini_appid,
            "secret": config.wechat_mini_secret,
            "js_code": code,
            "grant_type": "authorization_code"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if "openid" in data:
            return data["openid"]
        else:
            logger.error(f"获取openid失败: {data}")
            return None
            
    except Exception as e:
        logger.error(f"获取openid异常: {e}")
        return None

@router.post("/api/subscription/save")
async def save_subscription(request: SubscriptionRequest, user_id: str = Depends(get_current_user)):
    """
    保存用户订阅信息
    
    Args:
        request: 订阅请求
        user_id: 当前用户ID（从token解析）
    """
    try:
        # 获取openid
        openid = request.openid
        if not openid and request.code:
            openid = get_openid_from_code(request.code)
        
        if not openid:
            raise HTTPException(status_code=400, detail="无法获取openid")
        
        # 只保存用户接受的订阅
        if request.status == "accept":
            success = miniprogram_push_service.save_user_subscription(
                user_id=user_id,
                openid=openid,
                template_id=request.template_id,
                template_name="意图匹配通知"
            )
            
            if success:
                return {"code": 200, "message": "订阅保存成功"}
            else:
                raise HTTPException(status_code=500, detail="保存订阅失败")
        else:
            # 用户拒绝或禁用，可以记录日志
            logger.info(f"用户 {user_id} 拒绝订阅: {request.status}")
            return {"code": 200, "message": "已记录订阅状态"}
            
    except Exception as e:
        logger.error(f"保存订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/subscription/status")
async def get_subscription_status(user_id: str = Depends(get_current_user)):
    """
    获取用户订阅状态
    
    Args:
        user_id: 用户ID
    """
    try:
        subscriptions = miniprogram_push_service.get_user_subscriptions(user_id)
        
        return {
            "code": 200,
            "data": {
                "has_subscription": len(subscriptions) > 0,
                "subscriptions": subscriptions
            }
        }
        
    except Exception as e:
        logger.error(f"获取订阅状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/subscription/test")
async def test_push(request: PushTestRequest, user_id: str = Depends(get_current_user)):
    """
    测试推送功能
    
    Args:
        request: 测试请求
        user_id: 用户ID
    """
    try:
        # 构造测试数据
        match_data = {
            "profile_name": request.profile_name,
            "intent_name": request.intent_name,
            "score": request.score,
            "match_id": 999,  # 测试ID
            "intent_id": 1,
            "profile_id": 1
        }
        
        # 发送推送
        success = miniprogram_push_service.send_match_notification(
            user_id=request.user_id or user_id,
            match_data=match_data
        )
        
        if success:
            return {"code": 200, "message": "测试推送已发送"}
        else:
            return {"code": 400, "message": "推送失败，请检查订阅状态"}
            
    except Exception as e:
        logger.error(f"测试推送失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 辅助函数：获取当前用户（需要根据实际认证实现修改）
def get_current_user(authorization: str = Header(None)):
    """
    从请求头获取当前用户
    这里需要根据实际的认证机制修改
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权")
    
    # 解析token获取user_id
    # 这里简化处理，实际需要JWT解析
    token = authorization.replace("Bearer ", "")
    # ... token解析逻辑
    
    return "test_user_id"  # 返回实际的user_id