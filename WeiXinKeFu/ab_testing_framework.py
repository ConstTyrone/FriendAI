#!/usr/bin/env python3
"""
A/B测试框架 - 对比向量匹配vs LLM增强匹配
系统化评估两种方法的性能差异
"""

import asyncio
import json
import sqlite3
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.intent_matcher import IntentMatcher
from src.services.performance_monitor import init_performance_monitor, MatchingMetrics
from src.config.config import config

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """单次测试结果"""
    method: str  # vector/hybrid_fast/hybrid_balanced/hybrid_accurate
    intent_id: int
    intent_name: str
    matches_found: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    response_time: float
    api_calls: int
    api_cost: float
    avg_score: float
    max_score: float
    avg_confidence: float

@dataclass
class ABTestReport:
    """A/B测试报告"""
    test_id: str
    test_time: str
    total_intents: int
    total_profiles: int
    
    # 方法A（向量）
    method_a_name: str
    method_a_results: List[TestResult]
    method_a_avg_precision: float
    method_a_avg_recall: float
    method_a_avg_f1: float
    method_a_avg_time: float
    method_a_total_cost: float
    
    # 方法B（LLM增强）
    method_b_name: str
    method_b_results: List[TestResult]
    method_b_avg_precision: float
    method_b_avg_recall: float
    method_b_avg_f1: float
    method_b_avg_time: float
    method_b_total_cost: float
    
    # 比较结果
    precision_improvement: float
    recall_improvement: float
    f1_improvement: float
    time_difference: float
    cost_difference: float
    statistical_significance: float
    winner: str
    recommendations: List[str]

class ABTestingFramework:
    """A/B测试框架"""
    
    def __init__(self, db_path: str = "user_profiles.db"):
        self.db_path = db_path
        self.monitor = init_performance_monitor(db_path)
        self.ground_truth = {}  # 存储真实匹配（人工标注）
        
    def load_ground_truth(self, intent_id: int) -> List[int]:
        """
        加载真实匹配结果（理想情况下应该有人工标注）
        这里使用规则：
        - 创业合伙人(ID=16) -> 李四(ID=2)
        - Python开发(ID=15) -> 张三(ID=1), 钱七(ID=5)
        - 技术顾问(ID=17) -> 赵六(ID=4)
        """
        ground_truth_map = {
            16: [2],        # 创业合伙人 -> 李四
            15: [1, 5],     # Python开发 -> 张三, 钱七
            17: [4],        # 技术顾问 -> 赵六
            10: [],         # 招聘人才（通用）
            11: [],         # 寻找客户（通用）
            12: [1, 4],     # AI技术专家 -> 张三, 赵六
            13: [],         # 寻找客户（通用）
            14: [1, 2]      # AI机器人方向合伙人 -> 张三, 李四
        }
        return ground_truth_map.get(intent_id, [])
    
    async def run_single_test(
        self,
        intent_id: int,
        intent_name: str,
        user_id: str,
        method: str,
        use_hybrid: bool = False,
        hybrid_mode: str = "balanced"
    ) -> TestResult:
        """运行单次测试"""
        
        # 初始化匹配器
        matcher = IntentMatcher(
            db_path=self.db_path,
            use_ai=True,
            use_hybrid=use_hybrid,
            hybrid_mode=hybrid_mode
        )
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行匹配
        matches = await matcher.match_intent_with_profiles(
            intent_id=intent_id,
            user_id=user_id
        )
        
        # 计算耗时
        response_time = time.time() - start_time
        
        # 获取真实匹配
        true_matches = self.load_ground_truth(intent_id)
        
        # 获取预测的profile IDs
        predicted_ids = [m['profile_id'] for m in matches]
        
        # 计算评估指标
        true_positives = len(set(predicted_ids) & set(true_matches))
        false_positives = len(set(predicted_ids) - set(true_matches))
        false_negatives = len(set(true_matches) - set(predicted_ids))
        
        # 计算精确率、召回率、F1分数
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        # 计算平均分数和置信度
        avg_score = np.mean([m['score'] for m in matches]) if matches else 0
        max_score = max([m['score'] for m in matches]) if matches else 0
        avg_confidence = np.mean([m.get('confidence', 0.5) for m in matches]) if matches else 0
        
        # 估算API成本
        api_calls = len(matches) if use_hybrid else 0
        api_cost = api_calls * 0.01  # 每次调用0.01元
        
        return TestResult(
            method=method,
            intent_id=intent_id,
            intent_name=intent_name,
            matches_found=len(matches),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            response_time=response_time,
            api_calls=api_calls,
            api_cost=api_cost,
            avg_score=avg_score,
            max_score=max_score,
            avg_confidence=avg_confidence
        )
    
    async def run_ab_test(
        self,
        user_id: str,
        intent_ids: Optional[List[int]] = None,
        method_a: str = "vector",
        method_b: str = "hybrid_accurate"
    ) -> ABTestReport:
        """运行完整的A/B测试"""
        
        print("\n" + "="*70)
        print("🧪 A/B测试开始")
        print("="*70)
        print(f"方法A: {method_a}")
        print(f"方法B: {method_b}")
        print()
        
        # 获取要测试的意图
        if intent_ids is None:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name FROM user_intents 
                WHERE user_id = ? AND status = 'active'
                ORDER BY priority DESC
                LIMIT 5
            """, (user_id,))
            intents = cursor.fetchall()
            conn.close()
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            intents = []
            for intent_id in intent_ids:
                cursor.execute("SELECT id, name FROM user_intents WHERE id = ?", (intent_id,))
                intent = cursor.fetchone()
                if intent:
                    intents.append(intent)
            conn.close()
        
        # 方法A测试结果
        method_a_results = []
        print(f"\n📊 测试方法A: {method_a}")
        print("-" * 50)
        
        for intent_id, intent_name in intents:
            print(f"测试意图: {intent_name} (ID={intent_id})")
            
            if method_a == "vector":
                result = await self.run_single_test(
                    intent_id, intent_name, user_id,
                    method="vector", use_hybrid=False
                )
            else:
                # 混合模式
                mode = method_a.replace("hybrid_", "")
                result = await self.run_single_test(
                    intent_id, intent_name, user_id,
                    method=method_a, use_hybrid=True, hybrid_mode=mode
                )
            
            method_a_results.append(result)
            print(f"  ✅ 完成 - 找到{result.matches_found}个匹配, "
                  f"精确率:{result.precision:.2f}, 召回率:{result.recall:.2f}, "
                  f"耗时:{result.response_time:.2f}s")
        
        # 方法B测试结果
        method_b_results = []
        print(f"\n📊 测试方法B: {method_b}")
        print("-" * 50)
        
        for intent_id, intent_name in intents:
            print(f"测试意图: {intent_name} (ID={intent_id})")
            
            if method_b == "vector":
                result = await self.run_single_test(
                    intent_id, intent_name, user_id,
                    method="vector", use_hybrid=False
                )
            else:
                # 混合模式
                mode = method_b.replace("hybrid_", "")
                result = await self.run_single_test(
                    intent_id, intent_name, user_id,
                    method=method_b, use_hybrid=True, hybrid_mode=mode
                )
            
            method_b_results.append(result)
            print(f"  ✅ 完成 - 找到{result.matches_found}个匹配, "
                  f"精确率:{result.precision:.2f}, 召回率:{result.recall:.2f}, "
                  f"耗时:{result.response_time:.2f}s")
        
        # 计算平均指标
        method_a_avg_precision = np.mean([r.precision for r in method_a_results])
        method_a_avg_recall = np.mean([r.recall for r in method_a_results])
        method_a_avg_f1 = np.mean([r.f1_score for r in method_a_results])
        method_a_avg_time = np.mean([r.response_time for r in method_a_results])
        method_a_total_cost = sum([r.api_cost for r in method_a_results])
        
        method_b_avg_precision = np.mean([r.precision for r in method_b_results])
        method_b_avg_recall = np.mean([r.recall for r in method_b_results])
        method_b_avg_f1 = np.mean([r.f1_score for r in method_b_results])
        method_b_avg_time = np.mean([r.response_time for r in method_b_results])
        method_b_total_cost = sum([r.api_cost for r in method_b_results])
        
        # 计算改进率
        precision_improvement = (method_b_avg_precision - method_a_avg_precision) / method_a_avg_precision * 100 if method_a_avg_precision > 0 else 0
        recall_improvement = (method_b_avg_recall - method_a_avg_recall) / method_a_avg_recall * 100 if method_a_avg_recall > 0 else 0
        f1_improvement = (method_b_avg_f1 - method_a_avg_f1) / method_a_avg_f1 * 100 if method_a_avg_f1 > 0 else 0
        time_difference = method_b_avg_time - method_a_avg_time
        cost_difference = method_b_total_cost - method_a_total_cost
        
        # 统计显著性测试（简化版）
        statistical_significance = self.calculate_significance(method_a_results, method_b_results)
        
        # 确定获胜者
        if method_b_avg_f1 > method_a_avg_f1 and statistical_significance > 0.05:
            winner = method_b
        elif method_a_avg_f1 > method_b_avg_f1 and statistical_significance > 0.05:
            winner = method_a
        else:
            winner = "无显著差异"
        
        # 生成建议
        recommendations = self.generate_recommendations(
            method_a, method_b, 
            precision_improvement, recall_improvement,
            time_difference, cost_difference
        )
        
        # 创建报告
        report = ABTestReport(
            test_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            total_intents=len(intents),
            total_profiles=5,  # 测试数据中有5个联系人
            method_a_name=method_a,
            method_a_results=method_a_results,
            method_a_avg_precision=method_a_avg_precision,
            method_a_avg_recall=method_a_avg_recall,
            method_a_avg_f1=method_a_avg_f1,
            method_a_avg_time=method_a_avg_time,
            method_a_total_cost=method_a_total_cost,
            method_b_name=method_b,
            method_b_results=method_b_results,
            method_b_avg_precision=method_b_avg_precision,
            method_b_avg_recall=method_b_avg_recall,
            method_b_avg_f1=method_b_avg_f1,
            method_b_avg_time=method_b_avg_time,
            method_b_total_cost=method_b_total_cost,
            precision_improvement=precision_improvement,
            recall_improvement=recall_improvement,
            f1_improvement=f1_improvement,
            time_difference=time_difference,
            cost_difference=cost_difference,
            statistical_significance=statistical_significance,
            winner=winner,
            recommendations=recommendations
        )
        
        return report
    
    def calculate_significance(self, results_a: List[TestResult], results_b: List[TestResult]) -> float:
        """计算统计显著性（简化版）"""
        # 使用F1分数进行比较
        f1_a = [r.f1_score for r in results_a]
        f1_b = [r.f1_score for r in results_b]
        
        # 计算均值差异
        mean_diff = abs(np.mean(f1_b) - np.mean(f1_a))
        
        # 计算标准误差
        se_a = np.std(f1_a) / np.sqrt(len(f1_a)) if len(f1_a) > 0 else 0
        se_b = np.std(f1_b) / np.sqrt(len(f1_b)) if len(f1_b) > 0 else 0
        se_combined = np.sqrt(se_a**2 + se_b**2)
        
        # 计算z分数
        z_score = mean_diff / se_combined if se_combined > 0 else 0
        
        # 简化的p值估算
        if z_score > 2.58:
            return 0.01  # 99%置信度
        elif z_score > 1.96:
            return 0.05  # 95%置信度
        elif z_score > 1.65:
            return 0.10  # 90%置信度
        else:
            return 0.50  # 无显著差异
    
    def generate_recommendations(
        self,
        method_a: str,
        method_b: str,
        precision_imp: float,
        recall_imp: float,
        time_diff: float,
        cost_diff: float
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于精确率和召回率
        if recall_imp > 50:
            recommendations.append(f"🎯 {method_b}显著提升召回率({recall_imp:.1f}%)，建议在需要全面覆盖的场景使用")
        elif recall_imp < -50:
            recommendations.append(f"⚠️ {method_b}召回率下降({recall_imp:.1f}%)，需要优化匹配阈值")
        
        if precision_imp > 30:
            recommendations.append(f"✅ {method_b}精确率提升({precision_imp:.1f}%)，减少了误匹配")
        elif precision_imp < -30:
            recommendations.append(f"⚠️ {method_b}精确率下降({precision_imp:.1f}%)，可能产生过多误匹配")
        
        # 基于时间和成本
        if time_diff > 10:
            recommendations.append(f"⏱️ {method_b}响应时间增加{time_diff:.1f}秒，考虑使用缓存或批处理优化")
        elif time_diff < -5:
            recommendations.append(f"⚡ {method_b}响应速度提升{abs(time_diff):.1f}秒")
        
        if cost_diff > 0.5:
            recommendations.append(f"💰 {method_b}成本增加¥{cost_diff:.2f}，建议在高价值场景使用")
        
        # 综合建议
        if recall_imp > 30 and time_diff < 20:
            recommendations.append("🏆 建议采用LLM增强匹配作为主要方法，显著提升匹配质量")
        elif recall_imp < 0 and time_diff > 10:
            recommendations.append("💡 建议优化LLM提示词或使用更快的匹配模式")
        
        if not recommendations:
            recommendations.append("📊 两种方法表现相近，可根据具体场景选择")
        
        return recommendations
    
    def print_report(self, report: ABTestReport):
        """打印A/B测试报告"""
        
        print("\n" + "="*70)
        print("📊 A/B测试报告")
        print("="*70)
        print(f"测试ID: {report.test_id}")
        print(f"测试时间: {report.test_time}")
        print(f"测试规模: {report.total_intents}个意图, {report.total_profiles}个联系人")
        
        print("\n" + "-"*70)
        print(f"方法A: {report.method_a_name}")
        print("-"*70)
        print(f"平均精确率: {report.method_a_avg_precision:.2%}")
        print(f"平均召回率: {report.method_a_avg_recall:.2%}")
        print(f"平均F1分数: {report.method_a_avg_f1:.2%}")
        print(f"平均响应时间: {report.method_a_avg_time:.2f}秒")
        print(f"总API成本: ¥{report.method_a_total_cost:.2f}")
        
        print("\n" + "-"*70)
        print(f"方法B: {report.method_b_name}")
        print("-"*70)
        print(f"平均精确率: {report.method_b_avg_precision:.2%}")
        print(f"平均召回率: {report.method_b_avg_recall:.2%}")
        print(f"平均F1分数: {report.method_b_avg_f1:.2%}")
        print(f"平均响应时间: {report.method_b_avg_time:.2f}秒")
        print(f"总API成本: ¥{report.method_b_total_cost:.2f}")
        
        print("\n" + "-"*70)
        print("📈 性能对比")
        print("-"*70)
        print(f"精确率变化: {report.precision_improvement:+.1f}%")
        print(f"召回率变化: {report.recall_improvement:+.1f}%")
        print(f"F1分数变化: {report.f1_improvement:+.1f}%")
        print(f"响应时间差异: {report.time_difference:+.2f}秒")
        print(f"成本差异: ¥{report.cost_difference:+.2f}")
        print(f"统计显著性: p={report.statistical_significance:.3f}")
        
        print("\n" + "-"*70)
        print(f"🏆 获胜者: {report.winner}")
        print("-"*70)
        
        print("\n💡 优化建议:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
        
        # 保存报告到文件
        self.save_report(report)
    
    def save_report(self, report: ABTestReport):
        """保存报告到文件"""
        filename = f"ab_test_report_{report.test_id}.json"
        
        # 转换为可序列化的字典
        report_dict = asdict(report)
        
        # 将TestResult对象转换为字典
        report_dict['method_a_results'] = [asdict(r) for r in report.method_a_results]
        report_dict['method_b_results'] = [asdict(r) for r in report.method_b_results]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 报告已保存到: {filename}")

async def main():
    """主函数"""
    
    print("🧪 LLM增强意图匹配 A/B测试框架")
    print("="*70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API Key: {'✅ 已配置' if config.qwen_api_key else '❌ 未配置'}")
    
    # 初始化测试框架
    ab_tester = ABTestingFramework()
    
    # 真实用户ID
    user_id = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"
    
    # 运行A/B测试
    print("\n开始A/B测试...")
    
    # 测试1: 向量 vs LLM精确模式
    print("\n" + "="*70)
    print("测试1: 传统向量 vs LLM混合精确模式")
    print("="*70)
    
    report1 = await ab_tester.run_ab_test(
        user_id=user_id,
        intent_ids=[16, 15, 17],  # 创业合伙人、Python开发、技术顾问
        method_a="vector",
        method_b="hybrid_accurate"
    )
    
    ab_tester.print_report(report1)
    
    # 测试2: 快速模式 vs 精确模式
    print("\n" + "="*70)
    print("测试2: 混合快速模式 vs 混合精确模式")
    print("="*70)
    
    report2 = await ab_tester.run_ab_test(
        user_id=user_id,
        intent_ids=[16, 15, 17],
        method_a="hybrid_fast",
        method_b="hybrid_accurate"
    )
    
    ab_tester.print_report(report2)
    
    print("\n" + "="*70)
    print("✅ A/B测试完成！")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())