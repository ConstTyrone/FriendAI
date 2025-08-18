#!/usr/bin/env python3
"""
测试优化后的LLM评分系统
验证是否能给出更智能、更高的匹配分数
"""

import sys
import os
import asyncio
import json
import time

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'WeiXinKeFu'))

from src.services.llm_matching_service import init_llm_matching_service
from src.config.config import config

async def test_llm_scoring():
    """测试LLM评分系统"""
    
    # 初始化LLM服务
    llm_service = init_llm_matching_service(
        api_key=config.qwen_api_key,
        api_endpoint=config.qwen_api_endpoint
    )
    
    # 测试用例1：技术顾问匹配技术合作意图
    test_cases = [
        {
            "name": "技术顾问匹配技术合作",
            "intent": {
                "id": 1,
                "name": "寻找技术合作伙伴",
                "description": "寻找有技术背景的人才进行项目合作，最好懂AI或软件开发",
                "type": "cooperation",
                "conditions": {
                    "keywords": ["技术", "AI", "软件", "开发"],
                    "preferred": [
                        {"field": "position", "value": "技术相关"},
                        {"field": "experience", "value": "3年以上"}
                    ]
                },
                "threshold": 0.6
            },
            "profile": {
                "id": 1,
                "profile_name": "张三",
                "position": "技术顾问",
                "company": "某科技公司",
                "basic_info": {
                    "age": "35岁",
                    "education": "硕士",
                    "location": "北京"
                },
                "tags": ["技术专家", "咨询顾问", "AI领域"],
                "recent_activities": [
                    "参加AI技术峰会",
                    "发表技术文章",
                    "指导创业团队"
                ]
            }
        },
        {
            "name": "销售经理匹配商务合作",
            "intent": {
                "id": 2,
                "name": "寻找商务合作伙伴",
                "description": "寻找有销售或市场背景的人才，帮助拓展业务",
                "type": "business",
                "conditions": {
                    "keywords": ["销售", "市场", "商务", "业务"],
                    "preferred": [
                        {"field": "position", "value": "销售或市场相关"}
                    ]
                },
                "threshold": 0.5
            },
            "profile": {
                "id": 2,
                "profile_name": "李四",
                "position": "区域销售经理",
                "company": "某贸易公司",
                "basic_info": {
                    "age": "30岁",
                    "education": "本科",
                    "location": "上海"
                },
                "tags": ["销售精英", "客户关系", "团队管理"],
                "recent_activities": [
                    "完成季度销售目标",
                    "开拓新客户",
                    "组织团队培训"
                ]
            }
        },
        {
            "name": "跨界人才潜在价值",
            "intent": {
                "id": 3,
                "name": "寻找创业合伙人",
                "description": "寻找有创业精神的合作伙伴，行业不限，重要的是有激情和资源",
                "type": "partnership",
                "conditions": {
                    "keywords": ["创业", "合伙", "资源", "激情"],
                    "preferred": [
                        {"field": "personality", "value": "有创业精神"}
                    ]
                },
                "threshold": 0.5
            },
            "profile": {
                "id": 3,
                "profile_name": "王五",
                "position": "产品经理",
                "company": "互联网公司",
                "basic_info": {
                    "age": "28岁",
                    "education": "本科",
                    "location": "深圳"
                },
                "tags": ["产品思维", "用户体验", "数据分析"],
                "personality": "积极主动，富有创造力",
                "recent_activities": [
                    "主导新产品上线",
                    "参加创业活动",
                    "学习投资知识"
                ]
            }
        }
    ]
    
    print("🧪 开始测试优化后的LLM评分系统\n")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['name']}")
        print("-" * 40)
        
        intent = test_case["intent"]
        profile = test_case["profile"]
        
        print(f"意图: {intent['name']}")
        print(f"联系人: {profile['profile_name']} - {profile['position']}")
        
        start_time = time.time()
        
        try:
            # 调用LLM判断
            judgment = await llm_service.judge_match(
                intent=intent,
                profile=profile,
                use_cache=False  # 不使用缓存，确保每次都是新的判断
            )
            
            elapsed_time = time.time() - start_time
            
            # 显示结果
            print(f"\n🎯 匹配结果:")
            print(f"  • 匹配分数: {judgment.match_score:.2%}")
            print(f"  • 置信度: {judgment.confidence:.2%}")
            print(f"  • 是否匹配: {'✅ 是' if judgment.is_match else '❌ 否'}")
            
            if judgment.matched_aspects:
                print(f"\n✅ 匹配优势:")
                for aspect in judgment.matched_aspects:
                    print(f"  • {aspect}")
            
            if judgment.missing_aspects:
                print(f"\n⚠️ 待改进方面:")
                for aspect in judgment.missing_aspects:
                    print(f"  • {aspect}")
            
            print(f"\n💡 AI分析:")
            print(f"  {judgment.explanation}")
            
            if judgment.suggestions:
                print(f"\n📝 建议:")
                print(f"  {judgment.suggestions}")
            
            print(f"\n⏱️ 处理时间: {elapsed_time:.2f}秒")
            
            # 评估优化效果
            print(f"\n📊 优化评估:")
            if judgment.match_score >= 0.7:
                print("  🎉 优秀！给出了较高的匹配分数，符合积极匹配原则")
            elif judgment.match_score >= 0.5:
                print("  👍 良好！识别到了潜在价值")
            else:
                print("  🤔 分数偏低，可能需要进一步优化")
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成")

async def main():
    """主函数"""
    # 检查API Key
    if not config.qwen_api_key:
        print("❌ 错误: QWEN_API_KEY 未配置")
        print("请在 .env 文件中设置 QWEN_API_KEY")
        return
    
    await test_llm_scoring()

if __name__ == "__main__":
    asyncio.run(main())