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
    
    async def match_intent_with_profiles(self, intent_id: int, user_id: str, regenerate_embedding: bool = False) -> List[Dict]:
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
            
            # 如果需要重新生成embedding
            if regenerate_embedding and self.vector_service:
                try:
                    description = intent.get('description', '')
                    conditions = intent.get('conditions', {})
                    
                    # 构建意图文本用于生成embedding
                    intent_text = f"{description}"
                    if conditions.get('keywords'):
                        intent_text += f" 关键词: {' '.join(conditions['keywords'])}"
                    
                    # 生成新的embedding
                    embedding = await self.vector_service.generate_embedding(intent_text)
                    
                    if embedding:
                        # 更新数据库中的embedding
                        import pickle
                        embedding_blob = pickle.dumps(embedding)
                        cursor.execute("""
                            UPDATE user_intents
                            SET embedding = ?
                            WHERE id = ? AND user_id = ?
                        """, (embedding_blob, intent_id, user_id))
                        
                        conn.commit()
                        logger.info(f"意图{intent_id}的embedding已重新生成")
                        
                        # 更新intent对象中的embedding
                        intent['embedding'] = embedding_blob
                except Exception as e:
                    logger.error(f"重新生成embedding失败: {e}")
            
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
                    intent_threshold = intent.get('threshold', 0.7)
                    profile_name = profile.get('profile_name', '未知联系人')
                    
                    # 记录阈值比较过程
                    logger.info(f"🎯 阈值判断: 意图={intent.get('name')} 联系人={profile_name}")
                    logger.info(f"   最终混合分数: {score:.3f}")
                    logger.info(f"   意图阈值: {intent_threshold:.3f}")
                    logger.info(f"   匹配结果: {score:.3f} {'≥' if score >= intent_threshold else '<'} {intent_threshold:.3f} = {'✅匹配成功' if score >= intent_threshold else '❌不匹配'}")
                    
                    # 只保留达到阈值的匹配
                    if score >= intent_threshold:
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
                        match_id, should_push = self._save_match_record(
                            cursor, intent_id, profile['id'], user_id,
                            score, matched_conditions, explanation, match_type
                        )
                        
                        if match_id and should_push:  # 只有新记录或显著改善时才添加到推送列表
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
                try:
                    for intent in intents:
                        logger.info(f"🔍 处理意图: {intent['name']} (阈值: {intent.get('threshold', 0.6)})")
                        
                        # 使用comprehensive模式获得最佳匹配结果
                        hybrid_results = await self.hybrid_matcher.match(
                            intent, [profile], 
                            mode=self.matching_mode
                        )
                        
                        logger.info(f"📊 混合匹配结果数量: {len(hybrid_results) if hybrid_results else 0}")
                        
                        if hybrid_results:
                            result = hybrid_results[0]  # 取第一个结果
                            score = result['score']
                            explanation = result.get('explanation', '')
                            matched_conditions = result.get('matched_conditions', [])
                            match_type = result.get('match_type', 'hybrid')
                            confidence = result.get('confidence', 0.8)
                            
                            logger.info(f"🎯 混合匹配详情: 意图={intent['name']}, 分数={score:.3f}, 类型={match_type}")
                            
                            # 使用意图自身设置的阈值，尊重用户的意图配置
                            intent_threshold = intent.get('threshold', 0.6)  # 默认0.6，但优先使用用户设置
                            logger.info(f"⚖️ 阈值判断: {score:.3f} >= {intent_threshold} = {score >= intent_threshold}")
                            
                            if score >= intent_threshold:
                                # 保存匹配记录
                                try:
                                    match_id, should_push = self._save_match_record(
                                        cursor, intent['id'], profile_id, user_id,
                                        score, matched_conditions, explanation, match_type
                                    )
                                    if match_id and should_push:
                                        logger.info(f"💾 新匹配记录保存成功: match_id={match_id}")
                                        
                                        matches.append({
                                            'match_id': match_id,
                                            'intent_id': intent['id'],
                                            'intent_name': intent['name'],
                                            'profile_id': profile_id,  # 添加profile_id
                                            'profile_name': profile.get('profile_name', '未知'),  # 添加profile_name
                                            'score': score,
                                            'matched_conditions': matched_conditions,
                                            'explanation': explanation,
                                            'match_type': match_type,
                                            'confidence': confidence
                                        })
                                    logger.info(f"✅ 混合匹配成功: {intent['name']} -> {profile.get('profile_name', 'Unknown')} (分数: {score:.2%})")
                                except Exception as save_error:
                                    logger.error(f"❌ 保存匹配记录失败: {save_error}")
                            else:
                                logger.info(f"❌ 分数未达到阈值: {intent['name']} ({score:.3f} < {intent_threshold})")
                        else:
                            logger.warning(f"⚠️ 混合匹配器未返回结果: {intent['name']}")
                            
                except Exception as hybrid_error:
                    logger.error(f"❌ 混合匹配器异常: {hybrid_error}")
                    import traceback
                    traceback.print_exc()
                    logger.info("🔄 降级到传统匹配模式")
                    # 发生异常时降级到传统匹配
                    matches = []  # 清空可能的部分结果
            else:
                # 使用传统匹配方法
                logger.info("🔄 使用传统意图匹配方法")
                for intent in intents:
                    score = await self._calculate_match_score(intent, profile)
                    
                    if score >= (intent.get('threshold', 0.7)):
                        matched_conditions = self._get_matched_conditions(intent, profile)
                        explanation = await self._generate_explanation(intent, profile, matched_conditions)
                        
                        # 保存匹配记录
                        match_id, should_push = self._save_match_record(
                            cursor, intent['id'], profile_id, user_id,
                            score, matched_conditions, explanation, 'traditional'
                        )
                        
                        if match_id and should_push:
                            matches.append({
                                'match_id': match_id,
                                'intent_id': intent['id'],
                                'intent_name': intent['name'],
                                'profile_id': profile_id,  # 添加profile_id
                                'profile_name': profile.get('profile_name', '未知'),  # 添加profile_name
                                'score': score,
                                'matched_conditions': matched_conditions,
                                'explanation': explanation,
                                'match_type': 'traditional'
                            })
            
            conn.commit()
            conn.close()
            
            logger.info(f"联系人 {profile_id} 匹配完成，找到 {len(matches)} 个匹配")
            
            # 如果有匹配结果，尝试推送通知
            if matches:
                try:
                    # 异步推送通知，不阻塞主流程
                    asyncio.create_task(self._async_push_matches(matches, user_id))
                    logger.info(f"已触发异步推送任务，共 {len(matches)} 个匹配")
                except Exception as push_error:
                    logger.warning(f"触发推送任务失败: {push_error}")
                    # 推送失败不影响主流程
            
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
                          explanation: str, match_type: str = 'rule') -> tuple:
        """保存匹配记录"""
        try:
            # 检查是否已存在
            cursor.execute("""
                SELECT id, match_score, is_read FROM intent_matches 
                WHERE intent_id = ? AND profile_id = ?
            """, (intent_id, profile_id))
            
            existing = cursor.fetchone()
            if existing:
                existing_id, existing_score, is_read = existing
                
                # 只有分数有显著变化时才更新（避免频繁更新）
                score_changed = abs(score - (existing_score or 0)) > 0.05
                
                if score_changed:
                    # 更新现有记录，但保留原始created_at和is_read状态
                    cursor.execute("""
                        UPDATE intent_matches 
                        SET match_score = ?, matched_conditions = ?, 
                            explanation = ?, match_type = ?, 
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        score,
                        json.dumps(matched_conditions, ensure_ascii=False),
                        explanation,
                        match_type,
                        existing_id
                    ))
                    
                    # 只有在分数大幅提升时才重置为未读（从0.1改为0.3，避免频繁触发）
                    # 并且需要间隔24小时以上才能再次提醒
                    if score - (existing_score or 0) > 0.3 and is_read == 1:
                        # 检查上次更新时间，避免频繁提醒
                        cursor.execute("""
                            SELECT updated_at FROM intent_matches 
                            WHERE id = ? 
                            AND datetime(updated_at) < datetime('now', '-24 hours')
                        """, (existing_id,))
                        
                        if cursor.fetchone():
                            # 距离上次更新超过24小时，才重置为未读
                            cursor.execute("""
                                UPDATE intent_matches 
                                SET is_read = 0
                                WHERE id = ?
                            """, (existing_id,))
                            logger.info(f"匹配分数显著提升且超过24小时，重置为未读: intent_id={intent_id}, profile_id={profile_id}")
                            return (existing_id, True)  # 返回ID和需要推送标志
                        else:
                            logger.debug(f"匹配分数提升但未超过24小时冷却期，不重置: intent_id={intent_id}, profile_id={profile_id}")
                            return (existing_id, False)
                
                return (existing_id, False)  # 已存在且无需推送
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
                return (cursor.lastrowid, True)  # 新记录需要推送
                
        except Exception as e:
            logger.error(f"保存匹配记录失败: {e}")
            return (0, False)
    
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
                SELECT id, match_score, is_read FROM intent_matches 
                WHERE intent_id = ? AND profile_id = ?
            """, (intent_id, profile_id))
            
            existing = cursor.fetchone()
            if existing:
                existing_id, existing_score, is_read = existing
                
                # 只有分数有显著变化时才更新
                score_changed = abs(score - (existing_score or 0)) > 0.05
                
                if score_changed:
                    # 更新现有记录，但保留原始created_at和is_read状态
                    cursor.execute("""
                        UPDATE intent_matches 
                        SET match_score = ?, matched_conditions = ?, 
                            explanation = ?, match_type = ?, 
                            extended_info = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        score,
                        json.dumps(matched_conditions, ensure_ascii=False),
                        explanation,
                        match_type,
                        json.dumps(extended_info, ensure_ascii=False),
                        existing_id
                    ))
                    
                    # 如果分数显著提升且之前已读，可以重置为未读
                    if score - (existing_score or 0) > 0.1 and is_read == 1:
                        cursor.execute("""
                            UPDATE intent_matches 
                            SET is_read = 0
                            WHERE id = ?
                        """, (existing_id,))
                        logger.info(f"混合匹配分数显著提升，重置为未读: intent_id={intent_id}, profile_id={profile_id}")
                
                return existing_id
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
                match_id, _ = self._save_match_record(
                    cursor, intent_id, profile_id, user_id,
                    result.get('score', 0.0),
                    result.get('matched_conditions', []),
                    result.get('explanation', ''),
                    result.get('match_type', 'hybrid')
                )
                return match_id
            return 0
    
    def _get_user_table_name(self, user_id: str) -> str:
        """获取用户数据表名"""
        # 清理用户ID中的特殊字符
        clean_id = ''.join(c if c.isalnum() or c == '_' else '_' for c in user_id)
        return f"profiles_{clean_id}"
    
    async def _async_push_matches(self, matches: List[Dict], user_id: str):
        """
        异步推送匹配结果通知
        
        Args:
            matches: 匹配结果列表
            user_id: 用户ID
        """
        try:
            # 导入推送服务
            from .push_service import push_service
            
            logger.info(f"开始异步推送 {len(matches)} 个匹配结果给用户 {user_id}")
            
            # 批量处理推送
            push_service.batch_process_matches(matches, user_id)
            
            # 暂时禁用微信客服通知，避免错误
            # 小程序会通过轮询API获取通知
            logger.info(f"✅ 匹配通知已记录，等待小程序轮询获取")
            
        except Exception as e:
            logger.error(f"异步推送失败: {e}")
    
    async def _send_wechat_notification(self, matches: List[Dict], user_id: str):
        """
        发送微信客服通知
        
        Args:
            matches: 匹配结果列表
            user_id: 用户ID
        """
        try:
            # 检查是否有企业微信客户端
            from ..services.wework_client import wework_client
            
            # 对于测试用户，直接使用user_id作为external_userid
            # 实际生产环境应该查询绑定关系
            external_userid = user_id  # 简化处理：直接使用user_id
            
            logger.info(f"准备发送微信通知给用户 {user_id} (external_userid: {external_userid})")
            
            # 构建通知消息
            message_lines = [
                "🎯 找到新的匹配联系人！",
                ""
            ]
            
            for i, match in enumerate(matches[:3], 1):  # 最多显示3个
                intent_name = match.get('intent_name', '未知意图')
                profile_name = match.get('profile_name', '未知联系人')
                score = match.get('score', 0)
                explanation = match.get('explanation', '')
                
                message_lines.append(f"{i}. [{intent_name}]")
                message_lines.append(f"   匹配联系人：{profile_name}")
                message_lines.append(f"   匹配度：{score:.0%}")
                if explanation:
                    # 限制解释长度
                    if len(explanation) > 50:
                        explanation = explanation[:50] + "..."
                    message_lines.append(f"   原因：{explanation}")
                message_lines.append("")
            
            if len(matches) > 3:
                message_lines.append(f"... 还有 {len(matches) - 3} 个匹配")
                message_lines.append("")
            
            message_lines.append("💡 登录小程序查看详情")
            
            message_text = "\n".join(message_lines)
            
            # 发送微信消息
            # 获取客服账号ID
            from ..config.config import config
            open_kfid = config.wechat_kf_id
            
            result = wework_client.send_text_message(
                external_userid=external_userid,
                open_kfid=open_kfid,
                content=message_text  # 修正参数名
            )
            
            if result:
                logger.info(f"微信通知发送成功给用户 {user_id} (external_userid: {external_userid})")
            else:
                logger.warning(f"微信通知发送失败给用户 {user_id}")
                
        except Exception as e:
            logger.error(f"发送微信通知失败: {e}")
            raise
    
    async def reevaluate_intent_threshold(self, intent_id: int, user_id: str, new_threshold: float) -> int:
        """
        重新评估意图的阈值（不重新计算匹配分数）
        
        Args:
            intent_id: 意图ID
            user_id: 用户ID
            new_threshold: 新的阈值
            
        Returns:
            更新的匹配记录数量
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            updated_count = 0
            
            # 获取该意图的所有匹配记录
            cursor.execute("""
                SELECT id, match_score, is_pushed
                FROM intent_matches
                WHERE intent_id = ? AND user_id = ?
                ORDER BY match_score DESC
            """, (intent_id, user_id))
            
            matches = cursor.fetchall()
            
            for match_id, score, is_pushed in matches:
                # 根据新阈值判断是否应该保留或删除匹配
                if score < new_threshold:
                    # 分数低于新阈值，删除匹配记录
                    cursor.execute("""
                        DELETE FROM intent_matches
                        WHERE id = ?
                    """, (match_id,))
                    updated_count += 1
                    logger.info(f"删除低于新阈值的匹配: match_id={match_id}, score={score:.3f} < {new_threshold:.3f}")
                else:
                    # 分数高于阈值，保留记录
                    logger.debug(f"保留匹配: match_id={match_id}, score={score:.3f} >= {new_threshold:.3f}")
            
            # 提交更改
            conn.commit()
            conn.close()
            
            logger.info(f"意图{intent_id}阈值重新评估完成，更新了{updated_count}个匹配记录")
            return updated_count
            
        except Exception as e:
            logger.error(f"重新评估意图阈值失败: {e}")
            if conn:
                conn.close()
            raise
    

# 全局匹配引擎实例（启用最强LLM加成混合匹配）
intent_matcher = IntentMatcher(
    use_ai=True, 
    use_hybrid=True, 
    hybrid_mode="comprehensive"  # 使用全面模式：向量+规则+LLM判断
)