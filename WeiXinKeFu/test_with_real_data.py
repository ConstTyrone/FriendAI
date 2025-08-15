#!/usr/bin/env python3
"""
使用真实数据测试LLM增强意图匹配系统
测试用户: wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q
"""

import asyncio
import json
import sqlite3
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.intent_matcher import IntentMatcher
from src.services.performance_monitor import init_performance_monitor
from src.config.config import config

async def test_with_real_user_data():
    """使用真实用户数据进行测试"""
    
    print("="*70)
    print("🎯 使用真实数据测试LLM增强意图匹配系统")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key: {'✅ 已配置' if config.qwen_api_key else '❌ 未配置'}")
    print()
    
    # 真实用户ID
    real_user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    # 初始化性能监控器
    monitor = init_performance_monitor()
    print("✅ 性能监控器已初始化")
    
    # 连接数据库检查数据
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    # 检查用户意图
    print("\n📋 检查用户意图...")
    cursor.execute("""
        SELECT id, name, type, status 
        FROM user_intents 
        WHERE user_id = ?
        ORDER BY priority DESC
    """, (real_user_id,))
    
    intents = cursor.fetchall()
    if intents:
        print(f"找到 {len(intents)} 个意图:")
        for intent in intents:
            print(f"  - ID={intent[0]}: {intent[1]} ({intent[2]}) - 状态: {intent[3]}")
    else:
        print("❌ 没有找到任何意图")
        print("\n请先运行: python init_test_data.py 来创建测试数据")
        conn.close()
        return
    
    # 检查用户联系人
    print("\n👥 检查用户联系人...")
    clean_user = ''.join(c if c.isalnum() or c == '_' else '_' for c in real_user_id)
    user_table = f"profiles_{clean_user}"
    
    # 检查表是否存在
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """, (user_table,))
    
    if not cursor.fetchone():
        print(f"❌ 用户表 {user_table} 不存在")
        print("\n请先运行: python init_test_data.py 来创建测试数据")
        conn.close()
        return
    
    cursor.execute(f"SELECT id, profile_name FROM {user_table}")
    profiles = cursor.fetchall()
    
    if profiles:
        print(f"找到 {len(profiles)} 个联系人:")
        for profile in profiles[:5]:  # 只显示前5个
            print(f"  - ID={profile[0]}: {profile[1]}")
        if len(profiles) > 5:
            print(f"  ... 还有 {len(profiles)-5} 个联系人")
    else:
        print("❌ 没有找到任何联系人")
        conn.close()
        return
    
    conn.close()
    
    # 测试不同模式的意图匹配
    print("\n" + "="*70)
    print("🔬 开始测试意图匹配")
    print("="*70)
    
    # 测试配置
    test_configs = [
        {"use_ai": True, "use_hybrid": False, "name": "传统向量模式"},
        {"use_ai": True, "use_hybrid": True, "hybrid_mode": "fast", "name": "混合快速模式"},
        {"use_ai": True, "use_hybrid": True, "hybrid_mode": "balanced", "name": "混合平衡模式"},
        {"use_ai": True, "use_hybrid": True, "hybrid_mode": "accurate", "name": "混合精确模式"}
    ]
    
    # 选择第一个活跃意图进行测试
    test_intent_id = intents[0][0] if intents else 1
    
    print(f"\n使用意图: {intents[0][1] if intents else '未知'} (ID={test_intent_id})")
    
    all_results = {}
    
    for config_item in test_configs:
        print(f"\n{'='*50}")
        print(f"📝 测试模式: {config_item['name']}")
        print('='*50)
        
        # 初始化意图匹配器
        matcher = IntentMatcher(
            use_ai=config_item["use_ai"],
            use_hybrid=config_item.get("use_hybrid", False),
            hybrid_mode=config_item.get("hybrid_mode", "balanced")
        )
        
        # 记录开始时间
        start_time = datetime.now()
        
        try:
            # 执行匹配
            matches = await matcher.match_intent_with_profiles(
                intent_id=test_intent_id,
                user_id=real_user_id
            )
            
            # 计算耗时
            elapsed = (datetime.now() - start_time).total_seconds()
            
            print(f"⏱️  耗时: {elapsed:.2f}秒")
            print(f"📊 匹配结果: {len(matches)}个")
            
            # 保存结果
            all_results[config_item['name']] = {
                'matches': matches,
                'elapsed': elapsed,
                'count': len(matches)
            }
            
            # 显示前3个匹配结果
            if matches:
                print("\n🎯 Top 3 匹配:")
                for i, match in enumerate(matches[:3], 1):
                    print(f"\n  #{i} {match.get('profile_name', '未知')}")
                    print(f"     分数: {match['score']:.2f}")
                    print(f"     类型: {match.get('match_type', 'unknown')}")
                    
                    # 混合模式的额外信息
                    if config_item.get("use_hybrid"):
                        if 'confidence' in match:
                            print(f"     置信度: {match['confidence']:.1%}")
                        if 'matched_aspects' in match:
                            aspects = match['matched_aspects']
                            if aspects:
                                print(f"     匹配方面: {', '.join(aspects[:3])}")
                        if 'scores_breakdown' in match:
                            breakdown = match['scores_breakdown']
                            print(f"     分数构成: 向量={breakdown.get('vector', 0):.2f}, "
                                  f"LLM={breakdown.get('llm', 0):.2f}")
                        if 'explanation' in match and match['explanation']:
                            # 只显示前100个字符
                            exp = match['explanation']
                            if len(exp) > 100:
                                exp = exp[:100] + "..."
                            print(f"     解释: {exp}")
            else:
                print("\n❌ 没有找到匹配的联系人")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 对比分析
    print("\n" + "="*70)
    print("📈 对比分析")
    print("="*70)
    
    print("\n模式对比:")
    print(f"{'模式':<20} {'耗时(秒)':<10} {'匹配数':<10} {'平均分数':<10}")
    print("-" * 50)
    
    for mode_name, result in all_results.items():
        avg_score = 0
        if result['matches']:
            scores = [m['score'] for m in result['matches']]
            avg_score = sum(scores) / len(scores)
        
        print(f"{mode_name:<20} {result['elapsed']:<10.2f} "
              f"{result['count']:<10} {avg_score:<10.2f}")
    
    # 性能统计
    print("\n" + "="*70)
    print("📊 性能统计")
    print("="*70)
    
    stats = await monitor.get_statistics()
    
    if stats and stats.get('overall'):
        overall = stats['overall']
        print(f"""
总体统计:
  - 总操作数: {overall.get('total_operations', 0)}
  - 平均响应时间: {overall.get('avg_response_time', 0):.2f}秒
  - API总成本: ¥{overall.get('total_api_cost', 0):.2f}
  - 缓存命中率: {overall.get('cache_hit_rate', 0):.1%}
""")
    
    print("\n" + "="*70)
    print("✅ 测试完成！")
    print("="*70)

async def check_database_status():
    """检查数据库状态"""
    print("\n" + "="*70)
    print("🔍 数据库状态检查")
    print("="*70)
    
    conn = sqlite3.connect("user_profiles.db")
    cursor = conn.cursor()
    
    # 检查所有表
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table'
        ORDER BY name
    """)
    
    tables = cursor.fetchall()
    print(f"\n数据库中的表 ({len(tables)}个):")
    for table in tables:
        print(f"  - {table[0]}")
    
    # 检查用户意图表
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT user_id) FROM user_intents")
    intent_stats = cursor.fetchone()
    print(f"\n用户意图统计:")
    print(f"  - 总意图数: {intent_stats[0]}")
    print(f"  - 用户数: {intent_stats[1]}")
    
    # 检查意图匹配表
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT intent_id) FROM intent_matches")
    match_stats = cursor.fetchone()
    print(f"\n意图匹配统计:")
    print(f"  - 总匹配数: {match_stats[0]}")
    print(f"  - 匹配的意图数: {match_stats[1]}")
    
    conn.close()

async def main():
    """主函数"""
    print("🚀 LLM增强意图匹配系统 - 真实数据测试")
    print("="*70)
    
    # 1. 检查数据库状态
    await check_database_status()
    
    # 2. 运行真实数据测试
    await test_with_real_user_data()
    
    print("\n💡 提示:")
    print("  - 如果没有数据，请先运行: python init_test_data.py")
    print("  - 确保API Key已配置: export QWEN_API_KEY=your_key")
    print("  - 查看详细日志: tail -f app.log")

if __name__ == "__main__":
    asyncio.run(main())