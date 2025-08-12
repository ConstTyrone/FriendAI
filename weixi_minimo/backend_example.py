# 后端代码示例：正确的微信登录实现

import requests
from fastapi import HTTPException
from pydantic import BaseModel

# 这些配置应该保存在后端的环境变量中，绝不能暴露给前端
WECHAT_APPID = "你的小程序AppID"
WECHAT_SECRET = "你的小程序AppSecret"  # 绝密！不能暴露！

class WechatLoginRequest(BaseModel):
    code: str  # 前端传来的临时登录凭证

@app.post("/api/login")
async def wechat_login(request: WechatLoginRequest):
    """
    正确的微信登录实现
    """
    try:
        # 1. 接收前端传来的 code
        code = request.code
        
        # 2. 调用微信API，用 code 换取 openid
        wx_api_url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": WECHAT_APPID,
            "secret": WECHAT_SECRET,  # 这是关键！只能在后端使用
            "js_code": code,
            "grant_type": "authorization_code"
        }
        
        # 3. 发送请求到微信服务器
        response = requests.get(wx_api_url, params=params)
        data = response.json()
        
        # 4. 检查返回结果
        if "openid" in data:
            openid = data["openid"]
            session_key = data["session_key"]
            unionid = data.get("unionid")  # 如果有的话
            
            # 5. 使用 openid 在数据库中查找或创建用户
            user_id = db.get_or_create_user(openid)
            
            # 6. 生成 token 并返回
            token = generate_token(openid)
            
            return {
                "success": True,
                "token": token,
                "wechat_user_id": openid,  # 这就是真实的微信用户ID
                "user_id": user_id,
                "unionid": unionid,
                "message": "登录成功"
            }
        else:
            # 微信API返回错误
            error_code = data.get("errcode", -1)
            error_msg = data.get("errmsg", "未知错误")
            raise HTTPException(
                status_code=400,
                detail=f"微信登录失败: {error_msg} (错误码: {error_code})"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"登录失败: {str(e)}"
        )

# ========== 对比：当前后端的简化实现（不安全） ==========

@app.post("/api/login")
async def login(request: UserLoginRequest):
    """
    当前的简化实现：直接接收 wechat_user_id
    问题：
    1. 没有验证用户身份
    2. 任何人都可以传入任意ID登录
    3. 不符合微信的安全规范
    """
    wechat_user_id = request.wechat_user_id
    # 直接使用，没有验证...
    user_id = db.get_or_create_user(wechat_user_id)
    # ...