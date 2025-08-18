# 线上部署推送通知功能指南

## 🚀 快速部署命令

在您的线上服务器执行以下命令：

```bash
# 1. 更新代码
cd /path/to/FriendAI
git pull origin main

# 2. 进入后端目录
cd WeiXinKeFu

# 3. 初始化数据库（添加推送相关表和字段）
python scripts/add_push_fields.py

# 4. 运行快速设置（可选，用于查看集成状态）
python quick_setup_push.py
```

## 📝 手动集成代码（重要！）

### 1. 更新 `src/handlers/message_handler.py`

在文件顶部添加导入：
```python
from ..services.push_service_enhanced import enhanced_push_service
```

在 `handle_wechat_kf_event` 函数中（约第340行），获取到 `external_userid` 和 `open_kfid` 后添加：

```python
# 记录用户会话信息（用于推送）
try:
    # 重置48小时计数器（用户发送了新消息）
    enhanced_push_service.reset_48h_counter(external_userid)
    
    # 更新会话信息
    enhanced_push_service.update_user_session(
        user_id=external_userid,
        external_userid=external_userid,
        open_kfid=open_kfid
    )
    logger.info(f"更新用户会话信息: {external_userid} -> {open_kfid}")
except Exception as e:
    logger.warning(f"更新会话信息失败: {e}")
```

### 2. 更新 `src/services/intent_matcher.py`

在 `match_intent_with_profiles` 函数的匹配成功后（约第500行）添加：

```python
# 触发推送通知
if match_score >= threshold:
    try:
        from ..services.push_service_enhanced import enhanced_push_service
        
        # 准备推送数据
        push_data = {
            'profile_id': profile[0],
            'profile_name': profile[1],
            'intent_id': intent_id,
            'intent_name': intent_row[1] if intent_row else '意图',
            'score': match_score,
            'explanation': explanation,
            'matched_conditions': matched_conditions,
            'match_id': match_id
        }
        
        # 异步推送（避免阻塞匹配流程）
        enhanced_push_service.process_match_for_push(push_data, user_id)
        logger.info(f"触发推送: 意图{intent_id} -> 联系人{profile[0]}")
    except Exception as e:
        logger.warning(f"推送失败，但不影响匹配: {e}")
```

## 🔄 重启服务

```bash
# 方式1：如果使用systemd
sudo systemctl restart friendai

# 方式2：如果使用supervisor
sudo supervisorctl restart friendai

# 方式3：如果使用screen/tmux
# 先结束当前进程，然后
python run.py

# 方式4：如果使用PM2
pm2 restart friendai
```

## ✅ 验证部署

### 1. 检查数据库表是否创建成功

```bash
# 运行数据库查看器
python scripts/db_viewer_sqlite.py

# 或直接用sqlite3命令
sqlite3 user_profiles.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%push%' OR name='wechat_kf_sessions';"
```

应该看到以下表：
- `wechat_kf_sessions`
- `push_templates`
- `user_push_preferences`（更新了字段）

### 2. 测试推送功能

```bash
# 运行测试脚本
python test_push_notification.py
```

### 3. 查看日志确认集成

```bash
# 查看服务日志
tail -f logs/app.log | grep -E "推送|会话|push"
```

## 🧪 功能测试流程

1. **建立会话**
   - 用户通过微信发送任意消息给客服账号
   - 查看日志确认会话记录：`更新用户会话信息`

2. **创建测试意图**
   ```bash
   curl -X POST http://localhost:8000/api/intents \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "测试推送意图",
       "description": "测试推送功能",
       "conditions": {
         "keywords": ["技术", "AI"]
       }
     }'
   ```

3. **验证推送**
   - 检查微信是否收到推送消息
   - 查看推送历史记录

## 🔍 故障排查

### 问题1：推送失败，提示"无有效会话"
**解决方案**：
```bash
# 检查会话表
sqlite3 user_profiles.db "SELECT * FROM wechat_kf_sessions WHERE user_id='YOUR_USER_ID';"
```
- 确保用户在48小时内发送过消息
- 检查 `open_kfid` 是否正确记录

### 问题2：代码更新后推送不工作
**解决方案**：
1. 确认手动集成的代码已添加
2. 检查导入路径是否正确
3. 重启服务
4. 查看错误日志

### 问题3：数据库表不存在
**解决方案**：
```bash
# 重新运行初始化脚本
python scripts/add_push_fields.py

# 如果还有问题，手动创建
python scripts/create_intent_tables.py
```

## 📊 监控推送状态

```bash
# 实时监控推送
watch -n 5 "sqlite3 user_profiles.db 'SELECT COUNT(*) as total_sessions FROM wechat_kf_sessions; SELECT COUNT(*) as active_users FROM user_push_preferences WHERE enable_push=1;'"

# 查看最近的推送记录
sqlite3 user_profiles.db "SELECT * FROM push_history_* ORDER BY created_at DESC LIMIT 10;"
```

## 🎯 推送功能配置

### 配置用户推送偏好

```sql
-- 在数据库中执行
UPDATE user_push_preferences
SET 
    enable_push = 1,              -- 开启推送
    quiet_hours = '22:00-08:00',  -- 静默时间
    daily_limit = 10,              -- 每日限制
    min_score = 0.7                -- 最低匹配度
WHERE user_id = 'YOUR_USER_ID';
```

### 配置推送模板

```sql
-- 添加自定义模板
INSERT INTO push_templates (
    template_name, 
    template_type, 
    content_template
) VALUES (
    'production_template',
    'text',
    '【FriendAI】发现新的匹配：{profile_name}符合您的意图"{intent_name}"，匹配度{score}%'
);
```

## 📈 性能优化建议

1. **异步处理**：推送操作已设计为非阻塞
2. **批量控制**：系统自动限制批量推送数量（最多3条）
3. **缓存优化**：会话信息会缓存，减少数据库查询

## 🔐 安全注意事项

1. **会话验证**：系统自动验证48小时时限
2. **频率限制**：遵守微信5条/48小时限制
3. **日志脱敏**：不记录完整的 `external_userid`

## ✨ 部署完成标志

当看到以下日志时，表示推送功能已正常工作：
- `更新用户会话信息: xxx -> xxx`
- `触发推送: 意图x -> 联系人x`
- `推送成功: 用户xxx, 消息ID: xxx`

## 📞 需要帮助？

如遇到问题：
1. 查看完整文档：`PUSH_NOTIFICATION_IMPLEMENTATION.md`
2. 运行诊断：`python test_push_notification.py`
3. 查看集成指南：`python scripts/integrate_push_handler.py`

---

**部署时间预计**：10-15分钟
**最后更新**：2025-01-18