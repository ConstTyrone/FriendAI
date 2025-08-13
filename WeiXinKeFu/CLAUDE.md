# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

请注意在实现任何有关微信客服时，查看weixin_doc文件夹中的文档

## Project Overview

This is a FastAPI-based intelligent user profile extraction system that integrates with WeWork (企业微信) and WeChat Customer Service (微信客服) platforms. The system handles message callbacks from both platforms, processes various message types through AI analysis, and extracts detailed user profiles with multi-user data isolation. The application features a complete REST API for frontend integration and advanced multimedia processing capabilities.

## Architecture

The application follows a modern, layered architecture with clear separation of concerns:

**Core Processing Flow**: 用户消息 → 解密 → 分类 → 转换为纯文本 → AI提取用户画像 → 存储画像数据 → API展示

### Project Structure (Updated 2025-08-04)

```
qiwei/
├── src/                              # 源代码目录
│   ├── core/                         # 核心层
│   │   └── main.py                   # FastAPI应用主文件，包含所有API端点
│   ├── services/                     # 服务层
│   │   ├── ai_service.py             # AI分析服务（通义千问API）
│   │   ├── media_processor.py        # 多媒体处理服务（ETL4LM、ASR）
│   │   └── wework_client.py          # 微信API客户端
│   ├── handlers/                     # 消息处理层
│   │   ├── message_handler.py        # 统一消息处理器
│   │   ├── message_classifier.py     # 消息分类器
│   │   ├── message_formatter.py      # 文本提取器
│   │   └── message_sync_optimizer.py # 消息同步优化器
│   ├── database/                     # 数据库层
│   │   ├── database_pg.py            # PostgreSQL数据库管理
│   │   ├── database_sqlite_v2.py     # SQLite多用户独立存储（推荐）
│   │   └── database_sqlite.py        # SQLite简化版本（兼容）
│   └── config/                       # 配置层
│       └── config.py                 # 环境变量配置管理
├── scripts/                          # 工具脚本
│   ├── db_viewer_pg.py              # PostgreSQL数据库管理工具
│   └── db_viewer_sqlite.py          # SQLite数据库管理工具
├── docs/                            # 文档系统
│   ├── api/                         # API文档
│   │   ├── API_DOCUMENTATION.md     # API基础文档
│   │   ├── FRONTEND_API_GUIDE.md    # 前端开发者指南
│   │   └── API_EXAMPLES.md          # 完整代码示例集合
│   └── setup/                       # 安装配置文档
│       └── DATABASE_SETUP.md        # 数据库配置说明
├── frontend-test/                   # 前端测试页面
│   ├── index.html                   # 主测试页面
│   ├── api-client.js                # API客户端封装
│   ├── app.js                       # 主应用逻辑
│   └── README.md                    # 前端使用说明
├── tests/                           # 测试文件
│   └── test_api.py                  # API自动化测试脚本
├── weixin_doc/                      # 微信官方文档
├── reference/                       # 技术参考文档
├── run.py                           # 应用启动脚本（模块化）
├── requirements.txt                 # Python依赖
├── README.md                        # 项目说明文档
├── PROJECT_STRUCTURE.md             # 详细结构说明
└── user_profiles.db                 # SQLite数据库文件（自动生成）
```

### Core Components

1. **FastAPI Application (src/core/main.py)**:
   - **WeChat Integration Endpoints**: `/wework/callback`, `/wechat/callback` for message handling
   - **Frontend API Endpoints**: Complete REST API with authentication
     - `POST /api/login` - User authentication with WeChat user ID
     - `GET /api/profiles` - Paginated user profiles with search
     - `GET /api/profiles/{id}` - Detailed profile view
     - `DELETE /api/profiles/{id}` - Profile deletion
     - `GET /api/search` - Full-text profile search
     - `GET /api/stats` - User statistics dashboard
     - `GET /api/recent` - Recent profiles
     - `GET /api/user/info` - Current user information
     - `GET /api/updates/check` - Real-time update checking
   - **CORS Support**: Configured for frontend integration
   - **Authentication**: Bearer token authentication system
   - **Database Integration**: Intelligent PostgreSQL/SQLite selection

2. **Service Layer Architecture**:
   - **AI Service (src/services/ai_service.py)**: 
     - Qwen API integration with specialized prompts
     - Chat record analysis with target user detection
     - JSON response parsing with auto-repair
     - Confidence score calculation
   - **Media Processor (src/services/media_processor.py)**:
     - ETL4LM integration for OCR and PDF processing
     - Alibaba Cloud ASR for voice recognition
     - Multi-format document processing
     - Timeout handling and progress tracking
   - **WeWork Client (src/services/wework_client.py)**:
     - Dual-platform support (Enterprise WeChat + WeChat Customer Service)
     - Message encryption/decryption
     - Token management and API calls
     - Message synchronization for WeChat Customer Service

3. **Message Processing Pipeline**:
   - **Classification (src/handlers/message_classifier.py)**: Intelligent message type detection
   - **Text Extraction (src/handlers/message_formatter.py)**: Universal text extraction from all message types
   - **Processing Orchestration (src/handlers/message_handler.py)**: Unified workflow management
   - **Real-time Media Processing**: Chat record media files processed during analysis

4. **Multi-User Database System**:
   - **PostgreSQL Support**: Advanced multi-tenant architecture with user quotas
   - **SQLite v2 (Recommended)**: Each WeChat user gets dedicated table (`profiles_user123`)
   - **Data Isolation**: Complete separation between users
   - **Database Features**:
     - Automatic table creation and indexing
     - Full-text search capabilities
     - Confidence scoring and metadata storage
     - Message processing logs and statistics
     - Interactive management tools

5. **Frontend Integration**:
   - **Complete API Documentation**: Three levels of documentation for different use cases
   - **Test Interface**: Ready-to-use HTML/JavaScript testing interface
   - **Multi-Framework Examples**: React, Vue.js, and vanilla JavaScript examples
   - **Real-time Updates**: Polling and WebSocket support patterns
   - **Mobile Responsive**: Optimized for mobile devices

## User Profile Extraction

The system extracts comprehensive user profiles with the following standardized fields:

### Core Profile Fields
1. **姓名（主键）** - Primary identifier, required field
2. **性别** - Male/Female/Unknown  
3. **年龄** - Specific age or age range
4. **电话** - Phone number or contact information
5. **所在地（常驻地）** - City or region of residence
6. **婚育** - Marital and parental status (已婚已育/已婚未育/未婚/离异/未知)
7. **学历（学校）** - Education level and institutions
8. **公司（行业）** - Current company and industry
9. **职位** - Current position or job title
10. **资产水平** - Asset level (High/Medium/Low/Unknown)
11. **性格** - Personality traits and characteristics

### Advanced Processing Capabilities
- **Text Messages**: Direct content analysis with context understanding
- **Voice Messages**: Automatic speech-to-text → profile extraction
- **Chat Records**: 
  - **Smart Target Detection**: Focuses only on target person (excludes forwarder)
  - **Multimedia Integration**: Processes embedded images, voice, files
  - **Advanced AI Prompting**: Specialized analysis for chat conversations
  - **Single Profile Output**: Ensures only one profile per analysis
- **Documents**: Full content extraction from Word, PDF, Excel, TXT files
- **Images**: OCR text recognition for profile information
- **Combined Analysis**: Multi-message type intelligent correlation

## Commands for Development

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Optional: Voice recognition support
pip install alibabacloud-nls-python-sdk
```

### Running the Application
```bash
# Method 1: Using modular startup script (recommended)
python run.py

# Method 2: Using uvicorn directly
uvicorn src.core.main:app --host 0.0.0.0 --port 3001 --reload
```

### Database Management Tools
```bash
# SQLite database management (multi-user version)
python scripts/db_viewer_sqlite.py

# PostgreSQL database management (advanced features)
python scripts/db_viewer_pg.py
```

### Testing and Validation
```bash
# Automated API testing
python tests/test_api.py

# Syntax validation
python -m py_compile src/core/main.py
python -m py_compile src/services/*.py
python -m py_compile src/handlers/*.py

# Configuration validation
python -c "from src.config.config import config; print('配置验证成功')"
```

### Frontend Testing
```bash
# Open frontend test interface
# Navigate to frontend-test/index.html in browser

# Or serve with Python
python -m http.server 8080
# Then visit http://localhost:8080/frontend-test/
```

### Common Development Workflows

1. **Adding New Message Types**:
   - Update `src/handlers/message_classifier.py` classification logic
   - Add handler in `src/handlers/message_handler.py`
   - Implement text extraction in `src/handlers/message_formatter.py`
   - Update AI prompts in `src/services/ai_service.py` if needed

2. **Frontend API Integration**:
   - Check `docs/api/FRONTEND_API_GUIDE.md` for detailed API documentation
   - Use `docs/api/API_EXAMPLES.md` for React/Vue/JavaScript examples
   - Test with `frontend-test/index.html` interface
   - Implement real-time updates using provided patterns

3. **Database Schema Changes**:
   - Modify `src/database/database_sqlite_v2.py` for SQLite
   - Update `src/database/database_pg.py` for PostgreSQL
   - Run database management tools to verify changes
   - Update API models in `src/core/main.py` if needed

4. **ETL4LM and Media Processing**:
   - Monitor console for processing status and timeouts
   - Check ETL integration in `src/services/media_processor.py`
   - Test with various file formats (images, PDFs, documents)
   - Verify OCR results in AI analysis output

## Environment Configuration

### Required Variables (.env file)
```bash
# WeChat Platform Credentials
WEWORK_CORP_ID=your_corp_id              # 企业ID/微信客服企业ID
WEWORK_SECRET=your_secret                # 企业微信应用密钥/微信客服Secret  
WEWORK_TOKEN=your_token                  # 回调Token
WEWORK_AES_KEY=your_aes_key             # 加密AES Key

# AI Analysis Service
QWEN_API_KEY=your_qwen_api_key          # 通义千问API密钥（必需）
QWEN_API_ENDPOINT=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### Optional Variables
```bash
# Enterprise WeChat Only
WEWORK_AGENT_ID=your_agent_id           # 企业微信应用ID（微信客服不需要）

# Server Configuration
LOCAL_SERVER_PORT=3001                  # API服务端口
ENVIRONMENT=development                 # development/production

# Voice Recognition (Alibaba Cloud ASR)
ASR_APPKEY=NM5zdrGkIl8xqSzO           # 预配置AppKey
ASR_TOKEN=your_asr_token               # 需要有效Token
ASR_URL=wss://nls-gateway-cn-shanghai.aliyuncs.com/ws/v1

# Database Configuration
DATABASE_PATH=user_profiles.db          # SQLite数据库路径
DATABASE_URL=postgresql://user:pass@localhost:5432/profiles_db  # PostgreSQL连接

# Media Processing
FFMPEG_PATH=your_ffmpeg_path           # ffmpeg路径（可选）
```

### Pre-configured Services
```bash
# ETL4LM Service (No API key required)
ETL_BASE_URL=http://110.16.193.170:50103
ETL_PREDICT_ENDPOINT=/v1/etl4llm/predict
```

## Message Processing Flow

### WeChat Customer Service Flow (Primary)
1. WeChat Customer Service sends GET request for URL verification
2. Service verifies signature and decrypts echostr, returns decrypted result  
3. Customer sends message → WeChat Customer Service sends POST event notification
4. Service identifies kf_msg_or_event and calls sync_msg API to retrieve actual content
5. Message is classified, processed, and analyzed by AI
6. User profile is extracted and stored in user-specific database table
7. Analysis results are formatted and sent back to customer via WeChat API

### Enterprise WeChat Flow (Secondary)
1. Enterprise WeChat sends GET request for URL verification
2. Service handles verification and message processing directly
3. Messages contain full content in callback (no sync_msg required)
4. Same classification, processing, and storage pipeline as WeChat Customer Service

### Frontend API Flow (New)
1. Frontend authenticates with WeChat user ID → receives Bearer token
2. Frontend calls REST APIs with token authentication
3. APIs return user-specific data from isolated database tables
4. Real-time updates available through polling endpoints
5. Complete CRUD operations supported for user profile management

## Platform Integration Notes

### WeChat Customer Service vs Enterprise WeChat
- **WeChat Customer Service**: Event-driven notifications + sync_msg API calls
- **Enterprise WeChat**: Direct message delivery in callbacks
- **API Compatibility**: Both platforms use identical processing pipeline after message retrieval
- **User Isolation**: Each WeChat user ID gets dedicated data storage regardless of platform

### Database Strategy
- **Development**: SQLite with multi-user tables (database_sqlite_v2.py)
- **Production**: PostgreSQL with advanced features (database_pg.py)
- **Automatic Fallback**: System intelligently selects available database
- **Data Migration**: Manual export/import between databases supported

### Frontend Integration Points
- **Authentication**: Simple Base64 token system (upgrade to JWT recommended for production)
- **Real-time Updates**: Polling every 30 seconds, WebSocket patterns provided
- **Mobile Support**: Responsive design with touch optimization
- **Multi-framework**: React, Vue.js, and vanilla JavaScript examples included

## Recent Updates and Improvements

### Project Restructure (2025-08-04)
- ✅ **Modular Architecture**: Clean separation of concerns with src/ directory structure  
- ✅ **Import Path Standardization**: Relative imports with proper module hierarchy
- ✅ **Enhanced Documentation**: Three-tier API documentation system
- ✅ **Frontend Integration**: Complete REST API with authentication
- ✅ **Database Evolution**: Multi-user SQLite v2 with isolated storage
- ✅ **Testing Infrastructure**: Automated API testing and frontend test interface

### Key Technical Improvements
- **Database Isolation**: Each WeChat user gets dedicated table (e.g., `profiles_user123`)
- **API Security**: Bearer token authentication with user validation
- **Real-time Features**: Update checking and polling mechanisms
- **Error Handling**: Comprehensive error recovery and user feedback
- **Performance**: Connection pooling and query optimization
- **Documentation**: Complete developer guides with code examples

### Configuration Dependencies
- **Critical**: WEWORK_CORP_ID, WEWORK_SECRET, WEWORK_TOKEN, WEWORK_AES_KEY, QWEN_API_KEY
- **Voice Features**: ASR_TOKEN (for speech recognition)
- **Media Processing**: FFMPEG_PATH (for voice conversion)
- **Database**: DATABASE_URL (PostgreSQL) or DATABASE_PATH (SQLite)
- **Auto-configured**: ETL4LM service endpoint