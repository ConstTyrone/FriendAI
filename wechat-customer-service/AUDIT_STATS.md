# 用户活动审计与统计功能

## 📊 功能概述

简化版审计系统，追踪用户使用情况，提供基础统计数据。

### 核心功能
- ✅ 统计总用户数
- ✅ 统计今日活跃用户（DAU）
- ✅ 记录每个用户的消息次数
- ✅ 追踪AI对话和表情包生成次数
- ✅ 显示最活跃用户排行

## 🏗️ 技术实现

### 数据库表

新增 `user_activity` 表：

```sql
CREATE TABLE user_activity (
    external_userid TEXT PRIMARY KEY,  -- 用户ID
    first_visit TIMESTAMP,              -- 首次访问时间
    last_visit TIMESTAMP,               -- 最后访问时间
    message_count INTEGER,              -- 总消息数
    ai_chat_count INTEGER,              -- AI对话次数
    emoticon_count INTEGER,             -- 表情包生成次数
    last_active_date TEXT               -- 最后活跃日期
)
```

### 埋点位置

系统在以下3个关键点记录用户活动：

1. **收到消息时** - `message_handler.py:59`
   - 记录类型：`text`
   - 自动更新 `message_count`

2. **AI对话成功后** - `message_handler.py:149`
   - 记录类型：`ai_chat`
   - 自动更新 `ai_chat_count`

3. **表情包生成成功后** - `message_handler.py:118`
   - 记录类型：`emoticon`
   - 自动更新 `emoticon_count`

## 📡 API接口

### 1. 获取总体统计

**端点**: `GET /stats`

**返回示例**:
```json
{
  "status": "success",
  "data": {
    "overview": {
      "total_users": 150,
      "active_today": 23,
      "total_messages": 5432,
      "ai_chats": 4200,
      "emoticons": 1232
    },
    "top_users": [
      {
        "userid": "wmxxxxxx",
        "message_count": 89,
        "ai_chat_count": 70,
        "emoticon_count": 19,
        "first_visit": "2025-10-01 08:30:00",
        "last_visit": "2025-10-02 14:20:00"
      }
    ]
  },
  "timestamp": 1696234567.89
}
```

### 2. 获取单个用户统计

**端点**: `GET /stats/user/{external_userid}`

**返回示例**:
```json
{
  "status": "success",
  "data": {
    "userid": "wmxxxxxx",
    "first_visit": "2025-10-01 08:30:00",
    "last_visit": "2025-10-02 14:20:00",
    "message_count": 89,
    "ai_chat_count": 70,
    "emoticon_count": 19,
    "last_active_date": "2025-10-02"
  },
  "timestamp": 1696234567.89
}
```

## 🚀 使用方法

### 查看统计数据

```bash
# 查看总体统计
curl http://localhost:3001/stats

# 查看单个用户统计
curl http://localhost:3001/stats/user/wmxxxxxx
```

### 在浏览器访问

- 总体统计：http://localhost:3001/stats
- API文档：http://localhost:3001/docs

## 📈 数据说明

### 指标定义

- **total_users**: 有过任何消息记录的用户总数
- **active_today**: 今天发送过消息的用户数（DAU - Daily Active Users）
- **total_messages**: 所有用户发送的消息总数
- **ai_chats**: 触发AI对话的次数（不包括表情包请求）
- **emoticons**: 成功生成表情包的次数

### 活跃度计算

- 用户每次发送消息都会更新 `last_active_date`
- DAU 统计当天 `last_active_date` 为今日的用户数
- 排行榜按 `message_count` 降序排列

## 🔧 代码文件

### 新增文件
- `src/database/audit_database.py` - 审计数据库管理

### 修改文件
- `src/handlers/message_handler.py` - 添加3个埋点
- `src/core/main.py` - 新增2个统计API端点

## 💡 使用场景

### 场景1：每日运营监控
- 打开 `/stats` 查看今日DAU
- 检查用户增长趋势
- 查看消息总量

### 场景2：用户行为分析
- 查看最活跃用户
- 分析AI对话与表情包使用比例
- 识别高价值用户

### 场景3：单用户追踪
- 查询某个用户的完整使用历史
- 了解用户活跃程度
- 确认用户首次和最后访问时间

## 🔒 注意事项

### 数据隐私
- 系统只记录使用频次，不存储消息内容
- 用户ID为微信加密后的external_userid
- 建议定期备份数据库

### 性能影响
- 埋点采用同步写入，对性能影响极小（<1ms）
- 数据库采用SQLite，单表索引优化
- 适合中小规模应用（<10万用户）

## 📊 未来扩展

如需更多功能，可以考虑：
- 每日/每周/每月统计报表
- 用户留存率分析
- 数据可视化Dashboard
- Excel导出功能
- 按时间范围查询

当前实现为极简版本，满足基础统计需求，可根据实际需要逐步扩展。
