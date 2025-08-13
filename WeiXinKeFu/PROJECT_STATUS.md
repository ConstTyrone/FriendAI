# 企业微信/微信客服集成项目状态

## 项目概述

基于FastAPI的企业微信和微信客服webhook服务，支持消息接收、分类、处理和AI分析。

## 当前功能状态

### ✅ 已完成功能

1. **基础架构**
   - FastAPI webhook服务 (`main.py`)
   - 企业微信/微信客服API客户端 (`wework_client.py`)
   - 配置管理 (`config/config.py`)

2. **消息处理**
   - 消息分类器 (`message_classifier.py`)
   - 消息格式化 (`message_formatter.py`) 
   - 消息处理器 (`message_handler.py`)
   - 消息同步优化 (`message_sync_optimizer.py`)

3. **多媒体处理**
   - ETL4LM集成（图片OCR、PDF解析）
   - 阿里云ASR语音识别
   - ffmpeg音频格式转换（AMR→PCM）

4. **AI服务**
   - 通义千问API集成 (`ai_service.py`)
   - JSON解析增强和自动修复
   - 用户画像分析和身份提取

### 🔧 技术实现

1. **语音识别流程**
   - 微信AMR语音文件下载
   - ffmpeg转换为PCM格式
   - 阿里云NLS SDK识别
   - 异步回调处理

2. **消息分类**
   - 支持文本、图片、语音、视频、文件、位置、链接、小程序等
   - 企业微信和微信客服双平台兼容

3. **AI分析**
   - 温度参数优化（0.3）
   - JSON括号匹配和自动修复
   - 系统角色约束确保输出格式

## 配置要求

### 环境变量
```bash
# 企业微信/微信客服配置
WEWORK_CORP_ID=企业ID
WEWORK_AGENT_ID=应用ID（微信客服可空）
WEWORK_SECRET=应用密钥
WEWORK_TOKEN=Token
WEWORK_AES_KEY=AES密钥
LOCAL_SERVER_PORT=3001

# AI服务配置
QWEN_API_KEY=通义千问API密钥
QWEN_API_ENDPOINT=https://dashscope.aliyuncs.com/compatible-mode/v1

# 语音识别配置
ASR_APPKEY=NM5zdrGkIl8xqSzO
ASR_TOKEN=9dadd6de5f8b458a852f45a2538bd602
ASR_URL=wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1

# ffmpeg路径
FFMPEG_PATH=ffmpeg可执行文件路径
```

### 依赖安装
```bash
pip install -r requirements.txt
pip install alibabacloud-nls-python-sdk
```

## 项目结构

```
qiwei/
├── main.py                 # FastAPI应用入口
├── wework_client.py        # 企业微信/微信客服客户端
├── ai_service.py           # AI服务（通义千问）
├── media_processor.py      # 多媒体处理（ETL+ASR）
├── message_classifier.py   # 消息分类
├── message_formatter.py    # 消息格式化
├── message_handler.py      # 消息处理
├── message_sync_optimizer.py  # 消息同步优化
├── run.py                  # 启动脚本
├── config/
│   └── config.py          # 配置管理
├── reference/             # 参考文档
├── weixin_doc/           # 微信客服官方文档
└── temp_media/           # 临时媒体文件
```

## 运行方式

```bash
# 方式1：直接运行
uvicorn main:app --host 0.0.0.0 --port 3001 --reload

# 方式2：使用启动脚本
python run.py
```

## 支持的消息类型

- **文本消息**：AI分析和用户画像提取
- **图片消息**：OCR文字识别
- **PDF文档**：内容解析和分析
- **语音消息**：转文字后AI分析
- **其他类型**：基础信息记录

## 最近更新

### 2025-08-01
- ✅ 修复了ASR异步启动逻辑问题
- ✅ 完善了ffmpeg路径配置和AMR转PCM转换
- ✅ 增强了AI JSON解析的稳定性
- ✅ 清理了项目结构，删除临时文件

## 下次开发计划

1. 测试完整语音识别功能
2. 优化消息处理性能
3. 添加更多消息类型支持
4. 完善错误处理和日志记录

---

**状态：** 开发完成，等待生产环境测试  
**最后更新：** 2025-08-01 20:30