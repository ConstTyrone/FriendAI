# 数据库结构文档

## 当前使用版本
- **代码版本**: `database_sqlite_v2.py`
- **数据库文件**: `user_profiles.db`
- **环境变量**: `DATABASE_PATH=user_profiles.db`

## 表结构说明

### 系统表
```
users                   - 用户主表
user_stats             - 用户统计信息
message_logs           - 消息日志
user_intents           - 用户意图
intent_matches         - 意图匹配结果
vector_index           - 向量索引
push_history           - 推送历史
user_push_preferences  - 推送偏好设置
```

### 用户画像表（profiles_xxx）
每个微信用户都有独立的表，格式为 `profiles_{wechat_user_id}`

#### v2版本定义的标准列（20个）
```sql
CREATE TABLE profiles_xxx (
    -- 基本字段
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name TEXT NOT NULL,           -- 联系人姓名（主键）
    
    -- 个人信息
    gender TEXT,                          -- 性别
    age TEXT,                              -- 年龄
    phone TEXT,                            -- 电话
    location TEXT,                         -- 位置
    marital_status TEXT,                   -- 婚姻状况
    education TEXT,                        -- 教育背景
    company TEXT,                          -- 公司
    position TEXT,                         -- 职位
    asset_level TEXT,                      -- 资产水平
    personality TEXT,                      -- 性格
    tags TEXT,                             -- 标签（JSON数组）
    
    -- AI分析元数据
    ai_summary TEXT,                       -- AI摘要
    confidence_score REAL,                 -- 置信度分数
    source_type TEXT,                      -- 来源类型
    
    -- 原始数据
    raw_message_content TEXT,              -- 原始消息内容
    raw_ai_response TEXT,                  -- AI原始响应
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(profile_name)
)
```

#### 当前额外的列（13个，可能不需要）
```sql
-- 向量搜索相关
embedding BLOB,                -- 向量嵌入数据
embedding_model TEXT,          -- 使用的向量模型
embedding_updated_at TIMESTAMP,-- 向量更新时间

-- 额外信息字段
wechat_id TEXT,               -- 微信ID
basic_info TEXT,              -- 基本信息JSON
recent_activities TEXT,       -- 最近活动JSON
raw_messages TEXT,            -- 原始消息历史
source TEXT,                  -- 数据来源
message_count INTEGER,        -- 消息计数
industry TEXT,                -- 行业
school TEXT,                  -- 学校
profile_picture TEXT,         -- 头像URL
last_message_time TEXT        -- 最后消息时间
```

## API字段映射问题

### 已修复的问题
创建联系人时，API传入的字段名是 `name`，但数据库期望 `profile_name`。
已在 `src/core/main.py` 第703行修复：
```python
profile_data = {
    "profile_name": request.name.strip(),  # 正确的字段名
    "name": request.name.strip(),          # 保留兼容性
    ...
}
```

## 建议

### 选项1：保留现状
- **优点**：不影响现有功能，额外的列不会造成问题
- **缺点**：数据库结构不够清晰

### 选项2：清理多余的列（谨慎）
如果确定不需要向量搜索等功能，可以删除多余的列。
但需要谨慎，因为可能有其他代码依赖这些列。

### 选项3：迁移到标准v2结构（推荐）
创建新的符合v2标准的表，逐步迁移数据。

## 环境配置

确保环境变量正确设置：
```bash
# .env 文件
DATABASE_PATH=user_profiles.db
DB_TYPE=sqlite  # 使用SQLite而不是PostgreSQL
```

## 代码中的数据库选择逻辑

`src/core/main.py` 中的选择逻辑：
```python
# 尝试使用PostgreSQL
if os.getenv('DATABASE_URL'):
    from ..database.database_pg import database_manager as db
else:
    # 默认使用SQLite v2
    from ..database.database_sqlite_v2 import database_manager as db
```