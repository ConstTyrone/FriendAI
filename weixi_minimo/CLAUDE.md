# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个"轻量、私密、AI-first"的社交关系维护微信小程序，帮助用户高效管理和维护重要的社交关系。

## 开发命令

### 开发工具
- **微信开发者工具**：主要开发和调试环境
- **编译**：在微信开发者工具中点击"编译"按钮或使用快捷键 Ctrl+B (Win) / Cmd+B (Mac)
- **真机调试**：使用"预览"或"真机调试"功能
- **模拟器测试**：开发者工具内置模拟器
- **npm包构建**：工具栏 → 工具 → 构建npm（首次使用TDesign组件时必须）

### 后端服务启动
```bash
cd D:\My project\qiwei
python run.py
```

### 开发环境配置
在微信开发者工具中：
1. **详情 → 本地设置**：
   - ✅ 不校验合法域名、web-view(业务域名)、TLS 版本以及 HTTPS 证书
   - ✅ 启用自定义处理命令
2. **详情 → 项目配置**：
   - ✅ ES6 转 ES5: 开启
   - ✅ 增强编译: 开启
   - ✅ 上传代码时样式自动补全: 开启

### 调试命令
- **清除缓存**：删除项目根目录下的 `.cache` 和 `.build` 文件夹（如果存在）
- **查看存储信息**：在settings页面点击"查看存储信息"
- **清除本地数据**：在settings页面点击"清除本地数据"

### 测试流程
1. 确保后端服务运行在 https://weixin.dataelem.com
2. 微信开发者工具编译小程序
3. 使用测试账户或微信登录进行功能测试
4. 开发环境自动使用 `dev_user_001` 测试账户

## 核心架构

### 应用入口与路由系统
- `app.js` - 全局路由守卫，自动拦截未登录用户访问受保护页面（contact-list、ai-search、contact-detail、contact-form）
- `app.json` - 定义5个页面，包括3个TabBar页面：设置、联系人、AI搜索
- 路由守卫通过重写 `wx.navigateTo`, `wx.switchTab`, `wx.redirectTo` 实现（app.js:177-258）
- 受保护页面在 `app.js:184-189` 中定义，未登录时自动跳转到设置页面进行登录

### 核心数据流架构
1. **认证层**：`utils/auth-manager.js` - 单例管理，支持微信code登录、测试账户登录和Mock模式登录
2. **数据层**：`utils/data-manager.js` - 联系人数据管理，包含缓存策略、事件系统和Mock数据支持
3. **API层**：`utils/api-client.js` - 统一HTTP客户端，自动重试和错误处理，支持Bearer token认证
4. **存储层**：`utils/storage-utils.js` - 带过期时间的缓存管理，支持前缀命名空间

### 状态管理模式
- **全局状态**：app.js 中的 globalData（isLoggedIn, userInfo, systemInfo, version）
- **组件状态**：Page级别的data状态
- **持久化**：wx.storage + 过期时间控制，使用StorageManager类管理命名空间
- **事件通信**：通过监听器模式在组件间通信

### 核心工具类
- `utils/constants.js` - API配置、存储键名、错误消息、UI配置的中心化管理
- `utils/format-utils.js` - 数据格式化（日期、电话、头像颜色生成、联系人显示名称）
- `utils/validator.js` - 输入验证和数据校验，包含Validator类支持链式验证
- `utils/url-utils.js` - URL和查询参数处理

## 技术栈

- **前端框架**：微信小程序原生开发
- **UI组件库**：TDesign Miniprogram（通过app.json全局注册组件）
- **后端API**：RESTful API (https://weixin.dataelem.com)
- **认证方式**：Token Based Authentication with JWT
- **数据存储**：wx.storage + 自动过期缓存系统

## 认证架构

### 三重登录模式设计
1. **微信原生登录（主要）**：通过 `wx.login()` 获取code → 后端换取openid → JWT Token
2. **测试账户登录（开发）**：直接使用预设用户ID绕过微信认证
3. **Mock模式登录（离线）**：网络不可用时使用本地模拟数据

### 认证状态管理
- **全局拦截**：app.js 重写微信路由API，自动检查页面访问权限
- **受保护页面**：contact-list、ai-search、contact-detail、contact-form
- **本地持久化**：token和用户信息保存在wx.storage，支持过期时间控制
- **API认证**：所有请求自动携带Authorization Bearer token
- **失效处理**：401状态码自动触发重新登录流程
- **自动恢复**：app启动时自动恢复登录状态和验证token有效性

### 环境自适应认证
- **开发环境**：检测 `systemInfo.platform === 'devtools'`，后端返回40029错误时自动使用 `dev_user_001`
- **生产环境**：使用真实微信code获取openid进行用户匹配
- **网络容错**：API失败时自动切换到Mock模式，使用本地模拟数据
- **降级策略**：微信登录 → 快速登录 → Mock登录

### 支持的测试账户
- `test_user_001`, `test_user_002`, `demo_user_001`（手动测试）
- `dev_user_001`（开发环境自动使用）
- `mock_user_dev`（Mock模式使用）

## 开发架构模式

### 单例管理器模式
- `authManager` - 认证状态单例，监听器事件系统（auth-manager.js:6-537）
- `dataManager` - 数据管理单例，内存+缓存双重存储（data-manager.js:5-740）
- `apiClient` - API客户端单例，自动重试和token管理（api-client.js:5-327）

### 智能缓存系统
```javascript
// StorageManager类提供命名空间和过期时间
const storage = new StorageManager('data');
storage.cache('contacts', data);  // 5分钟过期

// 自动过期检查
getStorageSync(key, defaultValue); // 过期自动返回defaultValue

// 过期时间配置
UI_CONFIG.CACHE_EXPIRE_TIME = 5 * 60 * 1000; // 5分钟
```

### API调用模式
```javascript
// 所有API调用通过dataManager，内置缓存和容错
const result = await dataManager.getContacts({
  page: 1, pageSize: 20, search: '关键词'
});

// AI搜索带匹配度计算
const searchResult = await dataManager.searchContacts('自然语言查询');
```

### 组件通信模式
- **Page级事件**：通过 dataset 传递数据
- **全局状态同步**：监听器模式自动更新UI
- **缓存策略**：本地优先 + API更新 + 自动过期

## 关键开发模式

### 错误处理策略
- **API层面**：3次指数退避重试，401自动触发重新登录（api-client.js:37-64）
- **网络容错**：API失败时自动使用本地模拟数据维持功能
- **存储容错**：所有storage操作都有try-catch和默认值

### 搜索架构
- **多维度匹配**：姓名(1.0) > 公司(0.7) > 职位(0.6) > 地区(0.5) > AI摘要(0.4)（ai-search.js:322-361）
- **防抖机制**：500ms延迟，避免频繁API调用
- **结果处理**：自动排序、标签格式化、匹配度计算

### 性能优化
- **分页加载**：UI_CONFIG.PAGE_SIZE = 20，支持下拉刷新和上拉加载更多
- **内存管理**：联系人使用Map映射提高查找效率（data-manager.js:9, 196-201）
- **缓存策略**：5分钟数据缓存，本地优先显示

## 重要约定

### 数据结构规范
- 联系人ID统一使用 `id` 或 `profile_id`
- 用户认证区分 `wechatUserId`（openid）和 `userId`（数据库ID）
- 所有时间戳使用毫秒级Unix时间戳

### API调用规范  
- 统一通过 `dataManager` 和 `authManager` 调用，不直接使用 `apiClient`
- 所有网络请求都有降级策略（缓存数据或模拟数据）
- 401错误自动触发登出和重新登录流程

### 文件结构约定
- **pages/**：微信小程序页面，每个页面包含 .js/.json/.wxml/.wxss 四个文件
- **components/**：自定义组件，包含contact-card、custom-tabbar、ai-chips等
- **utils/**：工具类模块，采用ES6模块化，单例模式管理状态
- **miniprogram_npm/**：TDesign组件库，通过"构建npm"生成
- **assets/**：静态资源文件

## 调试指南

### 常用调试方法
- **控制台日志**：所有关键操作都有详细console.log输出
- **网络调试**：微信开发者工具网络面板查看API请求
- **存储调试**：使用 `onViewStorageInfo()` 查看缓存使用情况（settings.js:687-711）
- **认证调试**：settings页面显示完整的登录状态信息

### 常见问题排查
- **编译错误**：检查文件完整性，运行"构建npm"，清除缓存重新编译
- **找不到页面**：检查app.json中pages路径配置，确保所有页面文件存在
- **登录失败**：检查后端服务状态，查看控制台错误信息
- **数据不显示**：检查token有效性，验证API响应格式，确认网络连接
- **搜索无结果**：确认后端搜索接口正常，检查查询参数格式
- **页面跳转失败**：检查路由守卫逻辑，确认登录状态
- **TDesign组件不显示**：运行"工具 → 构建npm"，检查miniprogram_npm文件夹

### 开发最佳实践
- 所有新功能先在 `settings` 页面添加测试入口
- 使用 `dataManager` 的监听器模式保持数据同步
- 遵循现有的错误处理和loading状态管理模式
- 新增工具函数统一放在对应的utils文件中
- 使用Mock模式进行离线开发和测试
- 所有API调用必须有降级策略（缓存或模拟数据）
- 新增页面需要在app.js的protectedPages数组中添加路由守卫

## 核心流程说明

### 登录流程
1. **真实微信登录**：`authManager.wechatLogin()` → wx.login() → 后端API `/api/login` → 保存token
2. **测试账户登录**：`authManager.quickLogin(userId)` → 直接调用后端API使用预设用户ID
3. **Mock模式登录**：`authManager.mockLogin()` → 完全本地模拟，不依赖后端服务
4. **自动登录检查**：`authManager.checkAutoLogin()` → 验证token有效性，自动恢复登录状态

### 数据获取流程
1. **联系人列表**：`dataManager.getContacts()` → 缓存优先 → API调用 → 降级到Mock数据
2. **联系人详情**：`dataManager.getContactDetail()` → Map缓存查找 → API获取完整数据
3. **AI搜索**：`dataManager.searchContacts()` → 后端AI搜索 → 本地匹配度计算 → 降级到本地搜索
4. **统计信息**：`dataManager.getStats()` → 缓存策略 → API更新

### 页面间通信
- 通过 `dataset` 传递联系人数据（contact-list.js:392, ai-search.js:461）
- 使用监听器模式同步状态更新（data-manager.js:700-722, auth-manager.js:456-479）
- 全局状态通过 `getApp().globalData` 共享

### Mock模式支持
- 当检测到网络错误或用户选择Mock登录时自动启用
- `dataManager.enableMockMode()` 启用Mock模式，使用预设的5个测试联系人
- Mock数据包含完整的联系人信息，支持搜索、详情查看等所有功能
- 用于离线开发和功能演示

## 常用开发任务

### 添加新页面
1. 在 `pages/` 目录创建新页面文件夹
2. 创建 .js/.json/.wxml/.wxss 四个文件
3. 在 `app.json` 的pages数组中注册页面路径
4. 如需要登录保护，在 `app.js:184-189` 的protectedPages数组中添加

### 修改API接口
1. 在 `utils/api-client.js` 中添加新的API方法
2. 在 `utils/data-manager.js` 中封装业务逻辑，添加缓存和容错处理
3. 更新 `utils/constants.js` 中的相关配置

### 添加新的工具函数
- 格式化相关：`utils/format-utils.js`
- 验证相关：`utils/validator.js`
- 存储相关：`utils/storage-utils.js`
- URL处理：`utils/url-utils.js`

### 测试功能
1. 在settings页面使用各种登录方式测试
2. 使用Mock模式进行离线功能测试
3. 检查控制台日志确认数据流正常
4. 使用"查看存储信息"监控缓存使用情况