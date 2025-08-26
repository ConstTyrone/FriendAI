import { STORAGE_KEYS, EVENT_TYPES } from './constants';
import { getStorageSync, setStorageSync, removeStorageSync } from './storage-utils';
import apiClient from './api-client';
import dataManager from './data-manager';

class AuthManager {
  constructor() {
    this.userInfo = null;
    this.token = null;
    this.wechatUserInfo = null;
    this.listeners = [];
    
    // 初始化时从存储中恢复数据
    this.restoreFromStorage();
  }

  /**
   * 从存储中恢复认证状态
   */
  restoreFromStorage() {
    try {
      this.token = getStorageSync(STORAGE_KEYS.AUTH_TOKEN);
      this.userInfo = getStorageSync(STORAGE_KEYS.USER_INFO);
      
      if (this.token) {
        apiClient.setToken(this.token);
        getApp().globalData.isLoggedIn = true;
        getApp().globalData.userInfo = this.userInfo;
      }
    } catch (error) {
      console.error('恢复认证状态失败:', error);
    }
  }

  /**
   * 微信登录
   */
  async wxLogin() {
    console.log('开始调用 wx.login()...');
    return new Promise((resolve, reject) => {
      wx.login({
        success: (res) => {
          console.log('wx.login 成功:', res);
          if (res.code) {
            resolve(res.code);
          } else {
            reject(new Error('微信登录失败：未获取到code'));
          }
        },
        fail: (error) => {
          console.error('wx.login 失败:', error);
          reject(error);
        }
      });
    });
  }

  /**
   * 获取微信用户信息
   */
  async getWxUserInfo() {
    return new Promise((resolve, reject) => {
      wx.getUserProfile({
        desc: '用于完善用户资料',
        success: (res) => {
          this.wechatUserInfo = res.userInfo;
          resolve(res.userInfo);
        },
        fail: reject
      });
    });
  }

  /**
   * 微信一键登录
   */
  async wechatLogin() {
    console.log('===== authManager.wechatLogin 开始 =====');
    try {
      // 1. 调用wx.login获取code
      const code = await this.wxLogin();
      console.log('获取到微信登录code:', code);
      
      // 2. 使用code调用后端登录接口
      console.log('准备调用 apiClient.login，发送code:', code);
      
      const loginResult = await apiClient.login(code, true);  // true表示使用code
      
      console.log('API登录返回结果:', loginResult);
      console.log('后端返回的微信ID:', loginResult.wechat_user_id);
      
      if (loginResult.success) {
        // 3. 保存认证信息
        this.token = loginResult.token;
        this.userInfo = {
          wechatUserId: loginResult.wechat_user_id || loginResult.openid,
          userId: loginResult.user_id,
          unionId: loginResult.unionid,
          externalUserId: loginResult.external_userid,
          isBound: loginResult.isBound || false,
          stats: loginResult.stats,
          loginTime: Date.now()
        };
        
        // 4. 存储到本地
        setStorageSync(STORAGE_KEYS.AUTH_TOKEN, this.token);
        setStorageSync(STORAGE_KEYS.WECHAT_USER_ID, loginResult.wechat_user_id || loginResult.openid);
        setStorageSync(STORAGE_KEYS.USER_INFO, this.userInfo);
        
        // 5. 设置API客户端token
        apiClient.setToken(this.token);
        
        // 6. 更新全局状态
        getApp().globalData.isLoggedIn = true;
        getApp().globalData.userInfo = this.userInfo;
        
        // 7. 触发登录成功事件
        this.notifyListeners(EVENT_TYPES.LOGIN_SUCCESS, this.userInfo);
        
        return {
          success: true,
          userInfo: this.userInfo,
          message: '登录成功'
        };
      }
      
      throw new Error(loginResult.detail || '登录失败');
    } catch (error) {
      console.error('微信登录失败:', error);
      return {
        success: false,
        error: error.message || '登录失败',
        detail: error.message
      };
    }
  }


  /**
   * 登出
   */
  logout() {
    try {
      // 清除本地存储
      removeStorageSync(STORAGE_KEYS.AUTH_TOKEN);
      removeStorageSync(STORAGE_KEYS.WECHAT_USER_ID);
      removeStorageSync(STORAGE_KEYS.USER_INFO);
      
      // 清除内存数据
      this.token = null;
      this.userInfo = null;
      this.wechatUserInfo = null;
      
      // 清除API客户端token
      apiClient.setToken(null);
      
      // 更新全局状态
      getApp().globalData.isLoggedIn = false;
      getApp().globalData.userInfo = null;
      
      // 触发登出事件
      this.notifyListeners(EVENT_TYPES.LOGOUT);
      
      return true;
    } catch (error) {
      console.error('登出失败:', error);
      return false;
    }
  }

  /**
   * 检查登录状态
   */
  isLoggedIn() {
    return !!(this.token && this.userInfo);
  }

  /**
   * 获取当前用户信息
   */
  getCurrentUser() {
    return this.userInfo;
  }

  /**
   * 获取当前Token
   */
  getToken() {
    return this.token;
  }

  /**
   * 刷新用户信息
   */
  async refreshUserInfo() {
    try {
      if (!this.isLoggedIn()) {
        throw new Error('用户未登录');
      }
      
      const userInfo = await apiClient.getUserInfo();
      
      if (userInfo.success) {
        this.userInfo = {
          ...this.userInfo,
          ...userInfo,
          updateTime: Date.now()
        };
        
        setStorageSync(STORAGE_KEYS.USER_INFO, this.userInfo);
        getApp().globalData.userInfo = this.userInfo;
        
        return this.userInfo;
      }
      
      throw new Error('刷新用户信息失败');
    } catch (error) {
      console.error('刷新用户信息失败:', error);
      throw error;
    }
  }

  /**
   * 更新用户信息（本地更新）
   */
  updateUserInfo(newUserInfo) {
    try {
      if (!this.isLoggedIn()) {
        console.warn('用户未登录，无法更新用户信息');
        return false;
      }
      
      // 合并新的用户信息
      this.userInfo = {
        ...this.userInfo,
        ...newUserInfo,
        updateTime: Date.now()
      };
      
      // 保存到本地存储
      setStorageSync(STORAGE_KEYS.USER_INFO, this.userInfo);
      
      // 更新全局状态
      getApp().globalData.userInfo = this.userInfo;
      
      console.log('用户信息已更新:', this.userInfo);
      return true;
    } catch (error) {
      console.error('更新用户信息失败:', error);
      return false;
    }
  }

  /**
   * 验证Token有效性
   */
  async validateToken() {
    try {
      if (!this.token) {
        return false;
      }
      
      // 通过调用需要认证的接口来验证token
      await apiClient.getUserInfo();
      return true;
    } catch (error) {
      // Token无效
      if (error.statusCode === 401) {
        this.logout();
        return false;
      }
      // 其他错误不影响token状态
      return true;
    }
  }

  /**
   * 添加事件监听器
   */
  addListener(listener) {
    this.listeners.push(listener);
    
    // 返回移除监听器的函数
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  /**
   * 通知所有监听器
   */
  notifyListeners(eventType, data = null) {
    this.listeners.forEach(listener => {
      try {
        listener(eventType, data);
      } catch (error) {
        console.error('事件监听器执行失败:', error);
      }
    });
  }

  /**
   * 自动登录检查
   */
  async checkAutoLogin() {
    try {
      if (this.isLoggedIn()) {
        // 验证token是否还有效
        const isValid = await this.validateToken();
        if (isValid) {
          return true;
        }
      }
      
      return false;
    } catch (error) {
      console.error('自动登录检查失败:', error);
      return false;
    }
  }

  /**
   * 获取用户统计信息
   */
  async getUserStats() {
    try {
      if (!this.isLoggedIn()) {
        return null;
      }
      
      const stats = await apiClient.getStats();
      
      // 更新用户信息中的统计数据
      if (this.userInfo) {
        this.userInfo.stats = stats;
        setStorageSync(STORAGE_KEYS.USER_INFO, this.userInfo);
        getApp().globalData.userInfo = this.userInfo;
      }
      
      return stats;
    } catch (error) {
      console.error('获取用户统计失败:', error);
      return null;
    }
  }
}

// 创建单例实例
const authManager = new AuthManager();

export default authManager;