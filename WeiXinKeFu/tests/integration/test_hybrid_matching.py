#!/usr/bin/env python3
"""
混合匹配系统测试脚本
测试向量匹配、LLM判断和混合策略的效果
"""

import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Dict, List
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.hybrid_matcher import init_hybrid_matcher, MatchingMode
from src.config.config import config

# 测试数据
TEST_INTENTS = [
    {
        'id': 1,
        'name': '寻找Python开发工程师',
        'description': '需要一位有3年以上经验的Python开发工程师，熟悉Django或Flask框架，有AI项目经验更佳。不要刚毕业的新人。',
        'type': 'recruitment',
        'priority': 8,
        'threshold': 0.7,
        'conditions': {
            'required': [
                {'field': 'skills', 'operator': 'contains', 'value': 'Python'},
                {'field': 'experience', 'operator': '>=', 'value': 3}
            ],
            'preferred': [
                {'field': 'skills', 'operator': 'contains_any', 'value': ['Django', 'Flask']},
                {'field': 'projects', 'operator': 'contains', 'value': 'AI'}
            ],
            'keywords': ['Python', 'Django', 'Flask', 'AI', '人工智能']
        }
    },
    {
        'id': 2,
        'name': '创业合伙人',
        'description': '寻找志同道合的创业伙伴，最好有创业经验，能承受压力，有技术背景优先。地点在上海。',
        'type': 'business',
        'priority': 9,
        'threshold': 0.6,
        'conditions': {
            'required': [
                {'field': 'location', 'operator': 'equals', 'value': '上海'}
            ],
            'preferred': [
                {'field': 'experience', 'operator': 'contains', 'value': '创业'},
                {'field': 'background', 'operator': 'contains', 'value': '技术'}
            ],
            'keywords': ['创业', '合伙人', '上海', '技术']
        }
    },
    {
        'id': 3,
        'name': '运动伙伴',
        'description': '找周末一起打羽毛球的朋友，水平中等就行，主要是锻炼身体，交朋友。',
        'type': 'social',
        'priority': 3,
        'threshold': 0.5,
        'conditions': {
            'preferred': [
                {'field': 'hobbies', 'operator': 'contains', 'value': '羽毛球'},
                {'field': 'hobbies', 'operator': 'contains', 'value': '运动'}
            ],
            'keywords': ['羽毛球', '运动', '健身']
        }
    }
]

TEST_PROFILES = [
    {
        'id': 1,
        'profile_name': '张三',
        'wechat_id': 'zhangsan123',
        'phone': '13800138001',
        'tags': ['Python开发', 'AI工程师', '5年经验'],
        'basic_info': {
            '性别': '男',
            '年龄': 28,
            '所在地': '上海',
            '学历': '硕士',
            '公司': '某AI创业公司',
            '职位': 'Python高级工程师'
        },
        'recent_activities': [
            '分享了Django项目经验',
            '参与AI模型训练项目',
            '正在学习深度学习'
        ]
    },
    {
        'id': 2,
        'profile_name': '李四',
        'wechat_id': 'lisi456',
        'phone': '13900139002',
        'tags': ['创业者', '技术背景', '连续创业'],
        'basic_info': {
            '性别': '男',
            '年龄': 35,
            '所在地': '上海',
            '学历': '本科',
            '公司': '自己创业',
            '职位': 'CEO'
        },
        'recent_activities': [
            '分享创业心得',
            '寻找技术合伙人',
            '参加创业活动'
        ]
    },
    {
        'id': 3,
        'profile_name': '王五',
        'wechat_id': 'wangwu789',
        'phone': '13700137003',
        'tags': ['Java开发', '2年经验', '应届生'],
        'basic_info': {
            '性别': '男',
            '年龄': 24,
            '所在地': '北京',
            '学历': '本科',
            '公司': '某互联网公司',
            '职位': 'Java初级工程师'
        },
        'recent_activities': [
            '学习Spring框架',
            '准备跳槽'
        ]
    },
    {
        'id': 4,
        'profile_name': '赵六',
        'wechat_id': 'zhaoliu101',
        'phone': '13600136004',
        'tags': ['运动爱好者', '羽毛球', '健身'],
        'basic_info': {
            '性别': '女',
            '年龄': 26,
            '所在地': '上海',
            '学历': '本科',
            '公司': '外企',
            '职位': '市场经理'
        },
        'recent_activities': [
            '周末打羽毛球',
            '健身房锻炼',
            '组织运动活动'
        ]
    },
    {
        'id': 5,
        'profile_name': '钱七',
        'wechat_id': 'qianqi202',
        'phone': '13500135005',
        'tags': ['Python初学者', '1年经验', 'Flask'],
        'basic_info': {
            '性别': '女',
            '年龄': 23,
            '所在地': '深圳',
            '学历': '本科',
            '公司': '小公司',
            '职位': 'Python开发'
        },
        'recent_activities': [
            '学习Flask框架',
            '做个人项目'
        ]
    }
]

async def test_single_match(matcher, intent, profile, mode):
    """测试单个匹配"""
    print(f"\n{'='*60}")
    print(f"测试意图: {intent['name']}")
    print(f"测试联系人: {profile['profile_name']}")
    print(f"匹配模式: {mode.value}")
    print('-'*60)
    
    # 执行匹配
    results = await matcher.match(
        intent=intent,
        profiles=[profile],
        mode=mode
    )
    
    if results:
        result = results[0]
        print(f"✅ 匹配成功!")
        print(f"  分数: {result['score']:.2f}")
        print(f"  置信度: {result.get('confidence', 0.5):.1%}")
        print(f"  匹配类型: {result['match_type']}")
        
        if 'scores_breakdown' in result:
            print(f"  分数细节:")
            for key, value in result['scores_breakdown'].items():
                print(f"    - {key}: {value:.2f}")
        
        if result.get('matched_aspects'):
            print(f"  匹配方面: {', '.join(result['matched_aspects'])}")
        
        if result.get('missing_aspects'):
            print(f"  缺失方面: {', '.join(result['missing_aspects'])}")
        
        if result.get('explanation'):
            print(f"  解释: {result['explanation'][:200]}...")
    else:
        print("❌ 未匹配")
    
    return results

async def test_batch_match(matcher, intent, profiles, mode):
    """测试批量匹配"""
    print(f"\n{'='*60}")
    print(f"批量测试意图: {intent['name']}")
    print(f"测试联系人数: {len(profiles)}")
    print(f"匹配模式: {mode.value}")
    print('-'*60)
    
    start_time = datetime.now()
    
    # 执行匹配
    results = await matcher.match(
        intent=intent,
        profiles=profiles,
        mode=mode
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print(f"⏱️  耗时: {elapsed:.2f}秒")
    print(f"📊 匹配结果: {len(results)}个")
    
    # 显示前3个结果
    for i, result in enumerate(results[:3], 1):
        profile = result['profile']
        print(f"\n  #{i} {profile['profile_name']}")
        print(f"     分数: {result['score']:.2f}")
        print(f"     置信度: {result.get('confidence', 0.5):.1%}")
        print(f"     类型: {result['match_type']}")
        
        if result.get('explanation'):
            # 截取解释的前100个字符
            explanation = result['explanation'][:100]
            if len(result['explanation']) > 100:
                explanation += '...'
            print(f"     说明: {explanation}")
    
    # 统计信息
    stats = await matcher.get_match_statistics(results)
    print(f"\n📈 统计信息:")
    print(f"   总匹配数: {stats['total']}")
    print(f"   高质量(>0.8): {stats['high_quality']}")
    print(f"   中等质量(0.6-0.8): {stats['medium_quality']}")
    print(f"   低质量(<0.6): {stats['low_quality']}")
    print(f"   平均分数: {stats['average_score']:.2f}")
    print(f"   平均置信度: {stats['average_confidence']:.1%}")
    
    return results

async def compare_modes(matcher, intent, profiles):
    """比较不同模式的效果"""
    print(f"\n{'='*70}")
    print(f"🔬 模式对比测试")
    print(f"意图: {intent['name']}")
    print(f"联系人数: {len(profiles)}")
    print('='*70)
    
    modes = [
        MatchingMode.FAST,
        MatchingMode.BALANCED,
        MatchingMode.ACCURATE,
        MatchingMode.COMPREHENSIVE
    ]
    
    results_by_mode = {}
    
    for mode in modes:
        print(f"\n▶️  测试模式: {mode.value}")
        start_time = datetime.now()
        
        try:
            results = await matcher.match(
                intent=intent,
                profiles=profiles,
                mode=mode
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            results_by_mode[mode.value] = {
                'results': results,
                'time': elapsed,
                'count': len(results)
            }
            
            print(f"   耗时: {elapsed:.2f}秒")
            print(f"   匹配数: {len(results)}")
            
            if results:
                scores = [r['score'] for r in results]
                print(f"   最高分: {max(scores):.2f}")
                print(f"   平均分: {sum(scores)/len(scores):.2f}")
                
                # 显示最佳匹配
                best = results[0]
                print(f"   最佳匹配: {best['profile']['profile_name']} (分数: {best['score']:.2f})")
        
        except Exception as e:
            print(f"   ❌ 错误: {e}")
            results_by_mode[mode.value] = {
                'error': str(e),
                'time': 0,
                'count': 0
            }
    
    # 对比分析
    print(f"\n📊 对比分析:")
    print(f"{'模式':<15} {'耗时(秒)':<10} {'匹配数':<10} {'最高分':<10}")
    print('-'*45)
    
    for mode_name, data in results_by_mode.items():
        if 'error' not in data and data['results']:
            max_score = max(r['score'] for r in data['results'])
            print(f"{mode_name:<15} {data['time']:<10.2f} {data['count']:<10} {max_score:<10.2f}")
        else:
            print(f"{mode_name:<15} {'N/A':<10} {data['count']:<10} {'N/A':<10}")

async def test_complex_intent():
    """测试复杂意图的匹配"""
    complex_intent = {
        'id': 4,
        'name': '高级技术合伙人',
        'description': '''
        寻找技术合伙人，要求：
        1. 5年以上开发经验，精通Python或Java
        2. 有创业经历或在创业公司工作过
        3. 理解AI/ML，有相关项目经验
        4. 不要纯管理背景，需要能写代码
        5. 最好在上海或愿意来上海
        6. 有技术团队管理经验
        7. 年龄28-40岁之间
        ''',
        'type': 'recruitment',
        'priority': 10,
        'threshold': 0.75,
        'conditions': {
            'required': [
                {'field': 'experience', 'operator': '>=', 'value': 5},
                {'field': 'skills', 'operator': 'contains_any', 'value': ['Python', 'Java']},
                {'field': 'age', 'operator': 'between', 'value': [28, 40]}
            ],
            'preferred': [
                {'field': 'experience', 'operator': 'contains', 'value': '创业'},
                {'field': 'skills', 'operator': 'contains_any', 'value': ['AI', 'ML', '机器学习']},
                {'field': 'location', 'operator': 'equals', 'value': '上海'},
                {'field': 'experience', 'operator': 'contains', 'value': '团队管理'}
            ],
            'keywords': ['Python', 'Java', 'AI', 'ML', '创业', '合伙人', '技术', '上海']
        }
    }
    
    print(f"\n{'='*70}")
    print("🧪 复杂意图测试")
    print('='*70)
    print(f"意图描述: {complex_intent['description'][:200]}...")
    
    # 初始化混合匹配器
    matcher = init_hybrid_matcher(use_vector=True, use_llm=True)
    
    # 测试不同模式
    await compare_modes(matcher, complex_intent, TEST_PROFILES)

async def main():
    """主测试函数"""
    print("🚀 开始测试混合匹配系统")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 初始化混合匹配器
    print("\n初始化混合匹配器...")
    matcher = init_hybrid_matcher(use_vector=True, use_llm=True)
    
    # 1. 单个匹配测试
    print("\n" + "="*70)
    print("📝 测试1: 单个匹配测试")
    print("="*70)
    
    # Python开发意图 vs 张三（应该高分匹配）
    await test_single_match(
        matcher,
        TEST_INTENTS[0],  # Python开发
        TEST_PROFILES[0],  # 张三 - Python高级工程师
        MatchingMode.COMPREHENSIVE
    )
    
    # Python开发意图 vs 王五（应该低分或不匹配）
    await test_single_match(
        matcher,
        TEST_INTENTS[0],  # Python开发
        TEST_PROFILES[2],  # 王五 - Java初级
        MatchingMode.COMPREHENSIVE
    )
    
    # 2. 批量匹配测试
    print("\n" + "="*70)
    print("📝 测试2: 批量匹配测试")
    print("="*70)
    
    # 测试所有意图
    for intent in TEST_INTENTS:
        await test_batch_match(
            matcher,
            intent,
            TEST_PROFILES,
            MatchingMode.ACCURATE
        )
    
    # 3. 模式对比测试
    print("\n" + "="*70)
    print("📝 测试3: 不同模式对比")
    print("="*70)
    
    await compare_modes(
        matcher,
        TEST_INTENTS[0],  # Python开发意图
        TEST_PROFILES
    )
    
    # 4. 复杂意图测试
    print("\n" + "="*70)
    print("📝 测试4: 复杂意图处理")
    print("="*70)
    
    await test_complex_intent()
    
    print("\n" + "="*70)
    print("✅ 测试完成!")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())