"""
意图匹配引擎 - AI增强版本
集成向量化和语义相似度计算
"""

import json
import sqlite3
import logging
import asyncio
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class IntentMatcher:
    """意图匹配引擎 - AI增强版（支持混合匹配）"""
    
    def __init__(self, db_path: str = "user_profiles.db", use_ai: bool = True, use_hybrid: bool = False, hybrid_mode: str = "balanced"):
        """
        初始化意图匹配引擎
        
        Args:
            db_path: 数据库路径
            use_ai: 是否使用AI（向量匹配）
            use_hybrid: 是否使用混合匹配（LLM+向量）
            hybrid_mode: 混合匹配模式 (fast/balanced/accurate/comprehensive)
        """
        self.db_path = db_path
        self.use_ai = use_ai
        self.use_hybrid = use_hybrid
        self.hybrid_mode = hybrid_mode
        self.vector_service = None
        self.hybrid_matcher = None
        
        # 如果启用混合匹配，初始化混合匹配器
        if self.use_hybrid:
            try:
                from .hybrid_matcher import init_hybrid_matcher, MatchingMode
                from ..config.config import config
                
                # 检查API key是否配置
                if not config.qwen_api_key:
                    logger.warning("⚠️ QWEN_API_KEY未配置，降级到向量匹配模式")
                    self.use_hybrid = False
                else:
                    self.hybrid_matcher = init_hybrid_matcher(
                        db_path=db_path,
                        use_vector=True,
                        use_llm=True
                    )
                    # 设置匹配模式
                    self.matching_mode = getattr(MatchingMode, hybrid_mode.upper(), MatchingMode.BALANCED)
                    logger.info(f"✅ 混合匹配器已启用，模式: {hybrid_mode}")
            except Exception as e:
                logger.error(f"❌ 混合匹配器初始化失败: {e}")
                self.use_hybrid = False
                self.hybrid_matcher = None
        
        # 如果没有启用混合匹配，尝试初始化向量服务
        if not self.use_hybrid and self.use_ai:
            try:
                # 先检查numpy是否可用
                try:
                    import numpy as np
                    logger.info("NumPy已安装")
                except ImportError:
                    logger.error("⚠️ NumPy未安装，请运行: pip install numpy")
                    raise ImportError("NumPy未安装")
                
                from .vector_service import vector_service
                self.vector_service = vector_service
                logger.info("✅ 向量服务已启用")
            except ImportError as e:
                logger.error(f"❌ 向量服务初始化失败 - 缺少依赖: {e}")
                logger.info("🚨 请在服务器上运行: pip install numpy scipy aiohttp")
                self.use_ai = False
                self.vector_service = None
            except Exception as e:
                logger.error(f"❌ 向量服务初始化失败: {e}")
                import traceback
                traceback.print_exc()
                self.use_ai = False
                self.vector_service = None
        
        if not self.use_hybrid and not self.use_ai:
            logger.info("🔄 使用基础规则匹配模式")
    
    async def match_intent_with_profiles(self, intent_id: int, user_id: str) -> List[Dict]:
        """
        将意图与用户的所有联系人进行匹配
        
        Args:
            intent_id: 意图ID
            user_id: 用户ID
            
        Returns:
            匹配结果列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取意图详情
            cursor.execute("""
                SELECT * FROM user_intents 
                WHERE id = ? AND user_id = ? AND status = 'active'
            """, (intent_id, user_id))
            
            intent_row = cursor.fetchone()
            if not intent_row:
                logger.warning(f"意图不存在或未激活: {intent_id}")
                return []
            
            # 构建意图对象
            columns = [desc[0] for desc in cursor.description]
            intent = dict(zip(columns, intent_row))
            
            # 解析条件
            try:
                intent['conditions'] = json.loads(intent['conditions']) if intent['conditions'] else {}
            except:
                intent['conditions'] = {}
            
            # 获取用户表名
            user_table = self._get_user_table_name(user_id)
            
            # 检查表是否存在
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (user_table,))
            
            if not cursor.fetchone():
                logger.warning(f"用户表不存在: {user_table}")
                conn.close()
                return []
            
            # 获取所有联系人
            cursor.execute(f"SELECT * FROM {user_table}")
            profiles = []
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor.fetchall():
                profile = dict(zip(columns, row))
                profiles.append(profile)
            
            # 如果启用混合匹配，使用混合匹配器
            if self.use_hybrid and self.hybrid_matcher:
                logger.info(f"使用混合匹配器，模式: {self.hybrid_mode}")
                
                # 调用混合匹配器
                hybrid_results = await self.hybrid_matcher.match(
                    intent=intent,
                    profiles=profiles,
                    mode=self.matching_mode
                )
                
                # 处理混合匹配结果
                matches = []
                for result in hybrid_results:
                    profile = result['profile']
                    score = result['score']
                    
                    # 只保留达到阈值的匹配
                    if score >= intent.get('threshold', 0.7):
                        # 保存匹配记录（包含LLM相关信息）
                        match_id = self._save_hybrid_match_record(
                            cursor=cursor,
                            intent_id=intent_id,
                            profile_id=profile['id'],
                            user_id=user_id,
                            result=result
                        )
                        
                        match_result = {
                            'match_id': match_id,
                            'intent_id': intent_id,
                            'intent_name': intent.get('name', ''),
                            'profile_id': profile['id'],
                            'profile_name': profile.get('profile_name', profile.get('name', '')),
                            'score': score,
                            'match_type': result.get('match_type', 'hybrid'),
                            'confidence': result.get('confidence', 0.5),
                            'matched_conditions': result.get('matched_conditions', []),
                            'matched_aspects': result.get('matched_aspects', []),
                            'missing_aspects': result.get('missing_aspects', []),
                            'explanation': result.get('explanation', ''),
                            'suggestions': result.get('suggestions', '')
                        }
                        
                        # 如果有分数细节，也包含进去
                        if 'scores_breakdown' in result:
                            match_result['scores_breakdown'] = result['scores_breakdown']
                        
                        matches.append(match_result)
                
            else:
                # 使用传统向量匹配
                matches = []
                for profile in profiles:
                    score, match_type = await self._calculate_match_score_with_type(intent, profile)
                    
                    if score >= (intent.get('threshold', 0.7)):
                        # 生成匹配解释
                        matched_conditions = self._get_matched_conditions(intent, profile)
                        explanation = await self._generate_explanation(intent, profile, matched_conditions)
                        
                        # 保存匹配记录
                        match_id = self._save_match_record(
                            cursor, intent_id, profile['id'], user_id,
                            score, matched_conditions, explanation, match_type
                        )
                        
                        match_result = {
                            'match_id': match_id,
                            'intent_id': intent_id,
                            'intent_name': intent.get('name', ''),
                            'profile_id': profile['id'],
                            'profile_name': profile.get('profile_name', profile.get('name', '未知')),
                            'score': score,
                            'match_type': match_type,
                            'matched_conditions': matched_conditions,
                            'explanation': explanation
                        }
                        matches.append(match_result)
                    
                    # 尝试推送通知（暂时禁用，避免异步冲突）
                    # TODO: 修复异步推送服务
                    # try:
                    #     from src.services.push_service import push_service
                    #     push_service.process_match_for_push(match_result, user_id)
                    # except Exception as e:
                    #     logger.warning(f"推送通知失败: {e}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"意图 {intent_id} 匹配完成，找到 {len(matches)} 个匹配")
            return matches
            
        except Exception as e:
            logger.error(f"匹配意图时出错: {e}")
            return []
    
    async def match_profile_with_intents(self, profile_id: int, user_id: str) -> List[Dict]:
        """
        将联系人与用户的所有活跃意图进行匹配
        
        Args:
            profile_id: 联系人ID
            user_id: 用户ID
            
        Returns:
            匹配结果列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取用户表名
            user_table = self._get_user_table_name(user_id)
            
            # 获取联系人详情
            cursor.execute(f"SELECT * FROM {user_table} WHERE id = ?", (profile_id,))
            profile_row = cursor.fetchone()
            
            if not profile_row:
                logger.warning(f"联系人不存在: {profile_id}")
                conn.close()
                return []
            
            columns = [desc[0] for desc in cursor.description]
            profile = dict(zip(columns, profile_row))
            
            # 获取所有活跃意图
            cursor.execute("""
                SELECT * FROM user_intents 
                WHERE user_id = ? AND status = 'active'
                ORDER BY priority DESC
            """, (user_id,))
            
            intents = []
            columns = [desc[0] for desc in cursor.description]
            
            for row in cursor.fetchall():
                intent = dict(zip(columns, row))
                # 解析条件
                try:
                    intent['conditions'] = json.loads(intent['conditions']) if intent['conditions'] else {}
                except:
                    intent['conditions'] = {}
                intents.append(intent)
            
            # 进行匹配 - 使用混合匹配器（如果启用）或传统匹配
            matches = []
            
            if self.use_hybrid and self.hybrid_matcher:
                # 使用最强的混合匹配器
                logger.info(f"🚀 使用混合匹配器 ({self.hybrid_mode}模式) 进行意图匹配")
                for intent in intents:
                    # 使用comprehensive模式获得最佳匹配结果
                    hybrid_results = await self.hybrid_matcher.match(
                        intent, [profile], 
                        mode=self.matching_mode
                    )
                    
                    if hybrid_results:
                        result = hybrid_results[0]  # 取第一个结果
                        score = result['score']
                        explanation = result.get('explanation', '')
                        matched_conditions = result.get('matched_conditions', [])
                        match_type = result.get('match_type', 'hybrid')
                        confidence = result.get('confidence', 0.8)
                        
                        # 使用意图自身设置的阈值，尊重用户的意图配置
                        intent_threshold = intent.get('threshold', 0.6)  # 默认0.6，但优先使用用户设置
                        if score >= intent_threshold:
                            # 保存匹配记录
                            match_id = self._save_match_record(
                                cursor, intent['id'], profile_id, user_id,
                                score, matched_conditions, explanation, match_type
                            )
                            
                            matches.append({
                                'match_id': match_id,
                                'intent_id': intent['id'],
                                'intent_name': intent['name'],
                                'score': score,
                                'matched_conditions': matched_conditions,
                                'explanation': explanation,
                                'match_type': match_type,
                                'confidence': confidence
                            })
                            logger.info(f"✅ 混合匹配成功: {intent['name']} -> {profile.get('profile_name', 'Unknown')} (分数: {score:.2%})")
            else:
                # 使用传统匹配方法
                logger.info("🔄 使用传统意图匹配方法")
                for intent in intents:
                    score = await self._calculate_match_score(intent, profile)
                    
                    if score >= (intent.get('threshold', 0.7)):
                        matched_conditions = self._get_matched_conditions(intent, profile)
                        explanation = await self._generate_explanation(intent, profile, matched_conditions)
                        
                        # 保存匹配记录
                        match_id = self._save_match_record(
                            cursor, intent['id'], profile_id, user_id,
                            score, matched_conditions, explanation, 'traditional'
                        )
                        
                        matches.append({
                            'match_id': match_id,
                            'intent_id': intent['id'],
                            'intent_name': intent['name'],
                            'score': score,
                            'matched_conditions': matched_conditions,
                            'explanation': explanation,
                            'match_type': 'traditional'
                        })
            
            conn.commit()
            conn.close()
            
            logger.info(f"联系人 {profile_id} 匹配完成，找到 {len(matches)} 个匹配")
            return matches
            
        except Exception as e:
            logger.error(f"匹配联系人时出错: {e}")
            return []
    
    async def _calculate_match_score_with_type(self, intent: Dict, profile: Dict) -> tuple:
        """计算匹配分数并返回匹配类型"""
        score = await self._calculate_match_score(intent, profile)
        
        # 判断匹配类型
        if self.use_ai and hasattr(self, '_last_semantic_score') and self._last_semantic_score > 0:
            if score > 0 and self._last_semantic_score < score:
                match_type = 'hybrid'  # AI增强匹配（AI+规则）
            else:
                match_type = 'vector'  # 纯AI语义匹配
        else:
            match_type = 'rule'  # 规则匹配
        
        return score, match_type
    
    async def _calculate_match_score(self, intent: Dict, profile: Dict) -> float:
        """
        计算匹配分数
        
        AI增强版本：结合向量相似度和条件匹配
        """
        score = 0.0
        weight_sum = 0.0
        
        conditions = intent.get('conditions', {})
        
        # 如果启用AI且有向量服务，先计算语义相似度
        semantic_score = 0.0
        if self.use_ai and self.vector_service:
            try:
                # 现在可以使用异步调用
                semantic_score, explanation = await self.vector_service.calculate_semantic_similarity(intent, profile, use_cache=False)
                logger.info(f"AI匹配 - 意图:{intent.get('name')} 联系人:{profile.get('profile_name', profile.get('name'))} 语义分数:{semantic_score:.2f} 说明:{explanation}")
                # 保存语义分数供判断匹配类型使用
                self._last_semantic_score = semantic_score
            except Exception as e:
                logger.warning(f"语义相似度计算失败: {e}")
                semantic_score = 0.0
                self._last_semantic_score = 0.0
        else:
            self._last_semantic_score = 0.0
        
        # 权重分配（AI模式和基础模式不同）
        if self.use_ai and semantic_score > 0:
            # AI模式：语义相似度30%，关键词30%，必要条件25%，优选条件15%
            score += semantic_score * 0.3
            weight_sum += 0.3
            
            keywords = conditions.get('keywords', [])
            if keywords:
                keyword_score = self._calculate_keyword_score(keywords, profile)
                score += keyword_score * 0.3
                weight_sum += 0.3
            
            required = conditions.get('required', [])
            if required:
                required_score = self._calculate_condition_score(required, profile, strict=True)
                score += required_score * 0.25
                weight_sum += 0.25
            
            preferred = conditions.get('preferred', [])
            if preferred:
                preferred_score = self._calculate_condition_score(preferred, profile, strict=False)
                score += preferred_score * 0.15
                weight_sum += 0.15
        else:
            # 基础模式：关键词40%，必要条件40%，优选条件20%
            keywords = conditions.get('keywords', [])
            if keywords:
                keyword_score = self._calculate_keyword_score(keywords, profile)
                score += keyword_score * 0.4
                weight_sum += 0.4
                logger.info(f"基础匹配 - 关键词:{keywords} 分数:{keyword_score:.2f}")
            
            required = conditions.get('required', [])
            if required:
                required_score = self._calculate_condition_score(required, profile, strict=True)
                score += required_score * 0.4
                weight_sum += 0.4
            
            preferred = conditions.get('preferred', [])
            if preferred:
                preferred_score = self._calculate_condition_score(preferred, profile, strict=False)
                score += preferred_score * 0.2
                weight_sum += 0.2
        
        # 记录最终分数
        final_score = score / weight_sum if weight_sum > 0 else 0.0
        logger.info(f"最终匹配分数: {final_score:.2f} (阈值: {intent.get('threshold', 0.7)})")
        
        # 如果没有任何条件，基于描述相似度给一个基础分
        if weight_sum == 0:
            # 如果有语义相似度，直接使用
            if semantic_score > 0:
                return semantic_score
            # 否则使用简单的描述匹配
            elif intent.get('description') and self._text_contains_keywords(
                intent['description'], 
                str(profile)
            ):
                return 0.5
            return 0.0
        
        return score / weight_sum if weight_sum > 0 else 0.0
    
    def _calculate_keyword_score(self, keywords: List[str], profile: Dict) -> float:
        """计算关键词匹配分数"""
        if not keywords:
            return 0.0
        
        # 构建联系人文本
        profile_text = self._build_profile_text(profile).lower()
        
        matched = 0
        for keyword in keywords:
            if keyword.lower() in profile_text:
                matched += 1
        
        return matched / len(keywords)
    
    def _calculate_condition_score(self, conditions: List[Dict], profile: Dict, strict: bool) -> float:
        """计算条件匹配分数"""
        if not conditions:
            return 1.0
        
        matched = 0
        for condition in conditions:
            if self._check_condition(condition, profile):
                matched += 1
            elif strict:
                return 0.0  # 严格模式下，一个不满足就返回0
        
        return matched / len(conditions)
    
    def _check_condition(self, condition: Dict, profile: Dict) -> bool:
        """检查单个条件是否满足"""
        field = condition.get('field')
        operator = condition.get('operator', 'contains')
        value = condition.get('value')
        
        if not field or value is None:
            return False
        
        # 获取字段值
        profile_value = profile.get(field)
        if profile_value is None:
            return False
        
        profile_value_str = str(profile_value).lower()
        value_str = str(value).lower()
        
        # 根据操作符进行匹配
        if operator == 'eq':
            return profile_value_str == value_str
        elif operator == 'contains':
            return value_str in profile_value_str
        elif operator == 'in':
            if isinstance(value, list):
                return profile_value_str in [str(v).lower() for v in value]
            return False
        elif operator == 'gt':
            try:
                return float(profile_value) > float(value)
            except:
                return False
        elif operator == 'lt':
            try:
                return float(profile_value) < float(value)
            except:
                return False
        elif operator == 'between':
            if isinstance(value, list) and len(value) == 2:
                try:
                    return float(value[0]) <= float(profile_value) <= float(value[1])
                except:
                    return False
        
        return False
    
    def _build_profile_text(self, profile: Dict) -> str:
        """构建联系人的文本表示"""
        text_parts = []
        
        # 重要字段
        important_fields = [
            'profile_name', 'name', 'company', 'position', 
            'education', 'location', 'personality', 'ai_summary',
            'gender', 'age', 'marital_status', 'asset_level'
        ]
        
        for field in important_fields:
            value = profile.get(field)
            if value and value != '未知':
                text_parts.append(str(value))
        
        # 标签
        tags = profile.get('tags')
        if tags:
            try:
                if isinstance(tags, str):
                    tags = json.loads(tags)
                if isinstance(tags, list):
                    text_parts.extend(tags)
            except:
                pass
        
        return ' '.join(text_parts)
    
    def _text_contains_keywords(self, text: str, keywords: str) -> bool:
        """简单的文本包含检查"""
        text_lower = text.lower()
        keywords_lower = keywords.lower()
        
        # 简单的关键词匹配
        common_keywords = ['投资', '创业', '技术', 'AI', '管理', '销售', '市场']
        for keyword in common_keywords:
            if keyword.lower() in text_lower and keyword.lower() in keywords_lower:
                return True
        
        return False
    
    def _get_matched_conditions(self, intent: Dict, profile: Dict) -> List[str]:
        """获取匹配的条件列表"""
        matched = []
        conditions = intent.get('conditions', {})
        
        # 检查关键词
        keywords = conditions.get('keywords', [])
        profile_text = self._build_profile_text(profile).lower()
        
        for keyword in keywords:
            if keyword.lower() in profile_text:
                matched.append(f"包含关键词'{keyword}'")
        
        # 检查必要条件
        required = conditions.get('required', [])
        for condition in required:
            if self._check_condition(condition, profile):
                field = condition.get('field')
                value = condition.get('value')
                matched.append(f"{field}符合'{value}'")
        
        return matched[:5]  # 最多返回5个
    
    async def _generate_explanation(self, intent: Dict, profile: Dict, matched_conditions: List[str]) -> str:
        """生成匹配解释（AI增强版）"""
        profile_name = profile.get('profile_name', profile.get('name', '该联系人'))
        
        # 如果启用AI，尝试生成智能解释
        if self.use_ai and self.vector_service:
            try:
                # 计算匹配分数用于生成解释
                score = await self._calculate_match_score(intent, profile)
                
                # 使用AI生成解释
                ai_explanation = await self.vector_service.generate_match_explanation(
                    intent, profile, score, matched_conditions
                )
                
                if ai_explanation:
                    return ai_explanation
            except Exception as e:
                logger.warning(f"AI解释生成失败，使用规则生成: {e}")
        
        # 降级到规则生成
        if not matched_conditions:
            return f"{profile_name}综合评分较高，可能符合您的意图"
        
        if len(matched_conditions) >= 3:
            return f"{profile_name}完美匹配：{', '.join(matched_conditions[:3])}"
        elif len(matched_conditions) >= 1:
            return f"{profile_name}符合条件：{matched_conditions[0]}"
        else:
            return f"{profile_name}可能适合您的需求"
    
    def _save_match_record(self, cursor, intent_id: int, profile_id: int, 
                          user_id: str, score: float, 
                          matched_conditions: List[str], 
                          explanation: str, match_type: str = 'rule') -> int:
        """保存匹配记录"""
        try:
            # 检查是否已存在
            cursor.execute("""
                SELECT id FROM intent_matches 
                WHERE intent_id = ? AND profile_id = ?
            """, (intent_id, profile_id))
            
            existing = cursor.fetchone()
            if existing:
                # 更新现有记录
                cursor.execute("""
                    UPDATE intent_matches 
                    SET match_score = ?, matched_conditions = ?, 
                        explanation = ?, match_type = ?, created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    score,
                    json.dumps(matched_conditions, ensure_ascii=False),
                    explanation,
                    match_type,
                    existing[0]
                ))
                return existing[0]
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO intent_matches (
                        intent_id, profile_id, user_id, match_score,
                        matched_conditions, explanation, match_type, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    intent_id, profile_id, user_id, score,
                    json.dumps(matched_conditions, ensure_ascii=False),
                    explanation,
                    match_type
                ))
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"保存匹配记录失败: {e}")
            return 0
    
    def _save_hybrid_match_record(self, cursor, intent_id: int, profile_id: int, 
                                 user_id: str, result: Dict) -> int:
        """保存混合匹配记录（包含LLM信息）"""
        try:
            # 提取各种信息
            score = result.get('score', 0.0)
            match_type = result.get('match_type', 'hybrid')
            confidence = result.get('confidence', 0.5)
            matched_conditions = result.get('matched_conditions', [])
            matched_aspects = result.get('matched_aspects', [])
            missing_aspects = result.get('missing_aspects', [])
            explanation = result.get('explanation', '')
            suggestions = result.get('suggestions', '')
            
            # 获取分数细节
            scores_breakdown = result.get('scores_breakdown', {})
            vector_score = scores_breakdown.get('vector', 0.0)
            llm_score = scores_breakdown.get('llm', 0.0)
            
            # 构建扩展信息JSON
            extended_info = {
                'confidence': confidence,
                'matched_aspects': matched_aspects,
                'missing_aspects': missing_aspects,
                'suggestions': suggestions,
                'vector_score': vector_score,
                'llm_score': llm_score,
                'scores_breakdown': scores_breakdown
            }
            
            # 检查是否已存在
            cursor.execute("""
                SELECT id FROM intent_matches 
                WHERE intent_id = ? AND profile_id = ?
            """, (intent_id, profile_id))
            
            existing = cursor.fetchone()
            if existing:
                # 更新现有记录
                cursor.execute("""
                    UPDATE intent_matches 
                    SET match_score = ?, matched_conditions = ?, 
                        explanation = ?, match_type = ?, 
                        extended_info = ?, created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    score,
                    json.dumps(matched_conditions, ensure_ascii=False),
                    explanation,
                    match_type,
                    json.dumps(extended_info, ensure_ascii=False),
                    existing[0]
                ))
                return existing[0]
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO intent_matches (
                        intent_id, profile_id, user_id, match_score,
                        matched_conditions, explanation, match_type, 
                        extended_info, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    intent_id, profile_id, user_id, score,
                    json.dumps(matched_conditions, ensure_ascii=False),
                    explanation,
                    match_type,
                    json.dumps(extended_info, ensure_ascii=False)
                ))
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"保存混合匹配记录失败: {e}")
            # 如果extended_info字段不存在，尝试使用传统方法
            if "no column named extended_info" in str(e).lower():
                logger.info("数据库缺少extended_info字段，使用传统保存方法")
                return self._save_match_record(
                    cursor, intent_id, profile_id, user_id,
                    result.get('score', 0.0),
                    result.get('matched_conditions', []),
                    result.get('explanation', ''),
                    result.get('match_type', 'hybrid')
                )
            return 0
    
    def _get_user_table_name(self, user_id: str) -> str:
        """获取用户数据表名"""
        # 清理用户ID中的特殊字符
        clean_id = ''.join(c if c.isalnum() or c == '_' else '_' for c in user_id)
        return f"profiles_{clean_id}"

# 全局匹配引擎实例（启用最强LLM加成混合匹配）
intent_matcher = IntentMatcher(
    use_ai=True, 
    use_hybrid=True, 
    hybrid_mode="comprehensive"  # 使用全面模式：向量+规则+LLM判断
)