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
            
            # 记录LLM原始响应
            logger.info(f"🤖 LLM原始响应:\n{response}")
            
            # 解析响应
            judgment = self._parse_judgment(response)
            
            # 记录解析结果
            logger.info(f"📊 LLM解析结果: 分数={judgment.match_score:.3f}, 置信度={judgment.confidence:.3f}, 是否匹配={judgment.is_match}")
            
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
        """构建判断prompt - 优化版分步评分法"""
        
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
        
        # 构建完整prompt - 分步评分法
        prompt = f"""你是一个智能的商务匹配专家，擅长发现人才潜力和合作机会。你的目标是帮助用户发现有价值的联系人。

## 🎯 核心任务
使用【两步评分法】分析意图和联系人的匹配度。

## 📚 评分示例（Few-shot Learning）

### 示例1 - A级匹配
意图：寻找AI技术合伙人，要求有技术背景
联系人：张三，AI算法工程师，5年经验，同城
分析：技术背景完全匹配，经验丰富，地理位置便利
级别：A级（完美匹配）
分数：0.92

### 示例2 - B级匹配  
意图：寻找电商运营人才
联系人：李四，市场经理，有电商推广经验
分析：有相关经验但非专职运营，值得深入了解
级别：B级（高度匹配）
分数：0.78

### 示例3 - C级匹配
意图：寻找投资人
联系人：王五，企业高管，有投资意向但非专业投资人
分析：有资金实力和投资意向，可以探索合作
级别：C级（良好匹配）
分数：0.65

### 示例4 - D级匹配
意图：寻找技术顾问
联系人：赵六，产品经理，了解技术但非技术专家
分析：有一定技术理解但专业度不够，可作为备选
级别：D级（潜在匹配）
分数：0.55

### 示例5 - E级匹配
意图：寻找销售总监
联系人：钱七，HR总监，可能认识销售人才
分析：本人不匹配但可能有人脉资源
级别：E级（间接价值）
分数：0.45

## 📋 两步评分法

### 第一步：判断匹配级别
请先判断这个匹配属于以下哪个级别：
- **A级 - 完美匹配**：多个核心维度都高度吻合，直接命中需求
- **B级 - 高度匹配**：主要需求满足，有明显合作价值
- **C级 - 良好匹配**：部分需求满足，值得深入探索
- **D级 - 潜在匹配**：有一定相关性，可能存在合作机会
- **E级 - 间接价值**：本人匹配度低但可能有人脉或资源价值
- **F级 - 基本无关**：几乎没有匹配点（慎用此级别）

### 第二步：在级别范围内给出精确分数
- **A级分数范围**：0.85-1.00（示例：0.88, 0.92, 0.95）
- **B级分数范围**：0.70-0.84（示例：0.72, 0.78, 0.82）
- **C级分数范围**：0.60-0.69（示例：0.62, 0.65, 0.68）
- **D级分数范围**：0.50-0.59（示例：0.52, 0.55, 0.58）
- **E级分数范围**：0.40-0.49（示例：0.42, 0.45, 0.48）
- **F级分数范围**：0.00-0.39（仅在确实完全无关时使用）

## 意图信息
{intent_info}

### 匹配条件
{conditions_info}

## 联系人信息
{profile_info}

## 🎯 评分指导原则

### 1. 级别判断要点
- **优先看积极面**：先找匹配点，再看不足
- **宽松理解条件**：大部分条件是"加分项"而非"必须项"
- **考虑潜在价值**：间接联系、未来潜力都很重要
- **避免过于严格**：不确定时，倾向于更高的级别

### 2. 分数细化原则
- 在确定级别后，根据匹配程度在该级别范围内调整
- 同一级别内，匹配点越多分数越高
- 考虑意图优先级，高优先级意图可适当提高分数
- 有特殊优势（如同城、直接经验）可接近级别上限

### 3. 常见场景参考
- 行业相关+职位相近 → B级或以上
- 行业相关但职位不同 → C级
- 行业不同但技能相关 → D级
- 仅地域接近 → D级或E级
- 可能认识目标人群 → E级

## 输出格式
请严格按照以下JSON格式返回结果：
{{
    "match_level": "B",
    "match_score": 0.78,
    "confidence": 0.85,
    "is_match": true,
    "matched_aspects": ["行业背景相关", "有管理经验", "地域合适"],
    "missing_aspects": ["非直接技术岗位"],
    "explanation": "该联系人在电商行业有丰富经验，虽然不是纯技术背景，但其管理经验和行业理解对技术团队很有价值。同城优势便于深入合作。建议进一步了解其技术团队管理经验。",
    "suggestions": "可以先约见面聊，了解其对技术的理解程度和团队资源。即使本人不完全匹配，其行业人脉也可能带来价值。"
}}

## ⚠️ 必须遵守的规则
1. **先确定级别，再给分数**：必须在match_level字段明确标注级别（A/B/C/D/E/F）
2. **分数必须在对应级别范围内**：例如B级必须在0.70-0.84之间
3. **默认倾向高分**：不确定时选择更高的级别和分数
4. **is_match判断**：D级及以上（>=0.50）都应设为true
5. **解释要积极正面**：多强调价值和可能性

## 🎯 自检清单
评分前请确认：
1. 是否先判断了级别？
2. 分数是否在级别范围内？
3. 是否考虑了所有可能的价值点？
4. 解释是否积极且具有建设性？
4. 分数是否至少在0.6以上（除非完全无关）？

**记住：宁可高估也不要低估，错过机会比多一次接触的代价更大！**"""
        
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
        """解析LLM响应 - 增强版，支持分步评分法和验证"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("响应中没有找到JSON")
            
            # 获取匹配级别和分数
            match_level = data.get('match_level', '')
            raw_score = float(data.get('match_score', 0))
            
            # 验证分数是否在对应级别范围内
            validated_score = self._validate_score_range(match_level, raw_score)
            
            # 如果分数被调整，记录日志
            if validated_score != raw_score:
                logger.warning(f"⚠️ LLM分数超出级别范围 - 级别:{match_level}, 原始分数:{raw_score:.3f}, 调整为:{validated_score:.3f}")
            else:
                logger.info(f"✅ LLM评分验证通过 - 级别:{match_level}, 分数:{validated_score:.3f}")
            
            return MatchJudgment(
                match_score=validated_score,
                confidence=float(data.get('confidence', 0.8)),  # 默认置信度0.8
                is_match=bool(data.get('is_match', False)) or validated_score >= 0.50,  # D级及以上为匹配
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

def init_llm_matching_service(api_key: str, db_path: str = "user_profiles.db", api_endpoint: str = None):
    """初始化全局LLM匹配服务"""
    global llm_matching_service
    llm_matching_service = LLMMatchingService(api_key, db_path, api_endpoint)
    return llm_matching_service