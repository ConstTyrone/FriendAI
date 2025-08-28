"""
关系发现服务
用于自动发现联系人之间的潜在关系
"""

import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher
import re

# 导入AI关系分析器
try:
    from .ai_relationship_analyzer import AIRelationshipAnalyzer
    AI_AVAILABLE = True
except ImportError as e:
    AI_AVAILABLE = False
    AIRelationshipAnalyzer = None

logger = logging.getLogger(__name__)

class RelationshipService:
    """关系发现服务类"""
    
    def __init__(self, database):
        """
        初始化关系发现服务
        
        Args:
            database: 数据库实例
        """
        self.db = database
        self.rules_cache = {}  # 缓存检测规则
        
        # 初始化AI分析器
        self.ai_analyzer = AIRelationshipAnalyzer() if AI_AVAILABLE else None
        if self.ai_analyzer:
            logger.info("AI关系分析器初始化成功")
        else:
            logger.info("AI关系分析器不可用，使用传统规则匹配")
            
        self._load_detection_rules()
        
    def _load_detection_rules(self):
        """从数据库加载关系检测规则"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM relationship_rules 
                    WHERE is_active = 1 
                    ORDER BY priority DESC
                """)
                rules = cursor.fetchall()
                
                self.rules_cache = {}
                for rule in rules:
                    rule_dict = dict(rule)
                    # 解析JSON字段
                    for field in ['field_mappings', 'conditions', 'exclusions']:
                        if field in rule_dict and rule_dict[field]:
                            try:
                                rule_dict[field] = json.loads(rule_dict[field])
                            except:
                                rule_dict[field] = {} if field != 'exclusions' else []
                    
                    self.rules_cache[rule_dict['rule_name']] = rule_dict
                    
                logger.info(f"✅ 加载了 {len(self.rules_cache)} 个关系检测规则")
        except Exception as e:
            logger.error(f"加载关系检测规则失败: {e}")
            self.rules_cache = {}
    
    def discover_relationships_for_profile(self, user_id: str, profile_id: int, profile_data: Dict) -> List[Dict]:
        """
        为特定的联系人发现关系
        
        Args:
            user_id: 用户ID
            profile_id: 联系人ID
            profile_data: 联系人数据
            
        Returns:
            发现的关系列表
        """
        start_time = time.time()
        discovered_relationships = []
        
        try:
            # 获取用户的所有其他联系人
            table_name = self.db._get_user_table_name(user_id)
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 查询其他联系人（排除自己）
                cursor.execute(f"""
                    SELECT * FROM {table_name}
                    WHERE id != ? AND profile_name != ?
                """, (profile_id, profile_data.get('profile_name', '')))
                
                other_profiles = cursor.fetchall()
                profiles_scanned = len(other_profiles)
                
                # 遍历其他联系人，检测关系
                for other_profile in other_profiles:
                    other_data = dict(other_profile)
                    
                    # 应用所有规则
                    relationships = self._apply_detection_rules(
                        profile_data, other_data, user_id
                    )
                    
                    for relationship in relationships:
                        # 添加额外信息
                        relationship.update({
                            'user_id': user_id,
                            'source_profile_id': profile_id,
                            'source_profile_name': profile_data.get('profile_name'),
                            'target_profile_id': other_data['id'],
                            'target_profile_name': other_data['profile_name']
                        })
                        discovered_relationships.append(relationship)
                
                # 保存发现的关系
                if discovered_relationships:
                    self._save_relationships(discovered_relationships)
                
                # 记录发现日志
                duration_ms = int((time.time() - start_time) * 1000)
                self._log_discovery(
                    user_id=user_id,
                    trigger_type='profile_create',
                    trigger_profile_id=profile_id,
                    trigger_profile_name=profile_data.get('profile_name'),
                    relationships_found=len(discovered_relationships),
                    scan_duration_ms=duration_ms,
                    profiles_scanned=profiles_scanned,
                    rules_applied=len(self.rules_cache)
                )
                
                logger.info(f"✅ 为 {profile_data.get('profile_name')} 发现了 {len(discovered_relationships)} 个关系")
                
        except Exception as e:
            logger.error(f"发现关系失败: {e}")
            
        return discovered_relationships
    
    def _apply_detection_rules(self, source: Dict, target: Dict, user_id: str) -> List[Dict]:
        """
        应用所有检测规则
        
        Args:
            source: 源联系人数据
            target: 目标联系人数据
            user_id: 用户ID
            
        Returns:
            检测到的关系列表
        """
        detected_relationships = []
        
        for rule_name, rule in self.rules_cache.items():
            try:
                # 检查规则类型
                if rule['rule_type'] == 'field_match':
                    match_result = self._check_field_match(source, target, rule)
                    if match_result:
                        detected_relationships.append(match_result)
                        
            except Exception as e:
                logger.warning(f"应用规则 {rule_name} 失败: {e}")
                
        # 合并相同类型的关系，选择置信度最高的
        merged = {}
        for rel in detected_relationships:
            key = rel['relationship_type']
            if key not in merged or rel['confidence_score'] > merged[key]['confidence_score']:
                merged[key] = rel
                
        return list(merged.values())
    
    def _check_field_match(self, source: Dict, target: Dict, rule: Dict) -> Optional[Dict]:
        """
        检查字段匹配规则
        
        Args:
            source: 源联系人数据
            target: 目标联系人数据  
            rule: 检测规则
            
        Returns:
            如果匹配返回关系信息，否则返回None
        """
        field_mappings = rule.get('field_mappings', {})
        if not field_mappings:
            return None
            
        source_field = field_mappings.get('source')
        target_field = field_mappings.get('target')
        
        if not source_field or not target_field:
            return None
            
        # 获取字段值
        source_value = source.get(source_field) or ''
        target_value = target.get(target_field) or ''
        
        # 确保是字符串并去除空格
        source_value = str(source_value).strip() if source_value else ''
        target_value = str(target_value).strip() if target_value else ''
        
        if not source_value or not target_value:
            return None
            
        # 根据匹配逻辑进行比较
        matching_logic = rule.get('matching_logic', 'exact')
        threshold = rule.get('matching_threshold', 0.8)
        
        confidence_score = 0.0
        matched = False
        evidence = {}
        
        if matching_logic == 'exact':
            # 精确匹配
            if source_value.lower() == target_value.lower():
                matched = True
                confidence_score = 1.0
                evidence['match_type'] = 'exact'
                evidence['matched_values'] = f"{source_value} == {target_value}"
                
        elif matching_logic == 'fuzzy':
            # 模糊匹配
            similarity = self._calculate_similarity(source_value, target_value)
            if similarity >= threshold:
                matched = True
                confidence_score = similarity
                evidence['match_type'] = 'fuzzy'
                evidence['similarity'] = similarity
                evidence['matched_values'] = f"{source_value} ~= {target_value}"
                
        elif matching_logic == 'contains':
            # 包含匹配
            if source_value.lower() in target_value.lower() or target_value.lower() in source_value.lower():
                matched = True
                # 计算置信度基于重叠程度
                shorter = min(len(source_value), len(target_value))
                longer = max(len(source_value), len(target_value))
                confidence_score = shorter / longer if longer > 0 else 0
                confidence_score = max(confidence_score, threshold)  # 至少达到阈值
                evidence['match_type'] = 'contains'
                evidence['matched_values'] = f"{source_value} ⊂ {target_value}"
                
        if matched:
            # 应用规则权重
            confidence_score *= rule.get('weight', 1.0)
            
            return {
                'relationship_type': rule['relationship_type'],
                'relationship_subtype': None,
                'relationship_direction': 'bidirectional',
                'confidence_score': min(confidence_score, 1.0),
                'evidence': evidence,
                'evidence_fields': f"{source_field}",
                'matching_method': rule['rule_type'],
                'status': 'discovered'
            }
            
        return None
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        计算两个字符串的相似度
        
        Args:
            str1: 第一个字符串
            str2: 第二个字符串
            
        Returns:
            相似度分数（0-1）
        """
        # 预处理：转小写，去除空格和特殊字符
        str1 = re.sub(r'[^\w\s]', '', str1.lower()).strip()
        str2 = re.sub(r'[^\w\s]', '', str2.lower()).strip()
        
        if not str1 or not str2:
            return 0.0
            
        # 使用SequenceMatcher计算相似度
        similarity = SequenceMatcher(None, str1, str2).ratio()
        
        # 检查是否有公共子串（处理缩写等情况）
        # 例如："腾讯科技" 和 "腾讯"
        if str1 in str2 or str2 in str1:
            # 提高相似度分数
            overlap_bonus = 0.2
            similarity = min(1.0, similarity + overlap_bonus)
            
        return similarity
    
    def _save_relationships(self, relationships: List[Dict]):
        """
        保存发现的关系到数据库
        
        Args:
            relationships: 关系列表
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                for rel in relationships:
                    # 检查是否已存在相同的关系
                    cursor.execute("""
                        SELECT id FROM relationships
                        WHERE user_id = ? AND source_profile_id = ? 
                        AND target_profile_id = ? AND relationship_type = ?
                    """, (
                        rel['user_id'], 
                        rel['source_profile_id'],
                        rel['target_profile_id'],
                        rel['relationship_type']
                    ))
                    
                    existing = cursor.fetchone()
                    
                    if not existing:
                        # 插入新关系
                        cursor.execute("""
                            INSERT INTO relationships (
                                user_id, source_profile_id, source_profile_name,
                                target_profile_id, target_profile_name,
                                relationship_type, relationship_subtype, relationship_direction,
                                confidence_score, evidence, evidence_fields,
                                matching_method, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            rel['user_id'],
                            rel['source_profile_id'],
                            rel['source_profile_name'],
                            rel['target_profile_id'],
                            rel['target_profile_name'],
                            rel['relationship_type'],
                            rel.get('relationship_subtype'),
                            rel.get('relationship_direction', 'bidirectional'),
                            rel['confidence_score'],
                            json.dumps(rel.get('evidence', {})),
                            rel.get('evidence_fields', ''),
                            rel.get('matching_method', ''),
                            rel.get('status', 'discovered')
                        ))
                    else:
                        # 更新现有关系的置信度（如果新的更高）
                        cursor.execute("""
                            UPDATE relationships
                            SET confidence_score = MAX(confidence_score, ?),
                                evidence = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (
                            rel['confidence_score'],
                            json.dumps(rel.get('evidence', {})),
                            existing[0]
                        ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"保存关系失败: {e}")
    
    def _log_discovery(self, **kwargs):
        """记录关系发现日志"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO relationship_discovery_logs (
                        user_id, trigger_type, trigger_profile_id, trigger_profile_name,
                        relationships_found, scan_duration_ms, profiles_scanned, rules_applied
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    kwargs.get('user_id'),
                    kwargs.get('trigger_type'),
                    kwargs.get('trigger_profile_id'),
                    kwargs.get('trigger_profile_name'),
                    kwargs.get('relationships_found', 0),
                    kwargs.get('scan_duration_ms', 0),
                    kwargs.get('profiles_scanned', 0),
                    kwargs.get('rules_applied', 0)
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.warning(f"记录发现日志失败: {e}")
    
    def get_profile_relationships(self, user_id: str, profile_id: int) -> List[Dict]:
        """
        获取某个联系人的所有关系
        
        Args:
            user_id: 用户ID
            profile_id: 联系人ID
            
        Returns:
            关系列表
        """
        try:
            logger.info(f"🔍 特定联系人关系查询开始 - 用户ID: {user_id}, 联系人ID: {profile_id}")
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 首先检查该联系人相关的关系总数
                cursor.execute("""
                    SELECT COUNT(*) FROM relationships 
                    WHERE user_id = ? AND (source_profile_id = ? OR target_profile_id = ?)
                """, (user_id, profile_id, profile_id))
                total_count = cursor.fetchone()[0]
                logger.info(f"📊 联系人 {profile_id} 相关的总关系数量: {total_count}")
                
                # 检查活跃关系数量
                cursor.execute("""
                    SELECT COUNT(*) FROM relationships 
                    WHERE user_id = ? AND (source_profile_id = ? OR target_profile_id = ?)
                    AND status != 'deleted'
                """, (user_id, profile_id, profile_id))
                active_count = cursor.fetchone()[0]
                logger.info(f"📊 联系人 {profile_id} 相关的活跃关系数量: {active_count}")
                
                cursor.execute("""
                    SELECT * FROM relationships
                    WHERE user_id = ? 
                    AND (source_profile_id = ? OR target_profile_id = ?)
                    AND status != 'deleted'
                    ORDER BY confidence_score DESC
                """, (user_id, profile_id, profile_id))
                
                relationships = []
                rows = cursor.fetchall()
                logger.info(f"📊 联系人关系SQL查询返回行数: {len(rows)}")
                
                for row in rows:
                    rel = dict(row)
                    logger.info(f"📋 联系人关系记录: ID={rel.get('id')}, source={rel.get('source_profile_id')}, target={rel.get('target_profile_id')}, status={rel.get('status')}")
                    
                    # 解析JSON字段
                    if rel.get('evidence'):
                        try:
                            rel['evidence'] = json.loads(rel['evidence'])
                        except:
                            rel['evidence'] = {}
                            
                    relationships.append(rel)
                    
                logger.info(f"✅ 特定联系人关系查询完成 - 返回 {len(relationships)} 个关系")
                return relationships
                
        except Exception as e:
            logger.error(f"❌ 获取联系人关系失败: {e}")
            return []
    
    def get_all_relationships(self, user_id: str) -> List[Dict]:
        """
        获取用户的所有关系
        
        Args:
            user_id: 用户ID
            
        Returns:
            关系列表
        """
        try:
            logger.info(f"🔍 全局关系查询开始 - 用户ID: {user_id}")
            
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 首先检查relationships表中是否有数据
                cursor.execute("SELECT COUNT(*) FROM relationships WHERE user_id = ?", (user_id,))
                total_count = cursor.fetchone()[0]
                logger.info(f"📊 用户 {user_id} 的总关系数量: {total_count}")
                
                # 检查有多少非删除状态的关系
                cursor.execute("SELECT COUNT(*) FROM relationships WHERE user_id = ? AND status != 'deleted'", (user_id,))
                active_count = cursor.fetchone()[0]
                logger.info(f"📊 用户 {user_id} 的活跃关系数量: {active_count}")
                
                # 查看所有状态的关系
                cursor.execute("SELECT status, COUNT(*) FROM relationships WHERE user_id = ? GROUP BY status", (user_id,))
                status_stats = cursor.fetchall()
                logger.info(f"📊 用户 {user_id} 的关系状态分布: {status_stats}")
                
                cursor.execute("""
                    SELECT * FROM relationships
                    WHERE user_id = ? 
                    AND status != 'deleted'
                    ORDER BY confidence_score DESC
                """, (user_id,))
                
                relationships = []
                rows = cursor.fetchall()
                logger.info(f"📊 SQL查询返回行数: {len(rows)}")
                
                for row in rows:
                    rel = dict(row)
                    logger.info(f"📋 关系记录: ID={rel.get('id')}, source={rel.get('source_profile_id')}, target={rel.get('target_profile_id')}, status={rel.get('status')}")
                    
                    # 解析JSON字段
                    if rel.get('evidence'):
                        try:
                            rel['evidence'] = json.loads(rel['evidence'])
                        except:
                            rel['evidence'] = {}
                            
                    relationships.append(rel)
                
                logger.info(f"✅ 全局关系查询完成 - 返回 {len(relationships)} 个关系")
                return relationships
                
        except Exception as e:
            logger.error(f"❌ 获取所有关系失败: {e}")
            return []
    
    def confirm_relationship(self, user_id: str, relationship_id: int, confirmed: bool = True) -> bool:
        """
        确认或否认一个关系
        
        Args:
            user_id: 用户ID
            relationship_id: 关系ID
            confirmed: 是否确认
            
        Returns:
            是否成功
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                if confirmed:
                    cursor.execute("""
                        UPDATE relationships
                        SET status = 'confirmed',
                            confirmed_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND user_id = ?
                    """, (relationship_id, user_id))
                else:
                    cursor.execute("""
                        UPDATE relationships
                        SET status = 'ignored',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND user_id = ?
                    """, (relationship_id, user_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"确认关系失败: {e}")
            return False
    
    def get_relationship_stats(self, user_id: str) -> Dict:
        """
        获取关系统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            统计信息
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 总关系数
                cursor.execute("""
                    SELECT COUNT(*) FROM relationships
                    WHERE user_id = ? AND status != 'deleted'
                """, (user_id,))
                total = cursor.fetchone()[0]
                
                # 已确认的关系
                cursor.execute("""
                    SELECT COUNT(*) FROM relationships
                    WHERE user_id = ? AND status = 'confirmed'
                """, (user_id,))
                confirmed = cursor.fetchone()[0]
                
                # 按类型统计
                cursor.execute("""
                    SELECT relationship_type, COUNT(*) as count
                    FROM relationships
                    WHERE user_id = ? AND status != 'deleted'
                    GROUP BY relationship_type
                """, (user_id,))
                
                by_type = {}
                for row in cursor.fetchall():
                    by_type[row[0]] = row[1]
                
                return {
                    'total_relationships': total,
                    'confirmed_relationships': confirmed,
                    'discovered_relationships': total - confirmed,
                    'relationships_by_type': by_type
                }
                
        except Exception as e:
            logger.error(f"获取关系统计失败: {e}")
            return {
                'total_relationships': 0,
                'confirmed_relationships': 0,
                'discovered_relationships': 0,
                'relationships_by_type': {}
            }
    
    def delete_discovered_relationships(self, user_id: str, profile_id: int) -> int:
        """删除某个联系人的已发现但未确认的关系"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 删除状态为'discovered'的关系记录
                cursor.execute("""
                    DELETE FROM relationships 
                    WHERE user_id = ? 
                    AND (source_profile_id = ? OR target_profile_id = ?) 
                    AND status = 'discovered'
                """, (user_id, profile_id, profile_id))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"删除了联系人 {profile_id} 的 {deleted_count} 个未确认关系")
                return deleted_count
                
        except Exception as e:
            logger.error(f"删除已发现关系失败: {e}")
            return 0
    
    def get_relationship_detail(self, user_id: str, relationship_id: int) -> Optional[Dict]:
        """获取关系的详细信息"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 获取关系详情，包含所有字段
                cursor.execute("""
                    SELECT 
                        id, user_id, 
                        source_profile_id, source_profile_name,
                        target_profile_id, target_profile_name,
                        relationship_type, relationship_subtype, relationship_direction,
                        confidence_score, relationship_strength,
                        evidence, evidence_fields, matching_method,
                        status, confirmed_by, confirmed_at,
                        metadata, tags,
                        discovered_at, updated_at
                    FROM relationships 
                    WHERE user_id = ? AND id = ?
                """, (user_id, relationship_id))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # 将行数据转换为字典
                columns = [
                    'id', 'user_id',
                    'source_profile_id', 'source_profile_name', 
                    'target_profile_id', 'target_profile_name',
                    'relationship_type', 'relationship_subtype', 'relationship_direction',
                    'confidence_score', 'relationship_strength',
                    'evidence', 'evidence_fields', 'matching_method',
                    'status', 'confirmed_by', 'confirmed_at',
                    'metadata', 'tags',
                    'discovered_at', 'updated_at'
                ]
                
                relationship = dict(zip(columns, row))
                
                # 解析JSON字段
                try:
                    if relationship['evidence']:
                        import json
                        relationship['evidence'] = json.loads(relationship['evidence'])
                except:
                    relationship['evidence'] = {}
                    
                try:
                    if relationship['metadata']:
                        import json
                        relationship['metadata'] = json.loads(relationship['metadata'])
                except:
                    relationship['metadata'] = {}
                
                return relationship
                
        except Exception as e:
            logger.error(f"获取关系详情失败: {e}")
            return None
    
    def discover_relationships_with_ai(self, user_id: str, profile_id: int, profile_data: Dict) -> List[Dict]:
        """
        使用AI增强的关系发现
        
        Args:
            user_id: 微信用户ID
            profile_id: 联系人ID
            profile_data: 联系人数据
            
        Returns:
            发现的关系列表
        """
        try:
            logger.info(f"开始AI增强关系发现，用户: {user_id}, 联系人: {profile_id}")
            
            # 获取所有其他联系人
            other_profiles = self._get_other_profiles(user_id, profile_id)
            
            if not other_profiles:
                logger.info("没有其他联系人，无法进行关系发现")
                return []
            
            discovered_relationships = []
            
            # 如果AI可用，优先使用AI分析
            if self.ai_analyzer:
                ai_relationships = self._discover_with_ai(profile_data, other_profiles)
                discovered_relationships.extend(ai_relationships)
            
            # 使用传统规则作为补充或备用
            rule_relationships = self._apply_detection_rules(profile_data, other_profiles[0], user_id)
            
            # 合并和去重
            final_relationships = self._merge_relationship_results(
                discovered_relationships, 
                rule_relationships,
                user_id,
                profile_id
            )
            
            # 保存发现的关系
            if final_relationships:
                self._save_relationships(final_relationships)
                
            # 记录发现日志
            self._log_discovery(
                user_id=user_id,
                trigger_type='ai_enhanced_scan',
                trigger_profile_id=profile_id,
                trigger_profile_name=profile_data.get('profile_name', profile_data.get('name', '未知')),
                relationships_found=len(final_relationships),
                ai_used=bool(self.ai_analyzer)
            )
            
            logger.info(f"AI增强关系发现完成，发现 {len(final_relationships)} 个关系")
            return final_relationships
            
        except Exception as e:
            logger.error(f"AI增强关系发现失败: {e}")
            return []
    
    def _discover_with_ai(self, target_profile: Dict, other_profiles: List[Dict]) -> List[Dict]:
        """使用AI发现关系"""
        ai_relationships = []
        
        try:
            for other_profile in other_profiles:
                # 使用AI分析器分析关系
                analysis = self.ai_analyzer.analyze_relationship_with_ai(target_profile, other_profile)
                
                # 只保留置信度足够的关系
                if analysis.get('confidence_score', 0) >= 0.4:  # 可配置阈值
                    ai_relationship = {
                        'source_profile_id': target_profile.get('id'),
                        'source_profile_name': target_profile.get('profile_name', target_profile.get('name', '未知')),
                        'target_profile_id': other_profile.get('id'),
                        'target_profile_name': other_profile.get('profile_name', other_profile.get('name', '未知')),
                        
                        'relationship_type': analysis.get('relationship_type', 'colleague'),
                        'relationship_subtype': analysis.get('relationship_subtype', ''),
                        'relationship_direction': analysis.get('relationship_direction', 'bidirectional'),
                        'confidence_score': analysis.get('confidence_score', 0.5),
                        'relationship_strength': analysis.get('relationship_strength', 'medium'),
                        
                        'evidence': json.dumps(analysis.get('evidence', {}), ensure_ascii=False),
                        'evidence_fields': ','.join(analysis.get('matched_fields', [])),
                        'matching_method': 'ai_inference',
                        
                        'metadata': json.dumps({
                            'ai_reasoning': analysis.get('ai_reasoning', ''),
                            'explanation': analysis.get('explanation', ''),
                            'analysis_metadata': analysis.get('analysis_metadata', {}),
                            'enhanced_by_ai': True
                        }, ensure_ascii=False),
                        
                        'status': 'discovered',
                        'discovered_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    ai_relationships.append(ai_relationship)
                    
                # 避免API频率限制
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"AI关系发现过程失败: {e}")
            
        return ai_relationships
    
    def _merge_relationship_results(self, ai_relationships: List[Dict], rule_relationships: List[Dict], 
                                  user_id: str, profile_id: int) -> List[Dict]:
        """
        合并AI和规则发现的关系结果
        
        Args:
            ai_relationships: AI发现的关系
            rule_relationships: 规则发现的关系
            user_id: 用户ID
            profile_id: 联系人ID
            
        Returns:
            合并后的关系列表
        """
        try:
            merged = {}  # 用于去重的字典
            
            # 添加AI关系（优先级高）
            for rel in ai_relationships:
                key = f"{rel['source_profile_id']}-{rel['target_profile_id']}-{rel['relationship_type']}"
                merged[key] = {
                    **rel,
                    'user_id': user_id,
                    'primary_discovery_method': 'ai'
                }
            
            # 添加规则关系（作为补充）
            for rel in rule_relationships:
                key = f"{rel['source_profile_id']}-{rel['target_profile_id']}-{rel['relationship_type']}"
                
                if key not in merged:
                    # 新关系，直接添加
                    merged[key] = {
                        **rel,
                        'user_id': user_id,
                        'primary_discovery_method': 'rules'
                    }
                else:
                    # 关系已存在，合并证据
                    existing = merged[key]
                    if existing.get('primary_discovery_method') == 'ai':
                        # 保持AI结果，但添加规则证据
                        try:
                            existing_evidence = json.loads(existing.get('evidence', '{}'))
                            rule_evidence = json.loads(rel.get('evidence', '{}'))
                            
                            combined_evidence = {**existing_evidence, **rule_evidence}
                            existing['evidence'] = json.dumps(combined_evidence, ensure_ascii=False)
                            
                            # 合并匹配字段
                            existing_fields = set(existing.get('evidence_fields', '').split(','))
                            rule_fields = set(rel.get('evidence_fields', '').split(','))
                            combined_fields = existing_fields | rule_fields
                            existing['evidence_fields'] = ','.join(filter(None, combined_fields))
                            
                        except (json.JSONDecodeError, Exception) as e:
                            logger.warning(f"合并证据失败: {e}")
            
            return list(merged.values())
            
        except Exception as e:
            logger.error(f"合并关系结果失败: {e}")
            return ai_relationships or rule_relationships
    
    def get_ai_relationship_suggestions(self, user_id: str, profile_id: int, limit: int = 10) -> List[Dict]:
        """
        获取AI关系建议
        
        Args:
            user_id: 用户ID
            profile_id: 目标联系人ID
            limit: 返回数量限制
            
        Returns:
            关系建议列表
        """
        if not self.ai_analyzer:
            return []
            
        try:
            # 获取目标联系人
            target_profile = self.db.get_user_profile_detail(user_id, profile_id)
            if not target_profile:
                return []
            
            # 获取所有候选联系人
            candidate_profiles = self._get_other_profiles(user_id, profile_id)
            if not candidate_profiles:
                return []
            
            # 使用AI分析器获取建议
            suggestions = self.ai_analyzer.get_relationship_suggestions(
                target_profile, 
                candidate_profiles, 
                top_k=limit
            )
            
            return suggestions
            
        except Exception as e:
            logger.error(f"获取AI关系建议失败: {e}")
            return []
    
    def analyze_relationship_quality(self, user_id: str, relationship_id: int) -> Dict:
        """
        分析关系质量
        
        Args:
            user_id: 用户ID
            relationship_id: 关系ID
            
        Returns:
            关系质量分析结果
        """
        try:
            # 获取关系详情
            relationship = self.get_relationship_detail(user_id, relationship_id)
            if not relationship:
                return {'error': '关系不存在'}
            
            # 基础质量分析
            quality_score = relationship.get('confidence_score', 0.5)
            
            # 证据强度分析
            evidence_fields = relationship.get('evidence_fields', '')
            field_count = len([f for f in evidence_fields.split(',') if f.strip()])
            
            # 匹配方法权重
            method_weights = {
                'ai_inference': 1.0,
                'exact': 0.9,
                'fuzzy': 0.7,
                'pattern_match': 0.6
            }
            
            method_weight = method_weights.get(relationship.get('matching_method', 'fuzzy'), 0.5)
            
            # 综合质量评分
            final_score = (quality_score * 0.6) + (min(field_count / 3, 1.0) * 0.2) + (method_weight * 0.2)
            
            # 质量等级
            if final_score >= 0.8:
                quality_level = 'excellent'
                quality_desc = '高质量关系'
            elif final_score >= 0.6:
                quality_level = 'good'
                quality_desc = '良好关系'
            elif final_score >= 0.4:
                quality_level = 'moderate'
                quality_desc = '中等关系'
            else:
                quality_level = 'poor'
                quality_desc = '需要验证'
            
            return {
                'quality_score': final_score,
                'quality_level': quality_level,
                'quality_description': quality_desc,
                'evidence_strength': field_count,
                'method_reliability': method_weight,
                'confidence_score': quality_score,
                'recommendations': self._get_quality_recommendations(final_score, relationship)
            }
            
        except Exception as e:
            logger.error(f"关系质量分析失败: {e}")
            return {'error': f'分析失败: {str(e)}'}
    
    def _get_quality_recommendations(self, score: float, relationship: Dict) -> List[str]:
        """获取质量改进建议"""
        recommendations = []
        
        if score < 0.4:
            recommendations.append("建议收集更多证据信息")
            recommendations.append("可以手动确认或忽略此关系")
            
        if score < 0.6:
            recommendations.append("建议验证关系的准确性")
            
        if relationship.get('matching_method') != 'ai_inference':
            recommendations.append("可以使用AI重新分析提高准确性")
            
        if not relationship.get('confirmed_at'):
            recommendations.append("建议确认关系以提高可靠性")
            
        return recommendations


# 单例实例
relationship_service = None

def get_relationship_service(database):
    """获取关系发现服务实例"""
    global relationship_service
    if relationship_service is None:
        relationship_service = RelationshipService(database)
    return relationship_service