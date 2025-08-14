import { API_CONFIG, STORAGE_KEYS, ERROR_MESSAGES } from './constants';
import { getStorageSync, setStorageSync, removeStorageSync } from './storage-utils';
import { objectToQueryString } from './url-utils';

class APIClient {
  constructor() {
    this.baseURL = API_CONFIG.BASE_URL;
    this.timeout = API_CONFIG.TIMEOUT;
    this.retryCount = API_CONFIG.RETRY_COUNT;
    this.token = getStorageSync(STORAGE_KEYS.AUTH_TOKEN);
  }

  /**
   * 通用请求方法
   */
  async request(endpoint, options = {}) {
    // 兼容两种调用方式
    // 方式1: request('/api/endpoint', { method: 'POST', data: {...} })
    // 方式2: request({ url: '/api/endpoint', method: 'POST', data: {...} })
    let url, requestOptions;
    
    if (typeof endpoint === 'object') {
      // 方式2: 第一个参数是包含所有配置的对象
      url = `${this.baseURL}${endpoint.url}`;
      // 从endpoint对象中排除url字段，避免覆盖完整的URL
      const { url: _, ...restOptions } = endpoint;
      requestOptions = restOptions;
    } else {
      // 方式1: 第一个参数是URL字符串，第二个参数是选项
      url = `${this.baseURL}${endpoint}`;
      requestOptions = options;
    }
    
    console.log(`[API请求] ${requestOptions.method || 'GET'} ${url}`);
    
    const defaultOptions = {
      method: 'GET',
      timeout: this.timeout,
      header: {
        'Content-Type': 'application/json',
        ...(this.token && { 'Authorization': `Bearer ${this.token}` }),
        ...requestOptions.header
      },
      ...requestOptions
    };
    
    console.log('[API请求] 请求选项:', defaultOptions);
    console.log('[API请求] 请求数据:', requestOptions.data);

    let lastError;
    
    // 重试机制
    for (let attempt = 0; attempt <= this.retryCount; attempt++) {
      try {
        const response = await this.makeRequest(url, defaultOptions);
        console.log('[API响应] 原始响应:', response);
        return this.handleResponse(response);
      } catch (error) {
        console.error(`[API错误] 第${attempt + 1}次尝试失败:`, error);
        lastError = error;
        
        // 认证失败不重试
        if (error.statusCode === 401) {
          this.handleAuthError();
          throw error;
        }
        
        // 最后一次尝试或非网络错误不重试
        if (attempt === this.retryCount || error.statusCode !== 0) {
          break;
        }
        
        // 等待后重试
        console.log(`[API重试] 等待 ${Math.pow(2, attempt)} 秒后重试...`);
        await this.delay(Math.pow(2, attempt) * 1000);
      }
    }
    
    throw lastError;
  }

  /**
   * 发起微信请求
   */
  makeRequest(url, options) {
    return new Promise((resolve, reject) => {
      console.log('[API请求]', {
        url,
        method: options.method || 'GET',
        hasToken: !!options.header?.Authorization
      });
      
      wx.request({
        url,
        ...options,
        success: (res) => {
          console.log('[API响应]', {
            url,
            statusCode: res.statusCode,
            data: res.data
          });
          resolve(res);
        },
        fail: (error) => {
          console.error('[API失败]', {
            url,
            error: error,
            token: options.header?.Authorization ? '已设置' : '未设置'
          });
          reject(error);
        }
      });
    });
  }

  /**
   * 处理响应
   */
  handleResponse(response) {
    const { statusCode, data } = response;
    
    if (statusCode >= 200 && statusCode < 300) {
      return data;
    }
    
    const error = new Error(data?.detail || ERROR_MESSAGES.SERVER_ERROR);
    error.statusCode = statusCode;
    error.data = data;
    throw error;
  }

  /**
   * 处理认证错误
   */
  handleAuthError() {
    this.token = null;
    removeStorageSync(STORAGE_KEYS.AUTH_TOKEN);
    removeStorageSync(STORAGE_KEYS.WECHAT_USER_ID);
    
    // 触发登出事件
    getApp().globalData.isLoggedIn = false;
    
    wx.showToast({
      title: ERROR_MESSAGES.AUTH_FAILED,
      icon: 'error',
      duration: 2000
    });
  }

  /**
   * 延迟函数
   */
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 设置认证Token
   */
  setToken(token) {
    this.token = token;
    setStorageSync(STORAGE_KEYS.AUTH_TOKEN, token);
  }

  /**
   * 用户登录
   * @param {string} codeOrUserId - 微信登录code或用户ID
   * @param {boolean} isCode - 是否是code（默认true）
   */
  async login(codeOrUserId, isCode = true) {
    const payload = isCode 
      ? { code: codeOrUserId }  // 新方式：发送code
      : { wechat_user_id: codeOrUserId };  // 兼容旧方式
    
    const data = await this.request('/api/login', {
      method: 'POST',
      data: JSON.stringify(payload)
    });
    
    if (data.success) {
      this.setToken(data.token);
      // 保存后端返回的真实微信用户ID（openid或unionid）
      setStorageSync(STORAGE_KEYS.WECHAT_USER_ID, data.wechat_user_id || data.openid);
      return data;
    }
    
    throw new Error(data.detail || '登录失败');
  }

  /**
   * 获取画像列表
   */
  async getProfiles(params = {}) {
    const { page = 1, pageSize = 20, search = '' } = params;
    
    const queryParams = {
      page: page.toString(),
      page_size: pageSize.toString()
    };
    
    if (search) {
      queryParams.search = search;
    }
    
    const queryString = objectToQueryString(queryParams);
    return await this.request(`/api/profiles?${queryString}`);
  }

  /**
   * 获取画像详情
   */
  async getProfileDetail(profileId) {
    const data = await this.request(`/api/profiles/${profileId}`);
    return data.profile;
  }

  /**
   * 删除画像
   */
  async deleteProfile(profileId) {
    return await this.request(`/api/profiles/${profileId}`, {
      method: 'DELETE'
    });
  }

  /**
   * 获取联系人互动记录
   */
  async getContactInteractions(contactId, limit = 10) {
    const queryString = objectToQueryString({
      limit: limit.toString()
    });
    
    return await this.request(`/api/profiles/${contactId}/interactions?${queryString}`);
  }

  /**
   * 创建联系人
   */
  async createProfile(profileData) {
    return await this.request('/api/profiles', {
      method: 'POST',
      data: JSON.stringify(profileData)
    });
  }

  /**
   * 更新联系人
   */
  async updateProfile(profileId, profileData) {
    return await this.request(`/api/profiles/${profileId}`, {
      method: 'PUT',
      data: JSON.stringify(profileData)
    });
  }

  /**
   * 搜索画像
   */
  async searchProfiles(query, limit = 20) {
    const queryString = objectToQueryString({
      q: query,
      limit: limit.toString()
    });
    
    return await this.request(`/api/search?${queryString}`);
  }

  /**
   * 获取最近画像
   */
  async getRecentProfiles(limit = 10) {
    const queryString = objectToQueryString({
      limit: limit.toString()
    });
    
    return await this.request(`/api/recent?${queryString}`);
  }

  /**
   * 获取统计信息
   */
  async getStats() {
    return await this.request('/api/stats');
  }

  /**
   * 获取用户信息
   */
  async getUserInfo() {
    return await this.request('/api/user/info');
  }

  /**
   * 检查更新
   */
  async checkUpdates(lastCheck = null) {
    const params = {};
    if (lastCheck) {
      params.last_check = lastCheck;
    }
    
    const queryString = objectToQueryString(params);
    return await this.request(`/api/updates/check?${queryString}`);
  }

  /**
   * 上传文件
   */
  async uploadFile(filePath, fileName) {
    return new Promise((resolve, reject) => {
      wx.uploadFile({
        url: `${this.baseURL}/api/upload`,
        filePath,
        name: 'file',
        formData: {
          fileName
        },
        header: {
          ...(this.token && { 'Authorization': `Bearer ${this.token}` })
        },
        success: (res) => {
          try {
            const data = JSON.parse(res.data);
            if (res.statusCode === 200 && data.success) {
              resolve(data);
            } else {
              reject(new Error(data.detail || '上传失败'));
            }
          } catch (error) {
            reject(new Error('响应解析失败'));
          }
        },
        fail: reject
      });
    });
  }

  // ============ 企微绑定相关API ============

  /**
   * 创建绑定会话
   * @param {Object} params - 参数对象
   * @param {string} params.openid - 微信openid
   */
  async createBindingSession(params) {
    return await this.request('/api/binding/create-session', {
      method: 'POST',
      data: params
    });
  }

  /**
   * 检查绑定状态
   * @param {string} token - 绑定会话token
   */
  async checkBindingStatus(token) {
    const queryString = objectToQueryString({ token });
    return await this.request(`/api/binding/check-status?${queryString}`);
  }
  
  /**
   * 更新绑定会话验证码
   * @param {Object} params - 包含token和verify_code
   */
  async updateBindingSession(params) {
    return await this.request('/api/binding/update-session', {
      method: 'POST',
      data: params
    });
  }

  /**
   * 完成绑定（后端回调使用）
   * @param {Object} params - 参数对象
   * @param {string} params.state - 绑定会话token
   * @param {string} params.external_userid - 企微客服用户ID
   */
  async completeBinding(params) {
    return await this.request('/api/binding/callback', {
      method: 'POST',
      data: params
    });
  }

  /**
   * 解除绑定
   * @param {string} openid - 微信openid
   */
  async unbindAccount(openid) {
    return await this.request('/api/binding/unbind', {
      method: 'POST',
      data: { openid }
    });
  }

  /**
   * 获取绑定信息
   * @param {string} openid - 微信openid
   */
  async getBindingInfo(openid) {
    const queryString = objectToQueryString({ openid });
    return await this.request(`/api/binding/info?${queryString}`);
  }
}

// 创建单例实例
const apiClient = new APIClient();

export default apiClient;