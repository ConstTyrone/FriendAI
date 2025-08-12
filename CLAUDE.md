# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

FriendAI 是一个微信生态的社交关系管理系统，包含：
- **WeiXinKeFu**: 后端服务（Python FastAPI），提供用户画像分析和消息处理
- **weixi_minimo**: 微信小程序前端，用于联系人管理和AI搜索

## 常用开发命令

### 后端开发 (WeiXinKeFu)
```bash
# 启动开发服务器
python run.py

# 或使用 uvicorn 直接启动
uvicorn src.core.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
python tests/test_api.py

# 数据库查看（开发环境）
# 使用 SQLite 浏览器打开 data/app_data.db
```

### 前端开发 (weixi_minimo)
```bash
# 使用微信开发者工具打开 weixi_minimo 目录
# 配置服务器域名为后端地址（开发环境通常为 http://localhost:8000）

# 构建npm依赖（如果使用了npm包）
npm install
npm run build
```

## 架构关键点

### 后端架构
- **分层设计**: `core` (API层) → `services` (业务层) → `handlers` (处理层) → `database` (数据层)
- **数据隔离**: 每个微信用户使用独立的数据表（表名格式: `user_{openid}`）
- **消息处理流**: 微信回调 → 消息解密 → 内容提取 → AI分析 → 画像存储
- **双数据库支持**: 通过 `DB_TYPE` 环境变量切换 SQLite/PostgreSQL

### 前端架构
- **数据管理**: `utils/data-manager.js` 统一管理所有数据操作和缓存
- **认证流程**: `utils/auth-manager.js` 处理微信登录和Token管理
- **API客户端**: `utils/api-client.js` 封装所有后端接口调用
- **路由守卫**: 自动处理未登录重定向到登录页

### AI服务集成
- **通义千问API**: `services/ai_service.py` 处理用户画像分析
- **语音识别**: 支持微信语音消息转文字
- **图像OCR**: 提取图片中的文字信息
- **文档解析**: 解析PDF、Word等文档内容

## 关键配置文件

### 后端配置
- `.env`: 环境变量配置（企微密钥、AI API Key等）
- `config/config.py`: 应用配置管理
- `requirements.txt`: Python依赖包

### 前端配置
- `app.json`: 小程序全局配置
- `project.config.json`: 项目配置
- `utils/constants.js`: 应用常量定义

## API接口规范

### 认证
所有API请求需在Header中携带:
```
Authorization: Bearer {base64_encoded_token}
```

### 主要接口
- `POST /api/login`: 微信登录
- `GET /api/contacts`: 获取联系人列表
- `POST /api/contacts`: 创建联系人
- `PUT /api/contacts/{id}`: 更新联系人
- `DELETE /api/contacts/{id}`: 删除联系人
- `POST /api/search`: AI语义搜索
- `POST /wechat_callback`: 微信消息回调（企微/客服）

## 数据库结构

### 用户画像表 (user_{openid})
```sql
- id: 主键
- name: 姓名
- wechat_id: 微信号
- phone: 电话
- tags: 标签（JSON）
- basic_info: 基本信息（JSON）
- recent_activities: 近期动态（JSON）
- raw_messages: 原始消息（JSON）
- created_at/updated_at: 时间戳
```

### 绑定信息表 (binding_info)
```sql
- user_wx_id: 微信用户ID
- external_userid: 企微外部联系人ID
- wx_name: 微信昵称
- external_name: 企微联系人名称
```

## 增量更新机制（新功能）

系统已实现智能的增量更新机制，解决了"如何确认是同一个人"的核心问题：

### 核心特性
- **智能身份识别**：通过external_userid、电话、微信号等多维度匹配，置信度评分
- **增量信息累积**：新消息补充更新，不覆盖已有信息，保留完整历史
- **冲突智能处理**：自动检测信息冲突，AI辅助解决，低置信度人工确认

### 启用方式
```python
from src.config.enable_incremental import enable_incremental_update
enable_incremental_update()  # 启用增量更新

# 使用增强的消息处理器
from src.handlers.message_handler_enhanced import process_message_with_incremental_update
```

### 新增文件
- `src/database/database_enhanced.py` - 增强数据库，支持身份管理
- `src/services/ai_service_enhanced.py` - 增强AI服务，支持增量分析
- `src/handlers/message_handler_enhanced.py` - 增强消息处理器
- `tests/test_incremental_update.py` - 测试脚本
- `docs/INCREMENTAL_UPDATE_GUIDE.md` - 详细使用指南

## 注意事项

1. **Token简化**: 当前使用Base64编码的简单Token，生产环境需要升级为JWT
2. **错误处理**: 前端已实现全局错误处理和用户提示
3. **缓存策略**: 前端使用本地存储缓存联系人数据，需注意及时更新
4. **消息解密**: 企微消息需要正确配置Token、EncodingAESKey和CorpID
5. **AI调用限流**: 注意通义千问API的调用频率限制
6. **增量更新**: 新功能默认启用，可通过配置切换回原模式

## 开发提示

- 修改后端API时，同步更新前端 `api-client.js` 中的接口定义
- 新增数据字段时，检查前后端的数据模型是否一致
- 处理微信回调时，确保返回正确的响应格式避免重试
- 小程序发布前，确保已配置正确的服务器域名白名单