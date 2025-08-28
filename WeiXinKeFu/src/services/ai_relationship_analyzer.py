"""
AI增强的关系识别分析器
集成通义千问API进行智能关系识别和分析
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Optional
import requests
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class AIRelationshipAnalyzer:
    """AI增强的关系识别分析器"""
    
    def __init__(self):
        self.api_key = os.getenv('QWEN_API_KEY')
        self.api_endpoint = os.getenv('QWEN_API_ENDPOINT', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        
        if not self.api_key:
            logger.warning("未配置QWEN_API_KEY，AI增强功能将无法使用")
            
        # AI分析配置
        self.config = {
            'model': 'qwen-plus',
            'temperature': 0.3,  # 较低的温度确保一致性
            'max_tokens': 2000,
            'timeout': 30
        }
        
        # 关系类型映射和权重
        self.relationship_types = {
            'colleague': {'weight': 0.8, 'confidence_boost': 0.1},
            'friend': {'weight': 0.7, 'confidence_boost': 0.05},
            'partner': {'weight': 0.9, 'confidence_boost': 0.15},
            'client': {'weight': 0.85, 'confidence_boost': 0.12},
            'supplier': {'weight': 0.8, 'confidence_boost': 0.1},
            'alumni': {'weight': 0.6, 'confidence_boost': 0.08},
            'family': {'weight': 0.95, 'confidence_boost': 0.2},
            'neighbor': {'weight': 0.4, 'confidence_boost': 0.05},
            'same_location': {'weight': 0.3, 'confidence_boost': 0.02},
            'competitor': {'weight': 0.7, 'confidence_boost': 0.08},
            'investor': {'weight': 0.9, 'confidence_boost': 0.15}
        }
        
    def analyze_relationship_with_ai(self, profile1: Dict, profile2: Dict) -> Dict:
        """
        使用AI分析两个联系人之间的潜在关系
        
        Args:
            profile1: 第一个联系人的资料
            profile2: 第二个联系人的资料
            
        Returns:
            分析结果字典，包含关系类型、置信度、证据等
        """
        try:
            # 构建AI提示词
            prompt = self._build_relationship_analysis_prompt(profile1, profile2)
            
            # 调用AI API
            ai_response = self._call_qwen_api(prompt)
            
            if not ai_response:
                return self._create_fallback_analysis(profile1, profile2)
            
            # 解析AI响应
            analysis_result = self._parse_ai_response(ai_response, profile1, profile2)
            
            # 增强分析结果
            enhanced_result = self._enhance_analysis_with_rules(analysis_result, profile1, profile2)
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"AI关系分析失败: {e}")
            return self._create_fallback_analysis(profile1, profile2)
    
    def _build_relationship_analysis_prompt(self, profile1: Dict, profile2: Dict) -> str:
        """构建关系分析提示词"""
        
        # 提取关键信息
        p1_info = self._extract_profile_info(profile1)
        p2_info = self._extract_profile_info(profile2)
        
        prompt = f"""
作为一个专业的社交关系分析专家，请分析以下两个联系人之间可能存在的关系：

联系人A：{p1_info['name']}
- 公司：{p1_info['company']}
- 职位：{p1_info['position']}
- 地区：{p1_info['location']}
- 学历：{p1_info['education']}
- 行业：{p1_info['industry']}
- 标签：{', '.join(p1_info['tags'])}

联系人B：{p2_info['name']}
- 公司：{p2_info['company']}
- 职位：{p2_info['position']}
- 地区：{p2_info['location']}
- 学历：{p2_info['education']}
- 行业：{p2_info['industry']}
- 标签：{', '.join(p2_info['tags'])}

请分析他们之间可能的关系类型，并提供以下信息：

1. 最可能的关系类型（从以下选择）：
   - colleague（同事）
   - friend（朋友）
   - partner（合作伙伴）
   - client（客户关系）
   - supplier（供应商）
   - alumni（校友）
   - family（家人）
   - neighbor（邻居）
   - same_location（同地区）
   - competitor（竞争对手）
   - investor（投资关系）

2. 置信度（0-1之间的小数）

3. 关系方向：
   - bidirectional（双向关系）
   - A_to_B（A到B的单向关系）
   - B_to_A（B到A的单向关系）

4. 关系强度（strong/medium/weak）

5. 支持证据（具体说明为什么认为他们有这种关系）

6. 匹配的字段（哪些信息字段支持这个关系判断）

请以JSON格式返回结果：
{{
    "relationship_type": "关系类型",
    "confidence_score": 置信度数值,
    "relationship_direction": "关系方向",
    "relationship_strength": "关系强度",
    "evidence": "详细的证据说明",
    "matched_fields": ["匹配的字段列表"],
    "explanation": "简短的关系说明",
    "ai_reasoning": "AI的推理过程"
}}

请基于提供的信息进行客观、准确的分析。如果信息不足以确定明确关系，请设置较低的置信度。
"""
        return prompt
    
    def _extract_profile_info(self, profile: Dict) -> Dict:
        """提取联系人关键信息"""
        return {
            'name': profile.get('profile_name', profile.get('name', '未知')),
            'company': profile.get('company', '未知'),
            'position': profile.get('position', '未知'),
            'location': profile.get('location', profile.get('address', '未知')),
            'education': profile.get('education', '未知'),
            'industry': self._extract_industry_from_company(profile.get('company', '')),
            'tags': profile.get('tags', []) if isinstance(profile.get('tags', []), list) else []
        }
    
    def _extract_industry_from_company(self, company: str) -> str:
        """从公司名称提取行业信息"""
        if not company or company == '未知':
            return '未知'
        
        # 简单的行业识别逻辑
        industry_keywords = {
            '科技': ['科技', '技术', '软件', '网络', 'IT', '互联网', '数据', '人工智能', 'AI'],
            '金融': ['银行', '金融', '投资', '保险', '证券', '基金', '支付'],
            '制造': ['制造', '生产', '工厂', '机械', '汽车', '电子'],
            '教育': ['教育', '学校', '培训', '学院', '大学'],
            '医疗': ['医院', '医疗', '药', '健康', '生物'],
            '房地产': ['房地产', '地产', '建筑', '装修'],
            '零售': ['零售', '商场', '超市', '电商', '购物'],
            '媒体': ['媒体', '广告', '传媒', '文化', '娱乐']
        }
        
        for industry, keywords in industry_keywords.items():
            for keyword in keywords:
                if keyword in company:
                    return industry
        
        return '其他'
    
    def _call_qwen_api(self, prompt: str) -> Optional[str]:
        """调用通义千问API"""
        if not self.api_key:
            return None
            
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.config['model'],
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': self.config['temperature'],
                'max_tokens': self.config['max_tokens']
            }
            
            response = requests.post(
                f"{self.api_endpoint}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.config['timeout']
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and result['choices']:
                    return result['choices'][0]['message']['content']
            else:
                logger.error(f"AI API调用失败: {response.status_code}, {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error("AI API调用超时")
        except Exception as e:
            logger.error(f"AI API调用异常: {e}")
            
        return None
    
    def _parse_ai_response(self, ai_response: str, profile1: Dict, profile2: Dict) -> Dict:
        """解析AI响应"""
        try:
            # 尝试直接解析JSON
            if ai_response.startswith('{') and ai_response.endswith('}'):
                return json.loads(ai_response)
            
            # 尝试提取JSON部分
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = ai_response[start_idx:end_idx+1]
                return json.loads(json_str)
            
            # JSON解析失败，尝试提取关键信息
            return self._extract_info_from_text(ai_response)
            
        except json.JSONDecodeError as e:
            logger.error(f"AI响应JSON解析失败: {e}")
            return self._extract_info_from_text(ai_response)
        except Exception as e:
            logger.error(f"AI响应解析异常: {e}")
            return self._create_default_analysis()
    
    def _extract_info_from_text(self, text: str) -> Dict:
        """从文本中提取关键信息"""
        result = self._create_default_analysis()
        
        # 尝试提取关系类型
        for rel_type in self.relationship_types.keys():
            if rel_type in text.lower() or self._get_chinese_name(rel_type) in text:
                result['relationship_type'] = rel_type
                break
        
        # 尝试提取置信度
        import re
        confidence_match = re.search(r'置信度[:：]?\s*(\d*\.?\d+)', text)
        if confidence_match:
            try:
                confidence = float(confidence_match.group(1))
                if confidence > 1:
                    confidence = confidence / 100  # 百分比转小数
                result['confidence_score'] = min(max(confidence, 0), 1)
            except ValueError:
                pass
        
        # 提取证据说明
        if '证据' in text or '理由' in text:
            evidence_start = max(text.find('证据'), text.find('理由'))
            if evidence_start != -1:
                evidence_text = text[evidence_start:evidence_start+200]
                result['evidence'] = evidence_text
        
        return result
    
    def _get_chinese_name(self, rel_type: str) -> str:
        """获取关系类型的中文名称"""
        chinese_names = {
            'colleague': '同事',
            'friend': '朋友',
            'partner': '合作伙伴',
            'client': '客户',
            'supplier': '供应商',
            'alumni': '校友',
            'family': '家人',
            'neighbor': '邻居',
            'same_location': '同地区',
            'competitor': '竞争对手',
            'investor': '投资'
        }
        return chinese_names.get(rel_type, rel_type)
    
    def _create_default_analysis(self) -> Dict:
        """创建默认分析结果"""
        return {
            'relationship_type': 'colleague',
            'confidence_score': 0.5,
            'relationship_direction': 'bidirectional',
            'relationship_strength': 'medium',
            'evidence': 'AI分析中，信息不足',
            'matched_fields': [],
            'explanation': '需要更多信息确定关系',
            'ai_reasoning': 'AI分析过程中出现问题，使用默认分析'
        }
    
    def _enhance_analysis_with_rules(self, analysis: Dict, profile1: Dict, profile2: Dict) -> Dict:
        """使用规则增强AI分析结果"""
        try:
            enhanced = analysis.copy()
            
            # 基于字段匹配增强置信度
            field_matches = self._calculate_field_matches(profile1, profile2)
            
            # 更新匹配字段
            if not enhanced.get('matched_fields'):
                enhanced['matched_fields'] = list(field_matches.keys())
            
            # 基于匹配强度调整置信度
            match_score = sum(field_matches.values()) / max(len(field_matches), 1)
            
            # 获取关系类型配置
            rel_type = enhanced.get('relationship_type', 'colleague')
            type_config = self.relationship_types.get(rel_type, {'weight': 0.5, 'confidence_boost': 0})
            
            # 计算增强置信度
            base_confidence = enhanced.get('confidence_score', 0.5)
            field_boost = match_score * 0.3  # 字段匹配增强
            type_boost = type_config['confidence_boost']  # 关系类型增强
            
            enhanced_confidence = min(base_confidence + field_boost + type_boost, 1.0)
            enhanced['confidence_score'] = enhanced_confidence
            
            # 根据置信度调整关系强度
            if enhanced_confidence > 0.8:
                enhanced['relationship_strength'] = 'strong'
            elif enhanced_confidence < 0.4:
                enhanced['relationship_strength'] = 'weak'
            else:
                enhanced['relationship_strength'] = 'medium'
            
            # 增强证据说明
            evidence_parts = [enhanced.get('evidence', '')]
            
            if field_matches:
                match_descriptions = []
                for field, score in field_matches.items():
                    if score > 0.7:
                        match_descriptions.append(f"{field}高度匹配")
                    elif score > 0.3:
                        match_descriptions.append(f"{field}部分匹配")
                
                if match_descriptions:
                    evidence_parts.append(f"字段匹配: {', '.join(match_descriptions)}")
            
            enhanced['evidence'] = '; '.join(filter(None, evidence_parts))
            
            # 添加分析元数据
            enhanced['analysis_metadata'] = {
                'ai_used': True,
                'field_match_score': match_score,
                'enhanced_confidence': enhanced_confidence,
                'original_confidence': base_confidence,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            return enhanced
            
        except Exception as e:
            logger.error(f"增强分析失败: {e}")
            return analysis
    
    def _calculate_field_matches(self, profile1: Dict, profile2: Dict) -> Dict[str, float]:
        """计算字段匹配分数"""
        matches = {}
        
        # 公司匹配
        company1 = profile1.get('company', '').strip()
        company2 = profile2.get('company', '').strip()
        if company1 and company2 and company1 != '未知' and company2 != '未知':
            if company1.lower() == company2.lower():
                matches['company'] = 1.0
            else:
                # 简单的相似度计算
                similarity = self._calculate_similarity(company1, company2)
                if similarity > 0.7:
                    matches['company'] = similarity
        
        # 地区匹配
        location1 = profile1.get('location', profile1.get('address', '')).strip()
        location2 = profile2.get('location', profile2.get('address', '')).strip()
        if location1 and location2 and location1 != '未知' and location2 != '未知':
            similarity = self._calculate_similarity(location1, location2)
            if similarity > 0.5:
                matches['location'] = similarity
        
        # 教育匹配
        education1 = profile1.get('education', '').strip()
        education2 = profile2.get('education', '').strip()
        if education1 and education2 and education1 != '未知' and education2 != '未知':
            similarity = self._calculate_similarity(education1, education2)
            if similarity > 0.6:
                matches['education'] = similarity
        
        # 职位相关性
        position1 = profile1.get('position', '').strip()
        position2 = profile2.get('position', '').strip()
        if position1 and position2 and position1 != '未知' and position2 != '未知':
            # 检查职位互补性（如销售和客户经理）
            complementary_score = self._calculate_position_complementarity(position1, position2)
            if complementary_score > 0.3:
                matches['position_complementary'] = complementary_score
        
        return matches
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """计算字符串相似度（简化版）"""
        if not str1 or not str2:
            return 0.0
        
        # 简单的Jaccard相似度
        set1 = set(str1.lower())
        set2 = set(str2.lower())
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_position_complementarity(self, pos1: str, pos2: str) -> float:
        """计算职位互补性"""
        complementary_pairs = [
            (['销售', '业务'], ['客户', '采购']),
            (['产品', '设计'], ['开发', '工程']),
            (['市场', '营销'], ['品牌', '推广']),
            (['财务', '会计'], ['审计', '风控']),
            (['HR', '人事'], ['招聘', '培训']),
            (['投资', '基金'], ['创业', '企业'])
        ]
        
        pos1_lower = pos1.lower()
        pos2_lower = pos2.lower()
        
        for group1, group2 in complementary_pairs:
            if any(keyword in pos1_lower for keyword in group1) and \
               any(keyword in pos2_lower for keyword in group2):
                return 0.8
            if any(keyword in pos2_lower for keyword in group1) and \
               any(keyword in pos1_lower for keyword in group2):
                return 0.8
        
        return 0.0
    
    def _create_fallback_analysis(self, profile1: Dict, profile2: Dict) -> Dict:
        """创建备用分析结果（不使用AI）"""
        # 基于规则的简单分析
        field_matches = self._calculate_field_matches(profile1, profile2)
        
        # 确定关系类型
        relationship_type = 'colleague'  # 默认
        confidence = 0.3  # 较低的默认置信度
        
        if 'company' in field_matches and field_matches['company'] > 0.8:
            relationship_type = 'colleague'
            confidence = 0.7
        elif 'education' in field_matches and field_matches['education'] > 0.7:
            relationship_type = 'alumni'
            confidence = 0.6
        elif 'location' in field_matches and field_matches['location'] > 0.7:
            relationship_type = 'same_location'
            confidence = 0.5
        elif 'position_complementary' in field_matches:
            relationship_type = 'partner'
            confidence = 0.65
        
        return {
            'relationship_type': relationship_type,
            'confidence_score': confidence,
            'relationship_direction': 'bidirectional',
            'relationship_strength': 'medium' if confidence > 0.6 else 'weak',
            'evidence': f'基于字段匹配分析: {", ".join(field_matches.keys())}',
            'matched_fields': list(field_matches.keys()),
            'explanation': f'系统检测到{self._get_chinese_name(relationship_type)}关系',
            'ai_reasoning': '未使用AI分析，基于规则匹配',
            'analysis_metadata': {
                'ai_used': False,
                'field_match_score': sum(field_matches.values()) / max(len(field_matches), 1),
                'analysis_timestamp': datetime.now().isoformat()
            }
        }
    
    def batch_analyze_relationships(self, profile_pairs: List[Tuple[Dict, Dict]]) -> List[Dict]:
        """
        批量分析关系
        
        Args:
            profile_pairs: 联系人对列表
            
        Returns:
            分析结果列表
        """
        results = []
        
        for i, (profile1, profile2) in enumerate(profile_pairs):
            try:
                logger.info(f"批量分析进度: {i+1}/{len(profile_pairs)}")
                
                result = self.analyze_relationship_with_ai(profile1, profile2)
                results.append(result)
                
                # 避免API频率限制
                if i < len(profile_pairs) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"批量分析第{i+1}个关系对失败: {e}")
                results.append(self._create_fallback_analysis(profile1, profile2))
        
        return results
    
    def get_relationship_suggestions(self, target_profile: Dict, candidate_profiles: List[Dict], top_k: int = 10) -> List[Dict]:
        """
        为目标联系人获取关系建议
        
        Args:
            target_profile: 目标联系人
            candidate_profiles: 候选联系人列表
            top_k: 返回前K个建议
            
        Returns:
            关系建议列表，按置信度降序排列
        """
        suggestions = []
        
        for candidate in candidate_profiles:
            if candidate.get('id') == target_profile.get('id'):
                continue
                
            analysis = self.analyze_relationship_with_ai(target_profile, candidate)
            
            # 只保留置信度较高的建议
            if analysis.get('confidence_score', 0) >= 0.4:
                suggestions.append({
                    'target_profile': target_profile,
                    'candidate_profile': candidate,
                    'analysis': analysis
                })
        
        # 按置信度排序
        suggestions.sort(key=lambda x: x['analysis'].get('confidence_score', 0), reverse=True)
        
        return suggestions[:top_k]