#!/usr/bin/env python3
"""
测试关系API的实际返回数据结构
"""

import requests
import json
import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.database_sqlite_v2 import SQLiteDatabase

def test_relationship_api():
    """测试关系API"""
    
    # 服务器配置
    BASE_URL = "http://localhost:8000"  # 根据实际端口调整
    TEST_USER_ID = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    print("=== 关系API测试开始 ===")
    
    # 1. 先获取用户的联系人列表
    print("\n1. 获取联系人列表...")
    
    try:
        # 生成测试token (简单的Base64编码)
        import base64
        token = base64.b64encode(TEST_USER_ID.encode()).decode()
        headers = {'Authorization': f'Bearer {token}'}
        
        # 获取联系人
        response = requests.get(f"{BASE_URL}/api/profiles", headers=headers)
        print(f"联系人API状态码: {response.status_code}")
        
        if response.status_code == 200:
            profiles_data = response.json()
            print(f"联系人数量: {len(profiles_data.get('profiles', []))}")
            
            if profiles_data.get('profiles'):
                # 使用第一个联系人进行关系测试
                test_profile_id = profiles_data['profiles'][0]['id']
                test_profile_name = profiles_data['profiles'][0]['profile_name']
                print(f"测试联系人: {test_profile_name} (ID: {test_profile_id})")
                
                # 2. 获取关系数据
                print(f"\n2. 获取联系人 {test_profile_name} 的关系...")
                rel_response = requests.get(f"{BASE_URL}/api/relationships/{test_profile_id}", headers=headers)
                print(f"关系API状态码: {rel_response.status_code}")
                
                if rel_response.status_code == 200:
                    rel_data = rel_response.json()
                    print(f"API返回结构: {list(rel_data.keys())}")
                    print(f"关系数量: {rel_data.get('total', 0)}")
                    
                    if rel_data.get('relationships'):
                        print(f"\n--- 第一个关系记录详细信息 ---")
                        first_rel = rel_data['relationships'][0]
                        print(json.dumps(first_rel, indent=2, ensure_ascii=False))
                        
                        # 重点检查confidence_score字段
                        confidence = first_rel.get('confidence_score')
                        print(f"\n⭐ confidence_score 字段:")
                        print(f"  - 原始值: {confidence} (类型: {type(confidence)})")
                        print(f"  - 乘以100: {(confidence or 0) * 100}")
                        print(f"  - 前端格式化结果: {round((confidence or 0) * 100)}")
                        
                    else:
                        print("❌ 没有关系数据")
                        
                        # 3. 尝试直接查询数据库
                        print("\n3. 直接查询数据库...")
                        check_database(TEST_USER_ID, test_profile_id)
                else:
                    print(f"❌ 关系API失败: {rel_response.text}")
            else:
                print("❌ 没有联系人数据")
        else:
            print(f"❌ 联系人API失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        
        # 如果API失败，直接查询数据库
        print("\n尝试直接查询数据库...")
        check_database(TEST_USER_ID, None)

def check_database(user_id, profile_id=None):
    """直接查询数据库"""
    try:
        db = SQLiteDatabase()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查relationships表是否存在
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='relationships'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                print("❌ relationships表不存在")
                return
                
            print("✅ relationships表存在")
            
            # 检查表结构
            cursor.execute("PRAGMA table_info(relationships)")
            columns = cursor.fetchall()
            print(f"表结构: {[col[1] for col in columns]}")
            
            # 检查是否有confidence_score字段
            has_confidence = any(col[1] == 'confidence_score' for col in columns)
            print(f"是否有confidence_score字段: {has_confidence}")
            
            # 查询数据
            cursor.execute("SELECT COUNT(*) FROM relationships WHERE user_id = ?", (user_id,))
            total_count = cursor.fetchone()[0]
            print(f"用户 {user_id} 的关系记录数量: {total_count}")
            
            if total_count > 0:
                cursor.execute("""
                    SELECT id, source_profile_id, target_profile_id, relationship_type, 
                           confidence_score, status, created_at
                    FROM relationships 
                    WHERE user_id = ? 
                    LIMIT 5
                """, (user_id,))
                
                rows = cursor.fetchall()
                print(f"\n前5条关系记录:")
                for row in rows:
                    print(f"  ID:{row[0]}, {row[1]}→{row[2]}, 类型:{row[3]}, 置信度:{row[4]}, 状态:{row[5]}")
            
            # 如果指定了profile_id，查询特定关系
            if profile_id:
                cursor.execute("""
                    SELECT * FROM relationships
                    WHERE user_id = ? AND (source_profile_id = ? OR target_profile_id = ?)
                    LIMIT 3
                """, (user_id, profile_id, profile_id))
                
                rows = cursor.fetchall()
                print(f"\n联系人 {profile_id} 相关的关系:")
                if rows:
                    for row in rows:
                        rel_dict = dict(row)
                        print(f"  置信度: {rel_dict.get('confidence_score')}")
                        print(f"  完整记录: {rel_dict}")
                else:
                    print("  没有找到相关关系")
                    
    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")

if __name__ == "__main__":
    test_relationship_api()
