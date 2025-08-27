"""
评分数据分析服务
收集和分析LLM评分数据，支持自适应优化和A/B测试
"""

import json
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    """用户反馈类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    IGNORED = "ignored"

class ScoringStrategy(Enum):
    """评分策略类型"""
    SIMPLE = "simple"  # 极简版本
    GUIDED = "guided"  # 轻量引导版本
    COMPLEX = "complex"  # 复杂规则版本（已弃用）

@dataclass
class ScoringRecord:
    """评分记录"""
    id: Optional[int] = None
    user_id: str = ""
    intent_id: int = 0
    profile_id: int = 0
    intent_type: str = ""
    strategy: str = ScoringStrategy.SIMPLE.value
    llm_score: float = 0.0
    final_score: float = 0.0
    confidence: float = 0.0
    matched_aspects: List[str] = None
    missing_aspects: List[str] = None
    explanation: str = ""
    user_feedback: Optional[str] = None
    processing_time: float = 0.0
    prompt_tokens: int = 0
    response_tokens: int = 0
    created_at: str = ""
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        if self.matched_aspects is None:
            self.matched_aspects = []
        if self.missing_aspects is None:
            self.missing_aspects = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

class ScoringAnalytics:
    """评分分析服务"""
    
    def __init__(self, db_path: str = "scoring_analytics.db"):
        """
        初始化评分分析服务
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self._init_database()
        
        # 统计缓存
        self.stats_cache = {}
        self.cache_ttl = timedelta(minutes=5)
        
        logger.info(f"✅ 评分分析服务初始化成功")
    
    def _init_database(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建评分记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scoring_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    intent_id INTEGER NOT NULL,
                    profile_id INTEGER NOT NULL,
                    intent_type TEXT,
                    strategy TEXT DEFAULT 'simple',
                    llm_score REAL NOT NULL,
                    final_score REAL NOT NULL,
                    confidence REAL DEFAULT 0.8,
                    matched_aspects TEXT,
                    missing_aspects TEXT,
                    explanation TEXT,
                    user_feedback TEXT,
                    processing_time REAL,
                    prompt_tokens INTEGER DEFAULT 0,
                    response_tokens INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_intent 
                ON scoring_records (user_id, intent_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback 
                ON scoring_records (user_feedback)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created 
                ON scoring_records (created_at)
            """)
            
            # 创建A/B测试表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ab_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    strategy_a TEXT NOT NULL,
                    strategy_b TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT,
                    status TEXT DEFAULT 'active',
                    winner TEXT,
                    confidence_level REAL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            
            # 创建评分质量指标表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scoring_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    total_scores INTEGER DEFAULT 0,
                    avg_score REAL,
                    score_std REAL,
                    positive_feedback_rate REAL,
                    negative_feedback_rate REAL,
                    avg_confidence REAL,
                    avg_processing_time REAL,
                    created_at TEXT NOT NULL,
                    
                    UNIQUE(date, strategy)
                )
            """)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
            raise
    
    def record_scoring(
        self,
        user_id: str,
        intent: Dict,
        profile: Dict,
        llm_score: float,
        final_score: float,
        confidence: float,
        matched_aspects: List[str],
        missing_aspects: List[str],
        explanation: str,
        strategy: str = ScoringStrategy.SIMPLE.value,
        processing_time: float = 0.0
    ) -> int:
        """
        记录评分数据
        
        Returns:
            记录ID
        """
        record = ScoringRecord(
            user_id=user_id,
            intent_id=intent.get('id', 0),
            profile_id=profile.get('id', 0),
            intent_type=intent.get('type', ''),
            strategy=strategy,
            llm_score=llm_score,
            final_score=final_score,
            confidence=confidence,
            matched_aspects=matched_aspects,
            missing_aspects=missing_aspects,
            explanation=explanation,
            processing_time=processing_time
        )
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO scoring_records (
                    user_id, intent_id, profile_id, intent_type, strategy,
                    llm_score, final_score, confidence, matched_aspects, 
                    missing_aspects, explanation, processing_time, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.user_id, record.intent_id, record.profile_id,
                record.intent_type, record.strategy, record.llm_score,
                record.final_score, record.confidence,
                json.dumps(record.matched_aspects, ensure_ascii=False),
                json.dumps(record.missing_aspects, ensure_ascii=False),
                record.explanation, record.processing_time, record.created_at
            ))
            
            record_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"📊 记录评分数据: ID={record_id}, 分数={final_score:.3f}, 策略={strategy}")
            
            # 清理统计缓存
            self.stats_cache = {}
            
            return record_id
            
        except Exception as e:
            logger.error(f"记录评分数据失败: {e}")
            return 0
    
    async def record_scoring_event(self, event: Dict) -> bool:
        """
        记录评分事件（用于反馈API）
        
        Args:
            event: 评分事件数据字典
                
        Returns:
            是否记录成功
        """
        try:
            # 如果有用户反馈，更新反馈
            if event.get('user_feedback'):
                return self.update_feedback(
                    event['user_id'],
                    event['intent_id'], 
                    event['profile_id'],
                    event['user_feedback']
                )
            return True
            
        except Exception as e:
            logger.error(f"记录评分事件失败: {e}")
            return False
    
    async def get_user_feedback_count(self, user_id: str) -> int:
        """
        获取用户反馈数量
        
        Args:
            user_id: 用户ID
            
        Returns:
            反馈数量
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) 
                FROM scoring_records
                WHERE user_id = ? AND user_feedback IS NOT NULL
            """, (user_id,))
            
            count = cursor.fetchone()[0] if cursor.fetchone() else 0
            conn.close()
            
            return count
            
        except Exception as e:
            logger.error(f"获取反馈数量失败: {e}")
            return 0
            
    async def calculate_calibration(self, user_id: str) -> Optional[Dict]:
        """
        计算校准参数
        
        Args:
            user_id: 用户ID
            
        Returns:
            校准参数字典
        """
        try:
            # 获取反馈分离度
            separation = await self.get_feedback_separation(user_id)
            
            if separation and separation.get('separation', 0) > 0.2:
                # 计算校准参数
                calibration = {
                    'enabled': True,
                    'boost_factor': min(0.2, separation['positive_ratio'] * 0.3),
                    'penalty_factor': min(0.2, separation['negative_ratio'] * 0.3),
                    'separation_threshold': separation['separation'],
                    'confidence_boost': 1.1 if separation['separation'] > 0.3 else 1.0
                }
                
                logger.info(f"计算校准参数: {calibration}")
                return calibration
            
            return None
            
        except Exception as e:
            logger.error(f"计算校准失败: {e}")
            return None
    
    async def get_feedback_separation(self, user_id: str) -> Optional[Dict]:
        """
        获取反馈分离度
        
        Args:
            user_id: 用户ID
            
        Returns:
            分离度统计
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询正面和负面反馈的平均分数
            cursor.execute("""
                SELECT 
                    AVG(CASE WHEN user_feedback = 'positive' THEN final_score END) as positive_avg,
                    AVG(CASE WHEN user_feedback = 'negative' THEN final_score END) as negative_avg,
                    COUNT(CASE WHEN user_feedback = 'positive' THEN 1 END) as positive_count,
                    COUNT(CASE WHEN user_feedback = 'negative' THEN 1 END) as negative_count,
                    COUNT(*) as total_count
                FROM scoring_records
                WHERE user_id = ? AND user_feedback IS NOT NULL
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[4] > 0:
                positive_avg = result[0] or 0
                negative_avg = result[1] or 0
                positive_count = result[2]
                negative_count = result[3]
                total_count = result[4]
                
                separation = {
                    'positive_avg': positive_avg,
                    'negative_avg': negative_avg,
                    'separation': abs(positive_avg - negative_avg),
                    'positive_ratio': positive_count / total_count if total_count > 0 else 0,
                    'negative_ratio': negative_count / total_count if total_count > 0 else 0,
                    'total_feedback': total_count
                }
                
                return separation
                
            return None
            
        except Exception as e:
            logger.error(f"获取反馈分离度失败: {e}")
            return None
    
    def update_feedback(
        self,
        user_id: str,
        intent_id: int,
        profile_id: int,
        feedback: str
    ) -> bool:
        """
        更新用户反馈
        
        Args:
            user_id: 用户ID
            intent_id: 意图ID
            profile_id: 联系人ID
            feedback: 反馈类型 (positive/negative/neutral/ignored)
            
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE scoring_records
                SET user_feedback = ?, updated_at = ?
                WHERE user_id = ? AND intent_id = ? AND profile_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (feedback, datetime.now().isoformat(), user_id, intent_id, profile_id))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if affected > 0:
                logger.info(f"✅ 更新用户反馈: 意图={intent_id}, 联系人={profile_id}, 反馈={feedback}")
                # 清理统计缓存
                self.stats_cache = {}
                return True
            else:
                logger.warning(f"未找到评分记录: 意图={intent_id}, 联系人={profile_id}")
                return False
                
        except Exception as e:
            logger.error(f"更新用户反馈失败: {e}")
            return False
    
    def get_score_distribution(
        self,
        user_id: Optional[str] = None,
        strategy: Optional[str] = None,
        days: int = 7
    ) -> Dict:
        """
        获取分数分布统计
        
        Args:
            user_id: 用户ID（可选）
            strategy: 策略类型（可选）
            days: 统计天数
            
        Returns:
            分数分布统计
        """
        cache_key = f"dist_{user_id}_{strategy}_{days}"
        
        # 检查缓存
        if cache_key in self.stats_cache:
            cached = self.stats_cache[cache_key]
            if datetime.now() - cached['time'] < self.cache_ttl:
                return cached['data']
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            if strategy:
                conditions.append("strategy = ?")
                params.append(strategy)
            
            conditions.append("created_at > ?")
            params.append((datetime.now() - timedelta(days=days)).isoformat())
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 查询分数分布
            cursor.execute(f"""
                SELECT 
                    CASE 
                        WHEN final_score >= 0.85 THEN 'A级 (0.85-1.0)'
                        WHEN final_score >= 0.70 THEN 'B级 (0.70-0.84)'
                        WHEN final_score >= 0.60 THEN 'C级 (0.60-0.69)'
                        WHEN final_score >= 0.50 THEN 'D级 (0.50-0.59)'
                        WHEN final_score >= 0.40 THEN 'E级 (0.40-0.49)'
                        ELSE 'F级 (0.0-0.39)'
                    END as score_level,
                    COUNT(*) as count,
                    AVG(final_score) as avg_score,
                    AVG(confidence) as avg_confidence
                FROM scoring_records
                WHERE {where_clause}
                GROUP BY score_level
                ORDER BY avg_score DESC
            """, params)
            
            distribution = {}
            total = 0
            
            for row in cursor.fetchall():
                level, count, avg_score, avg_confidence = row
                distribution[level] = {
                    'count': count,
                    'avg_score': round(avg_score, 3),
                    'avg_confidence': round(avg_confidence, 3)
                }
                total += count
            
            # 计算百分比
            for level in distribution:
                distribution[level]['percentage'] = round(
                    distribution[level]['count'] / total * 100 if total > 0 else 0, 
                    1
                )
            
            # 获取反馈统计
            cursor.execute(f"""
                SELECT 
                    user_feedback,
                    COUNT(*) as count
                FROM scoring_records
                WHERE {where_clause} AND user_feedback IS NOT NULL
                GROUP BY user_feedback
            """, params)
            
            feedback_stats = {}
            for feedback, count in cursor.fetchall():
                feedback_stats[feedback] = count
            
            result = {
                'distribution': distribution,
                'total_scores': total,
                'feedback_stats': feedback_stats,
                'period_days': days,
                'strategy': strategy or 'all',
                'timestamp': datetime.now().isoformat()
            }
            
            conn.close()
            
            # 缓存结果
            self.stats_cache[cache_key] = {
                'data': result,
                'time': datetime.now()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"获取分数分布失败: {e}")
            return {}
    
    def calculate_calibration_params(
        self,
        user_id: str,
        min_feedback_count: int = 10
    ) -> Dict:
        """
        基于用户反馈计算自适应校准参数
        
        Args:
            user_id: 用户ID
            min_feedback_count: 最小反馈数量要求
            
        Returns:
            校准参数
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取有反馈的评分记录
            cursor.execute("""
                SELECT 
                    llm_score, final_score, user_feedback,
                    intent_type, confidence
                FROM scoring_records
                WHERE user_id = ? AND user_feedback IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 100
            """, (user_id,))
            
            records = cursor.fetchall()
            conn.close()
            
            if len(records) < min_feedback_count:
                logger.info(f"反馈数量不足({len(records)}/{min_feedback_count})，使用默认校准")
                return self._get_default_calibration()
            
            # 按反馈类型分组
            positive_scores = []
            negative_scores = []
            
            for llm_score, final_score, feedback, intent_type, confidence in records:
                if feedback == FeedbackType.POSITIVE.value:
                    positive_scores.append(llm_score)
                elif feedback == FeedbackType.NEGATIVE.value:
                    negative_scores.append(llm_score)
            
            # 计算校准参数
            calibration = {}
            
            if positive_scores:
                # 正反馈的分数通常应该更高
                positive_mean = np.mean(positive_scores)
                positive_std = np.std(positive_scores)
                calibration['positive_target'] = min(0.85, positive_mean + 0.1)
                calibration['positive_boost'] = max(0, 0.85 - positive_mean)
            
            if negative_scores:
                # 负反馈的分数通常应该更低
                negative_mean = np.mean(negative_scores)
                negative_std = np.std(negative_scores)
                calibration['negative_target'] = max(0.3, negative_mean - 0.1)
                calibration['negative_penalty'] = max(0, negative_mean - 0.3)
            
            # 计算整体调整系数
            if positive_scores and negative_scores:
                separation = np.mean(positive_scores) - np.mean(negative_scores)
                if separation < 0.2:
                    # 正负反馈区分度不够，需要加强
                    calibration['separation_factor'] = 1.5
                else:
                    calibration['separation_factor'] = 1.0
            
            calibration['confidence_threshold'] = 0.7  # 置信度阈值
            calibration['feedback_count'] = len(records)
            calibration['last_updated'] = datetime.now().isoformat()
            
            logger.info(f"✅ 计算校准参数: {calibration}")
            return calibration
            
        except Exception as e:
            logger.error(f"计算校准参数失败: {e}")
            return self._get_default_calibration()
    
    def _get_default_calibration(self) -> Dict:
        """获取默认校准参数"""
        return {
            'positive_target': 0.85,
            'positive_boost': 0.0,
            'negative_target': 0.3,
            'negative_penalty': 0.0,
            'separation_factor': 1.0,
            'confidence_threshold': 0.7,
            'feedback_count': 0,
            'last_updated': datetime.now().isoformat()
        }
    
    def get_intent_type_performance(self, days: int = 30) -> Dict:
        """
        获取不同意图类型的性能统计
        
        Args:
            days: 统计天数
            
        Returns:
            意图类型性能统计
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    intent_type,
                    COUNT(*) as total,
                    AVG(final_score) as avg_score,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time) as avg_time,
                    SUM(CASE WHEN user_feedback = 'positive' THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN user_feedback = 'negative' THEN 1 ELSE 0 END) as negative
                FROM scoring_records
                WHERE created_at > ?
                GROUP BY intent_type
                ORDER BY total DESC
            """, ((datetime.now() - timedelta(days=days)).isoformat(),))
            
            performance = {}
            
            for row in cursor.fetchall():
                intent_type, total, avg_score, avg_confidence, avg_time, positive, negative = row
                
                performance[intent_type or 'unknown'] = {
                    'total_evaluations': total,
                    'avg_score': round(avg_score, 3),
                    'avg_confidence': round(avg_confidence, 3),
                    'avg_processing_time': round(avg_time, 2),
                    'positive_feedback': positive,
                    'negative_feedback': negative,
                    'satisfaction_rate': round(positive / (positive + negative) * 100 if (positive + negative) > 0 else 0, 1)
                }
            
            conn.close()
            
            return {
                'intent_types': performance,
                'period_days': days,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取意图类型性能失败: {e}")
            return {}
    
    def start_ab_test(
        self,
        test_name: str,
        strategy_a: str,
        strategy_b: str,
        notes: str = ""
    ) -> int:
        """
        启动A/B测试
        
        Args:
            test_name: 测试名称
            strategy_a: 策略A
            strategy_b: 策略B
            notes: 备注
            
        Returns:
            测试ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO ab_tests (
                    test_name, strategy_a, strategy_b, 
                    start_date, status, notes, created_at
                ) VALUES (?, ?, ?, ?, 'active', ?, ?)
            """, (
                test_name, strategy_a, strategy_b,
                datetime.now().isoformat(), notes,
                datetime.now().isoformat()
            ))
            
            test_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"🚀 启动A/B测试: {test_name} (ID={test_id})")
            return test_id
            
        except Exception as e:
            logger.error(f"启动A/B测试失败: {e}")
            return 0
    
    def analyze_ab_test(self, test_id: int) -> Dict:
        """
        分析A/B测试结果
        
        Args:
            test_id: 测试ID
            
        Returns:
            测试分析结果
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取测试信息
            cursor.execute("""
                SELECT test_name, strategy_a, strategy_b, start_date, status
                FROM ab_tests
                WHERE id = ?
            """, (test_id,))
            
            test_info = cursor.fetchone()
            if not test_info:
                return {'error': 'Test not found'}
            
            test_name, strategy_a, strategy_b, start_date, status = test_info
            
            # 分析两种策略的表现
            results = {}
            
            for strategy in [strategy_a, strategy_b]:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        AVG(final_score) as avg_score,
                        AVG(confidence) as avg_confidence,
                        SUM(CASE WHEN user_feedback = 'positive' THEN 1 ELSE 0 END) as positive,
                        SUM(CASE WHEN user_feedback = 'negative' THEN 1 ELSE 0 END) as negative,
                        AVG(processing_time) as avg_time
                    FROM scoring_records
                    WHERE strategy = ? AND created_at > ?
                """, (strategy, start_date))
                
                row = cursor.fetchone()
                total, avg_score, avg_confidence, positive, negative, avg_time = row
                
                results[strategy] = {
                    'total_evaluations': total or 0,
                    'avg_score': round(avg_score or 0, 3),
                    'avg_confidence': round(avg_confidence or 0, 3),
                    'positive_feedback': positive or 0,
                    'negative_feedback': negative or 0,
                    'satisfaction_rate': round(
                        positive / (positive + negative) * 100 
                        if (positive and negative and (positive + negative) > 0) 
                        else 0, 1
                    ),
                    'avg_processing_time': round(avg_time or 0, 2)
                }
            
            # 判断获胜者
            winner = None
            confidence_level = 0.0
            
            if results[strategy_a]['total_evaluations'] >= 30 and results[strategy_b]['total_evaluations'] >= 30:
                # 简单的统计显著性检验（实际应该用更复杂的方法）
                diff = abs(results[strategy_a]['satisfaction_rate'] - results[strategy_b]['satisfaction_rate'])
                if diff > 10:
                    winner = strategy_a if results[strategy_a]['satisfaction_rate'] > results[strategy_b]['satisfaction_rate'] else strategy_b
                    confidence_level = min(0.95, 0.5 + diff / 100)
            
            conn.close()
            
            return {
                'test_id': test_id,
                'test_name': test_name,
                'status': status,
                'start_date': start_date,
                'results': results,
                'winner': winner,
                'confidence_level': confidence_level,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"分析A/B测试失败: {e}")
            return {'error': str(e)}
    
    def get_quality_metrics(self, days: int = 7) -> Dict:
        """
        获取评分质量指标
        
        Args:
            days: 统计天数
            
        Returns:
            质量指标
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 计算各项指标
            cursor.execute("""
                SELECT 
                    strategy,
                    COUNT(*) as total,
                    AVG(final_score) as avg_score,
                    AVG((final_score - ?)*(final_score - ?)) as variance,
                    AVG(confidence) as avg_confidence,
                    AVG(processing_time) as avg_time,
                    SUM(CASE WHEN user_feedback = 'positive' THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN user_feedback = 'negative' THEN 1 ELSE 0 END) as negative,
                    SUM(CASE WHEN user_feedback IS NOT NULL THEN 1 ELSE 0 END) as with_feedback
                FROM scoring_records
                WHERE created_at > ?
                GROUP BY strategy
            """, (0.5, 0.5, (datetime.now() - timedelta(days=days)).isoformat()))
            
            metrics = {}
            
            for row in cursor.fetchall():
                strategy, total, avg_score, variance, avg_confidence, avg_time, positive, negative, with_feedback = row
                
                metrics[strategy] = {
                    'total_evaluations': total,
                    'avg_score': round(avg_score, 3),
                    'score_std': round(np.sqrt(variance), 3),
                    'avg_confidence': round(avg_confidence, 3),
                    'avg_processing_time': round(avg_time, 2),
                    'positive_feedback_rate': round(positive / with_feedback * 100 if with_feedback > 0 else 0, 1),
                    'negative_feedback_rate': round(negative / with_feedback * 100 if with_feedback > 0 else 0, 1),
                    'feedback_coverage': round(with_feedback / total * 100 if total > 0 else 0, 1)
                }
            
            conn.close()
            
            return {
                'metrics': metrics,
                'period_days': days,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取质量指标失败: {e}")
            return {}

# 全局实例
scoring_analytics = ScoringAnalytics()