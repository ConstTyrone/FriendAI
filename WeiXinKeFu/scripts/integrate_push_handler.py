#!/usr/bin/env python
"""
集成推送功能到消息处理器的补丁脚本
显示需要在message_handler.py中添加的代码
"""

def show_integration_code():
    """显示需要集成的代码"""
    
    print("=" * 80)
    print("推送功能集成指南")
    print("=" * 80)
    
    print("\n📌 步骤1: 在message_handler.py顶部添加导入")
    print("-" * 40)
    print("""
# 在文件顶部的导入部分添加：
from ..services.push_service_enhanced import enhanced_push_service
""")
    
    print("\n📌 步骤2: 在handle_wechat_kf_event函数中添加会话记录")
    print("-" * 40)
    print("""
# 在获取到external_userid和open_kfid后（约第340行），添加：

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
""")
    
    print("\n📌 步骤3: 在intent_matcher.py中集成推送调用")
    print("-" * 40)
    print("""
# 在match_intent_with_profiles函数的匹配成功后（约第500行），添加：

# 触发推送通知
if match_score >= threshold:
    try:
        from ..services.push_service_enhanced import enhanced_push_service
        
        # 准备推送数据
        push_data = {
            'profile_id': profile[0],
            'profile_name': profile[1],
            'intent_id': intent_id,
            'intent_name': intent_row[1],  # intent name
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
""")
    
    print("\n📌 步骤4: 测试推送功能")
    print("-" * 40)
    print("""
# 创建测试脚本 test_push_notification.py：

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.push_service_enhanced import enhanced_push_service

# 测试用户ID（使用你的测试用户）
test_user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"

# 模拟会话信息（需要先通过微信发送消息建立会话）
enhanced_push_service.update_user_session(
    user_id=test_user_id,
    external_userid=test_user_id,
    open_kfid="wkxxxxxxxxxx"  # 替换为实际的客服账号ID
)

# 模拟匹配数据
match_data = {
    'profile_id': 1,
    'profile_name': '张三',
    'intent_id': 1,
    'intent_name': '寻找技术合作伙伴',
    'score': 0.85,
    'explanation': '技术背景匹配，有AI经验',
    'matched_conditions': ['AI经验', '北京', '创业者'],
    'match_id': 1
}

# 测试推送
success = enhanced_push_service.process_match_for_push(match_data, test_user_id)
print(f"推送结果: {'成功' if success else '失败'}")
""")
    
    print("\n📌 步骤5: 配置推送偏好")
    print("-" * 40)
    print("""
# 在数据库中配置用户推送偏好：

UPDATE user_push_preferences
SET 
    enable_push = 1,
    quiet_hours = '22:00-08:00',  -- 静默时间
    daily_limit = 10,
    min_score = 0.7
WHERE user_id = 'YOUR_USER_ID';
""")
    
    print("\n📌 步骤6: 监控推送状态")
    print("-" * 40)
    print("""
# 查看推送历史：

SELECT * FROM push_history_YOUR_USER_ID 
ORDER BY created_at DESC 
LIMIT 10;

# 查看会话状态：

SELECT * FROM wechat_kf_sessions
WHERE user_id = 'YOUR_USER_ID';
""")
    
    print("\n" + "=" * 80)
    print("✅ 集成完成后的功能流程：")
    print("=" * 80)
    print("""
1. 用户发送消息 → 记录/更新会话信息
2. 创建意图 → 自动匹配联系人
3. 匹配成功 → 检查推送资格
4. 符合条件 → 发送微信客服消息
5. 用户收到推送 → 可直接查看匹配详情
""")
    
    print("\n⚠️ 注意事项：")
    print("-" * 40)
    print("""
1. 必须先让用户发送消息建立会话（48小时内有效）
2. 48小时内最多发送5条消息（微信限制）
3. 需要正确配置客服账号ID（open_kfid）
4. 建议在静默时间外测试推送功能
5. 推送失败不会影响匹配功能的正常运行
""")

if __name__ == "__main__":
    show_integration_code()