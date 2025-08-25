# 微信客服用户画像系统

一个基于FastAPI的智能用户画像提取系统，支持企业微信和微信客服平台，通过AI分析用户消息自动生成详细的用户画像。

## 🎯 核心功能

- **多平台支持**: 企业微信 + 微信客服双平台支持
- **智能分析**: 基于通义千问API的用户画像提取
- **多媒体处理**: 语音识别、图像OCR、文档解析
- **数据隔离**: 每个微信用户拥有独立数据存储
- **实时API**: 完整的RESTful API供前端调用
- **可视化管理**: 内置数据库管理工具

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd qiwei

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入您的配置
```

### 2. 配置说明

在 `.env` 文件中配置以下参数：

```bash
# 微信配置
WEWORK_CORP_ID=your_corp_id
WEWORK_SECRET=your_secret
WEWORK_TOKEN=your_token
WEWORK_AES_KEY=your_aes_key

# AI服务配置
QWEN_API_KEY=your_qwen_api_key
ASR_TOKEN=your_asr_token

# 数据库配置
DATABASE_PATH=user_profiles.db

# 服务配置
LOCAL_SERVER_PORT=3001
```

### 3. 启动应用

```bash
# 方式一：使用启动脚本（推荐）
python run.py

# 方式二：直接使用uvicorn
uvicorn src.core.main:app --host 0.0.0.0 --port 3001 --reload
```

### 4. 访问服务

- **API文档**: http://localhost:3001/docs
- **前端测试**: 打开 `frontend-test/index.html`
- **数据库管理**: `python scripts/db_viewer_sqlite.py`

## 📋 项目结构

```
qiwei/
├── src/                    # 源代码
│   ├── core/              # 核心模块（FastAPI应用）
│   ├── services/          # 服务层（AI、媒体处理、微信客户端）
│   ├── handlers/          # 消息处理层
│   ├── database/          # 数据库层
│   └── config/            # 配置模块
├── frontend-test/         # 前端测试页面
├── scripts/              # 工具脚本
├── docs/                 # 文档
├── tests/               # 测试文件
└── weixin_doc/          # 微信官方文档
```

详细结构说明请查看 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

## 🎨 功能特性

### 消息处理流程

```
用户消息 → 解密 → 分类 → 文本提取 → AI分析 → 用户画像 → 数据存储
```

### 支持的消息类型

- **文本消息**: 直接分析文本内容
- **语音消息**: 自动语音转文字后分析
- **图片消息**: OCR识别文字内容
- **文件消息**: 支持Word、PDF、Excel文档解析
- **聊天记录**: 深度分析聊天内容，智能识别目标用户

### 用户画像字段

| 字段 | 说明 | 示例 |
|------|------|------|
| 姓名 | 用户姓名（主键） | 张三 |
| 性别 | 性别信息 | 男/女 |
| 年龄 | 年龄或年龄段 | 28岁 |
| 电话 | 联系方式 | 138****1234 |
| 所在地 | 居住地址 | 北京市朝阳区 |
| 婚育 | 婚姻状况 | 已婚已育 |
| 学历 | 教育背景 | 本科 |
| 公司 | 工作单位 | 某科技公司 |
| 职位 | 职务信息 | 软件工程师 |
| 资产水平 | 经济状况 | 中等 |
| 性格 | 性格特征 | 开朗活泼 |

## 🔧 开发指南

### API接口

系统提供完整的RESTful API：

- `POST /api/login` - 用户登录
- `GET /api/profiles` - 获取画像列表
- `GET /api/profiles/{id}` - 获取画像详情
- `DELETE /api/profiles/{id}` - 删除画像
- `GET /api/search` - 搜索画像
- `GET /api/stats` - 获取统计信息

详细API文档请查看：
- [API基础文档](docs/api/API_DOCUMENTATION.md)
- [前端开发指南](docs/api/FRONTEND_API_GUIDE.md)
- [代码示例](docs/api/API_EXAMPLES.md)

### 数据库管理

```bash
# SQLite数据库管理
python scripts/db_viewer_sqlite.py

# PostgreSQL数据库管理（可选）
python scripts/db_viewer_pg.py
```

### 测试工具

```bash
# 后端API测试
python tests/test_api.py

# 前端界面测试
# 打开 frontend-test/index.html
```

## 🛠️ 技术栈

### 后端技术
- **FastAPI**: 高性能Web框架
- **SQLite/PostgreSQL**: 数据库存储
- **通义千问API**: AI用户画像分析
- **阿里云ASR**: 语音识别服务
- **ETL4LM**: 文档和图像处理

### 前端技术
- **HTML5 + JavaScript**: 测试界面
- **Bootstrap 5**: UI框架
- **原生API调用**: 无框架依赖

## 📊 数据安全

- **用户隔离**: 每个微信用户拥有独立数据表
- **Token认证**: API访问需要有效Token
- **数据加密**: 微信消息加密传输
- **隐私保护**: 敏感信息自动脱敏

## 🚧 部署说明

### 开发环境
```bash
python run.py
```

### 生产环境
```bash
# 使用Gunicorn部署
pip install gunicorn
gunicorn src.core.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Docker部署
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

## 📝 更新日志

### v1.0.0 (2025-08-04)
- ✅ 项目结构重构，模块化设计
- ✅ 完整的用户画像CRUD功能
- ✅ 多用户数据隔离
- ✅ 前端API接口完整实现
- ✅ 语音识别和文档处理集成
- ✅ 数据库管理工具

### 主要改进
- 🔧 重新组织了项目文件结构
- 📚 完善了API文档和使用指南
- 🎨 优化了前端测试界面
- 🔒 增强了数据安全性
- 📊 完善了统计功能

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🆘 支持

- 📖 查看 [文档目录](docs/) 获取详细信息
- 🐛 [提交问题](../../issues) 报告bug
- 💡 [功能建议](../../issues) 提出新功能需求

## 📞 联系方式

- 开发团队: [开发者邮箱]
- 项目地址: [GitHub仓库地址]
- 技术支持: [支持邮箱]