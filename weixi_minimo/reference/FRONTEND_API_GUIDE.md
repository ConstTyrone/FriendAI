# 微信客服用户画像系统 - 前端开发者API指南

## 📖 概述

本系统为微信客服用户画像管理系统，提供用户画像数据的创建、查询、管理等功能。每个微信用户拥有独立的数据存储空间，确保数据隔离和安全性。

**服务器地址**: `http://localhost:3001` (开发环境)  
**API版本**: v1.0  
**认证方式**: Bearer Token

## 🔐 认证机制

### Token获取流程

1. 使用微信用户ID调用登录接口获取Token
2. 在后续所有API请求的Header中携带Token
3. Token格式：`Authorization: Bearer {token}`

### Token说明

- Token为Base64编码的微信用户ID（简化实现）
- 生产环境建议使用JWT或其他安全认证方式
- Token会自动保存在localStorage中

## 📋 API接口详情

### 1. 用户认证

#### 1.1 用户登录

**接口地址**: `POST /api/login`

**请求参数**:
```json
{
  "wechat_user_id": "string"  // 必填，微信用户ID
}
```

**响应示例**:
```json
{
  "success": true,
  "token": "dGVzdF91c2VyXzAwMQ==",
  "wechat_user_id": "test_user_001",
  "user_id": 1,
  "stats": {
    "total_profiles": 15,
    "unique_names": 12,
    "today_profiles": 3,
    "last_profile_at": "2025-08-04T10:30:00",
    "max_profiles": 1000,
    "used_profiles": 15,
    "max_daily_messages": 100
  }
}
```

**JavaScript示例**:
```javascript
async function login(wechatUserId) {
  const response = await fetch('/api/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      wechat_user_id: wechatUserId
    })
  });
  
  const data = await response.json();
  
  if (data.success) {
    localStorage.setItem('auth_token', data.token);
    localStorage.setItem('wechat_user_id', data.wechat_user_id);
    return data;
  } else {
    throw new Error(data.detail || '登录失败');
  }
}
```

---

### 2. 用户画像管理

#### 2.1 获取画像列表

**接口地址**: `GET /api/profiles`

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码，从1开始 |
| page_size | int | 否 | 20 | 每页数量，最大100 |
| search | string | 否 | - | 搜索关键词 |

**请求头**:
```
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "total": 45,
  "profiles": [
    {
      "id": 1,
      "profile_name": "张三",
      "gender": "男",
      "age": "28",
      "phone": "138****1234",
      "location": "北京",
      "marital_status": "已婚已育",
      "education": "本科",
      "company": "某科技公司",
      "position": "软件工程师",
      "asset_level": "中等",
      "personality": "开朗活泼，技术能力强",
      "ai_summary": "这是一位在北京工作的软件工程师...",
      "confidence_score": 0.85,
      "source_type": "text",
      "created_at": "2025-08-04T10:30:00",
      "updated_at": "2025-08-04T10:30:00"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

**JavaScript示例**:
```javascript
async function getProfiles(page = 1, pageSize = 20, search = '') {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString()
  });
  
  if (search) {
    params.append('search', search);
  }
  
  const response = await fetch(`/api/profiles?${params}`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
    }
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  return await response.json();
}
```

#### 2.2 获取画像详情

**接口地址**: `GET /api/profiles/{profile_id}`

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| profile_id | int | 是 | 画像ID |

**响应示例**:
```json
{
  "success": true,
  "profile": {
    "id": 1,
    "profile_name": "张三",
    "gender": "男",
    "age": "28",
    "phone": "138****1234",
    "location": "北京",
    "marital_status": "已婚已育",
    "education": "本科",
    "company": "某科技公司",
    "position": "软件工程师",
    "asset_level": "中等",
    "personality": "开朗活泼，技术能力强",
    "ai_summary": "这是一位在北京工作的软件工程师...",
    "confidence_score": 0.85,
    "source_type": "text",
    "raw_message_content": "用户发送的原始消息内容...",
    "raw_ai_response": {
      "summary": "AI分析总结",
      "user_profiles": [...]
    },
    "created_at": "2025-08-04T10:30:00",
    "updated_at": "2025-08-04T10:30:00"
  }
}
```

**JavaScript示例**:
```javascript
async function getProfileDetail(profileId) {
  const response = await fetch(`/api/profiles/${profileId}`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
    }
  });
  
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('画像不存在');
    }
    throw new Error(`HTTP ${response.status}`);
  }
  
  const data = await response.json();
  return data.profile;
}
```

#### 2.3 删除画像

**接口地址**: `DELETE /api/profiles/{profile_id}`

**路径参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| profile_id | int | 是 | 画像ID |

**响应示例**:
```json
{
  "success": true,
  "message": "画像删除成功"
}
```

**JavaScript示例**:
```javascript
async function deleteProfile(profileId) {
  const response = await fetch(`/api/profiles/${profileId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
    }
  });
  
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('画像不存在');
    }
    throw new Error(`HTTP ${response.status}`);
  }
  
  return await response.json();
}
```

---

### 3. 搜索和查询

#### 3.1 搜索画像

**接口地址**: `GET /api/search`

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| q | string | 是 | - | 搜索关键词 |
| limit | int | 否 | 20 | 结果数量限制 |

**响应示例**:
```json
{
  "success": true,
  "total": 5,
  "profiles": [
    {
      "id": 1,
      "profile_name": "张三",
      "company": "某科技公司",
      "position": "软件工程师",
      // ... 其他字段
    }
  ],
  "query": "张三"
}
```

**JavaScript示例**:
```javascript
async function searchProfiles(query, limit = 20) {
  const params = new URLSearchParams({
    q: query,
    limit: limit.toString()
  });
  
  const response = await fetch(`/api/search?${params}`, {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
    }
  });
  
  if (!response.ok) {
    throw new Error(`搜索失败: HTTP ${response.status}`);
  }
  
  return await response.json();
}
```

#### 3.2 获取最近画像

**接口地址**: `GET /api/recent`

**请求参数**:
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| limit | int | 否 | 10 | 结果数量，最大50 |

**响应示例**:
```json
{
  "success": true,
  "profiles": [
    {
      "id": 5,
      "profile_name": "李四",
      // ... 最新的画像数据
    }
  ],
  "total": 10
}
```

---

### 4. 统计信息

#### 4.1 获取用户统计

**接口地址**: `GET /api/stats`

**响应示例**:
```json
{
  "total_profiles": 45,
  "unique_names": 38,
  "today_profiles": 5,
  "last_profile_at": "2025-08-04T15:20:00",
  "max_profiles": 1000,
  "used_profiles": 45,
  "max_daily_messages": 100
}
```

**字段说明**:
| 字段 | 类型 | 说明 |
|------|------|------|
| total_profiles | int | 总画像数量 |
| unique_names | int | 唯一姓名数量 |
| today_profiles | int | 今日新增画像 |
| last_profile_at | string | 最后更新时间 |
| max_profiles | int | 最大画像限制 |
| used_profiles | int | 已使用画像数 |
| max_daily_messages | int | 每日消息限制 |

#### 4.2 获取用户信息

**接口地址**: `GET /api/user/info`

**响应示例**:
```json
{
  "success": true,
  "wechat_user_id": "test_user_001",
  "table_name": "profiles_test_user_001",
  "stats": {
    "total_profiles": 45,
    "unique_names": 38,
    // ... 统计信息
  }
}
```

---

### 5. 实时更新

#### 5.1 检查更新

**接口地址**: `GET /api/updates/check`

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| last_check | string | 否 | 上次检查时间 |

**响应示例**:
```json
{
  "success": true,
  "has_updates": true,
  "latest_profiles": [
    {
      "id": 10,
      "profile_name": "王五",
      // ... 最新画像数据
    }
  ],
  "total_profiles": 47,
  "check_time": "2025-08-04T15:30:00"
}
```

**轮询实现示例**:
```javascript
class RealTimeUpdater {
  constructor(interval = 30000) {
    this.interval = interval;
    this.timer = null;
    this.lastCheck = null;
  }
  
  start(callback) {
    this.timer = setInterval(async () => {
      try {
        const result = await this.checkUpdates();
        if (result.has_updates) {
          callback(result);
        }
        this.lastCheck = result.check_time;
      } catch (error) {
        console.error('检查更新失败:', error);
      }
    }, this.interval);
  }
  
  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
  
  async checkUpdates() {
    const params = new URLSearchParams();
    if (this.lastCheck) {
      params.append('last_check', this.lastCheck);
    }
    
    const response = await fetch(`/api/updates/check?${params}`, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      }
    });
    
    return await response.json();
  }
}

// 使用示例
const updater = new RealTimeUpdater(30000); // 30秒间隔
updater.start((result) => {
  console.log('发现新数据:', result.latest_profiles);
  // 刷新界面数据
  refreshProfileList();
});
```

---

## 🎨 数据模型

### UserProfile 用户画像对象

```typescript
interface UserProfile {
  id: number;                    // 画像ID
  profile_name: string;          // 姓名
  gender?: string;               // 性别
  age?: string;                  // 年龄
  phone?: string;                // 电话
  location?: string;             // 所在地
  marital_status?: string;       // 婚育状况
  education?: string;            // 学历
  company?: string;              // 公司
  position?: string;             // 职位
  asset_level?: string;          // 资产水平
  personality?: string;          // 性格描述
  ai_summary?: string;           // AI总结
  confidence_score?: number;     // 置信度 (0-1)
  source_type?: string;          // 消息类型
  raw_message_content?: string;  // 原始消息内容
  raw_ai_response?: object;      // AI原始响应
  created_at?: string;           // 创建时间
  updated_at?: string;           // 更新时间
}
```

### 消息类型枚举

```typescript
type MessageType = 
  | 'text'         // 文本消息
  | 'voice'        // 语音消息  
  | 'image'        // 图片消息
  | 'file'         // 文件消息
  | 'chat_record'  // 聊天记录
  | 'video'        // 视频消息
  | 'location'     // 位置消息
  | 'link'         // 链接消息
  | 'miniprogram'; // 小程序消息
```

---

## 🚨 错误处理

### HTTP状态码

| 状态码 | 说明 | 处理方式 |
|--------|------|----------|
| 200 | 请求成功 | 正常处理响应数据 |
| 400 | 请求参数错误 | 检查请求参数格式 |
| 401 | 认证失败 | 重新登录获取Token |
| 404 | 资源不存在 | 提示用户资源不存在 |
| 500 | 服务器内部错误 | 提示用户稍后重试 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 错误处理示例

```javascript
class APIError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function apiRequest(url, options = {}) {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        ...options.headers
      }
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        `API请求失败: ${response.status}`,
        response.status,
        errorData.detail || '未知错误'
      );
    }
    
    return await response.json();
    
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    
    // 网络错误
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new APIError('网络连接失败', 0, '请检查网络连接');
    }
    
    throw new APIError('请求异常', 0, error.message);
  }
}
```

---

## 🔧 开发工具

### 1. API调试工具

推荐使用以下工具进行API调试：
- **Postman**: 图形化API测试工具
- **curl**: 命令行工具
- **浏览器开发者工具**: Network面板查看请求

### 2. 测试数据

为了便于测试，可以使用以下测试用户ID：
- `test_user_001`
- `test_user_002` 
- `demo_user_001`

### 3. 本地开发配置

```javascript
// 开发环境配置
const config = {
  development: {
    apiBaseUrl: 'http://localhost:3001',
    timeout: 10000,
    retryCount: 3
  },
  production: {
    apiBaseUrl: 'https://your-api-domain.com',
    timeout: 5000,
    retryCount: 2
  }
};
```

---

## 🚀 最佳实践

### 1. Token管理

```javascript
class TokenManager {
  static getToken() {
    return localStorage.getItem('auth_token');
  }
  
  static setToken(token) {
    localStorage.setItem('auth_token', token);
  }
  
  static clearToken() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('wechat_user_id');
  }
  
  static isValidToken() {
    const token = this.getToken();
    if (!token) return false;
    
    try {
      // 简单验证token格式
      const decoded = atob(token);
      return decoded.length > 0;
    } catch {
      return false;
    }
  }
}
```

### 2. 请求拦截器

```javascript
class APIClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }
  
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    // 请求拦截
    const config = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
        ...options.headers
      }
    };
    
    try {
      const response = await fetch(url, config);
      
      // 统一错误处理
      if (response.status === 401) {
        TokenManager.clearToken();
        window.location.href = '/login';
        return;
      }
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      return await response.json();
      
    } catch (error) {
      console.error('API请求失败:', error);
      throw error;
    }
  }
  
  getAuthHeaders() {
    const token = TokenManager.getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }
}
```

### 3. 状态管理

```javascript
class ProfileStore {
  constructor() {
    this.profiles = [];
    this.stats = {};
    this.loading = false;
    this.error = null;
    this.listeners = [];
  }
  
  subscribe(listener) {
    this.listeners.push(listener);
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }
  
  notify() {
    this.listeners.forEach(listener => listener(this.getState()));
  }
  
  getState() {
    return {
      profiles: this.profiles,
      stats: this.stats,
      loading: this.loading,
      error: this.error
    };
  }
  
  setLoading(loading) {
    this.loading = loading;
    this.notify();
  }
  
  setProfiles(profiles) {
    this.profiles = profiles;
    this.loading = false;
    this.error = null;
    this.notify();
  }
  
  setError(error) {
    this.error = error;
    this.loading = false;
    this.notify();
  }
}
```

---

## 📱 移动端适配

### 1. 响应式设计要点

- 使用相对单位（rem、em、%）
- 设置合适的viewport meta标签
- 考虑触摸操作的便利性
- 优化加载性能

### 2. 移动端特殊处理

```javascript
// 检测移动设备
const isMobile = () => {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
};

// 移动端优化配置
const mobileConfig = {
  pageSize: isMobile() ? 10 : 20,  // 移动端减少每页数量
  timeout: isMobile() ? 15000 : 10000,  // 移动端增加超时时间
  retryCount: isMobile() ? 2 : 3
};
```

---

## 🔍 常见问题

### Q1: Token过期如何处理？
**A**: 当收到401状态码时，清除本地Token并重定向到登录页面。

### Q2: 如何处理网络超时？
**A**: 设置合理的超时时间，提供重试机制，向用户显示友好的错误信息。

### Q3: 分页数据如何缓存？
**A**: 可以使用Map结构缓存不同页码的数据，设置合理的缓存时间。

### Q4: 实时更新频率如何控制？
**A**: 建议30秒检查一次，避免过于频繁的请求影响性能。

### Q5: 如何优化大量数据的渲染？
**A**: 使用虚拟滚动、分页加载、图片懒加载等技术优化性能。

---

## 📞 技术支持

如有技术问题，请联系：
- 📧 邮箱: developer@example.com
- 💬 微信群: [开发者交流群]
- 📝 文档: 查看本项目的CLAUDE.md文件

## 📄 更新日志

### v1.0.0 (2025-08-04)
- ✅ 初始版本发布
- ✅ 完整的用户画像CRUD功能
- ✅ 实时更新机制
- ✅ 多用户数据隔离
- ✅ 完整的错误处理机制