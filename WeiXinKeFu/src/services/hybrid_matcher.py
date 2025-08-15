"""
混合匹配策略系统
智能结合向量匹配、规则匹配和LLM判断
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class MatchingMode(Enum):
    """匹配模式"""
    FAST = "fast"  # 快速模式（仅向量）
    BALANCED = "balanced"  # 平衡模式（向量+规则）
    ACCURATE = "accurate"  # 精确模式（向量+LLM）
    COMPREHENSIVE = "comprehensive"  # 全面模式（全部方法）

class HybridMatcher:
    """混合匹配器 - 智能路由和策略选择"""
    
    def __init__(
        self,
        db_path: str = "user_profiles.db",
        use_vector: bool = True,
        use_llm: bool = True
    ):
        """
        初始化混合匹配器
        
        Args:
            db_path: 数据库路径
            use_vector: 是否启用向量匹配
            use_llm: 是否启用LLM判断
        """
        self.db_path = db_path
        self.use_vector = use_vector
        self.use_llm = use_llm
        
        # 初始化各个匹配组件
        self._init_components()
        
        # 配置参数（根据测试结果优化）
        self.vector_threshold = 0.3  # 向量相似度阈值（从0.5降低到0.3）
        self.llm_threshold = 0.6  # LLM判断阈值（从0.7降低到0.6）
        self.top_k_candidates = 50  # 向量过滤的候选数量（从30增加到50）
        
        # 根据模式动态调整阈值
        self.mode_thresholds = {
            'fast': {'vector': 0.4, 'candidates': 20},
            'balanced': {'vector': 0.3, 'candidates': 30},
            'accurate': {'vector': 0.25, 'candidates': 40},
            'comprehensive': {'vector': 0.15, 'candidates': 50}  # 降低向量阈值，让更多候选进入LLM判断
        }
        
    def _init_components(self):
        """初始化匹配组件"""
        # 初始化意图匹配器（包含向量和规则）
        try:
            from .intent_matcher import IntentMatcher
            self.intent_matcher = IntentMatcher(
                db_path=self.db_path,
                use_ai=self.use_vector
            )
            logger.info("✅ 意图匹配器初始化成功")
        except Exception as e:
            logger.error(f"❌ 意图匹配器初始化失败: {e}")
            self.intent_matcher = None
        
        # 初始化LLM匹配服务
        if self.use_llm:
            try:
                from .llm_matching_service import init_llm_matching_service
                from ..config.config import config
                
                self.llm_service = init_llm_matching_service(
                    api_key=config.qwen_api_key,  # 修正为小写
                    db_path=self.db_path,
                    api_endpoint=config.qwen_api_endpoint
                )
                logger.info("✅ LLM匹配服务初始化成功")
            except Exception as e:
                logger.error(f"❌ LLM匹配服务初始化失败: {e}")
                self.llm_service = None
                self.use_llm = False
        else:
            self.llm_service = None
    
    async def match(
        self,
        intent: Dict,
        profiles: List[Dict],
        mode: Optional[MatchingMode] = None,
        user_context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        执行混合匹配
        
        Args:
            intent: 意图信息
            profiles: 联系人列表
            mode: 匹配模式（None表示自动选择）
            user_context: 用户上下文（如付费等级、优先级等）
            
        Returns:
            匹配结果列表，按分数降序排列
        """
        if not profiles:
            return []
        
        # 自动选择匹配模式
        if mode is None:
            mode = self._select_mode(intent, profiles, user_context)
        
        logger.info(f"🎯 使用匹配模式: {mode.value}")
        
        # 根据模式执行匹配
        if mode == MatchingMode.FAST:
            return await self._fast_match(intent, profiles)
        elif mode == MatchingMode.BALANCED:
            return await self._balanced_match(intent, profiles)
        elif mode == MatchingMode.ACCURATE:
            return await self._accurate_match(intent, profiles)
        else:  # COMPREHENSIVE
            return await self._comprehensive_match(intent, profiles)
    
    def _select_mode(
        self,
        intent: Dict,
        profiles: List[Dict],
        user_context: Optional[Dict]
    ) -> MatchingMode:
        """
        根据多种因素自动选择匹配模式
        
        决策因素：
        1. 意图复杂度
        2. 用户等级
        3. 意图优先级
        4. 候选数量
        5. 系统负载
        """
        # 评估意图复杂度
        complexity = self._assess_complexity(intent)
        
        # 获取用户等级和优先级
        user_tier = user_context.get('user_tier', 'free') if user_context else 'free'
        priority = intent.get('priority', 5)
        
        # 候选数量
        candidate_count = len(profiles)
        
        # 决策逻辑
        if user_tier == 'premium' and priority >= 8:
            # 高价值用户的重要意图 - 使用最准确的方法
            return MatchingMode.COMPREHENSIVE
        
        elif complexity == 'complex' or priority >= 7:
            # 复杂意图或高优先级 - 使用精确模式
            return MatchingMode.ACCURATE
        
        elif candidate_count > 100 or complexity == 'simple':
            # 大量候选或简单意图 - 使用快速模式
            return MatchingMode.FAST
        
        else:
            # 默认使用平衡模式
            return MatchingMode.BALANCED
    
    def _assess_complexity(self, intent: Dict) -> str:
        """评估意图复杂度"""
        if self.llm_service:
            complexity_level = self.llm_service.assess_complexity(intent)
            return complexity_level.value
        
        # 简单评估
        conditions = intent.get('conditions', {})
        total_conditions = (
            len(conditions.get('required', [])) +
            len(conditions.get('preferred', []))
        )
        
        if total_conditions <= 2:
            return 'simple'
        elif total_conditions <= 5:
            return 'moderate'
        else:
            return 'complex'
    
    async def _fast_match(
        self,
        intent: Dict,
        profiles: List[Dict]
    ) -> List[Dict]:
        """
        快速匹配模式 - 仅使用向量相似度
        性能最好，准确度较低
        """
        if not self.intent_matcher:
            return []
        
        # 使用模式特定的阈值
        threshold = self.mode_thresholds['fast']['vector']
        max_results = self.mode_thresholds['fast']['candidates']
        
        results = []
        
        for profile in profiles:
            # 使用意图匹配器计算分数（仅向量和规则）
            score = await self.intent_matcher._calculate_match_score(intent, profile)
            
            if score >= threshold:
                results.append({
                    'profile': profile,
                    'score': score,
                    'match_type': 'fast',
                    'confidence': 0.7,  # 快速模式置信度较低
                    'explanation': f"向量匹配分数: {score:.2f}"
                })
        
        # 按分数排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:max_results]  # 返回限定数量
    
    async def _balanced_match(
        self,
        intent: Dict,
        profiles: List[Dict]
    ) -> List[Dict]:
        """
        平衡模式 - 向量过滤 + 规则验证
        性能和准确度平衡
        """
        if not self.intent_matcher:
            return []
        
        # 使用模式特定的阈值
        threshold = self.mode_thresholds['balanced']['vector']
        max_results = self.mode_thresholds['balanced']['candidates']
        
        # 第一步：向量和规则匹配
        candidates = []
        for profile in profiles:
            score = await self.intent_matcher._calculate_match_score(intent, profile)
            
            if score >= threshold:
                candidates.append({
                    'profile': profile,
                    'vector_score': score
                })
        
        # 第二步：规则验证和调整分数
        results = []
        for candidate in candidates:
            profile = candidate['profile']
            
            # 获取匹配的条件
            matched_conditions = self.intent_matcher._get_matched_conditions(intent, profile)
            
            # 生成解释
            explanation = await self.intent_matcher._generate_explanation(
                intent, profile, matched_conditions
            )
            
            # 综合分数
            final_score = candidate['vector_score']
            
            # 使用意图自身的阈值进行最终过滤
            intent_threshold = intent.get('threshold', 0.6)
            if final_score >= intent_threshold:
                results.append({
                    'profile': profile,
                    'score': final_score,
                    'match_type': 'balanced',
                    'confidence': 0.8,
                    'matched_conditions': matched_conditions,
                    'explanation': explanation
                })
        
        # 排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:max_results]
    
    async def _accurate_match(
        self,
        intent: Dict,
        profiles: List[Dict]
    ) -> List[Dict]:
        """
        精确模式 - 向量过滤 + LLM判断
        准确度高，性能较低
        """
        if not self.llm_service:
            # 降级到平衡模式
            logger.warning("LLM服务不可用，降级到平衡模式")
            return await self._balanced_match(intent, profiles)
        
        # 使用模式特定的阈值
        threshold = self.mode_thresholds['accurate']['vector']
        max_candidates = self.mode_thresholds['accurate']['candidates']
        
        # 第一步：向量过滤获取候选
        vector_candidates = []
        if self.intent_matcher:
            for profile in profiles:
                score = await self.intent_matcher._calculate_match_score(intent, profile)
                if score >= threshold * 0.8:  # 进一步降低阈值以获取更多候选
                    vector_candidates.append({
                        'profile': profile,
                        'vector_score': score
                    })
        else:
            # 如果没有向量匹配，取前N个
            vector_candidates = [{'profile': p, 'vector_score': 0.5} for p in profiles[:max_candidates]]
        
        # 按向量分数排序，取Top K
        vector_candidates.sort(key=lambda x: x['vector_score'], reverse=True)
        top_candidates = vector_candidates[:max_candidates]
        
        # 第二步：LLM精确判断
        results = []
        for candidate in top_candidates:
            profile = candidate['profile']
            
            # LLM判断
            judgment = await self.llm_service.judge_match(
                intent, profile, use_cache=True
            )
            
            # 组合分数（向量25% + LLM 75% - LLM应该占主导地位）
            final_score = (
                candidate['vector_score'] * 0.25 +
                judgment.match_score * 0.75
            )
            
            # 使用意图自身的阈值
            intent_threshold = intent.get('threshold', 0.6)
            if final_score >= intent_threshold:
                results.append({
                    'profile': profile,
                    'score': final_score,
                    'match_type': 'accurate',
                    'confidence': judgment.confidence,
                    'matched_aspects': judgment.matched_aspects,
                    'missing_aspects': judgment.missing_aspects,
                    'explanation': judgment.explanation,
                    'suggestions': judgment.suggestions,
                    'vector_score': candidate['vector_score'],
                    'llm_score': judgment.match_score
                })
        
        # 排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    
    async def _comprehensive_match(
        self,
        intent: Dict,
        profiles: List[Dict]
    ) -> List[Dict]:
        """
        全面模式 - 所有方法综合
        最准确，性能最低，适合高价值场景
        """
        # 使用模式特定的阈值
        threshold = self.mode_thresholds['comprehensive']['vector']
        max_results = self.mode_thresholds['comprehensive']['candidates']
        
        results = []
        
        for profile in profiles:
            scores = {}
            
            # 1. 向量和规则匹配
            if self.intent_matcher:
                vector_score = await self.intent_matcher._calculate_match_score(intent, profile)
                scores['vector'] = vector_score
                
                # 获取匹配条件
                matched_conditions = self.intent_matcher._get_matched_conditions(intent, profile)
            else:
                scores['vector'] = 0.5
                matched_conditions = []
            
            # 2. LLM判断（使用更低的阈值）
            if self.llm_service and scores['vector'] >= threshold:  # 使用动态阈值
                judgment = await self.llm_service.judge_match(
                    intent, profile, use_cache=True
                )
                scores['llm'] = judgment.match_score
                llm_explanation = judgment.explanation
                suggestions = judgment.suggestions
                matched_aspects = judgment.matched_aspects
                missing_aspects = judgment.missing_aspects
                confidence = judgment.confidence
            else:
                scores['llm'] = 0.0
                llm_explanation = ""
                suggestions = None
                matched_aspects = []
                missing_aspects = []
                confidence = 0.5
            
            # 3. 综合评分（LLM为主导的权重配置）
            if scores['llm'] > 0:
                # 有LLM分数时：向量25% + LLM 75% (LLM更准确，应该占主导)
                final_score = scores['vector'] * 0.25 + scores['llm'] * 0.75
            else:
                # 仅有向量分数
                final_score = scores['vector']
            
            # 使用意图自身的阈值，而不是硬编码阈值
            intent_threshold = intent.get('threshold', 0.6)  # 使用意图设置的阈值
            if final_score >= intent_threshold:
                results.append({
                    'profile': profile,
                    'score': final_score,
                    'match_type': 'comprehensive',
                    'confidence': confidence,
                    'scores_breakdown': scores,
                    'matched_conditions': matched_conditions,
                    'matched_aspects': matched_aspects,
                    'missing_aspects': missing_aspects,
                    'explanation': llm_explanation or f"综合匹配分数: {final_score:.2f}",
                    'suggestions': suggestions
                })
        
        # 排序并返回
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:max_results]  # 返回限定数量的最佳匹配
    
    async def explain_match(
        self,
        intent: Dict,
        profile: Dict,
        match_result: Dict
    ) -> str:
        """
        生成详细的匹配解释
        
        Args:
            intent: 意图信息
            profile: 联系人信息
            match_result: 匹配结果
            
        Returns:
            详细解释文本
        """
        explanation_parts = []
        
        # 基础信息
        explanation_parts.append(
            f"📊 匹配分数: {match_result['score']:.2f}/1.00"
        )
        explanation_parts.append(
            f"🎯 匹配模式: {match_result['match_type']}"
        )
        explanation_parts.append(
            f"💡 置信度: {match_result.get('confidence', 0.5):.1%}"
        )
        
        # 分数细节
        if 'scores_breakdown' in match_result:
            breakdown = match_result['scores_breakdown']
            explanation_parts.append("\n📈 分数构成:")
            if 'vector' in breakdown:
                explanation_parts.append(f"  • 向量相似度: {breakdown['vector']:.2f}")
            if 'llm' in breakdown:
                explanation_parts.append(f"  • AI判断分数: {breakdown['llm']:.2f}")
        
        # 匹配方面
        if match_result.get('matched_aspects'):
            explanation_parts.append("\n✅ 匹配优势:")
            for aspect in match_result['matched_aspects']:
                explanation_parts.append(f"  • {aspect}")
        
        # 缺失方面
        if match_result.get('missing_aspects'):
            explanation_parts.append("\n⚠️ 待改进:")
            for aspect in match_result['missing_aspects']:
                explanation_parts.append(f"  • {aspect}")
        
        # 详细解释
        if match_result.get('explanation'):
            explanation_parts.append(f"\n💬 详细分析:\n{match_result['explanation']}")
        
        # 建议
        if match_result.get('suggestions'):
            explanation_parts.append(f"\n💡 建议:\n{match_result['suggestions']}")
        
        return '\n'.join(explanation_parts)
    
    async def get_match_statistics(
        self,
        results: List[Dict]
    ) -> Dict:
        """
        生成匹配统计信息
        
        Args:
            results: 匹配结果列表
            
        Returns:
            统计信息字典
        """
        if not results:
            return {
                'total': 0,
                'high_quality': 0,
                'medium_quality': 0,
                'low_quality': 0,
                'average_score': 0,
                'average_confidence': 0,
                'max_score': 0,
                'min_score': 0,
                'match_types': {
                    'fast': 0,
                    'balanced': 0,
                    'accurate': 0,
                    'comprehensive': 0
                }
            }
        
        scores = [r['score'] for r in results]
        confidences = [r.get('confidence', 0.5) for r in results]
        
        return {
            'total': len(results),
            'high_quality': len([r for r in results if r['score'] >= 0.8]),
            'medium_quality': len([r for r in results if 0.6 <= r['score'] < 0.8]),
            'low_quality': len([r for r in results if r['score'] < 0.6]),
            'average_score': sum(scores) / len(scores),
            'max_score': max(scores),
            'min_score': min(scores),
            'average_confidence': sum(confidences) / len(confidences),
            'match_types': {
                'fast': len([r for r in results if r['match_type'] == 'fast']),
                'balanced': len([r for r in results if r['match_type'] == 'balanced']),
                'accurate': len([r for r in results if r['match_type'] == 'accurate']),
                'comprehensive': len([r for r in results if r['match_type'] == 'comprehensive'])
            }
        }

# 全局实例
hybrid_matcher = None

def init_hybrid_matcher(db_path: str = "user_profiles.db", use_vector: bool = True, use_llm: bool = True):
    """初始化全局混合匹配器"""
    global hybrid_matcher
    hybrid_matcher = HybridMatcher(db_path, use_vector, use_llm)
    return hybrid_matcher