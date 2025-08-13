# 微信客服用户画像系统 - 前端API文档

## 🚀 快速开始

**基础URL**: `http://localhost:3001`

**认证方式**: Bearer Token (HTTP Authorization Header)

## 📋 接口概览

### 认证接口
- `POST /api/login` - 用户登录获取Token

### 数据查询接口
- `GET /api/profiles` - 获取用户画像列表（分页）
- `GET /api/profiles/{id}` - 获取画像详情
- `GET /api/search` - 搜索用户画像
- `GET /api/recent` - 获取最近画像
- `GET /api/stats` - 获取用户统计信息
- `GET /api/user/info` - 获取当前用户信息

### 数据管理接口
- `DELETE /api/profiles/{id}` - 删除用户画像

### 实时更新接口
- `GET /api/updates/check` - 检查数据更新

## 🔐 认证流程

### 1. 用户登录

```javascript
POST /api/login
Content-Type: application/json

{
  "wechat_user_id": "your_wechat_user_id"
}
```

**响应示例**:
```json
{
  "success": true,
  "token": "eW91cl93ZWNoYXRfdXNlcl9pZA==",
  "wechat_user_id": "your_wechat_user_id",
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

### 2. 使用Token访问API

所有需要认证的接口都需要在请求头中包含Token：

```javascript
Authorization: Bearer eW91cl93ZWNoYXRfdXNlcl9pZA==
```

## 📊 数据查询接口

### 获取用户画像列表

```javascript
GET /api/profiles?page=1&page_size=20&search=张三
Authorization: Bearer {token}
```

**参数**:
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20，最大100）
- `search`: 搜索关键词（可选）

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

### 获取画像详情

```javascript
GET /api/profiles/1
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "profile": {
    "id": 1,
    "profile_name": "张三",
    "gender": "男",
    "age": "28",
    // ... 其他字段
    "raw_message_content": "用户发送的原始消息内容...",
    "raw_ai_response": {
      "summary": "AI分析总结",
      "user_profiles": [...]
    }
  }
}
```

### 搜索用户画像

```javascript
GET /api/search?q=张三&limit=20
Authorization: Bearer {token}
```

**参数**:
- `q`: 搜索关键词（必须）
- `limit`: 结果数量限制（默认20）

### 获取最近画像

```javascript
GET /api/recent?limit=10
Authorization: Bearer {token}
```

### 获取用户统计信息

```javascript
GET /api/stats
Authorization: Bearer {token}
```

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

### 获取用户信息

```javascript
GET /api/user/info
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "wechat_user_id": "your_wechat_user_id",
  "table_name": "profiles_your_wechat_user_id",
  "stats": {
    // ... 统计信息
  }
}
```

## 🗑️ 数据管理接口

### 删除用户画像

```javascript
DELETE /api/profiles/1
Authorization: Bearer {token}
```

**响应示例**:
```json
{
  "success": true,
  "message": "画像删除成功"
}
```

## 🔄 实时更新接口

### 检查数据更新

```javascript
GET /api/updates/check?last_check=2025-08-04T10:00:00
Authorization: Bearer {token}
```

**参数**:
- `last_check`: 上次检查时间（可选）

**响应示例**:
```json
{
  "success": true,
  "has_updates": true,
  "latest_profiles": [
    // ... 最新的3个画像
  ],
  "total_profiles": 47,
  "check_time": "2025-08-04T15:30:00"
}
```

## 🎯 前端集成示例

### React/Vue.js 集成示例

```javascript
class UserProfileAPI {
  constructor(baseURL = 'http://localhost:3001') {
    this.baseURL = baseURL;
    this.token = localStorage.getItem('auth_token');
  }

  // 设置认证头
  getHeaders() {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.token}`
    };
  }

  // 登录
  async login(wechatUserId) {
    const response = await fetch(`${this.baseURL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wechat_user_id: wechatUserId })
    });
    
    const data = await response.json();
    if (data.success) {
      this.token = data.token;
      localStorage.setItem('auth_token', this.token);
    }
    return data;
  }

  // 获取画像列表
  async getProfiles(page = 1, pageSize = 20, search = '') {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString()
    });
    
    if (search) params.append('search', search);

    const response = await fetch(
      `${this.baseURL}/api/profiles?${params}`,
      { headers: this.getHeaders() }
    );
    
    return await response.json();
  }

  // 获取画像详情
  async getProfileDetail(profileId) {
    const response = await fetch(
      `${this.baseURL}/api/profiles/${profileId}`,
      { headers: this.getHeaders() }
    );
    
    return await response.json();
  }

  // 删除画像
  async deleteProfile(profileId) {
    const response = await fetch(
      `${this.baseURL}/api/profiles/${profileId}`,
      { 
        method: 'DELETE',
        headers: this.getHeaders() 
      }
    );
    
    return await response.json();
  }

  // 检查更新
  async checkForUpdates() {
    const response = await fetch(
      `${this.baseURL}/api/updates/check`,
      { headers: this.getHeaders() }
    );
    
    return await response.json();
  }
}

// 使用示例
const api = new UserProfileAPI();

// 登录
await api.login('your_wechat_user_id');

// 获取画像列表
const profiles = await api.getProfiles(1, 20);

// 实时检查更新（轮询）
setInterval(async () => {
  const updates = await api.checkForUpdates();
  if (updates.has_updates) {
    // 刷新界面数据
    console.log('发现新数据，刷新界面');
  }
}, 30000); // 每30秒检查一次
```

## 🔒 安全注意事项

1. **Token安全**: 当前使用简单的Base64编码，生产环境建议使用JWT
2. **HTTPS**: 生产环境必须使用HTTPS
3. **CORS**: 当前允许所有域名访问，生产环境应限制特定域名
4. **请求频率**: 建议实施API请求频率限制

## ❌ 错误处理

API采用标准HTTP状态码：

- `200`: 请求成功
- `400`: 请求参数错误
- `401`: 认证失败
- `404`: 资源不存在
- `500`: 服务器内部错误

**错误响应格式**:
```json
{
  "detail": "错误描述信息"
}
```

## 🚀 部署说明

启动API服务器：

```bash
# 开发环境
python run.py

# 或使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 3001 --reload
```

API文档自动生成地址：
- Swagger UI: `http://localhost:3001/docs`
- ReDoc: `http://localhost:3001/redoc`