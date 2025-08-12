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
   * 微信登录
   * @param {string} customWechatId - 可选的自定义微信ID（用于手动输入）
   */
  async wechatLogin(customWechatId = null) {
    console.log('===== authManager.wechatLogin 开始 =====');
    try {
      let loginResult;
      let code;
      
      if (customWechatId) {
        // 手动输入的微信ID，使用兼容模式
        console.log('使用手动输入的微信ID登录:', customWechatId);
        try {
          loginResult = await apiClient.login(customWechatId, false);  // false表示使用wechat_user_id
        } catch (apiError) {
          console.error('API调用失败:', apiError);
          throw apiError;
        }
      } else {
        // 正常的微信登录流程
        console.log('开始正常的微信登录流程');
        
        // 1. 调用wx.login获取code
        code = await this.wxLogin();
        console.log('获取到微信登录code:', code);
        
        // 2. 使用code调用后端登录接口
        console.log('准备调用 apiClient.login，发送code:', code);
        
        try {
          loginResult = await apiClient.login(code, true);  // true表示使用code
        } catch (apiError) {
          console.error('API调用失败:', apiError);
          
          // 如果是网络错误，提供本地模拟登录选项
          if (apiError.errMsg && apiError.errMsg.includes('request:fail')) {
            console.log('检测到网络错误，使用本地模拟登录');
            
            // 模拟登录响应
            loginResult = {
              success: true,
              token: 'local_test_token_' + Date.now(),
              wechat_user_id: 'wx_' + code.substring(0, 8),
              user_id: 'local_user_' + Date.now(),
              stats: {
                total_profiles: 0,
                today_profiles: 0
              },
              message: '本地模拟登录成功（后端服务不可用）'
            };
          } else {
            throw apiError;
          }
        }
      }
      
      console.log('API登录返回结果:', loginResult);
      console.log('后端返回的微信ID:', loginResult.wechat_user_id);
      
      // 检查是否已绑定企微账号
      if (loginResult.success && !loginResult.isBound) {
        console.log('用户未绑定企微账号，需要引导绑定');
        
        // 创建绑定会话
        const bindingSession = await apiClient.createBindingSession({
          openid: loginResult.openid || loginResult.wechat_user_id
        });
        
        console.log('绑定会话创建成功:', bindingSession);
        
        // 跳转到绑定页面，传递token和验证码
        const url = `/pages/bind-account/bind-account?token=${bindingSession.token}&openid=${loginResult.openid || loginResult.wechat_user_id}&verifyCode=${bindingSession.verify_code || ''}&autoOpen=true`;
        console.log('跳转URL:', url);
        
        wx.navigateTo({
          url: url
        });
        
        return {
          success: false,
          needBinding: true,
          message: '需要绑定企业微信账号'
        };
      }
      
      if (loginResult.success) {
        // 3. 保存认证信息
        this.token = loginResult.token;
        this.userInfo = {
          wechatUserId: loginResult.wechat_user_id || loginResult.openid,  // 真实的微信openid
          userId: loginResult.user_id,  // 后端数据库中的用户ID
          unionId: loginResult.unionid,  // 如果有unionid也保存
          externalUserId: loginResult.external_userid,  // 企微客服用户ID
          isBound: loginResult.isBound || false,  // 绑定状态
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
   * 用户登录流程（兼容旧版本）
   */
  async login(customUserId = null) {
    try {
      // 如果没有自定义用户ID，使用微信原生登录
      if (!customUserId) {
        return await this.wechatLogin();
      }
      
      // 1. 微信登录获取code
      const code = await this.wxLogin();
      
      // 2. 生成用户标识
      let userId = customUserId;
      if (!userId) {
        // 如果没有自定义用户ID，使用微信code生成
        userId = `wx_${code.substring(0, 8)}_${Date.now()}`;
      }
      
      // 3. 调用后端登录接口
      const loginResult = await apiClient.login(userId, false);  // false表示使用wechat_user_id
      
      if (loginResult.success) {
        // 4. 保存认证信息
        this.token = loginResult.token;
        this.userInfo = {
          wechatUserId: loginResult.wechat_user_id || loginResult.openid,  // 真实的微信openid
          userId: loginResult.user_id,  // 后端数据库中的用户ID
          unionId: loginResult.unionid,  // 如果有unionid也保存
          stats: loginResult.stats,
          loginTime: Date.now()
        };
        
        // 5. 存储到本地
        setStorageSync(STORAGE_KEYS.AUTH_TOKEN, this.token);
        setStorageSync(STORAGE_KEYS.WECHAT_USER_ID, loginResult.wechat_user_id);
        setStorageSync(STORAGE_KEYS.USER_INFO, this.userInfo);
        
        // 6. 设置API客户端token
        apiClient.setToken(this.token);
        
        // 7. 更新全局状态
        getApp().globalData.isLoggedIn = true;
        getApp().globalData.userInfo = this.userInfo;
        
        // 8. 触发登录成功事件
        this.notifyListeners(EVENT_TYPES.LOGIN_SUCCESS, this.userInfo);
        
        return loginResult;
      }
      
      throw new Error(loginResult.detail || '登录失败');
    } catch (error) {
      console.error('登录失败:', error);
      throw error;
    }
  }

  /**
   * 快速登录（使用测试用户ID）
   */
  async quickLogin(testUserId = 'test_user_001') {
    try {
      const loginResult = await apiClient.login(testUserId);
      
      if (loginResult.success) {
        this.token = loginResult.token;
        this.userInfo = {
          wechatUserId: loginResult.wechat_user_id || loginResult.openid,  // 真实的微信openid
          userId: loginResult.user_id,  // 后端数据库中的用户ID
          unionId: loginResult.unionid,  // 如果有unionid也保存
          stats: loginResult.stats,
          loginTime: Date.now()
        };
        
        setStorageSync(STORAGE_KEYS.AUTH_TOKEN, this.token);
        setStorageSync(STORAGE_KEYS.WECHAT_USER_ID, testUserId);
        setStorageSync(STORAGE_KEYS.USER_INFO, this.userInfo);
        
        // 设置API客户端token
        apiClient.setToken(this.token);
        
        getApp().globalData.isLoggedIn = true;
        getApp().globalData.userInfo = this.userInfo;
        
        this.notifyListeners(EVENT_TYPES.LOGIN_SUCCESS, this.userInfo);
        
        return {
          success: true,
          userInfo: this.userInfo,
          message: '登录成功',
          ...loginResult
        };
      }
      
      throw new Error('快速登录失败');
    } catch (error) {
      console.error('快速登录失败:', error);
      throw error;
    }
  }

  /**
   * Mock用户登录（本地模拟，不依赖后端）
   */
  async mockLogin(mockUserId = 'mock_user_dev') {
    try {
      console.log('使用Mock用户登录:', mockUserId);
      
      // 模拟登录数据
      const mockLoginResult = {
        success: true,
        token: 'mock_token_' + Date.now(),
        wechat_user_id: mockUserId,
        user_id: 'mock_user_' + Date.now(),
        stats: {
          total_profiles: 25,
          today_profiles: 3
        },
        message: 'Mock登录成功（本地模拟数据）'
      };
      
      // 保存认证信息
      this.token = mockLoginResult.token;
      this.userInfo = {
        wechatUserId: mockLoginResult.wechat_user_id,
        userId: mockLoginResult.user_id,
        unionId: null,
        stats: mockLoginResult.stats,
        loginTime: Date.now(),
        isMock: true  // 标识这是Mock用户
      };
      
      // 存储到本地
      setStorageSync(STORAGE_KEYS.AUTH_TOKEN, this.token);
      setStorageSync(STORAGE_KEYS.WECHAT_USER_ID, mockUserId);
      setStorageSync(STORAGE_KEYS.USER_INFO, this.userInfo);
      
      // 设置API客户端token
      apiClient.setToken(this.token);
      
      // 更新全局状态
      getApp().globalData.isLoggedIn = true;
      getApp().globalData.userInfo = this.userInfo;
      
      // 触发登录成功事件
      this.notifyListeners(EVENT_TYPES.LOGIN_SUCCESS, this.userInfo);
      
      // 启用DataManager的Mock模式
      dataManager.enableMockMode();
      
      return {
        success: true,
        userInfo: this.userInfo,
        message: 'Mock登录成功',
        isMock: true
      };
    } catch (error) {
      console.error('Mock登录失败:', error);
      return {
        success: false,
        error: error.message || 'Mock登录失败',
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
      
      // 尝试使用存储的用户ID重新登录
      const wechatUserId = getStorageSync(STORAGE_KEYS.WECHAT_USER_ID);
      if (wechatUserId) {
        await this.quickLogin(wechatUserId);
        return true;
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