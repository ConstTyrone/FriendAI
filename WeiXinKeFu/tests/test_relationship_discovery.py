#!/usr/bin/env python3
"""
测试关系发现系统
"""

import os
import sys
import json
import time
import logging
from datetime import datetime

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.database_sqlite_v2 import SQLiteDatabase
from src.services.relationship_service import RelationshipService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_relationship_discovery():
    """测试关系发现功能"""
    logger.info("开始测试关系发现系统...")
    
    # 初始化数据库和服务
    db = SQLiteDatabase()
    relationship_service = RelationshipService(db)
    
    # 测试用户ID
    test_user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    # 创建测试数据
    test_profiles = [
        {
            "profile_name": "张三",
            "company": "腾讯科技",
            "position": "产品经理",
            "location": "深圳",
            "education": "清华大学"
        },
        {
            "profile_name": "李四",
            "company": "腾讯",
            "position": "技术总监",
            "location": "深圳",
            "education": "北京大学"
        },
        {
            "profile_name": "王五",
            "company": "阿里巴巴",
            "position": "运营经理",
            "location": "杭州",
            "education": "清华大学"
        },
        {
            "profile_name": "赵六",
            "company": "腾讯科技有限公司",
            "position": "设计师",
            "location": "深圳",
            "education": "中央美院"
        }
    ]
    
    # 用户表会在save_user_profile时自动创建
    # 无需手动创建
    
    # 插入测试联系人
    profile_ids = []
    for profile_data in test_profiles:
        # 准备AI响应数据（模拟）
        ai_response = {
            "summary": f"测试联系人：{profile_data['profile_name']}",
            "user_profiles": [profile_data]
        }
        
        # 保存到数据库
        profile_id = db.save_user_profile(
            wechat_user_id=test_user_id,
            profile_data=profile_data,
            raw_message=f"测试数据：{profile_data['profile_name']}",
            message_type="test_create",
            ai_response=ai_response
        )
        
        if profile_id:
            profile_ids.append(profile_id)
            logger.info(f"✅ 创建测试联系人: {profile_data['profile_name']} (ID: {profile_id})")
    
    # 测试关系发现
    logger.info("\n开始测试关系发现...")
    
    # 为最后一个联系人（赵六）发现关系
    if profile_ids:
        last_profile_id = profile_ids[-1]
        last_profile = test_profiles[-1]
        last_profile['id'] = last_profile_id
        
        logger.info(f"\n为 {last_profile['profile_name']} 发现关系...")
        
        discovered_relationships = relationship_service.discover_relationships_for_profile(
            user_id=test_user_id,
            profile_id=last_profile_id,
            profile_data=last_profile
        )
        
        if discovered_relationships:
            logger.info(f"✅ 发现了 {len(discovered_relationships)} 个关系：")
            for rel in discovered_relationships:
                logger.info(f"  - {rel['source_profile_name']} 和 {rel['target_profile_name']}: "
                          f"{rel['relationship_type']} (置信度: {rel['confidence_score']:.2f})")
                logger.info(f"    证据: {rel.get('evidence', {})}")
        else:
            logger.info("❌ 未发现任何关系")
    
    # 测试获取关系
    logger.info("\n测试获取联系人关系...")
    if profile_ids and len(profile_ids) > 0:
        first_profile_id = profile_ids[0]
        relationships = relationship_service.get_profile_relationships(
            user_id=test_user_id,
            profile_id=first_profile_id
        )
        
        if relationships:
            logger.info(f"✅ {test_profiles[0]['profile_name']} 的关系数量: {len(relationships)}")
            for rel in relationships:
                logger.info(f"  - 关系类型: {rel['relationship_type']}, "
                          f"置信度: {rel['confidence_score']:.2f}, "
                          f"状态: {rel['status']}")
        else:
            logger.info(f"❌ {test_profiles[0]['profile_name']} 没有关系")
    
    # 测试关系统计
    logger.info("\n测试关系统计...")
    stats = relationship_service.get_relationship_stats(test_user_id)
    logger.info(f"✅ 关系统计:")
    logger.info(f"  - 总关系数: {stats['total_relationships']}")
    logger.info(f"  - 已确认: {stats['confirmed_relationships']}")
    logger.info(f"  - 待确认: {stats['discovered_relationships']}")
    logger.info(f"  - 按类型: {stats['relationships_by_type']}")
    
    # 测试确认关系
    logger.info("\n测试确认关系...")
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM relationships 
            WHERE user_id = ? 
            LIMIT 1
        """, (test_user_id,))
        
        rel_row = cursor.fetchone()
        if rel_row:
            rel_id = rel_row[0]
            success = relationship_service.confirm_relationship(
                user_id=test_user_id,
                relationship_id=rel_id,
                confirmed=True
            )
            
            if success:
                logger.info(f"✅ 成功确认关系 ID: {rel_id}")
            else:
                logger.info(f"❌ 确认关系失败 ID: {rel_id}")
    
    logger.info("\n✅ 关系发现系统测试完成！")

def cleanup_test_data():
    """清理测试数据"""
    logger.info("\n清理测试数据...")
    db = SQLiteDatabase()
    test_user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 删除测试关系
            cursor.execute("DELETE FROM relationships WHERE user_id = ?", (test_user_id,))
            logger.info(f"删除了 {cursor.rowcount} 个测试关系")
            
            # 删除测试日志
            cursor.execute("DELETE FROM relationship_discovery_logs WHERE user_id = ?", (test_user_id,))
            logger.info(f"删除了 {cursor.rowcount} 条发现日志")
            
            conn.commit()
            logger.info("✅ 测试数据清理完成")
            
    except Exception as e:
        logger.error(f"清理测试数据失败: {e}")

if __name__ == "__main__":
    try:
        # 运行测试
        test_relationship_discovery()
        
        # 询问是否清理数据
        response = input("\n是否清理测试数据？(y/n): ")
        if response.lower() == 'y':
            cleanup_test_data()
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()