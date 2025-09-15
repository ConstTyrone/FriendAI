# routes/auth.py
"""
用户认证相关路由
处理用户登录和身份验证
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import logging
import requests
import base64

logger = logging.getLogger(__name__)
router = APIRouter()

# 身份验证
security = HTTPBearer()

# 数据库导入（与main.py保持一致）
try:
    from ...database.database_pg import pg_database
    if pg_database.pool:
        db = pg_database
        logger.info("Auth模块使用PostgreSQL数据库")
    else:
        raise ImportError("PostgreSQL不可用")
except:
    from ...database.database_sqlite_v2 import database_manager as db
    logger.info("Auth模块使用SQLite数据库（备用方案）- 多用户独立存储版本")


# Pydantic模型
class UserLoginRequest(BaseModel):
    wechat_user_id: Optional[str] = None  # 兼容旧版本
    code: Optional[str] = None  # 新增：支持微信登录code


def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """验证用户token并返回微信用户ID"""
    try:
        # 这里简化处理，token就是base64编码的微信用户ID
        # 生产环境应该使用JWT或其他安全的认证方式
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
        logger.error(f"获取查询用户ID失败: {e}")
        return openid


@router.post("/api/login")
async def login(request: UserLoginRequest):
    """用户登录，获取访问token"""
    try:
        from ...config.config import config

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
            token = base64.b64encode(wechat_user_id.encode('utf-8')).decode('utf-8')

            # 获取用户统计信息
            stats = db.get_user_stats(wechat_user_id)

            # 检查绑定状态
            from ...database.binding_db import binding_db
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