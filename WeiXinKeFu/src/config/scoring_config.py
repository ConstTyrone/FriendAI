"""
评分系统配置管理
支持动态调整策略和参数
"""

import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class PromptStrategy(Enum):
    """提示词策略"""
    MINIMAL = "minimal"  # 极简版本（默认）
    GUIDED = "guided"  # 轻量引导版本
    LEGACY = "legacy"  # 旧版复杂版本（不推荐）

@dataclass
class ScoringConfig:
    """评分配置"""
    
    # 基础配置
    strategy: str = PromptStrategy.MINIMAL.value
    enable_analytics: bool = True  # 启用数据收集
    enable_calibration: bool = True  # 启用自适应校准
    enable_ab_testing: bool = False  # 启用A/B测试
    
    # 权重配置（混合评分时使用）
    weights: Dict[str, float] = field(default_factory=lambda: {
        'vector_similarity': 0.30,
        'keyword_matching': 0.30,
        'required_conditions': 0.25,
        'preferred_conditions': 0.15
    })
    
    # 阈值配置
    thresholds: Dict[str, float] = field(default_factory=lambda: {
        'match_threshold': 0.50,  # 匹配阈值
        'confidence_threshold': 0.70,  # 置信度阈值
        'high_score': 0.70,  # 高分阈值
        'low_score': 0.40,  # 低分阈值
    })
    
    # 校准参数（自适应）
    calibration: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'min_feedback_count': 10,  # 最小反馈数量
        'boost_factor': 0.1,  # 提升系数
        'penalty_factor': 0.1,  # 惩罚系数
        'separation_threshold': 0.2,  # 分离度阈值
    })
    
    # 提示词模板
    prompt_templates: Dict[str, str] = field(default_factory=lambda: {
        'minimal': """请评估以下用户与意图的匹配程度：

【意图需求】
{intent_description}{conditions}

【用户信息】
{profile_info}

请给出0-1之间的匹配分数，并提供简短的理由。

评分指导：
- 高度匹配（0.7-1.0）：核心需求基本满足
- 中度匹配（0.4-0.7）：部分符合或有潜在价值  
- 低度匹配（0-0.4）：相关性较弱

输出JSON格式：
{{
    "match_score": 0.75,
    "confidence": 0.8,
    "is_match": true,
    "matched_aspects": ["符合的方面"],
    "missing_aspects": ["不符合的方面"],
    "explanation": "简短解释",
    "suggestions": "建议"
}}""",
        
        'guided': """作为匹配专家，请分析意图与用户的匹配程度。

【任务说明】
评估用户是否符合意图需求，考虑直接匹配和潜在价值。

【意图需求】
{intent_description}{conditions}

【用户信息】
{profile_info}

【评分标准】
- 0.8-1.0：高度匹配，完全满足核心需求
- 0.6-0.8：良好匹配，满足主要需求
- 0.4-0.6：中度匹配，部分满足或有潜在价值
- 0.2-0.4：低度匹配，间接相关
- 0-0.2：基本不匹配

请输出JSON格式的评估结果。"""
    })
    
    # A/B测试配置
    ab_test: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': False,
        'test_name': '',
        'strategy_a': PromptStrategy.MINIMAL.value,
        'strategy_b': PromptStrategy.GUIDED.value,
        'traffic_split': 0.5,  # A策略的流量比例
    })
    
    # 性能配置
    performance: Dict[str, Any] = field(default_factory=lambda: {
        'cache_enabled': True,
        'cache_ttl': 3600,  # 缓存有效期（秒）
        'batch_size': 5,
        'max_parallel': 3,
        'timeout': 30,  # LLM调用超时（秒）
    })
    
    # 实验性功能
    experimental: Dict[str, bool] = field(default_factory=lambda: {
        'multi_round_refinement': False,  # 多轮优化
        'context_aware_prompting': False,  # 上下文感知提示
        'dynamic_weight_adjustment': False,  # 动态权重调整
        'llm_self_critique': False,  # LLM自我批判
    })
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    def from_dict(self, data: Dict):
        """从字典加载配置"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def save(self, filepath: str):
        """保存配置到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 配置已保存到: {filepath}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def load(self, filepath: str):
        """从文件加载配置"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.from_dict(data)
            logger.info(f"✅ 配置已加载: {filepath}")
        except Exception as e:
            logger.error(f"加载配置失败: {e}")

class ScoringConfigManager:
    """评分配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = ScoringConfig()
        self.config_path = config_path or "scoring_config.json"
        
        # 尝试加载已有配置
        try:
            self.config.load(self.config_path)
        except:
            # 使用默认配置
            logger.info("使用默认评分配置")
            
        # 配置变更监听器
        self.listeners = []
        
    def get_config(self) -> ScoringConfig:
        """获取当前配置"""
        return self.config
    
    def update_config(self, updates: Dict[str, Any]):
        """
        更新配置
        
        Args:
            updates: 要更新的配置项
        """
        old_config = self.config.to_dict()
        
        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"更新配置: {key} = {value}")
        
        # 保存配置
        self.config.save(self.config_path)
        
        # 通知监听器
        self._notify_listeners(old_config, self.config.to_dict())
    
    def switch_strategy(self, strategy: str):
        """
        切换评分策略
        
        Args:
            strategy: 策略名称
        """
        if strategy not in [s.value for s in PromptStrategy]:
            logger.error(f"无效的策略: {strategy}")
            return
        
        self.config.strategy = strategy
        self.config.save(self.config_path)
        logger.info(f"✅ 切换到策略: {strategy}")
        
        # 通知监听器
        self._notify_listeners({'strategy': self.config.strategy}, {'strategy': strategy})
    
    def enable_ab_test(
        self,
        test_name: str,
        strategy_a: str,
        strategy_b: str,
        traffic_split: float = 0.5
    ):
        """
        启用A/B测试
        
        Args:
            test_name: 测试名称
            strategy_a: 策略A
            strategy_b: 策略B
            traffic_split: A策略的流量比例
        """
        self.config.ab_test = {
            'enabled': True,
            'test_name': test_name,
            'strategy_a': strategy_a,
            'strategy_b': strategy_b,
            'traffic_split': traffic_split
        }
        self.config.enable_ab_testing = True
        self.config.save(self.config_path)
        
        logger.info(f"✅ 启用A/B测试: {test_name}")
    
    def disable_ab_test(self):
        """禁用A/B测试"""
        self.config.enable_ab_testing = False
        self.config.ab_test['enabled'] = False
        self.config.save(self.config_path)
        
        logger.info("✅ 已禁用A/B测试")
    
    def update_weights(self, weights: Dict[str, float]):
        """
        更新评分权重
        
        Args:
            weights: 新的权重配置
        """
        # 验证权重总和为1
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            logger.warning(f"权重总和为{total}，将自动归一化")
            # 归一化
            weights = {k: v/total for k, v in weights.items()}
        
        self.config.weights = weights
        self.config.save(self.config_path)
        
        logger.info(f"✅ 更新权重: {weights}")
    
    def update_thresholds(self, thresholds: Dict[str, float]):
        """
        更新阈值配置
        
        Args:
            thresholds: 新的阈值配置
        """
        self.config.thresholds.update(thresholds)
        self.config.save(self.config_path)
        
        logger.info(f"✅ 更新阈值: {thresholds}")
    
    def enable_experimental_feature(self, feature: str):
        """
        启用实验性功能
        
        Args:
            feature: 功能名称
        """
        if feature in self.config.experimental:
            self.config.experimental[feature] = True
            self.config.save(self.config_path)
            logger.info(f"✅ 启用实验性功能: {feature}")
        else:
            logger.error(f"未知的实验性功能: {feature}")
    
    def disable_experimental_feature(self, feature: str):
        """
        禁用实验性功能
        
        Args:
            feature: 功能名称
        """
        if feature in self.config.experimental:
            self.config.experimental[feature] = False
            self.config.save(self.config_path)
            logger.info(f"✅ 禁用实验性功能: {feature}")
    
    def get_prompt_template(self, strategy: Optional[str] = None) -> str:
        """
        获取提示词模板
        
        Args:
            strategy: 策略名称（可选，默认使用当前策略）
            
        Returns:
            提示词模板
        """
        strategy = strategy or self.config.strategy
        return self.config.prompt_templates.get(
            strategy, 
            self.config.prompt_templates[PromptStrategy.MINIMAL.value]
        )
    
    def register_listener(self, listener):
        """
        注册配置变更监听器
        
        Args:
            listener: 监听器函数，接收(old_config, new_config)参数
        """
        self.listeners.append(listener)
    
    def _notify_listeners(self, old_config: Dict, new_config: Dict):
        """通知所有监听器"""
        for listener in self.listeners:
            try:
                listener(old_config, new_config)
            except Exception as e:
                logger.error(f"监听器通知失败: {e}")
    
    def get_ab_test_strategy(self) -> str:
        """
        根据A/B测试配置返回应该使用的策略
        
        Returns:
            策略名称
        """
        if not self.config.enable_ab_testing:
            return self.config.strategy
        
        import random
        if random.random() < self.config.ab_test['traffic_split']:
            return self.config.ab_test['strategy_a']
        else:
            return self.config.ab_test['strategy_b']
    
    def export_config(self, filepath: str):
        """
        导出配置
        
        Args:
            filepath: 导出文件路径
        """
        self.config.save(filepath)
        logger.info(f"✅ 配置已导出到: {filepath}")
    
    def import_config(self, filepath: str):
        """
        导入配置
        
        Args:
            filepath: 导入文件路径
        """
        old_config = self.config.to_dict()
        self.config.load(filepath)
        self._notify_listeners(old_config, self.config.to_dict())
        logger.info(f"✅ 配置已导入: {filepath}")
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        old_config = self.config.to_dict()
        self.config = ScoringConfig()
        self.config.save(self.config_path)
        self._notify_listeners(old_config, self.config.to_dict())
        logger.info("✅ 已重置为默认配置")

# 全局配置管理器实例
scoring_config_manager = ScoringConfigManager()