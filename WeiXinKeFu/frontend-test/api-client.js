/**
 * API客户端类
 * 封装所有API调用逻辑
 */
class APIClient {
    constructor(baseURL = 'http://localhost:3001') {
        this.baseURL = baseURL;
        this.token = localStorage.getItem('auth_token');
        this.isConnected = false;
    }

    /**
     * 获取请求头
     */
    getHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json'
        };
        
        if (includeAuth && this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        return headers;
    }

    /**
     * 通用请求方法
     */
    async request(url, options = {}) {
        const fullUrl = `${this.baseURL}${url}`;
        const startTime = Date.now();
        
        try {
            const response = await fetch(fullUrl, {
                ...options,
                headers: {
                    ...this.getHeaders(options.requireAuth !== false),
                    ...options.headers
                }
            });
            
            const duration = Date.now() - startTime;
            const data = await response.json();
            
            // 记录API调用日志
            this.logAPICall(options.method || 'GET', url, response.status, duration, data);
            
            if (!response.ok) {
                throw new Error(data.detail || `HTTP ${response.status}`);
            }
            
            return { success: true, data, status: response.status, duration };
            
        } catch (error) {
            const duration = Date.now() - startTime;
            
            // 记录错误日志
            this.logAPICall(options.method || 'GET', url, 'ERROR', duration, { error: error.message });
            
            return { 
                success: false, 
                error: error.message, 
                duration 
            };
        }
    }

    /**
     * 记录API调用日志
     */
    logAPICall(method, url, status, duration, data) {
        const logEntry = {
            timestamp: new Date().toLocaleString(),
            method,
            url,
            status,
            duration,
            data
        };
        
        // 触发日志事件
        window.dispatchEvent(new CustomEvent('apiLog', { detail: logEntry }));
    }

    /**
     * 测试服务器连接
     */
    async testConnection() {
        const result = await this.request('/', { requireAuth: false });
        this.isConnected = result.success;
        return result;
    }

    /**
     * 用户登录
     */
    async login(wechatUserId) {
        const result = await this.request('/api/login', {
            method: 'POST',
            requireAuth: false,
            body: JSON.stringify({ wechat_user_id: wechatUserId })
        });
        
        if (result.success) {
            this.token = result.data.token;
            localStorage.setItem('auth_token', this.token);
            localStorage.setItem('wechat_user_id', wechatUserId);
        }
        
        return result;
    }

    /**
     * 用户登出
     */
    logout() {
        this.token = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('wechat_user_id');
    }

    /**
     * 获取用户画像列表
     */
    async getProfiles(page = 1, pageSize = 20, search = '') {
        const params = new URLSearchParams({
            page: page.toString(),
            page_size: pageSize.toString()
        });
        
        if (search) {
            params.append('search', search);
        }
        
        return await this.request(`/api/profiles?${params}`);
    }

    /**
     * 获取画像详情
     */
    async getProfileDetail(profileId) {
        return await this.request(`/api/profiles/${profileId}`);
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
     * 获取用户统计信息
     */
    async getStats() {
        return await this.request('/api/stats');
    }

    /**
     * 搜索画像
     */
    async searchProfiles(query, limit = 20) {
        const params = new URLSearchParams({
            q: query,
            limit: limit.toString()
        });
        
        return await this.request(`/api/search?${params}`);
    }

    /**
     * 获取最近画像
     */
    async getRecent(limit = 10) {
        const params = new URLSearchParams({
            limit: limit.toString()
        });
        
        return await this.request(`/api/recent?${params}`);
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
        const params = new URLSearchParams();
        if (lastCheck) {
            params.append('last_check', lastCheck);
        }
        
        const url = `/api/updates/check${params.toString() ? '?' + params : ''}`;
        return await this.request(url);
    }

    /**
     * 检查是否已登录
     */
    isLoggedIn() {
        return !!this.token;
    }

    /**
     * 获取当前用户ID
     */
    getCurrentUserId() {
        return localStorage.getItem('wechat_user_id');
    }
}

// 创建全局API客户端实例
window.apiClient = new APIClient();