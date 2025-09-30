# 微信客服用户画像系统（简化版）

> 专注于微信客服消息处理和AI用户画像分析的独立系统

## 📋 项目简介

这是一个精简的微信客服消息处理系统，专注于核心功能：
- ✅ 微信客服消息接收和处理
- ✅ 多种消息类型支持（文本、语音、图片、文档、聊天记录）
- ✅ AI驱动的用户画像自动提取
- ✅ 简化的SQLite数据存储

**与原系统的区别：**
- ❌ 移除了小程序相关功能
- ❌ 移除了用户绑定机制
- ❌ 移除了意图匹配功能
- ❌ 移除了前端数据查询API
- ✅ 直接使用 external_userid 作为用户标识
- ✅ 简化的数据库结构（单表存储）

## 🚀 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

必需配置项：
- `WEWORK_CORP_ID` - 企业ID或微信客服企业ID
- `WEWORK_SECRET` - 应用密钥或客服Secret
- `WEWORK_TOKEN` - 回调Token
- `WEWORK_AES_KEY` - 加密AES Key
- `QWEN_API_KEY` - 通义千问API密钥

### 3. 启动服务

```bash
python run.py
```

服务将在 `http://0.0.0.0:3001` 启动。

### 4. 配置微信回调

在微信客服/企业微信后台配置回调URL：
```
http://your-server-domain:3001/wework/callback
```

## 📚 核心功能

### 消息处理流程

```
用户发送消息
    ↓
微信客服服务器
    ↓
POST /wework/callback（加密XML）
    ↓
签名验证 + AES解密
    ↓
识别事件类型：kf_msg_or_event
    ↓
调用sync_msg API拉取消息
    ↓
消息分类（text/voice/image/file/chat_record）
    ↓
文本提取
    ↓
调用通义千问AI分析
    ↓
提取用户画像（11个字段）
    ↓
存储到SQLite数据库
    ↓
发送分析结果给用户
```

### 支持的消息类型

| 消息类型 | 处理方式 | 说明 |
|---------|---------|------|
| 文本 | 直接分析 | 提取文本中的用户信息 |
| 语音 | ASR转文字 | 需配置阿里云ASR服务 |
| 图片 | OCR识别 | 使用ETL4LM进行OCR |
| 文档 | 内容解析 | 支持PDF、Word、Excel、TXT |
| 聊天记录 | 智能分析 | 排除转发者，分析对话者 |
| 位置 | 提取地理信息 | 位置名称和坐标 |
| 链接 | 提取链接信息 | 标题、描述、URL |

### 用户画像字段

系统提取以下11个标准字段：

1. **姓名**（主键，必填）
2. **性别**（男/女/未知）
3. **年龄**（具体年龄或年龄段）
4. **电话**（手机号或联系方式）
5. **所在地**（常驻地）
6. **婚育**（已婚已育/已婚未育/未婚/离异/未知）
7. **学历**（最高学历及院校）
8. **公司**（当前就职公司及行业）
9. **职位**（当前职位）
10. **资产水平**（高/中/低/未知）
11. **性格**（性格特征描述）

## 📂 项目结构

```
wechat-customer-service/
├── src/
│   ├── core/
│   │   └── main.py                    # FastAPI应用（只有微信回调）
│   ├── services/
│   │   ├── wework_client.py           # 微信客服客户端
│   │   ├── ai_service.py              # AI分析服务
│   │   └── media_processor.py         # 多媒体处理
│   ├── handlers/
│   │   ├── message_handler.py         # 消息处理器
│   │   ├── message_classifier.py      # 消息分类器
│   │   └── message_formatter.py       # 文本提取器
│   ├── database/
│   │   └── database_simple.py         # 简化数据库
│   └── config/
│       └── config.py                  # 配置管理
├── requirements.txt                    # Python依赖
├── run.py                             # 启动脚本
├── .env.example                       # 环境变量模板
└── README.md                          # 项目说明
```

## 🗄️ 数据库结构

SQLite单表设计：

```sql
CREATE TABLE profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_userid TEXT NOT NULL,      -- 微信客服用户ID
    name TEXT,                           -- 姓名
    gender TEXT,                         -- 性别
    age TEXT,                            -- 年龄
    phone TEXT,                          -- 电话
    location TEXT,                       -- 所在地
    marital_status TEXT,                 -- 婚育状况
    education TEXT,                      -- 学历
    company TEXT,                        -- 公司
    position TEXT,                       -- 职位
    asset_level TEXT,                    -- 资产水平
    personality TEXT,                    -- 性格
    raw_message TEXT,                    -- 原始消息
    message_type TEXT,                   -- 消息类型
    ai_response TEXT,                    -- AI完整响应
    created_at TIMESTAMP,                -- 创建时间
    updated_at TIMESTAMP                 -- 更新时间
);
```

## 🔧 可选功能配置

### 语音识别（ASR）

如需支持语音消息识别，有两种方式配置：

**方式一：自动Token管理（推荐）**

1. 安装依赖：
```bash
pip install alibabacloud-nls-python-sdk
pip install aliyun-python-sdk-core
```

2. 配置阿里云AccessKey：
```
ALIYUN_AK_ID=your_access_key_id
ALIYUN_AK_SECRET=your_access_key_secret
ASR_APPKEY=NM5zdrGkIl8xqSzO
```

系统会自动获取和刷新ASR Token，无需手动维护。

**方式二：手动Token配置（兼容模式）**

1. 安装SDK：
```bash
pip install alibabacloud-nls-python-sdk
```

2. 手动配置Token：
```
ASR_APPKEY=NM5zdrGkIl8xqSzO
ASR_TOKEN=your_manually_generated_token
```

注意：手动Token有效期为24小时，需定期更新。

### 音频转换（FFmpeg）

语音识别需要FFmpeg支持：

1. 下载安装：https://ffmpeg.org/download.html
2. 添加到系统PATH
3. 配置路径（可选）：`FFMPEG_PATH=ffmpeg`

## 📡 API端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 服务信息 |
| GET | `/wework/callback` | 微信URL验证 |
| POST | `/wework/callback` | 微信消息回调 |
| GET | `/wechat/callback` | 兼容路由 |
| POST | `/wechat/callback` | 兼容路由 |

## 🔐 安全性

- ✅ SHA1签名验证
- ✅ AES-256-CBC消息加密
- ✅ 事件防重复处理
- ✅ 消息游标管理

## 📝 日志

系统会输出详细的处理日志：
- 消息接收和验证
- 消息分类和处理
- AI分析过程
- 数据库操作
- 错误信息

## ⚠️ 注意事项

1. **环境变量**：确保所有必需的环境变量已正确配置
2. **网络访问**：服务器需要能够访问微信API和通义千问API
3. **端口开放**：确保配置的端口对外开放
4. **HTTPS**：生产环境建议使用HTTPS

## 🆘 常见问题

**Q: 如何查看数据库内容？**
A: 使用SQLite客户端工具，或运行：
```bash
sqlite3 wechat_profiles.db
.tables
SELECT * FROM profiles LIMIT 10;
```

**Q: 语音识别不工作？**
A: 检查：
1. 是否安装了ASR SDK（alibabacloud-nls-python-sdk）
2. 是否配置了ALIYUN_AK_ID和ALIYUN_AK_SECRET（推荐）或ASR_TOKEN（手动模式）
3. FFmpeg是否正确安装
4. 查看日志中的Token获取状态

**Q: 消息没有被处理？**
A: 检查：
1. 回调URL是否正确配置
2. 签名验证是否通过
3. 查看服务日志排查错误

## 📄 许可证

本项目仅供学习和研究使用。

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

**系统版本**: 1.0.0（简化版）
**最后更新**: 2025-09-30