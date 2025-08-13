"""
向量化服务
使用通义千问API进行文本向量化和相似度计算
"""

import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

class VectorService:
    """向量化服务类"""
    
    def __init__(self):
        """初始化向量服务"""
        self.api_key = os.getenv('QWEN_API_KEY')
        self.api_endpoint = os.getenv('QWEN_API_ENDPOINT', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.embedding_model = 'text-embedding-v3'  # 通义千问embedding模型
        self.dimension = 1536  # 向量维度
        self.session = None
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self.session:
            await self.session.close()
            
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        获取文本的向量表示
        
        Args:
            text: 要向量化的文本
            
        Returns:
            向量列表，失败返回None
        """
        if not text or not self.api_key:
            return None
            
        try:
            # 准备请求
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.embedding_model,
                'input': text,
                'encoding_format': 'float'
            }
            
            # 发送请求
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.post(
                f"{self.api_endpoint}/embeddings",
                headers=headers,
                json=data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    # 提取向量
                    if result.get('data') and len(result['data']) > 0:
                        embedding = result['data'][0].get('embedding')
                        return embedding
                else:
                    error_text = await response.text()
                    print(f"向量化API错误: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            print(f"获取向量时出错: {e}")
            return None
            
    async def get_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        批量获取文本向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        embeddings = []
        
        # 批量处理，每批最多10个
        batch_size = 10
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_tasks = [self.get_embedding(text) for text in batch]
            batch_results = await asyncio.gather(*batch_tasks)
            embeddings.extend(batch_results)
            
        return embeddings
        
    def calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            相似度分数(0-1)
        """
        if not vec1 or not vec2:
            return 0.0
            
        try:
            # 转换为numpy数组
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            
            # 计算余弦相似度
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            similarity = dot_product / (norm1 * norm2)
            
            # 归一化到0-1范围
            return max(0.0, min(1.0, (similarity + 1) / 2))
            
        except Exception as e:
            print(f"计算相似度时出错: {e}")
            return 0.0
            
    async def vectorize_intent(self, intent: Dict) -> Optional[List[float]]:
        """
        对意图进行向量化
        
        Args:
            intent: 意图数据
            
        Returns:
            意图向量
        """
        # 构建意图的文本表示
        text_parts = []
        
        # 添加意图名称和描述
        if intent.get('name'):
            text_parts.append(f"意图：{intent['name']}")
        if intent.get('description'):
            text_parts.append(f"描述：{intent['description']}")
            
        # 添加关键词
        conditions = intent.get('conditions', {})
        if isinstance(conditions, str):
            try:
                conditions = json.loads(conditions)
            except:
                conditions = {}
                
        keywords = conditions.get('keywords', [])
        if keywords:
            text_parts.append(f"关键词：{' '.join(keywords)}")
            
        # 添加必要条件
        required = conditions.get('required', [])
        for req in required:
            if isinstance(req, dict):
                field = req.get('field', '')
                value = req.get('value', '')
                text_parts.append(f"要求{field}：{value}")
                
        # 添加优选条件
        preferred = conditions.get('preferred', [])
        for pref in preferred:
            if isinstance(pref, dict):
                field = pref.get('field', '')
                value = pref.get('value', '')
                text_parts.append(f"希望{field}：{value}")
                
        # 组合文本并向量化
        intent_text = '\n'.join(text_parts)
        return await self.get_embedding(intent_text)
        
    async def vectorize_profile(self, profile: Dict) -> Optional[List[float]]:
        """
        对用户画像进行向量化
        
        Args:
            profile: 用户画像数据
            
        Returns:
            画像向量
        """
        # 构建画像的文本表示
        text_parts = []
        
        # 基本信息
        if profile.get('profile_name'):
            text_parts.append(f"姓名：{profile['profile_name']}")
        if profile.get('gender'):
            text_parts.append(f"性别：{profile['gender']}")
        if profile.get('age'):
            text_parts.append(f"年龄：{profile['age']}")
            
        # 职业信息
        if profile.get('company'):
            text_parts.append(f"公司：{profile['company']}")
        if profile.get('position'):
            text_parts.append(f"职位：{profile['position']}")
        if profile.get('industry'):
            text_parts.append(f"行业：{profile['industry']}")
            
        # 教育背景
        if profile.get('education'):
            text_parts.append(f"学历：{profile['education']}")
        if profile.get('school'):
            text_parts.append(f"学校：{profile['school']}")
            
        # 地理位置
        if profile.get('location'):
            text_parts.append(f"所在地：{profile['location']}")
            
        # 其他信息
        if profile.get('marital_status'):
            text_parts.append(f"婚育：{profile['marital_status']}")
        if profile.get('asset_level'):
            text_parts.append(f"资产水平：{profile['asset_level']}")
        if profile.get('personality'):
            text_parts.append(f"性格：{profile['personality']}")
            
        # AI摘要
        if profile.get('ai_summary'):
            text_parts.append(f"简介：{profile['ai_summary']}")
            
        # 组合文本并向量化
        profile_text = '\n'.join(text_parts)
        return await self.get_embedding(profile_text)
        
    async def calculate_semantic_similarity(
        self, 
        intent: Dict, 
        profile: Dict,
        use_cache: bool = True
    ) -> Tuple[float, str]:
        """
        计算意图和画像的语义相似度
        
        Args:
            intent: 意图数据
            profile: 画像数据
            use_cache: 是否使用缓存的向量
            
        Returns:
            (相似度分数, 解释文本)
        """
        try:
            # 获取或生成向量
            intent_vec = None
            profile_vec = None
            
            # 尝试使用缓存的向量
            if use_cache:
                intent_vec = intent.get('embedding')
                profile_vec = profile.get('embedding')
                
            # 生成新向量
            if not intent_vec:
                intent_vec = await self.vectorize_intent(intent)
            if not profile_vec:
                profile_vec = await self.vectorize_profile(profile)
                
            # 计算相似度
            if intent_vec and profile_vec:
                similarity = self.calculate_similarity(intent_vec, profile_vec)
                
                # 生成解释
                if similarity > 0.8:
                    explanation = "语义高度相似，非常匹配您的意图"
                elif similarity > 0.6:
                    explanation = "语义较为相似，符合您的意图"
                elif similarity > 0.4:
                    explanation = "语义有一定相似性，可能符合您的意图"
                else:
                    explanation = "语义相似度较低"
                    
                return similarity, explanation
            else:
                return 0.0, "无法计算语义相似度"
                
        except Exception as e:
            print(f"计算语义相似度时出错: {e}")
            return 0.0, f"计算出错: {e}"
            
    async def generate_match_explanation(
        self,
        intent: Dict,
        profile: Dict,
        match_score: float,
        matched_conditions: List[str]
    ) -> str:
        """
        使用AI生成匹配解释
        
        Args:
            intent: 意图数据
            profile: 画像数据
            match_score: 匹配分数
            matched_conditions: 匹配的条件列表
            
        Returns:
            解释文本
        """
        try:
            # 构建提示词
            prompt = f"""
            分析以下意图和用户画像的匹配情况，生成一句简洁的解释（不超过50字）：
            
            意图：{intent.get('name')}
            意图描述：{intent.get('description')}
            
            用户：{profile.get('profile_name')}
            公司职位：{profile.get('company')} {profile.get('position')}
            所在地：{profile.get('location')}
            
            匹配度：{match_score*100:.0f}%
            匹配的条件：{', '.join(matched_conditions[:3]) if matched_conditions else '无'}
            
            请用一句话解释为什么这个人符合这个意图，重点突出最相关的1-2个特征。
            """
            
            # 调用AI生成解释（这里可以使用通义千问的对话API）
            # 暂时返回基于规则的解释
            if match_score > 0.8:
                key_features = []
                if profile.get('position'):
                    key_features.append(profile['position'])
                if profile.get('company'):
                    key_features.append(f"在{profile['company']}")
                if profile.get('location'):
                    key_features.append(f"位于{profile['location']}")
                    
                if key_features:
                    return f"{profile.get('profile_name')}是{'，'.join(key_features[:2])}，高度符合您的意图"
                else:
                    return f"{profile.get('profile_name')}的背景与您的意图高度匹配"
            elif match_score > 0.6:
                return f"{profile.get('profile_name')}在多个方面符合您的意图要求"
            else:
                return f"{profile.get('profile_name')}部分符合您的意图"
                
        except Exception as e:
            print(f"生成解释时出错: {e}")
            return "符合您的意图要求"

# 创建全局实例
vector_service = VectorService()