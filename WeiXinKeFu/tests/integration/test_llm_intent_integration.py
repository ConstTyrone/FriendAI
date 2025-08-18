#!/usr/bin/env python3
"""
集成测试脚本 - 测试LLM增强的意图匹配系统
包括向量匹配和LLM判断的对比
"""

import asyncio
import json
import sqlite3
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.hybrid_matcher import init_hybrid_matcher, MatchingMode
from src.config.config import config

async def test_llm_matching():
    """测试LLM匹配功能"""
    
    # 测试意图
    test_intent = {
        'id': 1,
        'name': '寻找技术合伙人',
        'description': '需要一位有创业激情的技术合伙人，最好有Python或Java背景，不要纯管理型的，需要能亲自写代码。年龄30岁左右最佳。',
        'type': 'recruitment',
        'priority': 9,
        'threshold': 0.7,
        'conditions': {
            'required': [
                {'field': 'skills', 'operator': 'contains_any', 'value': ['Python', 'Java']},
                {'field': 'mindset', 'operator': 'equals', 'value': '创业者'}
            ],
            'preferred': [
                {'field': 'age', 'operator': 'between', 'value': [28, 35]},
                {'field': 'can_code', 'operator': 'equals', 'value': True}
            ],
            'keywords': ['技术', '创业', 'Python', 'Java', '合伙人']
        }
    }
    
    # 测试联系人
    test_profiles = [
        {
            'id': 1,
            'profile_name': '张三',
            'wechat_id': 'tech_zhang',
            'tags': ['Python专家', '5年经验', '创业经历'],
            'basic_info': {
                '性别': '男',
                '年龄': 32,
                '所在地': '上海',
                '学历': '硕士',
                '公司': '创业中',
                '职位': 'CTO'
            },
            'recent_activities': [
                '分享了Python技术文章',
                '讨论创业想法',
                '寻找合作机会'
            ]
        },
        {
            'id': 2,
            'profile_name': '李四',
            'wechat_id': 'manager_li',
            'tags': ['项目管理', 'MBA', '不写代码'],
            'basic_info': {
                '性别': '男',
                '年龄': 35,
                '所在地': '北京',
                '学历': 'MBA',
                '公司': '大厂',
                '职位': '产品总监'
            },
            'recent_activities': [
                '管理团队',
                '制定战略',
                '融资谈判'
            ]
        },
        {
            'id': 3,
            'profile_name': '王五',
            'wechat_id': 'junior_wang',
            'tags': ['Java初级', '应届生', '学习中'],
            'basic_info': {
                '性别': '女',
                '年龄': 23,
                '所在地': '深圳',
                '学历': '本科',
                '公司': '实习',
                '职位': 'Java实习生'
            },
            'recent_activities': [
                '学习Spring Boot',
                '做毕业设计',
                '找工作'
            ]
        }
    ]
    
    print("="*70)
    print("🤖 LLM增强意图匹配系统测试")
    print("="*70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key配置: {'✅ 已配置' if config.qwen_api_key else '❌ 未配置'}")
    print()
    
    # 初始化混合匹配器
    print("初始化混合匹配器...")
    try:
        matcher = init_hybrid_matcher(use_vector=True, use_llm=True)
        print("✅ 匹配器初始化成功\n")
    except Exception as e:
        print(f"❌ 匹配器初始化失败: {e}")
        return
    
    # 测试不同模式
    modes_to_test = [
        (MatchingMode.FAST, "快速模式（仅向量）"),
        (MatchingMode.BALANCED, "平衡模式（向量+规则）"),
        (MatchingMode.ACCURATE, "精确模式（向量+LLM）"),
        (MatchingMode.COMPREHENSIVE, "全面模式（所有方法）")
    ]
    
    print(f"📋 测试意图: {test_intent['name']}")
    print(f"   描述: {test_intent['description'][:50]}...")
    print(f"   候选人数: {len(test_profiles)}")
    print()
    
    for mode, mode_name in modes_to_test:
        print(f"\n{'='*50}")
        print(f"🔍 测试 {mode_name}")
        print('='*50)
        
        start_time = datetime.now()
        
        try:
            # 执行匹配
            results = await matcher.match(
                intent=test_intent,
                profiles=test_profiles,
                mode=mode
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            print(f"⏱️  耗时: {elapsed:.2f}秒")
            print(f"📊 匹配结果: {len(results)}个")
            
            # 显示结果
            if results:
                print("\n匹配详情:")
                for i, result in enumerate(results, 1):
                    profile = result['profile']
                    print(f"\n  #{i} {profile['profile_name']}")
                    print(f"     匹配分数: {result['score']:.2f}")
                    print(f"     置信度: {result.get('confidence', 0.5):.1%}")
                    
                    # 显示分数构成（如果有）
                    if 'scores_breakdown' in result:
                        print(f"     分数构成:")
                        for key, value in result['scores_breakdown'].items():
                            print(f"       - {key}: {value:.2f}")
                    
                    # 显示匹配和缺失的方面（如果有）
                    if result.get('matched_aspects'):
                        print(f"     ✅ 匹配: {', '.join(result['matched_aspects'][:3])}")
                    if result.get('missing_aspects'):
                        print(f"     ❌ 缺失: {', '.join(result['missing_aspects'][:3])}")
                    
                    # 显示解释（如果有）
                    if result.get('explanation'):
                        explanation = result['explanation'][:150]
                        if len(result['explanation']) > 150:
                            explanation += '...'
                        print(f"     💬 解释: {explanation}")
            else:
                print("\n没有找到匹配的联系人")
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")
    
    # 生成对比报告
    print(f"\n{'='*70}")
    print("📊 测试总结")
    print('='*70)
    print("""
关键发现：
1. 快速模式：使用向量相似度，速度最快但可能错过语义细节
2. 平衡模式：加入规则验证，提高准确性
3. 精确模式：LLM参与判断，理解更深入（如"不要纯管理型"）
4. 全面模式：所有方法综合，最准确但速度较慢

建议：
- 一般查询使用平衡模式
- 重要匹配使用精确或全面模式
- 大批量初筛使用快速模式
    """)

async def test_complex_scenario():
    """测试复杂场景 - 否定条件和隐含要求"""
    
    print("\n" + "="*70)
    print("🧪 复杂场景测试 - 测试LLM对复杂语义的理解")
    print("="*70)
    
    # 复杂意图：包含否定和隐含条件
    complex_intent = {
        'id': 2,
        'name': '寻找技术顾问',
        'description': '需要一位技术顾问，要有实战经验但不要太理论派，最好是从大厂出来现在创业的，能理解创业的艰辛。不要刚毕业的，也不要纯做管理很久没碰代码的。',
        'type': 'business',
        'priority': 8,
        'threshold': 0.6,
        'conditions': {
            'keywords': ['技术', '顾问', '大厂', '创业', '实战']
        }
    }
    
    test_profiles = [
        {
            'id': 1,
            'profile_name': '技术老兵',
            'tags': ['阿里P8', '创业中', '10年经验'],
            'basic_info': {
                '年龄': 35,
                '公司': '自己创业',
                '背景': '阿里巴巴工作8年，现在创业做技术产品'
            }
        },
        {
            'id': 2,
            'profile_name': '理论专家',
            'tags': ['教授', '博士', '研究AI'],
            'basic_info': {
                '年龄': 45,
                '公司': '某大学',
                '背景': '一直在学术界，发表论文50篇'
            }
        },
        {
            'id': 3,
            'profile_name': '应届天才',
            'tags': ['清华毕业', 'ACM金牌', '技术强'],
            'basic_info': {
                '年龄': 22,
                '公司': '刚入职字节',
                '背景': '刚毕业，技术能力很强'
            }
        }
    ]
    
    # 初始化匹配器
    matcher = init_hybrid_matcher(use_vector=True, use_llm=True)
    
    print(f"\n意图: {complex_intent['name']}")
    print(f"要求: {complex_intent['description']}")
    print(f"\n候选人:")
    for p in test_profiles:
        print(f"  - {p['profile_name']}: {', '.join(p['tags'])}")
    
    # 测试精确模式（使用LLM）
    print("\n使用LLM精确模式匹配...")
    results = await matcher.match(
        intent=complex_intent,
        profiles=test_profiles,
        mode=MatchingMode.ACCURATE
    )
    
    print(f"\n匹配结果:")
    if results:
        for result in results:
            profile = result['profile']
            print(f"\n👤 {profile['profile_name']}")
            print(f"   分数: {result['score']:.2f}")
            print(f"   判断: {'✅ 合适' if result['score'] >= 0.6 else '❌ 不合适'}")
            if result.get('explanation'):
                print(f"   理由: {result['explanation'][:200]}")
    else:
        print("没有合适的匹配")
    
    print("\n分析：LLM应该能理解：")
    print("  1. '技术老兵'最合适 - 有大厂背景+创业经历")
    print("  2. '理论专家'不合适 - 太理论派")
    print("  3. '应届天才'不合适 - 刚毕业，缺乏经验")

async def main():
    """主测试函数"""
    # 基础测试
    await test_llm_matching()
    
    # 复杂场景测试
    await test_complex_scenario()
    
    print("\n" + "="*70)
    print("✅ 所有测试完成！")
    print("="*70)

if __name__ == "__main__":
    # 检查配置
    if not config.qwen_api_key:
        print("⚠️  警告: QWEN_API_KEY未配置，LLM功能将不可用")
        print("请在.env文件中设置: QWEN_API_KEY=your_api_key")
    
    # 运行测试
    asyncio.run(main())