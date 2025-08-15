"""
性能监控和成本追踪模块
记录匹配系统的性能指标和API调用成本
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class MatchingMetrics:
    """匹配操作的性能指标"""
    timestamp: str
    user_id: str
    intent_id: int
    match_method: str  # vector/hybrid/llm
    match_mode: str  # fast/balanced/accurate/comprehensive
    
    # 性能指标
    total_time: float  # 总耗时（秒）
    vector_time: float  # 向量计算耗时
    llm_time: float  # LLM判断耗时
    db_time: float  # 数据库操作耗时
    
    # 结果指标
    profiles_count: int  # 处理的联系人数
    matches_count: int  # 匹配结果数
    vector_candidates: int  # 向量过滤后的候选数
    llm_candidates: int  # 进入LLM判断的候选数
    
    # 质量指标
    avg_score: float  # 平均匹配分数
    max_score: float  # 最高匹配分数
    min_score: float  # 最低匹配分数
    avg_confidence: float  # 平均置信度
    
    # 成本指标
    api_calls: int  # API调用次数
    api_cost: float  # API成本（元）
    cache_hits: int  # 缓存命中次数
    cache_miss: int  # 缓存未命中次数

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, db_path: str = "user_profiles.db"):
        """
        初始化性能监控器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self._init_database()
        
        # API成本配置（元/次）
        self.api_costs = {
            'qwen-plus': 0.008,  # 通义千问Plus
            'qwen-max': 0.012,   # 通义千问Max
            'vector': 0.001      # 向量计算
        }
        
        # 性能阈值（用于告警）
        self.thresholds = {
            'response_time': 5.0,  # 响应时间阈值（秒）
            'api_cost_daily': 100.0,  # 日API成本限额（元）
            'error_rate': 0.05,  # 错误率阈值
            'cache_hit_rate': 0.6  # 缓存命中率阈值
        }
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建性能指标表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    intent_id INTEGER,
                    match_method TEXT,
                    match_mode TEXT,
                    total_time REAL,
                    vector_time REAL,
                    llm_time REAL,
                    db_time REAL,
                    profiles_count INTEGER,
                    matches_count INTEGER,
                    vector_candidates INTEGER,
                    llm_candidates INTEGER,
                    avg_score REAL,
                    max_score REAL,
                    min_score REAL,
                    avg_confidence REAL,
                    api_calls INTEGER,
                    api_cost REAL,
                    cache_hits INTEGER,
                    cache_miss INTEGER,
                    metadata TEXT
                )
            """)
            
            # 创建索引（SQLite需要单独创建）
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON performance_metrics(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON performance_metrics(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_method ON performance_metrics(match_method)")
            
            # 创建API调用记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_call_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    api_type TEXT NOT NULL,
                    model TEXT,
                    tokens_used INTEGER,
                    cost REAL,
                    response_time REAL,
                    success BOOLEAN,
                    error_message TEXT
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_timestamp ON api_call_logs(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_api_type ON api_call_logs(api_type)")
            
            # 创建日统计表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_statistics (
                    date TEXT PRIMARY KEY,
                    total_matches INTEGER,
                    total_api_calls INTEGER,
                    total_api_cost REAL,
                    avg_response_time REAL,
                    cache_hit_rate REAL,
                    error_rate REAL,
                    unique_users INTEGER,
                    metadata TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            logger.info("✅ 性能监控数据库初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 性能监控数据库初始化失败: {e}")
    
    async def record_matching_metrics(self, metrics: MatchingMetrics):
        """
        记录匹配操作的性能指标
        
        Args:
            metrics: 性能指标对象
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 插入性能指标
            cursor.execute("""
                INSERT INTO performance_metrics (
                    timestamp, user_id, intent_id, match_method, match_mode,
                    total_time, vector_time, llm_time, db_time,
                    profiles_count, matches_count, vector_candidates, llm_candidates,
                    avg_score, max_score, min_score, avg_confidence,
                    api_calls, api_cost, cache_hits, cache_miss
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.timestamp,
                metrics.user_id,
                metrics.intent_id,
                metrics.match_method,
                metrics.match_mode,
                metrics.total_time,
                metrics.vector_time,
                metrics.llm_time,
                metrics.db_time,
                metrics.profiles_count,
                metrics.matches_count,
                metrics.vector_candidates,
                metrics.llm_candidates,
                metrics.avg_score,
                metrics.max_score,
                metrics.min_score,
                metrics.avg_confidence,
                metrics.api_calls,
                metrics.api_cost,
                metrics.cache_hits,
                metrics.cache_miss
            ))
            
            conn.commit()
            conn.close()
            
            # 检查是否超过阈值
            await self._check_thresholds(metrics)
            
        except Exception as e:
            logger.error(f"记录性能指标失败: {e}")
    
    async def record_api_call(
        self,
        api_type: str,
        model: str = None,
        tokens_used: int = 0,
        response_time: float = 0,
        success: bool = True,
        error_message: str = None
    ):
        """
        记录API调用
        
        Args:
            api_type: API类型（qwen/vector/other）
            model: 模型名称
            tokens_used: 使用的token数
            response_time: 响应时间（秒）
            success: 是否成功
            error_message: 错误信息
        """
        try:
            # 计算成本
            if api_type == 'qwen':
                cost = self.api_costs.get(model, 0.01)
            elif api_type == 'vector':
                cost = self.api_costs['vector']
            else:
                cost = 0
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO api_call_logs (
                    timestamp, api_type, model, tokens_used, cost,
                    response_time, success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                api_type,
                model,
                tokens_used,
                cost,
                response_time,
                success,
                error_message
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"记录API调用失败: {e}")
    
    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            user_id: 用户ID（可选）
            
        Returns:
            统计信息字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date)
            
            if end_date:
                conditions.append("timestamp <= ?")
                params.append(end_date)
            
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 获取总体统计
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_operations,
                    AVG(total_time) as avg_response_time,
                    MAX(total_time) as max_response_time,
                    MIN(total_time) as min_response_time,
                    AVG(matches_count) as avg_matches,
                    SUM(api_calls) as total_api_calls,
                    SUM(api_cost) as total_api_cost,
                    AVG(CASE WHEN cache_hits + cache_miss > 0 
                        THEN cache_hits * 1.0 / (cache_hits + cache_miss) 
                        ELSE 0 END) as cache_hit_rate
                FROM performance_metrics
                WHERE {where_clause}
            """, params)
            
            overall_stats = cursor.fetchone()
            
            # 按方法统计
            cursor.execute(f"""
                SELECT 
                    match_method,
                    COUNT(*) as count,
                    AVG(total_time) as avg_time,
                    AVG(matches_count) as avg_matches,
                    SUM(api_cost) as total_cost
                FROM performance_metrics
                WHERE {where_clause}
                GROUP BY match_method
            """, params)
            
            method_stats = cursor.fetchall()
            
            # 按模式统计
            cursor.execute(f"""
                SELECT 
                    match_mode,
                    COUNT(*) as count,
                    AVG(total_time) as avg_time,
                    AVG(avg_score) as avg_score,
                    AVG(avg_confidence) as avg_confidence
                FROM performance_metrics
                WHERE {where_clause}
                GROUP BY match_mode
            """, params)
            
            mode_stats = cursor.fetchall()
            
            conn.close()
            
            # 处理空结果情况
            if not overall_stats or overall_stats[0] is None:
                return {
                    'overall': {
                        'total_operations': 0,
                        'avg_response_time': 0,
                        'max_response_time': 0,
                        'min_response_time': 0,
                        'avg_matches': 0,
                        'total_api_calls': 0,
                        'total_api_cost': 0,
                        'cache_hit_rate': 0
                    },
                    'by_method': [],
                    'by_mode': []
                }
            
            return {
                'overall': {
                    'total_operations': overall_stats[0] or 0,
                    'avg_response_time': overall_stats[1] or 0,
                    'max_response_time': overall_stats[2] or 0,
                    'min_response_time': overall_stats[3] or 0,
                    'avg_matches': overall_stats[4] or 0,
                    'total_api_calls': overall_stats[5] or 0,
                    'total_api_cost': overall_stats[6] or 0,
                    'cache_hit_rate': overall_stats[7] or 0
                },
                'by_method': [
                    {
                        'method': row[0],
                        'count': row[1],
                        'avg_time': row[2],
                        'avg_matches': row[3],
                        'total_cost': row[4]
                    }
                    for row in method_stats
                ],
                'by_mode': [
                    {
                        'mode': row[0],
                        'count': row[1],
                        'avg_time': row[2],
                        'avg_score': row[3],
                        'avg_confidence': row[4]
                    }
                    for row in mode_stats
                ]
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
    async def _check_thresholds(self, metrics: MatchingMetrics):
        """检查是否超过阈值并发出告警"""
        alerts = []
        
        # 检查响应时间
        if metrics.total_time > self.thresholds['response_time']:
            alerts.append(f"⚠️ 响应时间过长: {metrics.total_time:.2f}秒 (阈值: {self.thresholds['response_time']}秒)")
        
        # 检查日成本
        today_cost = await self._get_today_cost()
        if today_cost > self.thresholds['api_cost_daily']:
            alerts.append(f"⚠️ 今日API成本超限: ¥{today_cost:.2f} (限额: ¥{self.thresholds['api_cost_daily']})")
        
        # 检查缓存命中率
        if metrics.cache_hits + metrics.cache_miss > 0:
            hit_rate = metrics.cache_hits / (metrics.cache_hits + metrics.cache_miss)
            if hit_rate < self.thresholds['cache_hit_rate']:
                alerts.append(f"⚠️ 缓存命中率过低: {hit_rate:.1%} (阈值: {self.thresholds['cache_hit_rate']:.1%})")
        
        # 记录告警
        for alert in alerts:
            logger.warning(alert)
    
    async def _get_today_cost(self) -> float:
        """获取今日API成本"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.now().date().isoformat()
            cursor.execute("""
                SELECT SUM(api_cost) 
                FROM performance_metrics 
                WHERE DATE(timestamp) = ?
            """, (today,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result[0] else 0.0
            
        except Exception as e:
            logger.error(f"获取今日成本失败: {e}")
            return 0.0
    
    async def generate_report(self, period: str = "daily") -> str:
        """
        生成性能报告
        
        Args:
            period: 报告周期（daily/weekly/monthly）
            
        Returns:
            Markdown格式的报告
        """
        # 确定时间范围
        end_date = datetime.now()
        if period == "daily":
            start_date = end_date - timedelta(days=1)
        elif period == "weekly":
            start_date = end_date - timedelta(days=7)
        else:  # monthly
            start_date = end_date - timedelta(days=30)
        
        # 获取统计数据
        stats = await self.get_statistics(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        # 生成报告
        report = f"""# 性能监控报告

**报告周期**: {period}
**时间范围**: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}

## 总体指标

- **总操作数**: {stats['overall']['total_operations']}
- **平均响应时间**: {stats['overall']['avg_response_time']:.2f}秒
- **最大响应时间**: {stats['overall']['max_response_time']:.2f}秒
- **平均匹配数**: {stats['overall']['avg_matches']:.1f}
- **API调用总数**: {stats['overall']['total_api_calls']}
- **API总成本**: ¥{stats['overall']['total_api_cost']:.2f}
- **缓存命中率**: {stats['overall']['cache_hit_rate']:.1%}

## 按匹配方法统计

| 方法 | 次数 | 平均耗时 | 平均匹配数 | 总成本 |
|------|------|----------|------------|--------|
"""
        
        for method in stats['by_method']:
            report += f"| {method['method']} | {method['count']} | {method['avg_time']:.2f}s | {method['avg_matches']:.1f} | ¥{method['total_cost']:.2f} |\n"
        
        report += """

## 按匹配模式统计

| 模式 | 次数 | 平均耗时 | 平均分数 | 平均置信度 |
|------|------|----------|----------|------------|
"""
        
        for mode in stats['by_mode']:
            report += f"| {mode['mode']} | {mode['count']} | {mode['avg_time']:.2f}s | {mode['avg_score']:.2f} | {mode['avg_confidence']:.1%} |\n"
        
        report += """

## 优化建议

"""
        
        # 生成优化建议
        if stats['overall']['cache_hit_rate'] < 0.6:
            report += "- ⚠️ 缓存命中率较低，建议优化缓存策略\n"
        
        if stats['overall']['avg_response_time'] > 3:
            report += "- ⚠️ 平均响应时间较长，建议优化算法或使用更快的匹配模式\n"
        
        if stats['overall']['total_api_cost'] > 50:
            report += f"- ⚠️ API成本较高（¥{stats['overall']['total_api_cost']:.2f}），建议增加缓存或减少LLM调用\n"
        
        return report

# 全局实例
performance_monitor = None

def init_performance_monitor(db_path: str = "user_profiles.db"):
    """初始化全局性能监控器"""
    global performance_monitor
    performance_monitor = PerformanceMonitor(db_path)
    return performance_monitor