#!/usr/bin/env python
"""
快速设置推送通知功能
一键完成数据库初始化和配置
"""
import os
import sys
import sqlite3
from datetime import datetime

# 添加项目根目录
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def quick_setup():
    """快速设置推送功能"""
    print("=" * 80)
    print("🚀 FriendAI 推送通知快速设置")
    print("=" * 80)
    
    # 1. 初始化数据库
    print("\n📦 步骤1: 初始化数据库...")
    try:
        from scripts.add_push_fields import add_push_fields
        add_push_fields()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False
    
    # 2. 显示需要手动更新的文件
    print("\n📝 步骤2: 需要手动更新的文件")
    print("-" * 40)
    
    print("\n1️⃣ 更新 src/handlers/message_handler.py")
    print("   在文件顶部添加:")
    print("   from ..services.push_service_enhanced import enhanced_push_service")
    print("\n   在handle_wechat_kf_event函数中（约340行）添加:")
    print("""
    # 记录用户会话信息
    enhanced_push_service.reset_48h_counter(external_userid)
    enhanced_push_service.update_user_session(
        user_id=external_userid,
        external_userid=external_userid,
        open_kfid=open_kfid
    )
    """)
    
    print("\n2️⃣ 更新 src/services/intent_matcher.py")
    print("   在match_intent_with_profiles函数的匹配成功后添加:")
    print("""
    # 触发推送
    from ..services.push_service_enhanced import enhanced_push_service
    push_data = {
        'profile_id': profile[0],
        'profile_name': profile[1],
        'intent_id': intent_id,
        'intent_name': intent_name,
        'score': match_score,
        'explanation': explanation,
        'match_id': match_id
    }
    enhanced_push_service.process_match_for_push(push_data, user_id)
    """)
    
    # 3. 创建示例配置
    print("\n⚙️ 步骤3: 创建示例配置...")
    try:
        conn = sqlite3.connect("user_profiles.db")
        cursor = conn.cursor()
        
        # 插入示例推送模板
        cursor.execute("""
            INSERT OR REPLACE INTO push_templates (
                template_name, template_type, content_template
            ) VALUES 
            ('default', 'text', 
             '🎯 新匹配提醒\\n\\n{profile_name} 符合您的意图【{intent_name}】\\n匹配度：{score}%\\n\\n{explanation}'),
            ('simple', 'text',
             '发现新匹配：{profile_name}（{score}%）')
        """)
        
        conn.commit()
        conn.close()
        print("✅ 示例配置创建完成")
    except Exception as e:
        print(f"⚠️ 创建示例配置失败: {e}")
    
    # 4. 显示测试命令
    print("\n🧪 步骤4: 测试推送功能")
    print("-" * 40)
    print("运行以下命令测试:")
    print("  python test_push_notification.py")
    
    print("\n✅ 快速设置完成！")
    print("\n下一步操作：")
    print("1. 手动更新上述两个文件")
    print("2. 重启后端服务: python run.py")
    print("3. 通过微信发送消息建立会话")
    print("4. 创建意图触发匹配，测试推送")
    
    return True

def check_integration_status():
    """检查集成状态"""
    print("\n" + "=" * 80)
    print("📊 检查集成状态")
    print("=" * 80)
    
    status = {
        "database": False,
        "push_service": False,
        "message_handler": False,
        "intent_matcher": False
    }
    
    # 检查数据库
    try:
        conn = sqlite3.connect("user_profiles.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wechat_kf_sessions'")
        if cursor.fetchone():
            status["database"] = True
        conn.close()
    except:
        pass
    
    # 检查推送服务文件
    if os.path.exists("src/services/push_service_enhanced.py"):
        status["push_service"] = True
    
    # 检查集成状态（需要手动确认）
    print("\n状态检查结果：")
    print(f"  ✅ 数据库准备: {'完成' if status['database'] else '未完成'}")
    print(f"  ✅ 推送服务: {'已创建' if status['push_service'] else '未创建'}")
    print(f"  ⚠️ 消息处理器集成: 需要手动确认")
    print(f"  ⚠️ 意图匹配器集成: 需要手动确认")
    
    return all(status.values())

if __name__ == "__main__":
    print("🎯 FriendAI 微信客服推送通知 - 快速设置工具")
    print("=" * 80)
    
    # 运行快速设置
    if quick_setup():
        # 检查状态
        check_integration_status()
        
        print("\n" + "=" * 80)
        print("🎉 设置完成！请按照提示完成手动步骤。")
        print("=" * 80)
    else:
        print("\n❌ 设置失败，请检查错误信息")