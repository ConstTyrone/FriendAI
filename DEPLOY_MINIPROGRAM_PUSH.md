# 微信小程序订阅消息推送部署指南

## 🎯 正确的推送实现方式

本指南帮助您部署**微信小程序订阅消息**推送功能，这是用户明确要求的推送方式。

## ⚠️ 重要说明

之前的 `push_service_enhanced.py` 是错误的实现（微信客服消息），请使用本指南部署正确的小程序订阅消息。

## 📋 前置准备

### 1. 微信公众平台配置

登录 [微信公众平台](https://mp.weixin.qq.com) 完成以下配置：

1. **进入小程序后台** → **功能** → **订阅消息**
2. **选择或创建模板**，建议使用：
   - 模板标题：`匹配结果通知` 或 `新消息提醒`
   - 关键词配置：
     * `thing1`: 匹配对象（20字符限制）
     * `thing2`: 意图名称（20字符限制）  
     * `number3`: 匹配度
     * `time4`: 匹配时间
3. **记录模板ID**（格式：`F3bKrBfKLz_xxxxxxxxxxx`）

### 2. 环境变量配置

在服务器的 `.env` 文件中添加：

```bash
# 微信小程序配置
WECHAT_MINI_APPID=wx50fc05960f4152a6
WECHAT_MINI_SECRET=你的小程序密钥
WECHAT_TEMPLATE_ID=你的模板ID
```

## 🚀 快速部署步骤

### 步骤1：更新代码

```bash
# 进入项目目录
cd /path/to/FriendAI

# 拉取最新代码
git pull origin main
```

### 步骤2：创建数据库表

```bash
cd WeiXinKeFu

# 创建订阅相关表
python -c "from src.services.miniprogram_push_service import miniprogram_push_service; miniprogram_push_service._ensure_subscription_table()"
```

### 步骤3：集成到意图匹配系统

编辑 `src/services/intent_matcher.py`，在文件顶部添加导入：

```python
from ..services.miniprogram_push_service import miniprogram_push_service
```

在 `match_intent_with_profiles` 函数中（约第500行），匹配成功后添加：

```python
# 保存匹配记录后，触发小程序推送
if match_score >= threshold:
    try:
        # 准备推送数据
        push_data = {
            'profile_id': profile[0],
            'profile_name': profile[1],
            'intent_id': intent_id,
            'intent_name': intent_row[1] if intent_row else '意图',
            'score': match_score,
            'explanation': explanation,
            'match_id': cursor.lastrowid
        }
        
        # 发送小程序推送通知
        success = miniprogram_push_service.send_match_notification(
            user_id=user_id,
            match_data=push_data
        )
        
        if success:
            logger.info(f"小程序推送成功: 用户{user_id}, 意图{intent_id}")
        else:
            logger.warning(f"小程序推送失败，用户可能未订阅")
            
    except Exception as e:
        logger.error(f"小程序推送异常: {e}")
        # 推送失败不影响匹配功能
```

### 步骤4：注册API路由

编辑 `src/core/main.py`，添加：

```python
# 在文件顶部导入区域添加
from fastapi import Header
from typing import Optional

# 导入订阅API（在其他导入语句附近）
from .subscription_api import router as subscription_router

# 注册路由（在app创建后）
app.include_router(subscription_router)

# 如果subscription_api.py中的get_current_user需要实现，添加：
def get_current_user(authorization: Optional[str] = Header(None)):
    """从请求头获取当前用户"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未授权")
    
    # 解析token获取user_id
    token = authorization.replace("Bearer ", "")
    try:
        # 使用你现有的token解析逻辑
        import base64
        user_id = base64.b64decode(token.encode()).decode()
        return user_id
    except:
        raise HTTPException(status_code=401, detail="无效的token")
```

### 步骤5：更新前端模板ID

编辑 `weixi_minimo/pages/intent-manager/subscribe.js`：

```javascript
const TEMPLATE_ID = '你的模板ID'; // 替换为实际的模板ID
```

### 步骤6：重启服务

```bash
# 根据您的部署方式选择
sudo systemctl restart friendai
# 或
sudo supervisorctl restart friendai
# 或
pm2 restart friendai
# 或直接运行
python run.py
```

## ✅ 验证部署

### 1. 检查数据库表

```bash
sqlite3 user_profiles.db "SELECT name FROM sqlite_master WHERE type='table' AND (name='user_subscriptions' OR name='miniprogram_push_history');"
```

应该看到：
- `user_subscriptions` - 用户订阅记录表
- `miniprogram_push_history` - 推送历史记录表

### 2. 测试订阅API

```bash
# 获取订阅状态
curl -X GET http://localhost:8000/api/subscription/status \
  -H "Authorization: Bearer YOUR_TOKEN"

# 测试推送
curl -X POST http://localhost:8000/api/subscription/test \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "profile_name": "测试联系人",
    "intent_name": "测试意图",
    "score": 0.85
  }'
```

### 3. 创建测试脚本

创建 `test_miniprogram_push.py`：

```python
#!/usr/bin/env python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.miniprogram_push_service import miniprogram_push_service

def test_push():
    """测试小程序推送"""
    
    # 测试数据
    test_user = "test_user_001"
    test_openid = "oXXXXXXXXXXXXXXXXXXXXXXX"  # 需要真实的openid
    
    # 1. 保存订阅（模拟用户订阅）
    print("1. 保存用户订阅...")
    success = miniprogram_push_service.save_user_subscription(
        user_id=test_user,
        openid=test_openid,
        template_id="YOUR_TEMPLATE_ID",
        template_name="意图匹配通知"
    )
    print(f"   结果: {'成功' if success else '失败'}")
    
    # 2. 发送测试推送
    print("\n2. 发送测试推送...")
    match_data = {
        "profile_name": "张三",
        "intent_name": "寻找AI技术合作",
        "score": 0.92,
        "match_id": 1,
        "intent_id": 1,
        "profile_id": 1
    }
    
    success = miniprogram_push_service.send_match_notification(
        user_id=test_user,
        match_data=match_data
    )
    print(f"   结果: {'成功' if success else '失败'}")
    
    # 3. 查看订阅状态
    print("\n3. 查看订阅状态...")
    subscriptions = miniprogram_push_service.get_user_subscriptions(test_user)
    for sub in subscriptions:
        print(f"   - 模板: {sub['template_name']}, 剩余次数: {sub['remaining_times']}")

if __name__ == "__main__":
    test_push()
```

## 📱 小程序端集成

### 1. 在意图管理页面添加订阅功能

编辑 `pages/intent-manager/intent-manager.js`：

```javascript
// 引入订阅模块
const subscribe = require('./subscribe');

Page({
  // ... 现有代码
  
  // 添加订阅方法
  onSubscribeNotification() {
    subscribe.requestSubscription().then(result => {
      if (result) {
        wx.showToast({
          title: '订阅成功',
          icon: 'success'
        });
      }
    }).catch(err => {
      console.error('订阅失败:', err);
    });
  },
  
  // 在创建意图后自动请求订阅
  onCreateIntent() {
    // ... 创建意图的代码
    
    // 创建成功后请求订阅
    this.onSubscribeNotification();
  }
});
```

### 2. 在页面添加订阅按钮

编辑 `pages/intent-manager/intent-manager.wxml`：

```xml
<!-- 在合适位置添加订阅按钮 -->
<button bindtap="onSubscribeNotification" type="primary" size="mini">
  <text class="t-icon t-icon-notification"></text>
  开启匹配通知
</button>
```

## 🔄 完整工作流程

1. **用户订阅**
   - 用户在小程序中点击"开启匹配通知"
   - 小程序调用 `wx.requestSubscribeMessage` 请求授权
   - 用户同意后，订阅信息通过API保存到数据库

2. **意图匹配**
   - 用户创建或更新意图
   - 系统自动进行意图匹配
   - 匹配成功时调用推送服务

3. **推送发送**
   - 检查用户是否有有效订阅
   - 获取小程序access_token
   - 调用微信API发送订阅消息
   - 记录推送历史

4. **用户接收**
   - 用户在微信"服务通知"中收到消息
   - 点击消息直接跳转到小程序匹配详情页

## ⚠️ 注意事项

### 订阅限制
- 一次订阅只能发送一条消息
- 用户需要多次订阅才能持续接收通知
- 建议在关键操作后引导用户订阅

### 模板限制
- `thing` 类型字段最多20个字符
- `number` 类型必须是数字
- `time` 类型需要标准时间格式

### 开发测试
- 开发版和体验版也可以测试推送
- 需要真实的openid才能发送成功
- 可以使用测试号进行开发

## 🔍 故障排查

### 问题1：推送失败，错误码43101
**原因**：用户拒绝接收消息
**解决**：引导用户重新订阅

### 问题2：推送失败，错误码47003
**原因**：模板参数不正确
**解决**：检查模板字段类型和长度限制

### 问题3：推送失败，错误码40003
**原因**：openid不正确
**解决**：确保openid来自同一个小程序

### 问题4：用户收不到通知
**可能原因**：
1. 用户未订阅或订阅已用完
2. 模板ID配置错误
3. access_token获取失败
4. 网络问题

**排查步骤**：
```bash
# 查看推送历史
sqlite3 user_profiles.db "SELECT * FROM miniprogram_push_history ORDER BY pushed_at DESC LIMIT 10;"

# 查看用户订阅
sqlite3 user_profiles.db "SELECT * FROM user_subscriptions WHERE user_id='YOUR_USER_ID';"

# 查看日志
tail -f logs/app.log | grep -E "订阅|推送|push"
```

## 📊 监控和统计

```bash
# 实时监控推送情况
watch -n 5 "sqlite3 user_profiles.db '
  SELECT COUNT(*) as total_subscriptions FROM user_subscriptions WHERE is_active=1;
  SELECT COUNT(*) as today_pushes FROM miniprogram_push_history WHERE date(pushed_at)=date(\"now\");
  SELECT push_status, COUNT(*) FROM miniprogram_push_history GROUP BY push_status;
'"
```

## ✨ 最佳实践

1. **引导订阅时机**
   - 创建意图后
   - 查看匹配结果前
   - 重要操作完成后

2. **推送内容优化**
   - 简洁明了的文案
   - 突出关键信息（匹配度、联系人）
   - 提供清晰的行动指引

3. **用户体验**
   - 不要频繁请求订阅
   - 说明订阅的价值
   - 提供订阅管理入口

---

**部署时间**：15-20分钟
**最后更新**：2025-01-18
**技术支持**：查看 `integrate_miniprogram_push.py` 获取详细集成说明