"""
高级置信度计算引擎
提供多因素综合评分和动态权重调整机制
"""

import json
import logging
import math
import re
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

class AdvancedConfidenceCalculator:
    """高级置信度计算器"""
    
    def __init__(self):
        """初始化置信度计算器"""
        # 字段重要性权重配置
        self.field_weights = {
            'company': 0.35,        # 公司信息权重最高
            'education': 0.25,      # 教育背景重要性较高
            'location': 0.20,       # 地理位置中等重要
            'position': 0.15,       # 职位信息补充作用
            'phone': 0.30,          # 电话号码精确匹配价值高
            'email': 0.25,          # 邮箱域名可显示关联
            'industry': 0.20,       # 行业相关性
            'age_group': 0.10       # 年龄段辅助判断
        }
        
        # 关系类型置信度基准
        self.relationship_baselines = {
            'colleague': {'base': 0.4, 'company_boost': 0.4, 'location_boost': 0.1},
            'friend': {'base': 0.3, 'location_boost': 0.3, 'education_boost': 0.2},
            'family': {'base': 0.2, 'phone_boost': 0.5, 'location_boost': 0.3},
            'partner': {'base': 0.3, 'company_boost': 0.3, 'industry_boost': 0.2},
            'client': {'base': 0.3, 'industry_boost': 0.3, 'position_boost': 0.2},
            'supplier': {'base': 0.3, 'industry_boost': 0.3, 'company_boost': 0.1},
            'alumni': {'base': 0.3, 'education_boost': 0.4, 'age_boost': 0.1},
            'neighbor': {'base': 0.2, 'location_boost': 0.5, 'phone_boost': 0.1},
            'same_location': {'base': 0.2, 'location_boost': 0.6},
            'competitor': {'base': 0.3, 'industry_boost': 0.3, 'position_boost': 0.2},
            'investor': {'base': 0.2, 'industry_boost': 0.4, 'company_boost': 0.2}
        }
        
        # 匹配方法可靠性系数
        self.method_reliability = {
            'exact_match': 1.0,
            'fuzzy_match': 0.8,
            'semantic_match': 0.7,
            'partial_match': 0.6,
            'ai_inference': 0.9,
            'rule_based': 0.7,
            'pattern_match': 0.6
        }
        
    def calculate_comprehensive_confidence(
        self, 
        profile1: Dict, 
        profile2: Dict,
        relationship_type: str,
        evidence: Dict = None,
        method: str = 'ai_inference'
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算综合置信度分数
        
        Args:
            profile1: 源联系人资料
            profile2: 目标联系人资料  
            relationship_type: 关系类型
            evidence: 支持证据
            method: 匹配方法
        
        Returns:
            (置信度分数, 详细分析结果)
        """
        try:
            logger.info(f"🧮 开始计算置信度 - 关系类型: {relationship_type}, 方法: {method}")
            
            # 1. 字段匹配分析
            field_scores = self._analyze_field_matches(profile1, profile2)
            
            # 2. 关系类型适配性评估
            type_score = self._calculate_type_compatibility(profile1, profile2, relationship_type)
            
            # 3. 证据强度评估
            evidence_score = self._evaluate_evidence_strength(evidence or {})
            
            # 4. 方法可靠性调整
            method_factor = self.method_reliability.get(method, 0.7)
            
            # 5. 综合置信度计算
            final_confidence, breakdown = self._compute_final_confidence(
                field_scores, type_score, evidence_score, method_factor, relationship_type
            )
            
            # 6. 生成详细分析报告
            analysis_report = {
                'final_confidence': final_confidence,
                'confidence_breakdown': breakdown,
                'field_analysis': field_scores,
                'type_compatibility': type_score,
                'evidence_strength': evidence_score,
                'method_reliability': method_factor,
                'quality_indicators': self._generate_quality_indicators(final_confidence, breakdown),
                'improvement_suggestions': self._suggest_improvements(field_scores, evidence_score),
                'calculation_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ 置信度计算完成 - 最终分数: {final_confidence:.3f}")
            return final_confidence, analysis_report
            
        except Exception as e:
            logger.error(f"❌ 置信度计算失败: {e}")
            return 0.5, {'error': str(e), 'fallback_confidence': 0.5}
    
    def _analyze_field_matches(self, profile1: Dict, profile2: Dict) -> Dict[str, Dict]:
        """分析字段匹配情况"""
        field_analysis = {}
        
        # 公司匹配分析
        company_result = self._analyze_company_match(
            profile1.get('company', ''), 
            profile2.get('company', '')
        )
        if company_result['score'] > 0:
            field_analysis['company'] = company_result
        
        # 教育背景匹配
        education_result = self._analyze_education_match(
            profile1.get('education', ''),
            profile2.get('education', '')
        )
        if education_result['score'] > 0:
            field_analysis['education'] = education_result
        
        # 地理位置匹配
        location_result = self._analyze_location_match(
            profile1.get('location', profile1.get('address', '')),
            profile2.get('location', profile2.get('address', ''))
        )
        if location_result['score'] > 0:
            field_analysis['location'] = location_result
        
        # 联系方式匹配
        contact_result = self._analyze_contact_match(profile1, profile2)
        if contact_result['score'] > 0:
            field_analysis['contact'] = contact_result
        
        # 职位互补性分析
        position_result = self._analyze_position_relationship(
            profile1.get('position', ''),
            profile2.get('position', '')
        )
        if position_result['score'] > 0:
            field_analysis['position'] = position_result
        
        return field_analysis
    
    def _analyze_company_match(self, company1: str, company2: str) -> Dict:
        """公司匹配分析"""
        if not company1 or not company2 or company1 == '未知' or company2 == '未知':
            return {'score': 0, 'type': 'no_data', 'explanation': '缺少公司信息'}
        
        # 精确匹配
        if company1.strip().lower() == company2.strip().lower():
            return {
                'score': 1.0,
                'type': 'exact_match',
                'explanation': f'公司完全匹配: {company1}'
            }
        
        # 计算高级相似度
        similarity = self._calculate_advanced_similarity(company1, company2)
        
        if similarity > 0.9:
            return {
                'score': 0.95,
                'type': 'near_exact',
                'explanation': f'公司高度相似: {company1} ≈ {company2}',
                'similarity': similarity
            }
        elif similarity > 0.7:
            return {
                'score': 0.8,
                'type': 'fuzzy_match',
                'explanation': f'公司相似: {company1} ~ {company2}',
                'similarity': similarity
            }
        elif similarity > 0.4:
            # 检查是否为母子公司或关联公司
            relation_score = self._check_company_relationship(company1, company2)
            if relation_score > 0:
                return {
                    'score': 0.6 + relation_score * 0.2,
                    'type': 'related_company',
                    'explanation': f'可能存在公司关联: {company1} ↔ {company2}',
                    'relation_confidence': relation_score
                }
        
        return {'score': 0, 'type': 'no_match', 'explanation': '公司不匹配'}
    
    def _analyze_education_match(self, edu1: str, edu2: str) -> Dict:
        """教育背景匹配分析"""
        if not edu1 or not edu2 or edu1 == '未知' or edu2 == '未知':
            return {'score': 0, 'type': 'no_data', 'explanation': '缺少教育信息'}
        
        # 提取学校名称
        school1 = self._extract_school_name(edu1)
        school2 = self._extract_school_name(edu2)
        
        if school1 and school2:
            similarity = self._calculate_advanced_similarity(school1, school2)
            
            if similarity > 0.8:
                return {
                    'score': 0.9,
                    'type': 'same_school',
                    'explanation': f'同校校友: {school1}',
                    'similarity': similarity
                }
            elif similarity > 0.5:
                return {
                    'score': 0.6,
                    'type': 'related_school',
                    'explanation': f'相关院校: {school1} ~ {school2}',
                    'similarity': similarity
                }
        
        return {'score': 0, 'type': 'no_match', 'explanation': '教育背景不匹配'}
    
    def _analyze_location_match(self, loc1: str, loc2: str) -> Dict:
        """地理位置匹配分析"""
        if not loc1 or not loc2 or loc1 == '未知' or loc2 == '未知':
            return {'score': 0, 'type': 'no_data', 'explanation': '缺少位置信息'}
        
        # 多层级地理匹配
        city1, province1, country1 = self._parse_location(loc1)
        city2, province2, country2 = self._parse_location(loc2)
        
        if city1 and city2 and city1.lower() == city2.lower():
            return {
                'score': 0.9,
                'type': 'same_city',
                'explanation': f'同城: {city1}'
            }
        elif province1 and province2 and province1.lower() == province2.lower():
            return {
                'score': 0.6,
                'type': 'same_province',
                'explanation': f'同省: {province1}'
            }
        elif country1 and country2 and country1.lower() == country2.lower():
            return {
                'score': 0.3,
                'type': 'same_country',
                'explanation': f'同国: {country1}'
            }
        
        return {'score': 0, 'type': 'no_match', 'explanation': '地理位置不匹配'}
    
    def _analyze_contact_match(self, profile1: Dict, profile2: Dict) -> Dict:
        """联系方式匹配分析"""
        phone1 = profile1.get('phone', '').strip()
        phone2 = profile2.get('phone', '').strip()
        email1 = profile1.get('email', '').strip()
        email2 = profile2.get('email', '').strip()
        
        max_score = 0
        best_match = {'score': 0, 'type': 'no_match', 'explanation': '联系方式不匹配'}
        
        # 电话号码匹配
        if phone1 and phone2:
            phone_similarity = self._compare_phone_numbers(phone1, phone2)
            if phone_similarity > 0.8:
                best_match = {
                    'score': 0.95,
                    'type': 'phone_match',
                    'explanation': '电话号码匹配',
                    'similarity': phone_similarity
                }
                max_score = 0.95
        
        # 邮箱域名匹配
        if email1 and email2 and max_score < 0.7:
            domain1 = email1.split('@')[-1] if '@' in email1 else ''
            domain2 = email2.split('@')[-1] if '@' in email2 else ''
            
            if domain1 and domain2 and domain1.lower() == domain2.lower():
                email_match = {
                    'score': 0.7,
                    'type': 'email_domain_match',
                    'explanation': f'邮箱域名匹配: @{domain1}'
                }
                if 0.7 > max_score:
                    best_match = email_match
                    max_score = 0.7
        
        return best_match
    
    def _analyze_position_relationship(self, pos1: str, pos2: str) -> Dict:
        """职位关系分析"""
        if not pos1 or not pos2 or pos1 == '未知' or pos2 == '未知':
            return {'score': 0, 'type': 'no_data', 'explanation': '缺少职位信息'}
        
        # 检查职位层级关系
        hierarchy_score = self._check_position_hierarchy(pos1, pos2)
        if hierarchy_score > 0:
            return {
                'score': 0.6,
                'type': 'hierarchy_relation',
                'explanation': f'可能存在上下级关系: {pos1} ↔ {pos2}',
                'hierarchy_confidence': hierarchy_score
            }
        
        # 检查职位互补性
        complementary_score = self._calculate_position_complementarity_advanced(pos1, pos2)
        if complementary_score > 0.5:
            return {
                'score': 0.7,
                'type': 'complementary_positions',
                'explanation': f'职位互补关系: {pos1} ⟷ {pos2}',
                'complementary_score': complementary_score
            }
        
        # 相似职位
        similarity = self._calculate_advanced_similarity(pos1, pos2)
        if similarity > 0.6:
            return {
                'score': 0.5,
                'type': 'similar_positions',
                'explanation': f'相似职位: {pos1} ~ {pos2}',
                'similarity': similarity
            }
        
        return {'score': 0, 'type': 'no_match', 'explanation': '职位关系不明确'}
    
    def _calculate_type_compatibility(
        self, 
        profile1: Dict, 
        profile2: Dict, 
        relationship_type: str
    ) -> Dict:
        """计算关系类型适配性"""
        baseline_config = self.relationship_baselines.get(
            relationship_type, 
            {'base': 0.3, 'company_boost': 0.2, 'location_boost': 0.1}
        )
        
        base_score = baseline_config['base']
        total_boost = 0
        
        # 根据关系类型计算适配性提升
        if relationship_type == 'colleague':
            company1 = profile1.get('company', '').strip()
            company2 = profile2.get('company', '').strip()
            if company1 and company2 and company1.lower() == company2.lower():
                total_boost += baseline_config.get('company_boost', 0.3)
        
        elif relationship_type == 'alumni':
            edu1 = profile1.get('education', '').strip()
            edu2 = profile2.get('education', '').strip()
            if edu1 and edu2:
                similarity = self._calculate_advanced_similarity(edu1, edu2)
                if similarity > 0.7:
                    total_boost += baseline_config.get('education_boost', 0.3)
        
        elif relationship_type in ['neighbor', 'same_location']:
            loc1 = profile1.get('location', '').strip()
            loc2 = profile2.get('location', '').strip()
            if loc1 and loc2:
                similarity = self._calculate_advanced_similarity(loc1, loc2)
                if similarity > 0.6:
                    total_boost += baseline_config.get('location_boost', 0.4)
        
        final_score = min(base_score + total_boost, 1.0)
        
        return {
            'type_score': final_score,
            'base_score': base_score,
            'boost_applied': total_boost,
            'explanation': f'{relationship_type}类型适配性: {final_score:.2f}'
        }
    
    def _evaluate_evidence_strength(self, evidence: Dict) -> Dict:
        """评估证据强度"""
        if not evidence:
            return {'score': 0.3, 'explanation': '缺少支持证据'}
        
        evidence_factors = []
        total_score = 0.3  # 基础分数
        
        # 检查匹配字段数量
        matched_fields = evidence.get('matched_fields', [])
        if isinstance(matched_fields, list) and len(matched_fields) > 0:
            field_score = min(len(matched_fields) * 0.15, 0.3)
            total_score += field_score
            evidence_factors.append(f"{len(matched_fields)}个字段匹配")
        
        # 检查AI分析质量
        if evidence.get('ai_analysis_quality'):
            total_score += 0.2
            evidence_factors.append("AI分析支持")
        
        # 检查数据完整性
        completeness = evidence.get('data_completeness', 0)
        if completeness > 0.7:
            total_score += 0.15
            evidence_factors.append("数据完整")
        elif completeness > 0.5:
            total_score += 0.1
            evidence_factors.append("数据较完整")
        
        # 检查交叉验证
        if evidence.get('cross_validated'):
            total_score += 0.15
            evidence_factors.append("交叉验证")
        
        return {
            'score': min(total_score, 1.0),
            'factors': evidence_factors,
            'explanation': f"证据强度: {', '.join(evidence_factors) if evidence_factors else '基础证据'}"
        }
    
    def _compute_final_confidence(
        self,
        field_scores: Dict,
        type_score: Dict,
        evidence_score: Dict,
        method_factor: float,
        relationship_type: str
    ) -> Tuple[float, Dict]:
        """计算最终置信度"""
        
        # 加权字段分数
        weighted_field_score = 0
        field_contributions = {}
        
        for field_name, field_data in field_scores.items():
            weight = self.field_weights.get(field_name, 0.1)
            contribution = field_data['score'] * weight
            weighted_field_score += contribution
            field_contributions[field_name] = {
                'score': field_data['score'],
                'weight': weight,
                'contribution': contribution
            }
        
        # 综合计算
        base_confidence = (
            weighted_field_score * 0.5 +           # 字段匹配 50%
            type_score['type_score'] * 0.3 +       # 类型适配 30% 
            evidence_score['score'] * 0.2          # 证据强度 20%
        )
        
        # 应用方法可靠性调整
        final_confidence = base_confidence * method_factor
        
        # 确保在合理范围内
        final_confidence = max(0.05, min(final_confidence, 0.98))
        
        breakdown = {
            'field_contribution': weighted_field_score,
            'type_contribution': type_score['type_score'],
            'evidence_contribution': evidence_score['score'],
            'method_reliability': method_factor,
            'base_confidence': base_confidence,
            'field_details': field_contributions
        }
        
        return final_confidence, breakdown
    
    def _calculate_advanced_similarity(self, str1: str, str2: str) -> float:
        """高级字符串相似度计算"""
        if not str1 or not str2:
            return 0.0
        
        # 使用SequenceMatcher获得更准确的相似度
        similarity = SequenceMatcher(None, str1.lower().strip(), str2.lower().strip()).ratio()
        
        # Jaccard相似度作为补充
        set1 = set(str1.lower())
        set2 = set(str2.lower())
        jaccard = len(set1 & set2) / len(set1 | set2) if len(set1 | set2) > 0 else 0
        
        # 综合相似度（序列相似度权重更高）
        return similarity * 0.7 + jaccard * 0.3
    
    def _extract_school_name(self, education: str) -> Optional[str]:
        """从教育信息中提取学校名称"""
        if not education:
            return None
        
        # 常见学校关键词
        school_patterns = [
            r'([^，,；;。.]*?大学)',
            r'([^，,；;。.]*?学院)',
            r'([^，,；;。.]*?学校)',
            r'([^，,；;。.]*?大专)',
            r'([^，,；;。.]*?职业技术学院)'
        ]
        
        for pattern in school_patterns:
            match = re.search(pattern, education)
            if match:
                return match.group(1).strip()
        
        return education.strip()
    
    def _parse_location(self, location: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """解析地理位置信息"""
        if not location:
            return None, None, None
        
        # 简化的地理位置解析
        parts = location.replace('，', ',').replace('、', ',').split(',')
        
        city = None
        province = None
        country = None
        
        if len(parts) >= 3:
            city = parts[-3].strip()
            province = parts[-2].strip()
            country = parts[-1].strip()
        elif len(parts) == 2:
            city = parts[0].strip()
            province = parts[1].strip()
            country = '中国'  # 默认
        elif len(parts) == 1:
            city = parts[0].strip()
        
        return city, province, country
    
    def _compare_phone_numbers(self, phone1: str, phone2: str) -> float:
        """比较电话号码相似度"""
        if not phone1 or not phone2:
            return 0.0
        
        # 清理电话号码格式
        clean1 = re.sub(r'[^\d]', '', phone1)
        clean2 = re.sub(r'[^\d]', '', phone2)
        
        if clean1 == clean2:
            return 1.0
        
        # 检查后7位是否相同（忽略区号）
        if len(clean1) >= 7 and len(clean2) >= 7:
            if clean1[-7:] == clean2[-7:]:
                return 0.8
        
        return 0.0
    
    def _check_company_relationship(self, company1: str, company2: str) -> float:
        """检查公司关联关系"""
        # 简化的公司关系检测
        keywords1 = set(company1.lower().split())
        keywords2 = set(company2.lower().split())
        
        # 检查共同关键词
        common_words = keywords1 & keywords2
        if len(common_words) > 0:
            return min(len(common_words) / max(len(keywords1), len(keywords2)), 0.8)
        
        return 0.0
    
    def _check_position_hierarchy(self, pos1: str, pos2: str) -> float:
        """检查职位层级关系"""
        senior_keywords = ['总', '副总', '主任', '经理', '总监', '主管', 'VP', 'CEO', 'CTO', 'CFO']
        junior_keywords = ['助理', '专员', '实习', '初级', '见习']
        
        pos1_lower = pos1.lower()
        pos2_lower = pos2.lower()
        
        pos1_senior = any(keyword in pos1_lower for keyword in senior_keywords)
        pos2_senior = any(keyword in pos2_lower for keyword in senior_keywords)
        pos1_junior = any(keyword in pos1_lower for keyword in junior_keywords)
        pos2_junior = any(keyword in pos2_lower for keyword in junior_keywords)
        
        if (pos1_senior and pos2_junior) or (pos2_senior and pos1_junior):
            return 0.8
        elif pos1_senior and pos2_senior:
            return 0.6  # 可能是同级
        
        return 0.0
    
    def _calculate_position_complementarity_advanced(self, pos1: str, pos2: str) -> float:
        """高级职位互补性计算"""
        complementary_matrix = {
            '销售': ['采购', '客户经理', '商务'],
            '产品': ['开发', '设计', '技术'],
            '市场': ['品牌', '运营', '推广'],
            '财务': ['审计', '投资', '风控'],
            '人事': ['招聘', '培训', '行政'],
            '投资': ['创业', '企业发展', '项目']
        }
        
        pos1_lower = pos1.lower()
        pos2_lower = pos2.lower()
        
        for key, complements in complementary_matrix.items():
            if key in pos1_lower:
                for complement in complements:
                    if complement in pos2_lower:
                        return 0.8
            elif key in pos2_lower:
                for complement in complements:
                    if complement in pos1_lower:
                        return 0.8
        
        return 0.0
    
    def _generate_quality_indicators(self, confidence: float, breakdown: Dict) -> Dict:
        """生成质量指标"""
        quality_level = 'low'
        if confidence >= 0.8:
            quality_level = 'high'
        elif confidence >= 0.6:
            quality_level = 'medium'
        
        indicators = {
            'overall_quality': quality_level,
            'confidence_tier': f'T{int((confidence * 10) // 2) + 1}',  # T1-T5分级
            'reliability_score': confidence,
            'data_sufficiency': len(breakdown.get('field_details', {})) >= 2,
            'multi_factor_support': breakdown.get('field_contribution', 0) > 0.3 and breakdown.get('evidence_contribution', 0) > 0.4
        }
        
        return indicators
    
    def _suggest_improvements(self, field_scores: Dict, evidence_score: Dict) -> List[str]:
        """提出改进建议"""
        suggestions = []
        
        if len(field_scores) < 2:
            suggestions.append("增加更多字段匹配以提高置信度")
        
        if evidence_score['score'] < 0.5:
            suggestions.append("收集更多支持证据")
        
        if 'company' not in field_scores and 'colleague' in str(field_scores):
            suggestions.append("验证公司信息以确认同事关系")
        
        if 'location' not in field_scores:
            suggestions.append("补充地理位置信息")
        
        return suggestions