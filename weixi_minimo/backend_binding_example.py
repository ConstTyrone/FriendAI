"""
企微客服与小程序用户绑定 - 后端实现示例
功能：实现openid与external_userid的绑定关系管理
"""

import json
import uuid
import time
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import redis
import pymysql
from pymysql.cursors import DictCursor
import jwt

# ======================== 配置 ========================
class Config:
    # 微信小程序配置
    WECHAT_APPID = "YOUR_APPID"  # 替换为你的小程序AppID
    WECHAT_SECRET = "YOUR_SECRET"  # 替换为你的小程序AppSecret
    
    # 企业微信配置
    CORP_ID = "YOUR_CORP_ID"  # 替换为你的企业ID
    CORP_SECRET = "YOUR_CORP_SECRET"  # 替换为你的企业密钥
    KF_SECRET = "YOUR_KF_SECRET"  # 客服密钥
    
    # JWT配置
    JWT_SECRET = "your-jwt-secret-key"  # 替换为安全的密钥
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_HOURS = 24 * 7  # 7天过期
    
    # Redis配置
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None
    
    # MySQL配置
    MYSQL_HOST = "localhost"
    MYSQL_PORT = 3306
    MYSQL_USER = "root"
    MYSQL_PASSWORD = "password"
    MYSQL_DATABASE = "wechat_binding"

# ======================== 数据模型 ========================
class LoginRequest(BaseModel):
    code: str  # 微信登录code

class CreateBindingSessionRequest(BaseModel):
    openid: str  # 微信openid

class BindingCallbackRequest(BaseModel):
    state: str  # 绑定会话token
    external_userid: str  # 企微客服用户ID

class CheckBindingStatusRequest(BaseModel):
    token: str  # 绑定会话token

# ======================== 数据库初始化 ========================
def init_database():
    """初始化数据库表"""
    connection = pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE
    )
    
    with connection.cursor() as cursor:
        # 创建用户绑定表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_binding (
                id INT PRIMARY KEY AUTO_INCREMENT,
                openid VARCHAR(64) UNIQUE NOT NULL COMMENT '微信openid',
                external_userid VARCHAR(64) UNIQUE COMMENT '企微客服用户ID',
                unionid VARCHAR(64) COMMENT '微信unionid(如果有)',
                bind_status TINYINT DEFAULT 0 COMMENT '绑定状态: 0-未绑定, 1-已绑定',
                bind_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '绑定时间',
                last_login DATETIME COMMENT '最后登录时间',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_openid (openid),
                INDEX idx_external_userid (external_userid)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户绑定关系表';
        """)
        
        # 创建用户信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_binding_id INT NOT NULL,
                profile_data JSON COMMENT '用户画像数据',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_binding_id) REFERENCES user_binding(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户画像表';
        """)
        
        connection.commit()
    connection.close()

# ======================== 工具函数 ========================
class DatabaseManager:
    def __init__(self):
        self.connection = None
    
    def get_connection(self):
        if not self.connection or not self.connection.open:
            self.connection = pymysql.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DATABASE,
                cursorclass=DictCursor
            )
        return self.connection
    
    def close(self):
        if self.connection:
            self.connection.close()

class RedisManager:
    def __init__(self):
        self.client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            password=Config.REDIS_PASSWORD,
            decode_responses=True
        )
    
    def set_with_expire(self, key: str, value: str, expire_seconds: int):
        self.client.setex(key, expire_seconds, value)
    
    def get(self, key: str) -> Optional[str]:
        return self.client.get(key)
    
    def delete(self, key: str):
        self.client.delete(key)

# ======================== 业务逻辑 ========================
class WechatService:
    @staticmethod
    def get_openid_from_code(code: str) -> Dict[str, Any]:
        """通过code获取openid"""
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": Config.WECHAT_APPID,
            "secret": Config.WECHAT_SECRET,
            "js_code": code,
            "grant_type": "authorization_code"
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if "openid" in data:
            return {
                "openid": data["openid"],
                "session_key": data.get("session_key"),
                "unionid": data.get("unionid")
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"微信登录失败: {data.get('errmsg', '未知错误')}"
            )

class TokenService:
    @staticmethod
    def generate_token(openid: str) -> str:
        """生成JWT token"""
        payload = {
            "openid": openid,
            "exp": datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRE_HOURS),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """验证JWT token"""
        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token已过期")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="无效的Token")

class BindingService:
    def __init__(self):
        self.db = DatabaseManager()
        self.redis = RedisManager()
    
    def check_binding_status(self, openid: str) -> Dict[str, Any]:
        """检查用户绑定状态"""
        connection = self.db.get_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT openid, external_userid, bind_status, bind_time
                FROM user_binding
                WHERE openid = %s
            """, (openid,))
            result = cursor.fetchone()
            
            if result and result['bind_status'] == 1:
                return {
                    "isBound": True,
                    "external_userid": result['external_userid'],
                    "bind_time": result['bind_time'].isoformat() if result['bind_time'] else None
                }
            else:
                return {"isBound": False}
    
    def create_binding_session(self, openid: str) -> str:
        """创建绑定会话"""
        # 生成唯一的绑定token
        bind_token = str(uuid.uuid4())
        
        # 存储到Redis，设置10分钟过期
        session_data = {
            "openid": openid,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        self.redis.set_with_expire(
            f"bind_session:{bind_token}",
            json.dumps(session_data),
            600  # 10分钟
        )
        
        # 在数据库中创建或更新用户记录
        connection = self.db.get_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO user_binding (openid, bind_status)
                VALUES (%s, 0)
                ON DUPLICATE KEY UPDATE 
                    updated_at = CURRENT_TIMESTAMP
            """, (openid,))
            connection.commit()
        
        return bind_token
    
    def complete_binding(self, state: str, external_userid: str) -> bool:
        """完成绑定"""
        # 从Redis获取绑定会话
        session_key = f"bind_session:{state}"
        session_data = self.redis.get(session_key)
        
        if not session_data:
            raise HTTPException(400, "无效或已过期的绑定token")
        
        session = json.loads(session_data)
        openid = session["openid"]
        
        # 更新数据库绑定关系
        connection = self.db.get_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE user_binding 
                SET external_userid = %s, 
                    bind_status = 1,
                    bind_time = CURRENT_TIMESTAMP
                WHERE openid = %s
            """, (external_userid, openid))
            connection.commit()
        
        # 更新Redis会话状态
        session["status"] = "bound"
        session["external_userid"] = external_userid
        self.redis.set_with_expire(session_key, json.dumps(session), 300)
        
        return True
    
    def get_binding_status(self, token: str) -> Dict[str, Any]:
        """获取绑定会话状态"""
        session_data = self.redis.get(f"bind_session:{token}")
        
        if not session_data:
            return {"status": "expired"}
        
        session = json.loads(session_data)
        
        # 如果状态是pending，再检查数据库
        if session["status"] == "pending":
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT bind_status, external_userid
                    FROM user_binding
                    WHERE openid = %s
                """, (session["openid"],))
                result = cursor.fetchone()
                
                if result and result['bind_status'] == 1:
                    session["status"] = "bound"
                    session["external_userid"] = result['external_userid']
                    self.redis.set_with_expire(
                        f"bind_session:{token}",
                        json.dumps(session),
                        300
                    )
        
        return {
            "status": session["status"],
            "externalUserId": session.get("external_userid")
        }

# ======================== FastAPI应用 ========================
app = FastAPI(title="企微绑定服务", version="1.0.0")

# 初始化服务
binding_service = BindingService()
wechat_service = WechatService()
token_service = TokenService()

# ======================== API路由 ========================

@app.post("/api/login")
async def login(request: LoginRequest):
    """微信小程序登录"""
    try:
        # 1. 通过code获取openid
        wechat_data = wechat_service.get_openid_from_code(request.code)
        openid = wechat_data["openid"]
        
        # 2. 检查绑定状态
        binding_status = binding_service.check_binding_status(openid)
        
        # 3. 生成token
        token = token_service.generate_token(openid)
        
        # 4. 返回结果
        return {
            "success": True,
            "token": token,
            "openid": openid,
            "isBound": binding_status["isBound"],
            "external_userid": binding_status.get("external_userid"),
            "message": "登录成功"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/binding/create-session")
async def create_binding_session(request: CreateBindingSessionRequest):
    """创建绑定会话"""
    try:
        token = binding_service.create_binding_session(request.openid)
        return {
            "success": True,
            "token": token
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/binding/callback")
async def binding_callback(request: BindingCallbackRequest):
    """企微客服回调接口 - 完成绑定"""
    try:
        success = binding_service.complete_binding(
            request.state,
            request.external_userid
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/binding/check-status")
async def check_binding_status(token: str):
    """检查绑定状态"""
    try:
        status = binding_service.get_binding_status(token)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/binding/unbind")
async def unbind_account(openid: str):
    """解除绑定"""
    try:
        connection = DatabaseManager().get_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE user_binding 
                SET external_userid = NULL, 
                    bind_status = 0
                WHERE openid = %s
            """, (openid,))
            connection.commit()
        
        return {"success": True, "message": "解绑成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/binding/info")
async def get_binding_info(openid: str):
    """获取绑定信息"""
    try:
        binding_status = binding_service.check_binding_status(openid)
        return binding_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ======================== 企微消息处理 ========================

@app.post("/api/wechat-work/callback")
async def handle_wechat_work_callback(request: Request):
    """
    处理企微客服事件回调
    当用户进入客服会话时，企微会调用此接口
    """
    try:
        # 解析XML数据（企微使用XML格式）
        body = await request.body()
        # 这里需要根据企微的实际回调格式解析
        # 示例：提取external_userid和state参数
        
        # 假设解析后得到以下数据
        external_userid = "extracted_external_userid"
        state = "extracted_state_from_url"
        
        # 完成绑定
        if state and external_userid:
            binding_service.complete_binding(state, external_userid)
        
        return {"success": True}
    except Exception as e:
        print(f"企微回调处理失败: {e}")
        return {"success": False}

# ======================== 启动应用 ========================
if __name__ == "__main__":
    import uvicorn
    
    # 初始化数据库
    init_database()
    
    # 启动服务
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )

"""
部署说明：
1. 安装依赖：
   pip install fastapi uvicorn redis pymysql pyjwt requests

2. 配置数据库：
   - 创建MySQL数据库：CREATE DATABASE wechat_binding;
   - 运行此脚本会自动创建表

3. 配置Redis：
   - 安装并启动Redis服务

4. 修改配置：
   - 在Config类中填写实际的配置信息
   - WECHAT_APPID和WECHAT_SECRET
   - 企业微信相关配置

5. 运行服务：
   python backend_binding_example.py

6. 企微配置：
   - 在企微后台配置客服回调URL：http://your-domain.com/api/wechat-work/callback
   - 配置客服链接时携带state参数

7. 前端配置：
   - 在constants.js中配置CORP_ID和KF_ID
   - 确保API地址正确
"""