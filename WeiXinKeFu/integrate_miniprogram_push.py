#!/usr/bin/env python
"""
集成微信小程序推送通知
在意图匹配成功时发送小程序订阅消息
"""

import os
import sys

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def show_integration_guide():
    """显示集成指南"""
    
    print("=" * 80)
    print("🔔 微信小程序订阅消息推送集成指南")
    print("=" * 80)
    
    print("\n📱 步骤1: 在微信公众平台配置订阅消息模板")
    print("-" * 40)
    print("""
1. 登录微信公众平台 (mp.weixin.qq.com)
2. 进入小程序后台 → 功能 → 订阅消息
3. 选择合适的模板，建议使用：
   - 模板标题：匹配结果通知
   - 关键词：
     * 匹配对象 (thing)
     * 意图名称 (thing)
     * 匹配度 (number)
     * 匹配时间 (time)
4. 记录模板ID (格式如: F3bKrBfKLz_xxxxxxxxxxx)
""")
    
    print("\n⚙️ 步骤2: 配置环境变量")
    print("-" * 40)
    print("""
在 .env 文件中添加：

# 微信小程序配置
WECHAT_MINI_APPID=wx50fc05960f4152a6
WECHAT_MINI_SECRET=你的小程序密钥
WECHAT_TEMPLATE_ID=你的模板ID
""")
    
    print("\n📝 步骤3: 修改 src/services/intent_matcher.py")
    print("-" * 40)
    print("""
在文件顶部添加导入：
```python
from ..services.miniprogram_push_service import miniprogram_push_service
```

在 match_intent_with_profiles 函数的匹配成功后（约第500行）添加：
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
            'match_id': cursor.lastrowid  # 刚插入的匹配记录ID
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
""")
    
    print("\n📱 步骤4: 修改小程序前端")
    print("-" * 40)
    print("""
1. 更新 pages/intent-manager/subscribe.js 中的模板ID：
   ```javascript
   const TEMPLATE_ID = '你的模板ID';
   ```

2. 在意图管理页面添加订阅按钮：
   ```javascript
   // pages/intent-manager/intent-manager.js
   const subscribe = require('./subscribe');
   
   // 添加订阅方法
   onSubscribeNotification() {
     subscribe.requestSubscription().then(result => {
       if (result) {
         wx.showToast({
           title: '订阅成功',
           icon: 'success'
         });
       }
     });
   }
   ```

3. 在页面WXML中添加按钮：
   ```xml
   <button bindtap="onSubscribeNotification" type="primary">
     开启匹配通知
   </button>
   ```
""")
    
    print("\n🔌 步骤5: 注册API路由")
    print("-" * 40)
    print("""
在 src/core/main.py 中添加：
```python
# 导入订阅API
from .subscription_api import router as subscription_router

# 注册路由
app.include_router(subscription_router)
```
""")
    
    print("\n✅ 步骤6: 测试推送功能")
    print("-" * 40)
    print("""
运行测试脚本：
```bash
python test_miniprogram_push.py
```
""")
    
    print("\n" + "=" * 80)
    print("📋 完整流程")
    print("=" * 80)
    print("""
1. 用户在小程序中点击"开启匹配通知"
2. 小程序弹出订阅授权弹窗
3. 用户同意后，订阅信息保存到数据库
4. 当意图匹配成功时，后端自动发送推送
5. 用户在微信服务通知中收到消息
6. 点击通知直接进入小程序查看匹配详情
""")
    
    print("\n⚠️ 注意事项")
    print("-" * 40)
    print("""
1. 用户必须主动订阅才能收到通知
2. 一次订阅只能发送一条消息（需要用户多次订阅）
3. 模板消息有字段长度限制（thing类型最多20字符）
4. 开发版和体验版也可以测试推送
5. 推送失败不会影响匹配功能的正常运行
""")

if __name__ == "__main__":
    show_integration_guide()