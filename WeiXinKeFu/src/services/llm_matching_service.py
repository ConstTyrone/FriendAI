"""
LLM意图匹配判断服务
使用大语言模型进行深度语义理解和精确匹配判断
"""

import json
import asyncio
import hashlib
import logging
import requests
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
    
    def __init__(self, qwen_api_key: str, db_path: str = "user_profiles.db", api_endpoint: str = None):
        """
        初始化LLM匹配服务
        
        Args:
            qwen_api_key: 通义千问API密钥
            db_path: 数据库路径
            api_endpoint: API端点（可选）
        """
        self.api_key = qwen_api_key
        self.db_path = db_path
        self.api_endpoint = api_endpoint or "https://dashscope.aliyuncs.com/compatible-mode/v1"
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
        
        logger.info(f"✅ LLM匹配服务初始化成功 (使用HTTP请求方式)")
        logger.info(f"   API端点: {self.api_endpoint}")
    
    async def judge_match(
        self,
        intent: Dict,
        profile: Dict,
        context: Optional[Dict] = None,
        use_cache: bool = True
    ) -> MatchJudgment:
        """
        使用LLM判断意图与联系人是否匹配
        
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
            # 构建prompt
            prompt = self._build_judgment_prompt(intent, profile, context)
            
            # 调用LLM
            response = await self._call_llm(prompt)
            
            # 解析响应
            judgment = self._parse_judgment(response)
            
            # 计算处理时间
            judgment.processing_time = (datetime.now() - start_time).total_seconds()
            
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
        context: Optional[Dict] = None
    ) -> str:
        """构建判断prompt"""
        
        # 提取意图信息
        intent_info = f"""
意图名称：{intent.get('name', '未命名')}
意图类型：{intent.get('type', '未分类')}
意图描述：{intent.get('description', '无描述')}
优先级：{intent.get('priority', 5)}/10
"""
        
        # 提取条件信息
        conditions = intent.get('conditions', {})
        if conditions:
            required = conditions.get('required', [])
            preferred = conditions.get('preferred', [])
            keywords = conditions.get('keywords', [])
            
            conditions_info = ""
            if required:
                conditions_info += f"必需条件：{json.dumps(required, ensure_ascii=False, indent=2)}\n"
            if preferred:
                conditions_info += f"偏好条件：{json.dumps(preferred, ensure_ascii=False, indent=2)}\n"
            if keywords:
                conditions_info += f"关键词：{', '.join(keywords)}\n"
        else:
            conditions_info = "无特定条件"
        
        # 提取联系人信息
        profile_info = f"""
姓名：{profile.get('profile_name', profile.get('name', '未知'))}
微信ID：{profile.get('wechat_id', '未知')}
电话：{profile.get('phone', '未知')}
"""
        
        # 基本信息
        basic_info = profile.get('basic_info', {})
        if basic_info:
            profile_info += f"基本信息：{json.dumps(basic_info, ensure_ascii=False, indent=2)}\n"
        
        # 标签
        tags = profile.get('tags', [])
        if tags:
            profile_info += f"标签：{', '.join(tags)}\n"
        
        # 最近活动
        activities = profile.get('recent_activities', [])
        if activities:
            profile_info += f"最近活动：{json.dumps(activities[:3], ensure_ascii=False, indent=2)}\n"
        
        # 构建完整prompt
        prompt = f"""你是一个智能的商务匹配专家，擅长发现人才潜力和合作机会。你的目标是帮助用户发现有价值的联系人。

## 核心任务
分析意图和联系人的匹配度，采用**积极乐观**的评判标准，重点挖掘匹配的可能性。

## 意图信息
{intent_info}

### 匹配条件
{conditions_info}

## 联系人信息
{profile_info}

## 🎯 智能评分原则

### 1. 基础分数起点高
- 只要有**任何相关性**，基础分就从 0.5 起步
- 有**行业相关性**，基础分从 0.6 起步
- 有**直接关键词匹配**，基础分从 0.7 起步

### 2. 加分项（每项+0.1到+0.2）
- 行业背景相关或相近
- 职位/角色有关联性
- 地域接近或可远程合作
- 年龄在合理范围内（±5岁也可接受）
- 有相关技能或经验
- 教育背景符合或接近
- 人脉资源可能有价值
- 性格特征适合合作
- 有潜在的业务协同性

### 3. 智能理解意图
- **不要过度解读**必需条件，大部分条件都是"最好有"而非"必须有"
- **灵活理解**关键词，例如"技术"可以包括各种技术相关角色
- **考虑间接价值**，如虽非目标人选但可能介绍合适人选
- **跨界潜力**，不同行业经验可能带来创新视角

### 4. 评分标准（更宽松）
- **0.85-1.0**: 完美匹配，立即推荐联系
- **0.75-0.85**: 高度匹配，强烈建议了解
- **0.65-0.75**: 良好匹配，值得深入交流
- **0.55-0.65**: 潜在匹配，可以试探性接触
- **0.45-0.55**: 间接价值，可能通过其认识目标人选
- **0.35-0.45**: 备选考虑，特定条件下可能有用
- **0.0-0.35**: 暂无明显关联（仅在完全无关时使用）

### 5. 判断心态
- 采用**"宁可错杀，不可放过"**的策略
- 相信**"每个人都有其独特价值"**
- 考虑**"六度分隔理论"**，间接联系也很重要
- 记住**"人的潜力是无限的"**

## 输出格式
请严格按照以下JSON格式返回结果：
{{
    "match_score": 0.78,
    "confidence": 0.85,
    "is_match": true,
    "matched_aspects": ["行业背景相关", "有技术管理经验", "年龄合适", "地域可接受"],
    "missing_aspects": ["非直接技术岗位"],
    "explanation": "虽然该联系人目前是技术顾问而非纯技术开发，但其技术背景和管理经验非常有价值。技术顾问通常对技术趋势和人才市场有深入了解，可能认识合适的技术人才。年龄和地域都在可接受范围内。",
    "suggestions": "建议先了解其技术专长领域和人脉资源，即使本人不完全匹配，也可能推荐合适人选或提供有价值的行业见解。"
}}

## ⚠️ 重要提醒
- **默认给高分**：除非明显完全不相关，否则分数应该在0.5以上
- **is_match 门槛低**：match_score >= 0.45 时就应该 is_match = true
- **解释要积极**：多说优点和可能性，少说缺点和问题
- **建议要务实**：提供具体的下一步行动建议
- **保持乐观**：用积极的语言描述匹配情况"""
        
        # 添加上下文信息
        if context:
            prompt += f"\n\n## 额外上下文\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        
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
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("响应中没有找到JSON")
            
            return MatchJudgment(
                match_score=float(data.get('match_score', 0)),
                confidence=float(data.get('confidence', 0)),
                is_match=bool(data.get('is_match', False)) or float(data.get('match_score', 0)) >= 0.45,  # 更宽松的阈值
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
                match_score=0.0,
                confidence=0.0,
                is_match=False,
                matched_aspects=[],
                missing_aspects=[],
                explanation=f"解析失败: {response[:200]}...",
                strategy_used='llm'
            )
    
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

def init_llm_matching_service(api_key: str, db_path: str = "user_profiles.db", api_endpoint: str = None):
    """初始化全局LLM匹配服务"""
    global llm_matching_service
    llm_matching_service = LLMMatchingService(api_key, db_path, api_endpoint)
    return llm_matching_service