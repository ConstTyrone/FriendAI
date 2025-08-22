"""
阿里云ASR Token自动管理服务
根据官方SDK文档实现自动获取和刷新Token机制
"""

import os
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ASRTokenManager:
    """阿里云ASR Token管理器 - 自动获取和刷新Token"""
    
    def __init__(self):
        # 从环境变量获取AccessKey配置
        self.access_key_id = os.getenv('ALIYUN_AK_ID')
        self.access_key_secret = os.getenv('ALIYUN_AK_SECRET')
        self.region_id = "cn-shanghai"
        self.domain = "nls-meta.cn-shanghai.aliyuncs.com"
        self.api_version = "2019-02-28"
        self.action = "CreateToken"
        
        # Token状态
        self._current_token: Optional[str] = None
        self._token_expire_time: Optional[int] = None
        self._last_refresh_time: Optional[float] = None
        self._refresh_lock = threading.Lock()
        
        # 自动刷新线程
        self._auto_refresh_thread: Optional[threading.Thread] = None
        self._stop_refresh = threading.Event()
        
        # 验证配置
        self._validate_config()
        
        # 启动自动刷新
        self._start_auto_refresh()
    
    def _validate_config(self):
        """验证必要的配置"""
        if not self.access_key_id or not self.access_key_secret:
            logger.warning(
                "⚠️ 缺少阿里云AccessKey配置！ASR Token将使用手动模式。\n"
                "要启用自动Token管理，请在.env文件中设置：\n"
                "ALIYUN_AK_ID=your_access_key_id\n"
                "ALIYUN_AK_SECRET=your_access_key_secret"
            )
            self._auto_mode = False
        else:
            self._auto_mode = True
            logger.info(f"✅ ASR Token管理器配置验证成功")
            logger.info(f"AccessKey ID: {self.access_key_id[:8]}...{self.access_key_id[-4:]}")
    
    def get_token(self) -> Optional[str]:
        """
        获取有效的ASR Token
        
        Returns:
            str: 有效的token，获取失败返回None
        """
        try:
            # 如果没有配置AccessKey，返回None使用手动token
            if not self._auto_mode:
                return None
            
            # 检查当前token是否有效
            if self._is_token_valid():
                return self._current_token
            
            # 需要刷新token
            return self._refresh_token()
            
        except Exception as e:
            logger.error(f"获取ASR Token失败: {e}")
            return None
    
    def _is_token_valid(self) -> bool:
        """检查当前token是否有效"""
        if not self._current_token or not self._token_expire_time:
            return False
        
        # 提前5分钟刷新token，避免在使用过程中过期
        current_time = int(time.time())
        safe_expire_time = self._token_expire_time - 300  # 提前5分钟
        
        return current_time < safe_expire_time
    
    def _refresh_token(self) -> Optional[str]:
        """刷新ASR Token"""
        with self._refresh_lock:
            # 双重检查，可能其他线程已经刷新了
            if self._is_token_valid():
                return self._current_token
            
            try:
                logger.info("🔄 正在刷新ASR Token...")
                
                # 检查SDK是否可用
                try:
                    from aliyunsdkcore.client import AcsClient
                    from aliyunsdkcore.request import CommonRequest
                except ImportError:
                    logger.error("阿里云SDK未安装，请运行: pip install aliyun-python-sdk-core")
                    return None
                
                # 创建阿里云客户端
                client = AcsClient(
                    self.access_key_id,
                    self.access_key_secret,
                    self.region_id
                )
                
                # 创建请求
                request = CommonRequest()
                request.set_domain(self.domain)
                request.set_version(self.api_version)
                request.set_action_name(self.action)
                request.set_method('POST')
                request.set_protocol_type('https')
                
                # 发送请求
                response = client.do_action_with_exception(request)
                response_data = response.decode('utf-8')
                
                # 解析响应
                result = json.loads(response_data)
                
                if 'Token' in result and 'Id' in result['Token']:
                    token = result['Token']['Id']
                    expire_time = result['Token']['ExpireTime']
                    
                    # 更新token信息
                    self._current_token = token
                    self._token_expire_time = expire_time
                    self._last_refresh_time = time.time()
                    
                    # 计算过期时间
                    expire_datetime = datetime.fromtimestamp(expire_time)
                    logger.info(f"✅ ASR Token刷新成功")
                    logger.info(f"Token: {token[:16]}...{token[-8:]}")
                    logger.info(f"过期时间: {expire_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    return token
                else:
                    logger.error(f"ASR Token响应格式异常: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"刷新ASR Token失败: {e}")
                return None
    
    def _start_auto_refresh(self):
        """启动自动刷新线程"""
        if not self._auto_mode:
            return
            
        if self._auto_refresh_thread and self._auto_refresh_thread.is_alive():
            return
        
        self._stop_refresh.clear()
        self._auto_refresh_thread = threading.Thread(
            target=self._auto_refresh_worker,
            daemon=True,
            name="ASRTokenRefresh"
        )
        self._auto_refresh_thread.start()
        logger.info("🚀 ASR Token自动刷新线程已启动")
    
    def _auto_refresh_worker(self):
        """自动刷新工作线程"""
        while not self._stop_refresh.is_set():
            try:
                # 如果没有token或即将过期，则刷新
                if not self._is_token_valid():
                    self._refresh_token()
                
                # 每分钟检查一次
                if self._stop_refresh.wait(60):
                    break
                    
            except Exception as e:
                logger.error(f"自动刷新线程异常: {e}")
                # 异常后等待5分钟再重试
                if self._stop_refresh.wait(300):
                    break
        
        logger.info("ASR Token自动刷新线程已停止")
    
    def stop_auto_refresh(self):
        """停止自动刷新"""
        self._stop_refresh.set()
        if self._auto_refresh_thread and self._auto_refresh_thread.is_alive():
            self._auto_refresh_thread.join(timeout=5)
    
    def get_token_info(self) -> Dict[str, Any]:
        """获取Token状态信息"""
        if not self._auto_mode:
            return {
                "auto_mode": False,
                "message": "使用手动Token模式，需要配置ALIYUN_AK_ID和ALIYUN_AK_SECRET启用自动模式"
            }
        
        if not self._current_token:
            return {
                "auto_mode": True,
                "has_token": False,
                "token": None,
                "expire_time": None,
                "remaining_seconds": None,
                "last_refresh": None
            }
        
        current_time = int(time.time())
        remaining_seconds = self._token_expire_time - current_time if self._token_expire_time else 0
        
        return {
            "auto_mode": True,
            "has_token": True,
            "token": f"{self._current_token[:16]}...{self._current_token[-8:]}",
            "expire_time": datetime.fromtimestamp(self._token_expire_time).strftime('%Y-%m-%d %H:%M:%S') if self._token_expire_time else None,
            "remaining_seconds": remaining_seconds,
            "remaining_hours": round(remaining_seconds / 3600, 2),
            "is_valid": self._is_token_valid(),
            "last_refresh": datetime.fromtimestamp(self._last_refresh_time).strftime('%Y-%m-%d %H:%M:%S') if self._last_refresh_time else None
        }
    
    def force_refresh(self) -> bool:
        """强制刷新Token"""
        if not self._auto_mode:
            logger.warning("自动模式未启用，无法强制刷新Token")
            return False
            
        try:
            logger.info("🔄 强制刷新ASR Token...")
            result = self._refresh_token()
            return result is not None
        except Exception as e:
            logger.error(f"强制刷新失败: {e}")
            return False

# 全局ASR Token管理器实例
asr_token_manager = ASRTokenManager()

def get_asr_token() -> Optional[str]:
    """获取有效的ASR Token的便捷函数"""
    return asr_token_manager.get_token()

def get_asr_token_info() -> Dict[str, Any]:
    """获取ASR Token状态信息的便捷函数"""
    return asr_token_manager.get_token_info()

def force_refresh_asr_token() -> bool:
    """强制刷新ASR Token的便捷函数"""
    return asr_token_manager.force_refresh()