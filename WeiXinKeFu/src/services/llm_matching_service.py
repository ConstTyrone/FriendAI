"""
LLM意图匹配判断服务
使用大语言模型进行深度语义理解和精确匹配判断
支持数据收集、自适应校准和A/B测试
"""

import json
import asyncio
import hashlib
import logging
import requests
import random
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class MatchStrategy(Enum):
    """匹配策略枚举"""
    VECTOR_ONLY = "vector_only"  # 仅向量
    LLM_ONLY = "llm_only"  # 仅LLM
    HYBRID = "hybrid"  # 混合
    ADAPTIVE = "adaptive"  # 自适应

class ComplexityLevel(Enum):
    """意图复杂度级别"""
    SIMPLE = "simple"  # 简单
    MODERATE = "moderate"  # 中等
    COMPLEX = "complex"  # 复杂

@dataclass
class MatchJudgment:
    """LLM匹配判断结果"""
    match_score: float  # 匹配分数 0-1
    confidence: float  # 置信度 0-1
    is_match: bool  # 是否匹配
    matched_aspects: List[str]  # 匹配的方面
    missing_aspects: List[str]  # 缺失的方面
    explanation: str  # 详细解释
    suggestions: Optional[str] = None  # 改进建议
    strategy_used: str = "llm"  # 使用的策略
    processing_time: float = 0.0  # 处理时间（秒）
    cached: bool = False  # 是否来自缓存

class LLMMatchingService:
    """LLM意图匹配服务"""
    
    def __init__(self, qwen_api_key: str, db_path: str = "user_profiles.db", api_endpoint: str = None, user_id: str = None):
        """
        初始化LLM匹配服务
        
        Args:
            qwen_api_key: 通义千问API密钥
            db_path: 数据库路径
            api_endpoint: API端点（可选）
            user_id: 用户ID（用于数据收集）
        """
        self.api_key = qwen_api_key
        self.db_path = db_path
        self.api_endpoint = api_endpoint or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.user_id = user_id
        self.cache = {}  # 内存缓存
        self.cache_ttl = timedelta(hours=24)  # 缓存有效期
        
        # 配置参数
        self.batch_size = 5  # 批处理大小
        self.max_parallel = 3  # 最大并行数
        self.timeout = 30  # API调用超时（秒）
        
        # 设置请求头
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # 初始化配置和分析服务
        try:
            from ..config.scoring_config import scoring_config_manager
            self.config_manager = scoring_config_manager
            self.config = self.config_manager.get_config()
            logger.info(f"✅ 加载评分配置: 策略={self.config.strategy}")
        except Exception as e:
            logger.warning(f"无法加载配置管理器: {e}，使用默认配置")
            self.config_manager = None
            self.config = None
        
        # 初始化数据分析服务
        try:
            from .scoring_analytics import scoring_analytics
            self.analytics = scoring_analytics if self.config and self.config.enable_analytics else None
            logger.info(f"✅ 数据分析服务: {'已启用' if self.analytics else '已禁用'}")
        except Exception as e:
            logger.warning(f"无法加载数据分析服务: {e}")
            self.analytics = None
        
        # 校准参数缓存
        self.calibration_params = None
        self.calibration_update_time = None
        
        logger.info(f"✅ LLM匹配服务初始化成功 (数据飞轮模式)")
        logger.info(f"   API端点: {self.api_endpoint}")
    
    async def judge_match(
        self,
        intent: Dict,
        profile: Dict,
        context: Optional[Dict] = None,
        use_cache: bool = True
    ) -> MatchJudgment:
        """
        使用LLM判断意图与联系人是否匹配（支持数据飞轮）
        
        Args:
            intent: 意图信息
            profile: 联系人信息
            context: 额外上下文
            use_cache: 是否使用缓存
            
        Returns:
            MatchJudgment: 匹配判断结果
        """
        start_time = datetime.now()
        
        # 检查缓存
        if use_cache:
            cache_key = self._generate_cache_key(intent, profile)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                cached_result.cached = True
                logger.info(f"🎯 命中缓存: {cache_key[:16]}...")
                return cached_result
        
        try:
            # 获取当前策略（支持A/B测试）
            strategy = self._get_current_strategy()
            
            # 构建prompt
            prompt = self._build_judgment_prompt(intent, profile, context, strategy)
            
            # 调用LLM
            response = await self._call_llm(prompt)
            
            # 记录LLM原始响应
            logger.info(f"🤖 LLM原始响应 (策略={strategy}):\n{response}")
            
            # 解析响应
            judgment = self._parse_judgment(response)
            
            # 应用自适应校准
            if self.config and self.config.enable_calibration:
                original_score = judgment.match_score
                judgment = await self._apply_calibration(judgment, intent, profile)
                if judgment.match_score != original_score:
                    logger.info(f"🔧 校准调整: {original_score:.3f} → {judgment.match_score:.3f}")
            
            # 记录解析结果
            logger.info(f"📊 LLM最终结果: 分数={judgment.match_score:.3f}, 置信度={judgment.confidence:.3f}, 是否匹配={judgment.is_match}")
            
            # 计算处理时间
            judgment.processing_time = (datetime.now() - start_time).total_seconds()
            judgment.strategy_used = strategy
            
            # 记录到数据分析服务
            if self.analytics and self.user_id:
                try:
                    self.analytics.record_scoring(
                        user_id=self.user_id,
                        intent=intent,
                        profile=profile,
                        llm_score=judgment.match_score,
                        final_score=judgment.match_score,
                        confidence=judgment.confidence,
                        matched_aspects=judgment.matched_aspects,
                        missing_aspects=judgment.missing_aspects,
                        explanation=judgment.explanation,
                        strategy=strategy,
                        processing_time=judgment.processing_time
                    )
                except Exception as e:
                    logger.warning(f"记录评分数据失败: {e}")
            
            # 存入缓存
            if use_cache:
                self._save_to_cache(cache_key, judgment)
            
            logger.info(f"✅ LLM判断完成: 分数={judgment.match_score:.2f}, 耗时={judgment.processing_time:.2f}s")
            return judgment
            
        except Exception as e:
            logger.error(f"❌ LLM判断失败: {e}")
            # 返回默认结果
            return MatchJudgment(
                match_score=0.0,
                confidence=0.0,
                is_match=False,
                matched_aspects=[],
                missing_aspects=[],
                explanation=f"LLM判断失败: {str(e)}",
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def batch_judge(
        self,
        intent: Dict,
        profiles: List[Dict],
        strategy: MatchStrategy = MatchStrategy.ADAPTIVE,
        parallel: bool = True
    ) -> List[MatchJudgment]:
        """
        批量判断多个联系人
        
        Args:
            intent: 意图信息
            profiles: 联系人列表
            strategy: 匹配策略
            parallel: 是否并行处理
            
        Returns:
            判断结果列表
        """
        if not profiles:
            return []
        
        # 根据策略过滤候选
        candidates = await self._filter_candidates(intent, profiles, strategy)
        
        if parallel and len(candidates) > 1:
            # 并行处理
            return await self._parallel_judge(intent, candidates)
        else:
            # 串行处理
            results = []
            for profile in candidates:
                judgment = await self.judge_match(intent, profile)
                results.append(judgment)
            return results
    
    async def explain_mismatch(
        self,
        intent: Dict,
        profile: Dict
    ) -> str:
        """
        解释为什么不匹配
        
        Args:
            intent: 意图信息
            profile: 联系人信息
            
        Returns:
            不匹配的详细解释
        """
        prompt = self._build_mismatch_prompt(intent, profile)
        
        try:
            response = await self._call_llm(prompt)
            return response
        except Exception as e:
            logger.error(f"生成不匹配解释失败: {e}")
            return "无法生成详细解释"
    
    def assess_complexity(self, intent: Dict) -> ComplexityLevel:
        """
        评估意图复杂度
        
        Args:
            intent: 意图信息
            
        Returns:
            复杂度级别
        """
        score = 0
        
        # 检查条件数量
        conditions = intent.get('conditions', {})
        required = conditions.get('required', [])
        preferred = conditions.get('preferred', [])
        
        score += len(required) * 2
        score += len(preferred)
        
        # 检查描述长度和复杂度
        description = intent.get('description', '')
        if len(description) > 200:
            score += 3
        if any(word in description for word in ['不要', '除了', '但是', '或者']):
            score += 2
        
        # 检查是否有复杂逻辑
        if '且' in description or '或' in description:
            score += 2
        
        # 判断复杂度级别
        if score <= 3:
            return ComplexityLevel.SIMPLE
        elif score <= 8:
            return ComplexityLevel.MODERATE
        else:
            return ComplexityLevel.COMPLEX
    
    def _build_judgment_prompt(
        self,
        intent: Dict,
        profile: Dict,
        context: Optional[Dict] = None,
        strategy: Optional[str] = None
    ) -> str:
        """构建判断prompt - 支持多策略"""
        
        # 提取意图信息
        intent_desc = intent.get('description', '无描述')
        intent_name = intent.get('name', '未命名')
        
        # 提取条件信息（如果有）
        conditions_text = ""
        conditions = intent.get('conditions', {})
        if conditions:
            required = conditions.get('required', [])
            preferred = conditions.get('preferred', [])
            
            if required:
                conditions_text += "\n必要条件："
                for req in required:
                    if isinstance(req, dict):
                        field = req.get('field', '')
                        value = req.get('value', '')
                        conditions_text += f"\n- {field}: {value}"
                    else:
                        conditions_text += f"\n- {req}"
            
            if preferred:
                conditions_text += "\n偏好条件："
                for pref in preferred:
                    if isinstance(pref, dict):
                        field = pref.get('field', '')
                        value = pref.get('value', '')
                        conditions_text += f"\n- {field}: {value}"
                    else:
                        conditions_text += f"\n- {pref}"
        
        # 提取联系人信息
        profile_text = f"姓名：{profile.get('profile_name', profile.get('name', '未知'))}"
        
        # 基本信息
        basic_info = profile.get('basic_info', {})
        if basic_info:
            for key, value in basic_info.items():
                if value:
                    # 将字段名转换为中文（如果需要）
                    field_name_map = {
                        'gender': '性别',
                        'age': '年龄',
                        'location': '所在地',
                        'education': '学历/学校',
                        'company': '公司',
                        'position': '职位',
                        'marital_status': '婚育',
                        'asset_level': '资产水平',
                        'personality': '性格'
                    }
                    field_name = field_name_map.get(key, key)
                    profile_text += f"\n{field_name}：{value}"
        
        # 标签
        tags = profile.get('tags', [])
        if tags:
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    pass
            if isinstance(tags, list) and tags:
                profile_text += f"\n标签：{', '.join(str(t) for t in tags)}"
        
        # AI摘要（如果有）
        if profile.get('ai_summary'):
            profile_text += f"\nAI摘要：{profile['ai_summary']}"
        
        # 根据策略获取prompt模板
        if strategy and self.config_manager:
            prompt_template = self.config_manager.get_prompt_template(strategy)
        else:
            # 使用默认极简模板
            prompt_template = """请评估以下用户与意图的匹配程度：

【意图需求】
{intent_description}{conditions}

【用户信息】
{profile_info}

请给出0-1之间的匹配分数，并提供简短的理由。

评分指导：
- 高度匹配（0.7-1.0）：核心需求基本满足
- 中度匹配（0.4-0.7）：部分符合或有潜在价值  
- 低度匹配（0-0.4）：相关性较弱

输出JSON格式：
{{
    "match_score": 0.75,
    "confidence": 0.8,
    "is_match": true,
    "matched_aspects": ["符合的方面"],
    "missing_aspects": ["不符合的方面"],
    "explanation": "简短解释",
    "suggestions": "建议"
}}"""
        
        # 格式化prompt
        prompt = prompt_template.format(
            intent_description=intent_desc,
            conditions=conditions_text,
            profile_info=profile_text
        )
        
        return prompt
    
    def _build_mismatch_prompt(self, intent: Dict, profile: Dict) -> str:
        """构建不匹配解释的prompt"""
        return f"""分析以下意图和联系人为什么不匹配，并提供改进建议。

意图：{json.dumps(intent, ensure_ascii=False, indent=2)}

联系人：{json.dumps(profile, ensure_ascii=False, indent=2)}

请提供：
1. 主要不匹配原因（最重要的3个）
2. 如果要匹配，联系人需要具备什么
3. 如果要匹配，意图可以如何调整
4. 其他可能更合适的匹配方向

要求回答简洁、实用、有建设性。"""
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM API (使用异步方式的同步请求)"""
        
        # 构造请求数据
        data = {
            "model": "qwen-plus",  # 或 "qwen-max"
            "messages": [
                {"role": "system", "content": "你是一个专业的匹配分析专家。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,  # 保证一致性
            "max_tokens": 1000
        }
        
        try:
            # 使用 asyncio 运行同步请求
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{self.api_endpoint}/chat/completions",
                    headers=self.headers,
                    data=json.dumps(data),
                    timeout=self.timeout
                )
            )
            
            # 检查响应状态
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                logger.info(f"LLM响应成功，内容长度: {len(content)}")
                return content
            else:
                error_msg = f"API调用失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.Timeout:
            raise Exception(f"LLM调用超时（{self.timeout}秒）")
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise
    
    def _parse_judgment(self, response: str) -> MatchJudgment:
        """解析LLM响应 - 极简版本"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("响应中没有找到JSON")
            
            # 获取分数
            raw_score = float(data.get('match_score', 0))
            
            # 基本范围验证（确保在0-1之间）
            validated_score = max(0.0, min(1.0, raw_score))
            
            # 如果分数被调整，记录日志
            if validated_score != raw_score:
                logger.warning(f"⚠️ LLM分数超出范围 - 原始分数:{raw_score:.3f}, 调整为:{validated_score:.3f}")
            else:
                logger.info(f"✅ LLM评分有效 - 分数:{validated_score:.3f}")
            
            return MatchJudgment(
                match_score=validated_score,
                confidence=float(data.get('confidence', 0.8)),  # 默认置信度0.8
                is_match=bool(data.get('is_match', False)) or validated_score >= 0.50,  # 0.5及以上为匹配
                matched_aspects=data.get('matched_aspects', []),
                missing_aspects=data.get('missing_aspects', []),
                explanation=data.get('explanation', ''),
                suggestions=data.get('suggestions'),
                strategy_used='llm'
            )
            
        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}\n原始响应: {response}")
            # 返回默认结果
            return MatchJudgment(
                match_score=0.55,  # 默认给中等分数
                confidence=0.5,
                is_match=True,  # 默认为潜在匹配
                matched_aspects=[],
                missing_aspects=[],
                explanation=f"解析失败，使用默认评分: {response[:200]}...",
                strategy_used='llm'
            )
    
    def _get_current_strategy(self) -> str:
        """
        获取当前应该使用的策略（支持A/B测试）
        
        Returns:
            策略名称
        """
        if self.config_manager:
            return self.config_manager.get_ab_test_strategy()
        return "minimal"
    
    async def _apply_calibration(
        self,
        judgment: MatchJudgment,
        intent: Dict,
        profile: Dict
    ) -> MatchJudgment:
        """
        应用自适应校准
        
        Args:
            judgment: 原始判断结果
            intent: 意图信息
            profile: 联系人信息
            
        Returns:
            校准后的判断结果
        """
        if not self.analytics or not self.user_id:
            return judgment
        
        try:
            # 获取或更新校准参数
            now = datetime.now()
            if (not self.calibration_params or 
                not self.calibration_update_time or
                now - self.calibration_update_time > timedelta(hours=1)):
                
                # 获取最新校准参数
                self.calibration_params = self.analytics.calculate_calibration_params(
                    self.user_id,
                    min_feedback_count=self.config.calibration.get('min_feedback_count', 10)
                )
                self.calibration_update_time = now
                logger.info(f"🔧 更新校准参数: {self.calibration_params}")
            
            # 应用校准
            calibrated_score = judgment.match_score
            
            # 根据置信度调整
            if judgment.confidence < self.calibration_params.get('confidence_threshold', 0.7):
                # 低置信度，向中间值靠拢
                calibrated_score = calibrated_score * 0.8 + 0.5 * 0.2
            
            # 根据分离度调整
            separation_factor = self.calibration_params.get('separation_factor', 1.0)
            if separation_factor != 1.0:
                # 增强正负反馈的区分度
                if calibrated_score > 0.5:
                    calibrated_score = 0.5 + (calibrated_score - 0.5) * separation_factor
                else:
                    calibrated_score = 0.5 - (0.5 - calibrated_score) * separation_factor
            
            # 确保在有效范围内
            calibrated_score = max(0.0, min(1.0, calibrated_score))
            
            # 更新判断结果
            judgment.match_score = calibrated_score
            judgment.is_match = calibrated_score >= self.config.thresholds.get('match_threshold', 0.5)
            
            return judgment
            
        except Exception as e:
            logger.warning(f"应用校准失败: {e}")
            return judgment
    
    def update_feedback(
        self,
        intent_id: int,
        profile_id: int,
        feedback: str
    ) -> bool:
        """
        更新用户反馈（用于数据飞轮）
        
        Args:
            intent_id: 意图ID
            profile_id: 联系人ID
            feedback: 反馈类型 (positive/negative/neutral/ignored)
            
        Returns:
            是否成功
        """
        if self.analytics and self.user_id:
            return self.analytics.update_feedback(
                self.user_id, intent_id, profile_id, feedback
            )
        return False
    
    def get_performance_stats(self, days: int = 7) -> Dict:
        """
        获取性能统计（用于监控和优化）
        
        Args:
            days: 统计天数
            
        Returns:
            性能统计数据
        """
        if self.analytics:
            return {
                'score_distribution': self.analytics.get_score_distribution(
                    user_id=self.user_id,
                    days=days
                ),
                'intent_performance': self.analytics.get_intent_type_performance(days),
                'quality_metrics': self.analytics.get_quality_metrics(days)
            }
        return {}
    
    def _validate_score_range(self, match_level: str, score: float) -> float:
        """
        验证分数是否在对应级别范围内，如果不在则调整到范围内
        
        Args:
            match_level: 匹配级别 (A/B/C/D/E/F)
            score: 原始分数
            
        Returns:
            调整后的分数
        """
        # 定义各级别的分数范围
        level_ranges = {
            'A': (0.85, 1.00),
            'B': (0.70, 0.84),
            'C': (0.60, 0.69),
            'D': (0.50, 0.59),
            'E': (0.40, 0.49),
            'F': (0.00, 0.39)
        }
        
        # 如果没有级别信息，根据分数推断级别
        if not match_level or match_level not in level_ranges:
            if score >= 0.85:
                match_level = 'A'
            elif score >= 0.70:
                match_level = 'B'
            elif score >= 0.60:
                match_level = 'C'
            elif score >= 0.50:
                match_level = 'D'
            elif score >= 0.40:
                match_level = 'E'
            else:
                match_level = 'F'
            logger.info(f"未提供级别，根据分数{score:.3f}推断为{match_level}级")
        
        # 获取级别范围
        min_score, max_score = level_ranges[match_level]
        
        # 验证和调整分数
        if score < min_score:
            # 分数偏低，调整到范围下限
            return min_score + 0.02  # 稍高于下限
        elif score > max_score:
            # 分数偏高，调整到范围上限
            return max_score - 0.01  # 稍低于上限
        else:
            # 分数在合理范围内
            return score
    
    def _generate_cache_key(self, intent: Dict, profile: Dict) -> str:
        """生成缓存键"""
        # 使用关键字段生成哈希
        key_data = {
            'intent_id': intent.get('id'),
            'intent_desc': intent.get('description', ''),
            'intent_conditions': intent.get('conditions', {}),
            'profile_id': profile.get('id'),
            'profile_name': profile.get('profile_name', ''),
            'profile_tags': profile.get('tags', []),
            'profile_basic': profile.get('basic_info', {})
        }
        
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[MatchJudgment]:
        """从缓存获取结果"""
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            # 检查是否过期
            if datetime.now() - cached_item['time'] < self.cache_ttl:
                return cached_item['judgment']
            else:
                # 过期则删除
                del self.cache[cache_key]
        return None
    
    def _save_to_cache(self, cache_key: str, judgment: MatchJudgment):
        """保存到缓存"""
        self.cache[cache_key] = {
            'judgment': judgment,
            'time': datetime.now()
        }
        
        # 限制缓存大小
        if len(self.cache) > 1000:
            # 删除最旧的项
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k]['time'])
            del self.cache[oldest_key]
    
    async def _filter_candidates(
        self,
        intent: Dict,
        profiles: List[Dict],
        strategy: MatchStrategy
    ) -> List[Dict]:
        """根据策略过滤候选联系人"""
        
        if strategy == MatchStrategy.LLM_ONLY:
            # LLM处理所有
            return profiles
            
        elif strategy == MatchStrategy.VECTOR_ONLY:
            # 不使用LLM
            return []
            
        elif strategy == MatchStrategy.HYBRID:
            # 使用向量过滤Top K
            try:
                from .vector_service import vector_service
                # 获取向量相似度排序
                scored_profiles = []
                for profile in profiles:
                    score, _ = await vector_service.calculate_semantic_similarity(
                        intent, profile, use_cache=True
                    )
                    scored_profiles.append((score, profile))
                
                # 排序并取Top K
                scored_profiles.sort(key=lambda x: x[0], reverse=True)
                top_k = min(20, len(scored_profiles))
                return [p for _, p in scored_profiles[:top_k]]
                
            except Exception as e:
                logger.error(f"向量过滤失败: {e}")
                return profiles[:20]  # 降级处理
                
        else:  # ADAPTIVE
            # 根据复杂度自适应
            complexity = self.assess_complexity(intent)
            
            if complexity == ComplexityLevel.SIMPLE:
                # 简单意图不使用LLM
                return []
            elif complexity == ComplexityLevel.MODERATE:
                # 中等复杂度，选择前10个
                return profiles[:10]
            else:
                # 复杂意图，选择前20个
                return profiles[:20]
    
    async def _parallel_judge(
        self,
        intent: Dict,
        profiles: List[Dict]
    ) -> List[MatchJudgment]:
        """并行判断多个联系人"""
        
        # 创建任务
        tasks = []
        for profile in profiles:
            task = self.judge_match(intent, profile)
            tasks.append(task)
        
        # 分批执行
        results = []
        for i in range(0, len(tasks), self.max_parallel):
            batch = tasks[i:i + self.max_parallel]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"并行判断失败: {result}")
                    # 添加失败结果
                    results.append(MatchJudgment(
                        match_score=0.0,
                        confidence=0.0,
                        is_match=False,
                        matched_aspects=[],
                        missing_aspects=[],
                        explanation=f"判断失败: {str(result)}"
                    ))
                else:
                    results.append(result)
        
        return results

# 全局实例（延迟初始化）
llm_matching_service = None

def init_llm_matching_service(api_key: str, db_path: str = "user_profiles.db", api_endpoint: str = None, user_id: str = None):
    """初始化全局LLM匹配服务（支持数据飞轮）"""
    global llm_matching_service
    llm_matching_service = LLMMatchingService(api_key, db_path, api_endpoint, user_id)
    return llm_matching_service