#!/usr/bin/env python3
"""
初始化测试数据
创建测试用的意图和联系人数据
"""

import sqlite3
import json
from datetime import datetime

def init_test_data():
    """初始化测试数据"""
    
    print("="*60)
    print("🔧 初始化测试数据")
    print("="*60)
    
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    # 1. 创建必要的表
    print("\n1. 创建数据库表...")
    
    # 创建用户意图表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_intents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            type TEXT,
            conditions TEXT,
            embedding BLOB,
            threshold REAL DEFAULT 0.7,
            priority INTEGER DEFAULT 5,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建意图匹配表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intent_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intent_id INTEGER NOT NULL,
            profile_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            match_score REAL,
            score_details TEXT,
            matched_conditions TEXT,
            explanation TEXT,
            match_type TEXT DEFAULT 'rule',
            extended_info TEXT,
            is_pushed BOOLEAN DEFAULT 0,
            pushed_at TIMESTAMP,
            push_channel TEXT,
            user_feedback TEXT,
            feedback_at TIMESTAMP,
            feedback_note TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            vector_similarity REAL,
            FOREIGN KEY (intent_id) REFERENCES user_intents(id)
        )
    """)
    
    # 创建测试用户的联系人表
    test_user = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"  # 使用指定的用户ID
    # 清理用户ID中的特殊字符作为表名
    clean_user = ''.join(c if c.isalnum() or c == '_' else '_' for c in test_user)
    user_table = f"profiles_{clean_user}"
    
    # 检查表是否存在以及结构是否正确
    cursor.execute(f"PRAGMA table_info({user_table})")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns] if columns else []
    
    # 必需的字段列表
    required_fields = [
        'profile_name', 'gender', 'age', 'phone', 'location', 
        'marital_status', 'education', 'company', 'position', 
        'asset_level', 'personality', 'tags', 'basic_info', 
        'recent_activities', 'raw_messages'
    ]
    
    # 检查是否所有必需字段都存在
    missing_fields = [field for field in required_fields if field not in column_names]
    
    if missing_fields or not columns:
        print(f"⚠️ 表结构不完整或不存在，重新创建表...")
        print(f"   缺少字段: {missing_fields}")
        
        # 删除旧表并创建新表
        cursor.execute(f"DROP TABLE IF EXISTS {user_table}")
        
        cursor.execute(f"""
            CREATE TABLE {user_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_name TEXT NOT NULL,
                gender TEXT,
                age TEXT,
                phone TEXT,
                location TEXT,
                marital_status TEXT,
                education TEXT,
                company TEXT,
                position TEXT,
                asset_level TEXT,
                personality TEXT,
                tags TEXT,
                basic_info TEXT,
                recent_activities TEXT,
                raw_messages TEXT,
                embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print(f"✅ 表 {user_table} 已重新创建")
    else:
        print(f"✅ 表 {user_table} 结构完整")
    
    print("✅ 数据库表创建完成")
    
    # 2. 插入测试意图
    print("\n2. 创建测试意图...")
    
    test_intents = [
        {
            'user_id': test_user,
            'name': '寻找Python开发工程师',
            'description': '需要一位有3年以上经验的Python开发工程师，熟悉Django或Flask框架，有AI项目经验更佳。不要刚毕业的新人。',
            'type': 'recruitment',
            'conditions': json.dumps({
                'required': [
                    {'field': 'skills', 'operator': 'contains', 'value': 'Python'},
                    {'field': 'experience', 'operator': '>=', 'value': 3}
                ],
                'preferred': [
                    {'field': 'skills', 'operator': 'contains_any', 'value': ['Django', 'Flask']},
                    {'field': 'projects', 'operator': 'contains', 'value': 'AI'}
                ],
                'keywords': ['Python', 'Django', 'Flask', 'AI', '人工智能', '开发', '工程师']
            }, ensure_ascii=False),
            'threshold': 0.6,
            'priority': 8
        },
        {
            'user_id': test_user,
            'name': '创业合伙人',
            'description': '寻找志同道合的创业伙伴，最好有创业经验，能承受压力，有技术背景优先。地点在上海。',
            'type': 'business',
            'conditions': json.dumps({
                'required': [
                    {'field': 'location', 'operator': 'equals', 'value': '上海'}
                ],
                'preferred': [
                    {'field': 'experience', 'operator': 'contains', 'value': '创业'},
                    {'field': 'background', 'operator': 'contains', 'value': '技术'}
                ],
                'keywords': ['创业', '合伙人', '上海', '技术', '创始人']
            }, ensure_ascii=False),
            'threshold': 0.5,
            'priority': 9
        },
        {
            'user_id': test_user,
            'name': '技术顾问',
            'description': '需要技术顾问，要有大厂经验，能提供架构设计建议，最好是从BAT出来的。',
            'type': 'consultation',
            'conditions': json.dumps({
                'keywords': ['技术', '顾问', '架构', 'BAT', '大厂', '阿里', '腾讯', '百度']
            }, ensure_ascii=False),
            'threshold': 0.6,
            'priority': 7
        }
    ]
    
    for intent in test_intents:
        cursor.execute("""
            INSERT OR REPLACE INTO user_intents 
            (user_id, name, description, type, conditions, threshold, priority, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        """, (
            intent['user_id'],
            intent['name'],
            intent['description'],
            intent['type'],
            intent['conditions'],
            intent['threshold'],
            intent['priority']
        ))
    
    print(f"✅ 创建了 {len(test_intents)} 个测试意图")
    
    # 3. 插入测试联系人
    print("\n3. 创建测试联系人...")
    
    test_profiles = [
        {
            'profile_name': '张三',
            'gender': '男',
            'age': '28',
            'phone': '13800138001',
            'location': '上海',
            'marital_status': '未婚',
            'education': '硕士',
            'company': '某AI创业公司',
            'position': 'Python高级工程师',
            'asset_level': '中',
            'personality': '技术型，专注',
            'tags': json.dumps(['Python开发', 'AI工程师', '5年经验', 'Django专家'], ensure_ascii=False),
            'basic_info': json.dumps({
                '性别': '男',
                '年龄': 28,
                '所在地': '上海',
                '学历': '硕士',
                '公司': '某AI创业公司',
                '职位': 'Python高级工程师',
                '技能': ['Python', 'Django', 'Flask', 'AI', '机器学习'],
                '经验': 5,
                '项目': 'AI相关项目多个'
            }, ensure_ascii=False),
            'recent_activities': json.dumps([
                '分享了Django项目经验',
                '参与AI模型训练项目',
                '正在学习深度学习'
            ], ensure_ascii=False)
        },
        {
            'profile_name': '李四',
            'gender': '男',
            'age': '35',
            'phone': '13900139002',
            'location': '上海',
            'marital_status': '已婚',
            'education': '本科',
            'company': '自己创业',
            'position': 'CEO',
            'asset_level': '高',
            'personality': '进取型，有冒险精神',
            'tags': json.dumps(['创业者', '技术背景', '连续创业', '上海'], ensure_ascii=False),
            'basic_info': json.dumps({
                '性别': '男',
                '年龄': 35,
                '所在地': '上海',
                '学历': '本科',
                '公司': '自己创业',
                '职位': 'CEO',
                '背景': '技术',
                '经验': '连续创业3次'
            }, ensure_ascii=False),
            'recent_activities': json.dumps([
                '分享创业心得',
                '寻找技术合伙人',
                '参加创业活动'
            ], ensure_ascii=False)
        },
        {
            'profile_name': '王五',
            'gender': '男',
            'age': '24',
            'phone': '13700137003',
            'location': '北京',
            'marital_status': '未婚',
            'education': '本科',
            'company': '某互联网公司',
            'position': 'Java初级工程师',
            'asset_level': '低',
            'personality': '学习型，积极',
            'tags': json.dumps(['Java开发', '2年经验', '应届生'], ensure_ascii=False),
            'basic_info': json.dumps({
                '性别': '男',
                '年龄': 24,
                '所在地': '北京',
                '学历': '本科',
                '公司': '某互联网公司',
                '职位': 'Java初级工程师',
                '技能': ['Java', 'Spring'],
                '经验': 2
            }, ensure_ascii=False),
            'recent_activities': json.dumps([
                '学习Spring框架',
                '准备跳槽'
            ], ensure_ascii=False)
        },
        {
            'profile_name': '赵六',
            'gender': '女',
            'age': '33',
            'phone': '13600136004',
            'location': '杭州',
            'marital_status': '已婚',
            'education': '硕士',
            'company': '前阿里巴巴',
            'position': '技术架构师',
            'asset_level': '高',
            'personality': '专业型，经验丰富',
            'tags': json.dumps(['架构师', '阿里P8', '10年经验', '技术顾问'], ensure_ascii=False),
            'basic_info': json.dumps({
                '性别': '女',
                '年龄': 33,
                '所在地': '杭州',
                '学历': '硕士',
                '公司': '前阿里巴巴',
                '职位': '技术架构师',
                '级别': 'P8',
                '经验': 10,
                '专长': '系统架构设计'
            }, ensure_ascii=False),
            'recent_activities': json.dumps([
                '分享架构设计经验',
                '提供技术咨询',
                '写技术博客'
            ], ensure_ascii=False)
        },
        {
            'profile_name': '钱七',
            'gender': '女',
            'age': '23',
            'phone': '13500135005',
            'location': '深圳',
            'marital_status': '未婚',
            'education': '本科',
            'company': '小公司',
            'position': 'Python实习生',
            'asset_level': '低',
            'personality': '学习型，有潜力',
            'tags': json.dumps(['Python初学者', '1年经验', 'Flask'], ensure_ascii=False),
            'basic_info': json.dumps({
                '性别': '女',
                '年龄': 23,
                '所在地': '深圳',
                '学历': '本科',
                '公司': '小公司',
                '职位': 'Python实习生',
                '技能': ['Python', 'Flask'],
                '经验': 1
            }, ensure_ascii=False),
            'recent_activities': json.dumps([
                '学习Flask框架',
                '做个人项目'
            ], ensure_ascii=False)
        }
    ]
    
    for profile in test_profiles:
        cursor.execute(f"""
            INSERT OR REPLACE INTO {user_table}
            (profile_name, gender, age, phone, location, marital_status, 
             education, company, position, asset_level, personality,
             tags, basic_info, recent_activities)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile['profile_name'],
            profile['gender'],
            profile['age'],
            profile['phone'],
            profile['location'],
            profile['marital_status'],
            profile['education'],
            profile['company'],
            profile['position'],
            profile['asset_level'],
            profile['personality'],
            profile['tags'],
            profile['basic_info'],
            profile['recent_activities']
        ))
    
    print(f"✅ 创建了 {len(test_profiles)} 个测试联系人")
    
    # 提交并关闭
    conn.commit()
    
    # 4. 显示创建的数据
    print("\n4. 验证数据...")
    
    # 显示意图
    cursor.execute("SELECT id, name, type FROM user_intents WHERE user_id = ?", (test_user,))
    intents = cursor.fetchall()
    print("\n创建的意图:")
    for intent in intents:
        print(f"  ID={intent[0]}: {intent[1]} ({intent[2]})")
    
    # 显示联系人
    cursor.execute(f"SELECT id, profile_name FROM {user_table}")
    profiles = cursor.fetchall()
    print("\n创建的联系人:")
    for profile in profiles:
        print(f"  ID={profile[0]}: {profile[1]}")
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ 测试数据初始化完成！")
    print("\n现在可以运行测试脚本了:")
    print("  python test_integrated_system.py")
    print("  python test_llm_intent_integration.py")
    print("  python test_hybrid_matching.py")

if __name__ == "__main__":
    init_test_data()