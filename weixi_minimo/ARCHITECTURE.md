# 社交关系维护小程序 - 架构设计文档

## 📋 项目概述

基于微信小程序开发的"轻量、私密、AI-first"社交关系维护工具，通过「联系人列表 + AI 语义搜索」双界面，让用户随时记录、快速召回、深度连接社交资产。

## 🏗️ 整体架构

### 技术栈
- **前端框架**: 微信小程序原生开发
- **UI组件库**: TDesign 小程序组件库
- **后端API**: RESTful API (http://localhost:3001)
- **认证方式**: 微信用户ID + Token
- **数据存储**: 本地缓存 + 远程数据库

### 架构图
```
┌─────────────────────────────────────────────────────────────┐
│                    微信小程序层                              │
├─────────────────────────────────────────────────────────────┤
│  Pages          │  Components      │  Utils               │
│  ├─ home        │  ├─ contact-card │  ├─ api-client       │
│  ├─ contact-list│  ├─ search-bar   │  ├─ auth-manager     │
│  ├─ ai-search   │  ├─ contact-form │  ├─ data-manager     │
│  ├─ contact-detail ├─ ai-chips    │  ├─ storage-utils    │
│  └─ settings    │  └─ loading      │  └─ format-utils     │
├─────────────────────────────────────────────────────────────┤
│                    服务层                                   │
├─────────────────────────────────────────────────────────────┤
│  API Service    │  Cache Service   │  Auth Service        │
│  ├─ 用户画像API │  ├─ 本地缓存     │  ├─ 微信登录         │
│  ├─ 搜索API     │  ├─ 图片缓存     │  ├─ Token管理        │
│  ├─ 统计API     │  └─ 搜索历史     │  └─ 权限控制         │
│  └─ 实时更新API │                  │                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    后端API服务                              │
│  RESTful API + 用户画像数据库 + AI分析服务                 │
└─────────────────────────────────────────────────────────────┘
```

## 📱 页面结构设计

### 页面路由
```
pages/
├── home/                    # 首页（可选）
│   ├── home.js
│   ├── home.json
│   ├── home.wxml
│   └── home.wxss
├── contact-list/            # 联系人列表页
│   ├── contact-list.js
│   ├── contact-list.json
│   ├── contact-list.wxml
│   └── contact-list.wxss
├── ai-search/               # AI语义搜索页
│   ├── ai-search.js
│   ├── ai-search.json
│   ├── ai-search.wxml
│   └── ai-search.wxss
├── contact-detail/          # 联系人详情页
│   ├── contact-detail.js
│   ├── contact-detail.json
│   ├── contact-detail.wxml
│   └── contact-detail.wxss
├── contact-form/            # 添加/编辑联系人页
│   ├── contact-form.js
│   ├── contact-form.json
│   ├── contact-form.wxml
│   └── contact-form.wxss
└── settings/                # 设置页
    ├── settings.js
    ├── settings.json
    ├── settings.wxml
    └── settings.wxss
```

### TabBar配置
```json
{
  "tabBar": {
    "color": "#999999",
    "selectedColor": "#5a67d8",
    "backgroundColor": "#ffffff",
    "borderStyle": "black",
    "list": [
      {
        "pagePath": "pages/contact-list/contact-list",
        "text": "联系人",
        "iconPath": "assets/icons/contact.png",
        "selectedIconPath": "assets/icons/contact-active.png"
      },
      {
        "pagePath": "pages/ai-search/ai-search",
        "text": "AI搜索",
        "iconPath": "assets/icons/search.png",
        "selectedIconPath": "assets/icons/search-active.png"
      }
    ]
  }
}
```

## 🧩 组件架构

### 公共组件
```
components/
├── contact-card/            # 联系人卡片组件
│   ├── index.js
│   ├── index.json
│   ├── index.wxml
│   └── index.wxss
├── search-bar/              # 搜索栏组件
│   ├── index.js
│   ├── index.json
│   ├── index.wxml
│   └── index.wxss
├── contact-form/            # 联系人表单组件
│   ├── index.js
│   ├── index.json
│   ├── index.wxml
│   └── index.wxss
├── ai-chips/                # AI建议词组件
│   ├── index.js
│   ├── index.json
│   ├── index.wxml
│   └── index.wxss
├── loading/                 # 加载动画组件
│   ├── index.js
│   ├── index.json
│   ├── index.wxml
│   └── index.wxss
└── empty-state/             # 空状态组件
    ├── index.js
    ├── index.json
    ├── index.wxml
    └── index.wxss
```

### 组件设计原则
- **单一职责**: 每个组件专注一个功能
- **可复用性**: 通过props和events实现灵活配置
- **性能优化**: 合理使用生命周期和数据更新
- **UI一致性**: 遵循TDesign设计规范

## 🔧 工具类设计

### 核心工具类
```
utils/
├── api-client.js            # API客户端封装
├── auth-manager.js          # 认证管理
├── data-manager.js          # 数据管理
├── storage-utils.js         # 本地存储工具
├── format-utils.js          # 数据格式化工具
├── constants.js             # 常量定义
└── validator.js             # 数据验证工具
```

### API客户端设计
```javascript
class APIClient {
  constructor() {
    this.baseURL = 'http://localhost:3001';
    this.token = null;
  }
  
  // 通用请求方法
  async request(endpoint, options = {}) {
    // 请求拦截、错误处理、重试逻辑
  }
  
  // 用户认证
  async login(wechatUserId) {}
  
  // 画像管理
  async getProfiles(params) {}
  async getProfileDetail(id) {}
  async deleteProfile(id) {}
  
  // 搜索功能
  async searchProfiles(query) {}
  async getSearchSuggestions() {}
  
  // 统计信息
  async getStats() {}
}
```

## 📊 状态管理设计

### 全局状态
```javascript
const globalData = {
  // 用户信息
  userInfo: {
    wechatUserId: '',
    token: '',
    stats: {}
  },
  
  // 联系人数据
  contacts: {
    list: [],
    total: 0,
    currentPage: 1,
    loading: false
  },
  
  // 搜索状态
  search: {
    query: '',
    results: [],
    suggestions: [],
    history: []
  },
  
  // 应用设置
  settings: {
    theme: 'light',
    autoSync: true,
    notifications: true
  }
};
```

### 数据流设计
```
用户操作 → 页面事件 → API调用 → 数据更新 → 界面刷新
    ↓
本地缓存 ← 数据预处理 ← API响应 ← 后端处理
```

## 🔐 认证与安全

### 认证流程
1. 微信小程序登录获取用户信息
2. 使用微信用户ID调用后端登录接口
3. 获取JWT Token并存储到本地
4. 后续请求携带Token进行认证

### 安全措施
- **数据加密**: 敏感数据本地加密存储
- **Token管理**: 自动刷新和失效处理
- **权限控制**: 基于用户角色的数据访问
- **输入验证**: 客户端和服务端双重验证
- **HTTPS通信**: 所有API请求使用HTTPS

## 🚀 性能优化策略

### 数据优化
- **分页加载**: 联系人列表分页显示
- **懒加载**: 图片和详细信息按需加载
- **本地缓存**: 常用数据本地缓存
- **预加载**: 预测用户行为进行数据预加载

### 渲染优化
- **虚拟列表**: 大量数据使用虚拟滚动
- **图片优化**: 图片压缩和CDN加速
- **代码分割**: 按页面拆分代码包
- **资源压缩**: 静态资源压缩和合并

### 用户体验优化
- **骨架屏**: 数据加载时显示骨架屏
- **缓存优先**: 优先显示缓存数据
- **离线支持**: 基础功能离线可用
- **错误恢复**: 友好的错误提示和恢复

## 📱 响应式设计

### 屏幕适配
- 使用rpx单位进行屏幕适配
- 支持不同尺寸设备的布局调整
- 考虑横屏和竖屏切换

### 交互优化
- 触摸操作的反馈效果
- 合理的点击区域大小
- 手势操作支持（滑动删除等）

## 🔄 数据同步

### 实时更新机制
- **轮询检查**: 定期检查数据更新
- **本地优先**: 本地操作立即响应
- **冲突解决**: 数据冲突的解决策略
- **离线队列**: 离线操作的队列管理

## 🧪 测试策略

### 测试类型
- **单元测试**: 工具函数和组件测试
- **集成测试**: API集成和数据流测试
- **端到端测试**: 完整用户流程测试
- **性能测试**: 页面加载和响应时间测试

### 测试工具
- 微信开发者工具内置测试
- 自定义测试脚本
- 真机测试验证

## 📋 开发计划

### 开发阶段
1. **Phase 1**: 基础架构和核心页面
2. **Phase 2**: API集成和数据管理
3. **Phase 3**: AI搜索和高级功能
4. **Phase 4**: 性能优化和用户体验
5. **Phase 5**: 测试和发布准备

### 里程碑
- [ ] 完成基础架构搭建
- [ ] 实现联系人列表功能
- [ ] 实现AI搜索功能
- [ ] 完成用户认证系统
- [ ] 性能优化和测试
- [ ] 发布第一个版本