# CLAUDE.md

这是微信客服用户画像系统的代码库指南，用于帮助Claude Code理解项目结构和开发流程。

## 项目概述

这是一个基于FastAPI的微信客服消息处理系统，专注于接收微信客服消息、使用AI提取用户画像并存储到SQLite数据库。系统已从原有复杂版本简化，移除了小程序、用户绑定、意图匹配等功能，直接使用`external_userid`作为用户标识。

## 核心架构

### 消息处理流程

系统采用事件驱动架构处理微信客服消息：

```
微信服务器 → /wework/callback (POST)
  → 签名验证 + AES解密
  → 识别事件类型 (kf_msg_or_event)
  → sync_msg API拉取消息
  → 消息分类 (classifier)
  → 文本提取 (text_extractor)
  → AI分析 (profile_extractor)
  → 数据库存储 (db.save_user_profile)
  → 发送分析结果给用户
```

### 关键组件职责

- **src/core/main.py**: FastAPI应用入口，处理微信回调验证和消息接收
- **src/services/wework_client.py**: 微信客服API客户端，负责access_token管理、消息解密、sync_msg调用、消息发送
- **src/handlers/message_handler.py**: 消息处理协调器，统一的消息处理流程入口
- **src/handlers/message_classifier.py**: 消息类型分类器（text/voice/image/file/chat_record/location）
- **src/handlers/message_formatter.py**: 多媒体消息转纯文本提取器
- **src/services/ai_service.py**: 通义千问AI集成，提取11字段用户画像
- **src/database/database_simple.py**: SQLite单表数据存储，使用external_userid索引

### 重要的技术约定

1. **消息游标管理**: `WeWorkClient._kf_cursors`按客服账号ID存储游标，支持增量拉取
2. **事件去重**: `handle_wechat_kf_event._processed_events`内存集合防止重复处理（生产建议用Redis）
3. **最新消息优先**: `sync_kf_messages(get_latest_only=True)`拉取所有消息后返回最新一条
4. **直接用户标识**: 系统直接使用`external_userid`，不需要验证码绑定流程
5. **消息转换**: `_convert_kf_message`将微信客服消息格式转换为内部统一格式，支持merged_msg聊天记录

## 常用命令

### 开发环境设置

```bash
# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（复制.env.example为.env并填写）
cp .env.example .env
```

### 启动服务

```bash
# 启动开发服务器（带热重载）
python run.py

# 或直接使用uvicorn
uvicorn src.core.main:app --host 0.0.0.0 --port 3001 --reload
```

服务默认运行在 `http://0.0.0.0:3001`，API文档可访问 `http://0.0.0.0:3001/docs`

### 数据库操作

```bash
# 查看数据库内容
sqlite3 wechat_profiles.db

# SQLite常用命令
.tables                              # 查看所有表
.schema profiles                     # 查看表结构
SELECT * FROM profiles LIMIT 10;     # 查看前10条记录
SELECT COUNT(*) FROM profiles;       # 统计总记录数
.quit                                # 退出
```

### 测试和调试

```bash
# 查看实时日志
python run.py  # 日志会输出到stdout

# 测试微信回调URL验证（需要实际微信服务器触发）
# GET /wework/callback?msg_signature=xxx&timestamp=xxx&nonce=xxx&echostr=xxx
```

## 环境变量配置

### 必需配置

```bash
WEWORK_CORP_ID=your_corp_id          # 企业ID或微信客服企业ID
WEWORK_SECRET=your_secret            # 应用密钥或客服Secret
WEWORK_TOKEN=your_token              # 回调Token（用于签名验证）
WEWORK_AES_KEY=your_aes_key          # 加密AES Key（43位Base64）
QWEN_API_KEY=your_qwen_key           # 通义千问API密钥
```

### 可选配置

```bash
DATABASE_PATH=wechat_profiles.db     # SQLite数据库路径
LOCAL_SERVER_PORT=3001               # 服务端口

# 语音识别（需要语音消息支持时配置）
ASR_APPKEY=NM5zdrGkIl8xqSzO          # 预配置AppKey
ALIYUN_AK_ID=your_ak_id              # 阿里云AccessKey ID（自动Token）
ALIYUN_AK_SECRET=your_ak_secret      # 阿里云AccessKey Secret
FFMPEG_PATH=ffmpeg                   # FFmpeg路径

# ETL4LM OCR服务（预配置，通常无需修改）
ETL_BASE_URL=http://110.16.193.170:50103
```

## 代码修改指南

### 添加新的消息类型处理

1. 在`message_classifier.py`的`classify_message()`中添加新类型识别逻辑
2. 在`message_formatter.py`的`extract_text()`中添加新类型的文本提取方法
3. 如需调用外部API，在`services/`目录下创建新的服务模块

### 修改用户画像字段

1. 更新`ai_service.py`中的prompt，指定新的字段要求
2. 修改`database_simple.py`中的表结构，添加新字段到`CREATE TABLE`语句
3. 更新`save_user_profile()`和相关查询方法以包含新字段
4. 更新`message_handler.py`中的字段映射字典（key_mapping）

### 扩展微信API功能

所有微信客服API调用应集中在`wework_client.py`中：
- 新增API方法应使用`get_access_token()`统一管理token
- 使用标准的错误处理模式：检查`errcode != 0`
- 添加详细的日志记录便于调试

### 数据库查询优化

`database_simple.py`已创建索引：
- `idx_external_userid`: 按用户查询
- `idx_name`: 按姓名查询
- `idx_created_at`: 按时间排序

添加新查询时考虑这些索引的使用。

## 常见问题排查

### 签名验证失败

检查`wework_client.py:verify_signature()`的日志输出，确认：
- WEWORK_TOKEN配置正确
- 参数排序逻辑正确（微信客服URL验证不包含echostr）
- 对于消息回调，需要包含encrypt_msg参数

### 消息未被处理

1. 检查`handle_wechat_kf_event()`的去重逻辑，event_id是否被误判为重复
2. 确认`sync_kf_messages()`成功拉取到消息（查看日志中的消息数量）
3. 检查`_convert_kf_message()`是否成功转换消息格式
4. 查看AI分析是否成功（profile_extractor日志）

### 语音识别不工作

1. 确认安装了`alibabacloud-nls-python-sdk`
2. 优先配置`ALIYUN_AK_ID`和`ALIYUN_AK_SECRET`以自动管理Token
3. 确认FFmpeg已安装并在PATH中可用
4. 查看`media_processor.py`中的Token获取和转换日志

### 数据库保存失败

检查`database_simple.py`的异常日志：
- 确认数据库文件路径可写
- 检查profile_data是否包含所有必需字段
- 确认ai_response可以正确序列化为JSON

## 部署注意事项

1. **生产环境建议使用HTTPS**：微信服务器建议使用安全连接
2. **事件去重机制**：当前使用内存集合，生产环境应改用Redis或数据库
3. **Token管理**：access_token有7200秒有效期，已实现自动刷新机制
4. **消息游标持久化**：当前游标存储在内存，重启会丢失，考虑持久化到Redis
5. **日志级别**：生产环境可调整为WARNING或ERROR减少日志量
6. **数据库备份**：定期备份SQLite数据库文件

## 项目依赖说明

- **fastapi + uvicorn**: Web框架和ASGI服务器
- **pycryptodome**: AES消息解密
- **requests**: HTTP客户端，调用微信和AI API
- **python-dotenv**: 环境变量管理
- **alibabacloud-nls-python-sdk**: 阿里云语音识别（可选）
- **aliyun-python-sdk-core**: 阿里云SDK核心库（自动Token管理）

所有依赖版本固定在`requirements.txt`中，确保环境一致性。