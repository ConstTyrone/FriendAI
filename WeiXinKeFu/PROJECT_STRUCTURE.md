# 项目文件结构

## 📁 整体结构

```
qiwei/                                  # 项目根目录
├── 📄 run.py                          # 应用启动脚本
├── 📄 requirements.txt                # Python依赖
├── 📄 CLAUDE.md                       # 项目开发指南
├── 📄 README.md                       # 项目说明
├── 📄 PROJECT_STRUCTURE.md            # 项目结构文档（本文件）
├── 📄 .env                            # 环境变量配置
├── 📄 .gitignore                      # Git忽略文件
│
├── 📂 src/                            # 源代码目录
│   ├── 📄 __init__.py
│   ├── 📂 core/                       # 核心模块
│   │   ├── 📄 __init__.py
│   │   └── 📄 main.py                 # FastAPI应用主文件
│   ├── 📂 services/                   # 服务层
│   │   ├── 📄 __init__.py
│   │   ├── 📄 ai_service.py           # AI分析服务
│   │   ├── 📄 media_processor.py      # 媒体处理服务
│   │   └── 📄 wework_client.py        # 企业微信客户端
│   ├── 📂 handlers/                   # 消息处理层
│   │   ├── 📄 __init__.py
│   │   ├── 📄 message_handler.py      # 统一消息处理器
│   │   ├── 📄 message_classifier.py   # 消息分类器
│   │   ├── 📄 message_formatter.py    # 消息格式化器
│   │   └── 📄 message_sync_optimizer.py # 消息同步优化器
│   └── 📂 database/                   # 数据库层
│       ├── 📄 __init__.py
│       ├── 📄 database_pg.py          # PostgreSQL数据库管理
│       ├── 📄 database_sqlite.py      # SQLite数据库管理（简单版）
│       ├── 📄 database_sqlite_v2.py   # SQLite数据库管理（完整版）
│       └── 📄 database_design.sql     # 数据库设计文件
│
├── 📂 config/                         # 配置文件
│   └── 📄 config.py                   # 应用配置
│
├── 📂 scripts/                        # 脚本工具
│   ├── 📄 db_viewer_pg.py            # PostgreSQL数据库查看器
│   └── 📄 db_viewer_sqlite.py        # SQLite数据库查看器
│
├── 📂 tests/                          # 测试文件
│   └── 📄 test_api.py                 # API测试脚本
│
├── 📂 docs/                           # 文档目录
│   ├── 📂 api/                        # API文档
│   │   ├── 📄 API_DOCUMENTATION.md   # API基础文档
│   │   ├── 📄 FRONTEND_API_GUIDE.md  # 前端API详细指南
│   │   └── 📄 API_EXAMPLES.md        # API使用示例
│   └── 📂 setup/                      # 安装配置文档
│       └── 📄 DATABASE_SETUP.md      # 数据库安装说明
│
├── 📂 frontend-test/                  # 前端测试页面
│   ├── 📄 index.html                 # 主页面
│   ├── 📄 api-client.js              # API客户端封装
│   ├── 📄 app.js                     # 主应用逻辑
│   └── 📄 README.md                  # 前端使用说明
│
├── 📂 reference/                      # 参考文档
│   ├── 📄 ETL接口文档.md             # ETL4LM API文档
│   └── 📄 阿里asr文档.md             # 阿里云ASR文档
│
├── 📂 weixin_doc/                     # 微信官方文档
│   ├── 📄 开发总领.md
│   ├── 📄 接收消息.md
│   ├── 📄 发送消息.md
│   ├── 📄 获取客户基础信息.md
│   └── 📄 ...                        # 其他微信文档
│
├── 📂 temp_media/                     # 临时媒体文件
│   └── 📄 .gitkeep                   # 保持目录结构
│
└── 📄 user_profiles.db               # SQLite数据库文件（自动生成）
```

## 🎯 模块说明

### 核心模块 (src/core/)
- **main.py**: FastAPI应用主文件，包含所有API端点定义

### 服务层 (src/services/)
- **ai_service.py**: AI分析服务，调用通义千问API进行用户画像分析
- **media_processor.py**: 媒体处理服务，包含语音识别、图像OCR、文件处理等
- **wework_client.py**: 企业微信/微信客服API客户端

### 消息处理层 (src/handlers/)
- **message_handler.py**: 统一消息处理器，orchestrates整个处理流程
- **message_classifier.py**: 消息分类器，识别消息类型
- **message_formatter.py**: 文本提取器，将各种消息转换为纯文本
- **message_sync_optimizer.py**: 消息同步优化器（待整合）

### 数据库层 (src/database/)
- **database_pg.py**: PostgreSQL数据库实现
- **database_sqlite_v2.py**: SQLite数据库实现（推荐）
- **database_sqlite.py**: SQLite数据库简化实现

### 工具脚本 (scripts/)
- **db_viewer_pg.py**: PostgreSQL数据库管理工具
- **db_viewer_sqlite.py**: SQLite数据库管理工具

## 🚀 启动方式

### 开发环境
```bash
# 直接启动
python run.py

# 或使用uvicorn
uvicorn src.core.main:app --host 0.0.0.0 --port 3001 --reload
```

### 生产环境
```bash
# 设置环境变量
export ENVIRONMENT=production

# 启动应用
python run.py
```

## 📋 导入路径规范

由于项目采用了模块化结构，各模块间的导入遵循以下规范：

### 绝对导入（推荐）
```python
# 从services导入ai_service
from src.services.ai_service import profile_extractor

# 从database导入数据库管理器
from src.database.database_sqlite_v2 import database_manager
```

### 相对导入
```python
# 在handlers模块内部
from .message_classifier import classifier
from ..services.ai_service import profile_extractor
from ..database.database_sqlite_v2 import database_manager
```

## 🔧 开发工具

### 数据库管理
```bash
# SQLite数据库查看器
python scripts/db_viewer_sqlite.py

# PostgreSQL数据库查看器  
python scripts/db_viewer_pg.py
```

### API测试
```bash
# 后端API测试
python tests/test_api.py

# 前端测试页面
# 打开 frontend-test/index.html
```

### 语法检查
```bash
# 检查Python语法
python -m py_compile src/core/main.py
python -m py_compile src/services/*.py
python -m py_compile src/handlers/*.py
```

## 📦 依赖管理

### 核心依赖
- **FastAPI**: Web框架
- **uvicorn**: ASGI服务器
- **requests**: HTTP客户端
- **pycryptodome**: 加密解密
- **python-dotenv**: 环境变量管理

### 可选依赖
- **psycopg2-binary**: PostgreSQL支持
- **alibabacloud-nls**: 阿里云语音识别

## 🗂️ 配置文件

### 环境配置 (.env)
```bash
# 微信配置
WEWORK_CORP_ID=your_corp_id
WEWORK_SECRET=your_secret
WEWORK_TOKEN=your_token
WEWORK_AES_KEY=your_aes_key

# API配置
QWEN_API_KEY=your_qwen_api_key
ASR_TOKEN=your_asr_token

# 数据库配置
DATABASE_PATH=user_profiles.db
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# 服务配置
LOCAL_SERVER_PORT=3001
ENVIRONMENT=development
```

## 📝 代码规范

### 文件命名
- 模块文件: `snake_case.py`
- 类名: `PascalCase`
- 函数名: `snake_case`
- 常量: `UPPER_CASE`

### 导入顺序
1. 标准库导入
2. 第三方库导入
3. 本地模块导入

### 日志规范
```python
import logging
logger = logging.getLogger(__name__)

# 使用示例
logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志")
```

## 🔄 版本控制

### Git忽略规则
```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.env
.venv/

# 数据库
*.db
*.sqlite

# 临时文件
temp_media/
logs/

# IDE
.vscode/
.idea/
```

## 📈 性能优化

### 数据库优化
- 使用数据库连接池
- 适当的索引设计
- 分页查询优化

### API优化
- 响应缓存
- 请求限流
- 异步处理

### 部署优化
- 使用 gunicorn + uvicorn workers
- 负载均衡配置
- 静态文件CDN

这个结构确保了：
✅ 清晰的模块分离
✅ 易于维护和扩展
✅ 符合Python最佳实践
✅ 便于团队协作开发