#!/usr/bin/env python3
"""
提示词优化工具 - 提高LLM判断质量
通过系统化测试和优化提示词来提升匹配准确性
"""

import asyncio
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.llm_matching_service import LLMMatchingService
from src.config.config import config

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class PromptVariant:
    """提示词变体"""
    name: str
    system_prompt: str
    user_prompt_template: str
    features: List[str]  # 特性：few-shot, cot, structured, etc.
    
@dataclass
class PromptTestResult:
    """提示词测试结果"""
    variant_name: str
    accuracy: float
    avg_confidence: float
    avg_response_time: float
    correct_matches: int
    total_tests: int
    false_positives: int
    false_negatives: int

class PromptOptimizer:
    """提示词优化器"""
    
    def __init__(self):
        self.llm_service = LLMMatchingService(
            api_key=config.qwen_api_key,
            api_endpoint=config.qwen_api_endpoint
        )
        self.test_cases = self.create_test_cases()
        self.prompt_variants = self.create_prompt_variants()
    
    def create_test_cases(self) -> List[Dict]:
        """创建测试用例"""
        return [
            {
                "intent": {
                    "name": "寻找Python开发工程师",
                    "description": "需要一位有3年以上经验的Python开发工程师，熟悉Django或Flask框架",
                    "conditions": {
                        "required": ["Python", "3年经验"],
                        "preferred": ["Django", "Flask", "AI经验"]
                    }
                },
                "profile": {
                    "name": "张三",
                    "position": "Python高级工程师",
                    "skills": ["Python", "Django", "Flask", "AI"],
                    "experience": "5年"
                },
                "expected_match": True,
                "expected_score_min": 0.8
            },
            {
                "intent": {
                    "name": "创业合伙人",
                    "description": "寻找志同道合的创业伙伴，最好有创业经验，能承受压力",
                    "conditions": {
                        "required": ["创业意愿", "承压能力"],
                        "preferred": ["创业经验", "技术背景"]
                    }
                },
                "profile": {
                    "name": "李四",
                    "position": "CEO",
                    "background": "连续创业者，技术背景",
                    "experience": "3次创业经验"
                },
                "expected_match": True,
                "expected_score_min": 0.85
            },
            {
                "intent": {
                    "name": "Java开发工程师",
                    "description": "需要精通Java和Spring框架的开发者",
                    "conditions": {
                        "required": ["Java", "Spring"],
                        "preferred": ["微服务", "分布式"]
                    }
                },
                "profile": {
                    "name": "王五",
                    "position": "Python开发",
                    "skills": ["Python", "Django"],
                    "experience": "2年"
                },
                "expected_match": False,
                "expected_score_max": 0.3
            }
        ]
    
    def create_prompt_variants(self) -> List[PromptVariant]:
        """创建不同的提示词变体"""
        return [
            # 变体1: 基础版
            PromptVariant(
                name="基础版",
                system_prompt="""你是一个专业的人才匹配专家。请根据意图和联系人信息判断匹配程度。
返回JSON格式：
{
  "match_score": 0-1的分数,
  "confidence": 0-1的置信度,
  "matched_aspects": ["匹配点1", "匹配点2"],
  "missing_aspects": ["缺失点1"],
  "explanation": "详细解释",
  "suggestions": "建议"
}""",
                user_prompt_template="""意图：{intent_desc}
联系人：{profile_desc}
请判断匹配程度。""",
                features=["basic"]
            ),
            
            # 变体2: 链式思考版 (Chain of Thought)
            PromptVariant(
                name="链式思考版",
                system_prompt="""你是一个专业的人才匹配专家。使用链式思考方法进行匹配判断。

分析步骤：
1. 识别意图的核心需求
2. 提取联系人的关键特征
3. 逐项对比匹配程度
4. 综合评估得出结论

返回JSON格式的最终判断。""",
                user_prompt_template="""意图详情：
{intent_desc}

联系人资料：
{profile_desc}

请按步骤分析：
1. 意图核心需求是什么？
2. 联系人有哪些相关特征？
3. 逐项对比分析
4. 给出最终匹配判断

最后以JSON格式返回结果。""",
                features=["cot", "structured"]
            ),
            
            # 变体3: Few-shot示例版
            PromptVariant(
                name="Few-shot示例版",
                system_prompt="""你是一个专业的人才匹配专家。参考以下示例进行判断。

示例1：
意图：寻找Python开发（要求3年经验）
联系人：5年Python经验的工程师
结果：高匹配(0.9)，因为完全满足且超出要求

示例2：
意图：寻找Java开发
联系人：Python开发者
结果：低匹配(0.2)，技能不匹配

请用类似方式分析新的匹配任务。""",
                user_prompt_template="""基于上述示例，分析以下匹配：

意图：{intent_desc}
联系人：{profile_desc}

请给出JSON格式的判断结果。""",
                features=["few-shot", "examples"]
            ),
            
            # 变体4: 评分标准版
            PromptVariant(
                name="评分标准版",
                system_prompt="""你是一个专业的人才匹配专家。使用以下评分标准：

评分维度（各占比）：
- 必要条件满足度 (40%)：完全满足1.0，部分满足0.5，不满足0
- 优选条件满足度 (30%)：每满足一项加分
- 经验匹配度 (20%)：超出要求加分，不足减分
- 综合潜力 (10%)：发展潜力和适应性

匹配等级：
- 完美匹配：0.9-1.0
- 高度匹配：0.7-0.89
- 中度匹配：0.5-0.69
- 低度匹配：0.3-0.49
- 不匹配：0-0.29""",
                user_prompt_template="""请按照评分标准分析：

意图需求：
{intent_desc}

候选人资料：
{profile_desc}

请逐项评分并给出JSON格式的综合结果。""",
                features=["scoring", "structured", "detailed"]
            ),
            
            # 变体5: 角色扮演版
            PromptVariant(
                name="角色扮演版",
                system_prompt="""你现在扮演一位资深的猎头顾问，有20年的人才匹配经验。

你的工作方式：
1. 深入理解客户（意图方）的真实需求，包括显性和隐性需求
2. 全面评估候选人的能力、潜力和适配性
3. 不仅看硬技能，还要考虑软技能和文化匹配
4. 给出专业、中肯的匹配建议

你的判断非常准确，深受客户信任。""",
                user_prompt_template="""作为资深猎头，请评估这个匹配：

客户需求：
{intent_desc}

候选人简历：
{profile_desc}

请给出你的专业判断（JSON格式）：
- 匹配分数和理由
- 优势和不足分析
- 给客户和候选人的建议""",
                features=["role-play", "professional", "comprehensive"]
            ),
            
            # 变体6: 对比分析版
            PromptVariant(
                name="对比分析版",
                system_prompt="""你是一个专业的人才匹配专家。使用对比分析方法。

分析框架：
1. 需求vs能力对比表
2. 优势劣势分析(SWOT)
3. 风险与机会评估
4. 综合匹配度计算

重点关注：
- 关键需求的满足程度
- 潜在的不匹配风险
- 可能的发展机会""",
                user_prompt_template="""请进行详细对比分析：

【需求方】
{intent_desc}

【候选人】
{profile_desc}

请制作对比表并给出JSON格式的分析结果：
1. 逐项对比（需求 vs 实际）
2. SWOT分析
3. 风险评估
4. 最终匹配判断""",
                features=["comparative", "swot", "risk-analysis"]
            )
        ]
    
    async def test_prompt_variant(self, variant: PromptVariant) -> PromptTestResult:
        """测试单个提示词变体"""
        
        print(f"\n测试提示词变体: {variant.name}")
        print("-" * 50)
        
        correct_matches = 0
        false_positives = 0
        false_negatives = 0
        total_confidence = 0
        total_time = 0
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"  测试用例 {i}/{len(self.test_cases)}...")
            
            # 构建提示词
            intent_desc = json.dumps(test_case["intent"], ensure_ascii=False)
            profile_desc = json.dumps(test_case["profile"], ensure_ascii=False)
            
            user_prompt = variant.user_prompt_template.format(
                intent_desc=intent_desc,
                profile_desc=profile_desc
            )
            
            # 测试LLM判断
            start_time = time.time()
            
            try:
                result = await self.llm_service._call_llm_api(
                    system_prompt=variant.system_prompt,
                    user_prompt=user_prompt
                )
                
                response_time = time.time() - start_time
                total_time += response_time
                
                # 解析结果
                if isinstance(result, dict):
                    match_score = result.get("match_score", 0)
                    confidence = result.get("confidence", 0.5)
                    total_confidence += confidence
                    
                    # 评估准确性
                    expected_match = test_case["expected_match"]
                    
                    if expected_match:
                        # 应该匹配
                        if match_score >= test_case.get("expected_score_min", 0.7):
                            correct_matches += 1
                            print(f"    ✅ 正确判断为匹配 (分数: {match_score:.2f})")
                        else:
                            false_negatives += 1
                            print(f"    ❌ 错误判断为不匹配 (分数: {match_score:.2f})")
                    else:
                        # 不应该匹配
                        if match_score <= test_case.get("expected_score_max", 0.3):
                            correct_matches += 1
                            print(f"    ✅ 正确判断为不匹配 (分数: {match_score:.2f})")
                        else:
                            false_positives += 1
                            print(f"    ❌ 错误判断为匹配 (分数: {match_score:.2f})")
                else:
                    print(f"    ⚠️ 解析失败")
                    
            except Exception as e:
                print(f"    ❌ 测试失败: {e}")
        
        # 计算总体指标
        total_tests = len(self.test_cases)
        accuracy = correct_matches / total_tests if total_tests > 0 else 0
        avg_confidence = total_confidence / total_tests if total_tests > 0 else 0
        avg_response_time = total_time / total_tests if total_tests > 0 else 0
        
        return PromptTestResult(
            variant_name=variant.name,
            accuracy=accuracy,
            avg_confidence=avg_confidence,
            avg_response_time=avg_response_time,
            correct_matches=correct_matches,
            total_tests=total_tests,
            false_positives=false_positives,
            false_negatives=false_negatives
        )
    
    async def optimize_prompts(self) -> Dict:
        """运行提示词优化测试"""
        
        print("\n" + "="*70)
        print("🔬 提示词优化测试")
        print("="*70)
        print(f"测试变体数: {len(self.prompt_variants)}")
        print(f"测试用例数: {len(self.test_cases)}")
        
        results = []
        
        for variant in self.prompt_variants:
            result = await self.test_prompt_variant(variant)
            results.append(result)
            
            # 打印即时结果
            print(f"\n📊 {variant.name} 测试结果:")
            print(f"  准确率: {result.accuracy:.1%}")
            print(f"  平均置信度: {result.avg_confidence:.1%}")
            print(f"  平均响应时间: {result.avg_response_time:.2f}秒")
            print(f"  正确: {result.correct_matches}/{result.total_tests}")
            print(f"  误报: {result.false_positives}, 漏报: {result.false_negatives}")
        
        # 找出最佳变体
        best_variant = max(results, key=lambda x: x.accuracy)
        
        # 生成优化报告
        report = self.generate_optimization_report(results, best_variant)
        
        return report
    
    def generate_optimization_report(self, results: List[PromptTestResult], best: PromptTestResult) -> Dict:
        """生成优化报告"""
        
        report = {
            "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_variants": len(results),
            "total_test_cases": len(self.test_cases),
            "results": [],
            "best_variant": best.variant_name,
            "best_accuracy": best.accuracy,
            "recommendations": []
        }
        
        # 添加所有结果
        for result in results:
            report["results"].append({
                "name": result.variant_name,
                "accuracy": result.accuracy,
                "confidence": result.avg_confidence,
                "response_time": result.avg_response_time,
                "correct": result.correct_matches,
                "false_positives": result.false_positives,
                "false_negatives": result.false_negatives
            })
        
        # 生成建议
        if best.accuracy >= 0.9:
            report["recommendations"].append(f"✅ {best.variant_name}表现优秀，建议采用")
        elif best.accuracy >= 0.7:
            report["recommendations"].append(f"👍 {best.variant_name}表现良好，可以使用")
        else:
            report["recommendations"].append(f"⚠️ 所有变体准确率偏低，需要进一步优化")
        
        # 分析特性影响
        cot_variants = [r for r in results if "链式思考" in r.variant_name]
        if cot_variants and cot_variants[0].accuracy > 0.8:
            report["recommendations"].append("💡 链式思考(CoT)方法效果显著，建议采用")
        
        few_shot_variants = [r for r in results if "Few-shot" in r.variant_name]
        if few_shot_variants and few_shot_variants[0].accuracy > 0.8:
            report["recommendations"].append("📚 Few-shot示例学习有效，建议增加更多示例")
        
        # 响应时间分析
        avg_time = sum(r.avg_response_time for r in results) / len(results)
        if best.avg_response_time > avg_time * 1.5:
            report["recommendations"].append(f"⏱️ 最佳变体响应较慢({best.avg_response_time:.2f}秒)，考虑优化")
        
        return report
    
    def print_report(self, report: Dict):
        """打印优化报告"""
        
        print("\n" + "="*70)
        print("📈 提示词优化报告")
        print("="*70)
        print(f"测试时间: {report['test_time']}")
        print(f"测试变体: {report['total_variants']}个")
        print(f"测试用例: {report['total_test_cases']}个")
        
        print("\n" + "-"*70)
        print("测试结果汇总")
        print("-"*70)
        print(f"{'变体名称':<15} {'准确率':<10} {'置信度':<10} {'响应时间':<10} {'正确/总数':<10}")
        print("-"*70)
        
        for result in report['results']:
            print(f"{result['name']:<15} "
                  f"{result['accuracy']:.1%}{'':5} "
                  f"{result['confidence']:.1%}{'':5} "
                  f"{result['response_time']:.2f}s{'':5} "
                  f"{result['correct']}/{report['total_test_cases']}")
        
        print("\n" + "-"*70)
        print(f"🏆 最佳变体: {report['best_variant']}")
        print(f"最高准确率: {report['best_accuracy']:.1%}")
        print("-"*70)
        
        print("\n💡 优化建议:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
        
        # 保存报告
        filename = f"prompt_optimization_report_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📁 报告已保存到: {filename}")

async def main():
    """主函数"""
    
    print("🚀 LLM提示词优化工具")
    print("="*70)
    
    if not config.qwen_api_key:
        print("❌ 错误: QWEN_API_KEY未配置")
        return
    
    # 初始化优化器
    optimizer = PromptOptimizer()
    
    # 运行优化测试
    report = await optimizer.optimize_prompts()
    
    # 打印报告
    optimizer.print_report(report)
    
    print("\n" + "="*70)
    print("✅ 提示词优化完成！")
    print("="*70)
    
    # 应用最佳提示词的建议
    print("\n📝 如何应用最佳提示词:")
    print("1. 打开 src/services/llm_matching_service.py")
    print("2. 找到 _build_judge_prompt 方法")
    print("3. 使用最佳变体的 system_prompt 和 user_prompt_template")
    print("4. 重新运行测试验证效果")

if __name__ == "__main__":
    asyncio.run(main())