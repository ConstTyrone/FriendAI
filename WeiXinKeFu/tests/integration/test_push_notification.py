#!/usr/bin/env python
"""
测试微信客服推送通知功能
"""
import sys
import os
import json
import sqlite3
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_test_environment():
    """设置测试环境"""
    print("=" * 80)
    print("微信客服推送通知测试")
    print("=" * 80)
    
    # 1. 运行数据库初始化
    print("\n1. 初始化数据库字段...")
    from scripts.add_push_fields import add_push_fields
    add_push_fields()
    
    print("\n✅ 数据库准备完成")
    return True

def test_push_service():
    """测试推送服务功能"""
    from src.services.push_service_enhanced import enhanced_push_service
    
    print("\n" + "=" * 80)
    print("测试推送服务功能")
    print("=" * 80)
    
    # 测试用户ID
    test_user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    # 1. 测试会话更新
    print("\n1. 测试会话信息更新...")
    try:
        # 注意：实际使用时需要从微信消息中获取真实的open_kfid
        # 这里使用模拟值进行测试
        enhanced_push_service.update_user_session(
            user_id=test_user_id,
            external_userid=test_user_id,
            open_kfid="wkAJ2GCAAASSxxxxxxxxxxx"  # 需要替换为实际的客服账号ID
        )
        print("   ✅ 会话信息更新成功")
    except Exception as e:
        print(f"   ❌ 会话信息更新失败: {e}")
        return False
    
    # 2. 测试会话获取
    print("\n2. 测试会话信息获取...")
    session_info = enhanced_push_service.get_user_session(test_user_id)
    if session_info:
        print(f"   ✅ 获取会话信息: external_userid={session_info[0]}, open_kfid={session_info[1]}")
    else:
        print("   ⚠️ 未找到会话信息")
    
    # 3. 测试推送资格检查
    print("\n3. 测试推送资格检查...")
    can_push, reason = enhanced_push_service.check_push_eligibility_enhanced(test_user_id, 1)
    print(f"   推送资格: {'✅ 可以推送' if can_push else '❌ 不可推送'}")
    print(f"   原因: {reason}")
    
    # 4. 测试消息格式化
    print("\n4. 测试消息格式化...")
    match_data = {
        'profile_id': 1,
        'profile_name': '张三',
        'intent_id': 1,
        'intent_name': '寻找AI技术合作伙伴',
        'score': 0.85,
        'explanation': '具有AI背景，在北京，有创业经验',
        'matched_conditions': ['AI经验', '北京', '创业者']
    }
    
    message = enhanced_push_service.format_push_message(match_data)
    print("   格式化后的消息：")
    print("   " + "-" * 40)
    print(message)
    print("   " + "-" * 40)
    
    return True

def test_real_push():
    """测试真实推送（需要有效的微信会话）"""
    from src.services.push_service_enhanced import enhanced_push_service
    
    print("\n" + "=" * 80)
    print("测试真实推送功能")
    print("=" * 80)
    
    # 测试用户ID
    test_user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    # 检查是否有有效会话
    session_info = enhanced_push_service.get_user_session(test_user_id)
    if not session_info:
        print("❌ 没有有效会话，请先通过微信发送消息建立会话")
        print("\n提示：")
        print("1. 用户需要先在微信中发送消息给客服账号")
        print("2. 系统会自动记录会话信息")
        print("3. 48小时内可以发送推送消息")
        return False
    
    print(f"✅ 找到有效会话: {session_info}")
    
    # 准备测试数据
    match_data = {
        'profile_id': 1,
        'profile_name': '测试联系人',
        'intent_id': 1,
        'intent_name': '测试意图',
        'score': 0.90,
        'explanation': '这是一条测试推送消息',
        'matched_conditions': ['条件1', '条件2'],
        'match_id': 1
    }
    
    # 询问是否发送
    print("\n准备发送推送消息...")
    print("消息内容：")
    print("-" * 40)
    message = enhanced_push_service.format_push_message(match_data)
    print(message)
    print("-" * 40)
    
    response = input("\n是否发送这条测试消息？(y/n): ")
    if response.lower() != 'y':
        print("取消发送")
        return False
    
    # 发送推送
    print("\n发送推送...")
    success = enhanced_push_service.process_match_for_push(match_data, test_user_id)
    
    if success:
        print("✅ 推送发送成功！")
        print("请检查微信客服消息")
    else:
        print("❌ 推送发送失败")
    
    return success

def check_push_status():
    """检查推送状态"""
    print("\n" + "=" * 80)
    print("检查推送状态")
    print("=" * 80)
    
    try:
        conn = sqlite3.connect("user_profiles.db")
        cursor = conn.cursor()
        
        # 检查会话表
        print("\n1. 微信客服会话状态：")
        cursor.execute("""
            SELECT user_id, open_kfid, last_message_time, message_count_48h
            FROM wechat_kf_sessions
            ORDER BY updated_at DESC
            LIMIT 5
        """)
        
        sessions = cursor.fetchall()
        if sessions:
            print(f"   找到 {len(sessions)} 个会话：")
            for session in sessions:
                print(f"   - 用户: {session[0][:20]}...")
                print(f"     客服ID: {session[1]}")
                print(f"     最后消息: {session[2]}")
                print(f"     48h推送数: {session[3]}")
        else:
            print("   暂无会话记录")
        
        # 检查推送偏好
        print("\n2. 用户推送偏好：")
        cursor.execute("""
            SELECT user_id, enable_push, quiet_hours, push_count_48h
            FROM user_push_preferences
            WHERE open_kfid IS NOT NULL
            LIMIT 5
        """)
        
        prefs = cursor.fetchall()
        if prefs:
            print(f"   找到 {len(prefs)} 个用户偏好：")
            for pref in prefs:
                print(f"   - 用户: {pref[0][:20]}...")
                print(f"     推送开关: {'开' if pref[1] else '关'}")
                print(f"     静默时间: {pref[2] or '无'}")
                print(f"     48h推送数: {pref[3]}")
        else:
            print("   暂无推送偏好设置")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 检查状态失败: {e}")

def main():
    """主测试流程"""
    print("🚀 开始测试微信客服推送通知功能")
    print("=" * 80)
    
    # 设置测试环境
    if not setup_test_environment():
        print("❌ 环境设置失败")
        return
    
    # 测试推送服务
    if not test_push_service():
        print("❌ 推送服务测试失败")
        return
    
    # 检查推送状态
    check_push_status()
    
    # 询问是否进行真实推送测试
    print("\n" + "=" * 80)
    response = input("是否进行真实推送测试？(需要有效的微信会话) (y/n): ")
    if response.lower() == 'y':
        test_real_push()
    
    print("\n✅ 测试完成！")
    print("\n下一步：")
    print("1. 运行 python scripts/integrate_push_handler.py 查看集成指南")
    print("2. 按照指南更新 message_handler.py 和 intent_matcher.py")
    print("3. 重启服务并通过微信发送消息测试")

if __name__ == "__main__":
    main()