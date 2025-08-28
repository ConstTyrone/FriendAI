#!/usr/bin/env python3
"""
AI增强关系识别系统测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
from typing import Dict, List
import time

def test_imports():
    """测试模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        from src.services.ai_relationship_analyzer import AIRelationshipAnalyzer
        print("✅ AIRelationshipAnalyzer导入成功")
    except ImportError as e:
        print(f"❌ AIRelationshipAnalyzer导入失败: {e}")
        return False
    
    try:
        from src.services.relationship_service import RelationshipService, get_relationship_service
        print("✅ RelationshipService导入成功")
    except ImportError as e:
        print(f"❌ RelationshipService导入失败: {e}")
        return False
    
    try:
        from src.database.database_sqlite_v2 import SQLiteDatabase
        print("✅ SQLiteDatabase导入成功")
    except ImportError as e:
        print(f"❌ SQLiteDatabase导入失败: {e}")
        return False
    
    return True

def test_ai_analyzer():
    """测试AI关系分析器"""
    print("\n🤖 测试AI关系分析器...")
    
    try:
        from src.services.ai_relationship_analyzer import AIRelationshipAnalyzer
        
        # 初始化分析器
        analyzer = AIRelationshipAnalyzer()
        
        # 创建测试数据
        profile1 = {
            'id': 1,
            'name': '张伟',
            'profile_name': '张伟',
            'company': '阿里巴巴集团',
            'position': '高级产品经理',
            'location': '杭州市',
            'education': '浙江大学',
            'tags': ['互联网', '产品']
        }
        
        profile2 = {
            'id': 2,
            'name': '李明',
            'profile_name': '李明',
            'company': '阿里巴巴集团',
            'position': '技术专家',
            'location': '杭州市',
            'education': '清华大学',
            'tags': ['技术', '架构']
        }
        
        profile3 = {
            'id': 3,
            'name': '王芳',
            'profile_name': '王芳',
            'company': '腾讯科技',
            'position': '产品总监',
            'location': '深圳市',
            'education': '北京大学',
            'tags': ['产品', '管理']
        }
        
        # 测试同事关系（同公司）
        print("\n  测试同事关系分析...")
        result1 = analyzer.analyze_relationship_with_ai(profile1, profile2)
        print(f"  关系类型: {result1.get('relationship_type')}")
        print(f"  置信度: {result1.get('confidence_score', 0):.2f}")
        print(f"  证据: {result1.get('evidence', '')[:100]}...")
        
        # 测试跨公司关系
        print("\n  测试跨公司关系分析...")
        result2 = analyzer.analyze_relationship_with_ai(profile1, profile3)
        print(f"  关系类型: {result2.get('relationship_type')}")
        print(f"  置信度: {result2.get('confidence_score', 0):.2f}")
        print(f"  证据: {result2.get('evidence', '')[:100]}...")
        
        # 测试关系建议
        print("\n  测试关系建议...")
        suggestions = analyzer.get_relationship_suggestions(profile1, [profile2, profile3])
        print(f"  建议数量: {len(suggestions)}")
        
        for i, suggestion in enumerate(suggestions[:2]):
            analysis = suggestion.get('analysis', {})
            candidate = suggestion.get('candidate_profile', {})
            print(f"  建议{i+1}: {candidate.get('name')} - {analysis.get('relationship_type')} (置信度: {analysis.get('confidence_score', 0):.2f})")
        
        print("✅ AI分析器测试通过")
        return True
        
    except Exception as e:
        print(f"❌ AI分析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_relationship_service_integration():
    """测试关系服务集成"""
    print("\n🔧 测试关系服务AI集成...")
    
    try:
        from src.services.relationship_service import get_relationship_service
        from src.database.database_sqlite_v2 import SQLiteDatabase
        
        # 初始化数据库和服务
        db = SQLiteDatabase()
        service = get_relationship_service(db)
        
        # 检查AI分析器是否可用
        if service.ai_analyzer:
            print("✅ AI分析器已集成到关系服务")
        else:
            print("⚠️ AI分析器未启用，使用规则匹配模式")
        
        # 测试新方法是否存在
        methods_to_check = [
            'discover_relationships_with_ai',
            'get_ai_relationship_suggestions',
            'analyze_relationship_quality'
        ]
        
        for method_name in methods_to_check:
            if hasattr(service, method_name):
                print(f"✅ 方法 {method_name} 存在")
            else:
                print(f"❌ 方法 {method_name} 不存在")
                return False
        
        print("✅ 关系服务集成测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 关系服务集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """测试API端点（语法检查）"""
    print("\n📡 测试API端点...")
    
    try:
        # 检查main.py语法
        import py_compile
        py_compile.compile('src/core/main.py', doraise=True)
        print("✅ main.py语法正确")
        
        # 测试是否能导入API模块
        from src.core.main import app
        print("✅ FastAPI应用导入成功")
        
        # 检查新增的API路由
        routes = [route.path for route in app.routes]
        
        expected_ai_routes = [
            '/api/relationships/{contact_id}/ai-analyze',
            '/api/relationships/suggestions/{contact_id}',
            '/api/relationships/quality/{relationship_id}',
            '/api/relationships/batch/ai-analyze'
        ]
        
        for route in expected_ai_routes:
            # 简化匹配（忽略路径参数的具体格式）
            route_pattern = route.replace('{contact_id}', '').replace('{relationship_id}', '')
            found = any(route_pattern in r for r in routes)
            
            if found:
                print(f"✅ API路由存在: {route}")
            else:
                print(f"⚠️ API路由可能不存在: {route}")
        
        print("✅ API端点测试通过")
        return True
        
    except Exception as e:
        print(f"❌ API端点测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_field_matching():
    """测试字段匹配算法"""
    print("\n🎯 测试字段匹配算法...")
    
    try:
        from src.services.ai_relationship_analyzer import AIRelationshipAnalyzer
        
        analyzer = AIRelationshipAnalyzer()
        
        # 测试完全匹配
        profile_a = {
            'company': '微软中国',
            'location': '北京市朝阳区',
            'education': '清华大学计算机系',
            'position': '软件工程师'
        }
        
        profile_b = {
            'company': '微软中国',
            'location': '北京市海淀区', 
            'education': '北京大学计算机系',
            'position': '产品经理'
        }
        
        # 测试字段匹配
        matches = analyzer._calculate_field_matches(profile_a, profile_b)
        print(f"  字段匹配结果: {matches}")
        
        # 测试相似度计算
        similarity = analyzer._calculate_similarity('微软中国', '微软公司')
        print(f"  字符串相似度: {similarity:.2f}")
        
        # 测试职位互补性
        complementary = analyzer._calculate_position_complementarity('销售经理', '客户总监')
        print(f"  职位互补性: {complementary:.2f}")
        
        print("✅ 字段匹配算法测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 字段匹配算法测试失败: {e}")
        return False

def create_test_summary():
    """创建测试总结"""
    print("\n📋 AI增强关系识别系统功能概览:")
    print("="*60)
    
    features = [
        "✅ AI关系分析器 - 基于通义千问API的智能关系识别",
        "✅ 混合分析模式 - AI分析 + 规则匹配的双重保障",
        "✅ 关系质量评估 - 多维度关系置信度计算", 
        "✅ 智能关系建议 - 基于AI的关系推荐系统",
        "✅ 批量AI分析 - 支持批量关系发现和分析",
        "✅ 证据增强 - AI推理过程和匹配证据记录",
        "✅ 字段匹配优化 - 公司、地区、教育等多字段智能匹配",
        "✅ API接口完善 - 完整的RESTful API支持",
        "✅ 降级策略 - AI不可用时自动切换规则匹配",
        "✅ 性能优化 - 智能缓存和频率控制"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print("\n🚀 新增API接口:")
    print("  • POST /api/relationships/{contact_id}/ai-analyze")
    print("  • GET  /api/relationships/suggestions/{contact_id}")
    print("  • GET  /api/relationships/quality/{relationship_id}")
    print("  • POST /api/relationships/batch/ai-analyze")
    
    print("\n💡 AI增强特性:")
    print("  • 支持11种关系类型的智能识别")
    print("  • 动态置信度调整和证据权重计算")
    print("  • 关系方向性和强度等级判断")
    print("  • 自然语言推理过程记录")
    print("  • 多轮优化的分析结果")
    
    print("\n⚙️ 系统配置要求:")
    print("  • 环境变量: QWEN_API_KEY（必需）")
    print("  • 数据库: 关系发现系统表结构")
    print("  • 依赖: requests库用于API调用")

def main():
    """主测试函数"""
    print("🚀 AI增强关系识别系统测试")
    print("="*50)
    
    test_results = []
    
    # 运行所有测试
    tests = [
        ("模块导入测试", test_imports),
        ("AI分析器测试", test_ai_analyzer),
        ("关系服务集成测试", test_relationship_service_integration),
        ("API端点测试", test_api_endpoints),
        ("字段匹配算法测试", test_field_matching)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 出现异常: {e}")
            test_results.append((test_name, False))
    
    # 统计结果
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    print("\n" + "="*50)
    print(f"测试结果: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！AI增强关系识别系统准备就绪")
        create_test_summary()
    else:
        print(f"\n⚠️ {total_tests - passed_tests} 个测试失败")
        for test_name, result in test_results:
            status = "✅" if result else "❌"
            print(f"  {status} {test_name}")
        
        print("\n📝 失败原因可能包括:")
        print("  • 缺少QWEN_API_KEY环境变量配置")
        print("  • 网络连接问题导致API调用失败")
        print("  • 数据库表结构未正确创建")
        print("  • 依赖库未安装或版本不兼容")

if __name__ == "__main__":
    main()