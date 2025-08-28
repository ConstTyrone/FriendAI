#!/usr/bin/env python3
"""
反馈数据分析脚本
用于分析用户反馈数据，识别模式和改进机会
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
import sys
import statistics

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FeedbackAnalyzer:
    """反馈数据分析器"""
    
    def __init__(self, db_path: str = "user_profiles.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
    def get_feedback_data(self, user_id: str = None) -> List[Dict]:
        """获取反馈数据"""
        query = """
            SELECT 
                im.*,
                ui.name as intent_name,
                ui.description as intent_description,
                ui.type as intent_type,
                ui.conditions as intent_conditions
            FROM intent_matches im
            LEFT JOIN user_intents ui ON im.intent_id = ui.id
            WHERE im.user_feedback IS NOT NULL
        """
        
        params = []
        if user_id:
            query += " AND im.user_id = ?"
            params.append(user_id)
            
        query += " ORDER BY im.created_at DESC"
        
        self.cursor.execute(query, params)
        columns = [desc[0] for desc in self.cursor.description]
        rows = self.cursor.fetchall()
        
        data = []
        for row in rows:
            record = dict(zip(columns, row))
            # 解析JSON字段
            if record.get('matched_conditions'):
                try:
                    record['matched_conditions'] = json.loads(record['matched_conditions'])
                except:
                    record['matched_conditions'] = []
            if record.get('score_details'):
                try:
                    record['score_details'] = json.loads(record['score_details'])
                except:
                    record['score_details'] = {}
            data.append(record)
            
        return data
    
    def analyze_score_distribution(self, data: List[Dict]) -> Dict:
        """分析分数分布"""
        if df.empty:
            return {
                'total': 0,
                'message': '无反馈数据'
            }
            
        results = {
            'total': len(df),
            'by_feedback': {},
            'score_stats': {},
            'score_separation': 0
        }
        
        # 按反馈类型分组
        for feedback_type in ['positive', 'negative', 'ignored']:
            type_df = df[df['user_feedback'] == feedback_type]
            if not type_df.empty:
                results['by_feedback'][feedback_type] = {
                    'count': len(type_df),
                    'percentage': len(type_df) / len(df) * 100,
                    'avg_score': type_df['match_score'].mean(),
                    'std_score': type_df['match_score'].std(),
                    'min_score': type_df['match_score'].min(),
                    'max_score': type_df['match_score'].max(),
                    'median_score': type_df['match_score'].median()
                }
        
        # 计算整体统计
        results['score_stats'] = {
            'mean': df['match_score'].mean(),
            'std': df['match_score'].std(),
            'min': df['match_score'].min(),
            'max': df['match_score'].max(),
            'median': df['match_score'].median(),
            'q25': df['match_score'].quantile(0.25),
            'q75': df['match_score'].quantile(0.75)
        }
        
        # 计算分数分离度
        if 'positive' in results['by_feedback'] and 'negative' in results['by_feedback']:
            results['score_separation'] = (
                results['by_feedback']['positive']['avg_score'] - 
                results['by_feedback']['negative']['avg_score']
            )
        
        return results
    
    def analyze_scoring_components(self, df: pd.DataFrame) -> Dict:
        """分析评分组件的表现"""
        if df.empty or 'score_details' not in df.columns:
            return {}
            
        components = {
            'vector_similarity': [],
            'keyword_score': [],
            'required_score': [],
            'preferred_score': []
        }
        
        feedback_components = {
            'positive': {k: [] for k in components.keys()},
            'negative': {k: [] for k in components.keys()},
            'ignored': {k: [] for k in components.keys()}
        }
        
        for _, row in df.iterrows():
            details = row.get('score_details', {})
            feedback = row.get('user_feedback')
            
            if details and feedback:
                for comp_name in components.keys():
                    if comp_name in details:
                        score = details[comp_name]
                        components[comp_name].append(score)
                        feedback_components[feedback][comp_name].append(score)
        
        # 计算统计信息
        results = {}
        
        # 整体组件统计
        results['overall'] = {}
        for comp_name, scores in components.items():
            if scores:
                results['overall'][comp_name] = {
                    'mean': statistics.mean(scores),
                    'std': statistics.stdev(scores) if len(scores) > 1 else 0,
                    'contribution': statistics.mean(scores) if scores else 0
                }
        
        # 按反馈类型的组件统计
        results['by_feedback'] = {}
        for feedback_type, comp_dict in feedback_components.items():
            results['by_feedback'][feedback_type] = {}
            for comp_name, scores in comp_dict.items():
                if scores:
                    results['by_feedback'][feedback_type][comp_name] = {
                        'mean': statistics.mean(scores),
                        'std': statistics.stdev(scores) if len(scores) > 1 else 0,
                        'count': len(scores)
                    }
        
        # 计算组件区分度
        results['discriminative_power'] = {}
        for comp_name in components.keys():
            pos_scores = feedback_components['positive'][comp_name]
            neg_scores = feedback_components['negative'][comp_name]
            
            if pos_scores and neg_scores:
                # 计算正负反馈的分数差异
                results['discriminative_power'][comp_name] = {
                    'separation': statistics.mean(pos_scores) - statistics.mean(neg_scores),
                    'positive_mean': statistics.mean(pos_scores),
                    'negative_mean': statistics.mean(neg_scores),
                    'effectiveness': abs(statistics.mean(pos_scores) - statistics.mean(neg_scores))
                }
        
        return results
    
    def identify_patterns(self, data: List[Dict]) -> Dict:
        """识别反馈模式"""
        patterns = {
            'false_positives': [],  # 高分但负反馈
            'false_negatives': [],  # 低分但正反馈
            'threshold_issues': [],  # 阈值附近的问题
            'component_issues': []   # 组件权重问题
        }
        
        if not data:
            return patterns
        
        # 识别假阳性（高分但负反馈）
        false_pos = [d for d in data if d.get('user_feedback') == 'negative' and d.get('match_score', 0) > 0.6]
        if false_pos:
            scores = [d.get('match_score', 0) for d in false_pos]
            patterns['false_positives'] = {
                'count': len(false_pos),
                'avg_score': statistics.mean(scores) if scores else 0,
                'examples': [{'intent_id': d.get('intent_id'), 'profile_id': d.get('profile_id'), 'match_score': d.get('match_score')} for d in false_pos[:5]]
            }
        
        # 识别假阴性（低分但正反馈）
        false_neg = [d for d in data if d.get('user_feedback') == 'positive' and d.get('match_score', 0) < 0.4]
        if false_neg:
            scores = [d.get('match_score', 0) for d in false_neg]
            patterns['false_negatives'] = {
                'count': len(false_neg),
                'avg_score': statistics.mean(scores) if scores else 0,
                'examples': [{'intent_id': d.get('intent_id'), 'profile_id': d.get('profile_id'), 'match_score': d.get('match_score')} for d in false_neg[:5]]
            }
        
        # 识别阈值问题
        threshold_range = [d for d in data if 0.45 <= d.get('match_score', 0) <= 0.55]
        if threshold_range:
            positive_count = sum(1 for d in threshold_range if d.get('user_feedback') == 'positive')
            negative_count = sum(1 for d in threshold_range if d.get('user_feedback') == 'negative')
            positive_scores = sorted([d.get('match_score', 0) for d in data if d.get('user_feedback') == 'positive'])
            suggested_threshold = positive_scores[int(len(positive_scores) * 0.1)] if positive_scores else 0.5
            
            patterns['threshold_issues'] = {
                'count': len(threshold_range),
                'positive_rate': positive_count / len(threshold_range) if threshold_range else 0,
                'negative_rate': negative_count / len(threshold_range) if threshold_range else 0,
                'suggestion': '考虑调整阈值到' + str(round(suggested_threshold, 2))
            }
        
        return patterns
    
    def generate_recommendations(self, analysis: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 基于分数分离度的建议
        if 'score_distribution' in analysis:
            dist = analysis['score_distribution']
            if dist.get('score_separation', 0) < 0.2:
                recommendations.append(
                    "⚠️ 分数分离度较低（{:.2f}），建议增加算法的区分能力".format(
                        dist.get('score_separation', 0)
                    )
                )
            
            # 检查反馈分布
            by_feedback = dist.get('by_feedback', {})
            if 'negative' in by_feedback:
                neg_rate = by_feedback['negative']['percentage']
                if neg_rate > 40:
                    recommendations.append(
                        f"📉 负反馈率较高（{neg_rate:.1f}%），建议提高匹配质量"
                    )
        
        # 基于组件分析的建议
        if 'component_analysis' in analysis:
            comp = analysis['component_analysis']
            disc_power = comp.get('discriminative_power', {})
            
            for comp_name, stats in disc_power.items():
                if stats['effectiveness'] < 0.1:
                    recommendations.append(
                        f"🔧 组件 {comp_name} 区分度较低（{stats['effectiveness']:.3f}），考虑调整权重"
                    )
        
        # 基于模式识别的建议
        if 'patterns' in analysis:
            patterns = analysis['patterns']
            
            if patterns.get('false_positives', {}).get('count', 0) > 5:
                recommendations.append(
                    "❌ 检测到较多假阳性（{}个），建议提高匹配标准".format(
                        patterns['false_positives']['count']
                    )
                )
            
            if patterns.get('false_negatives', {}).get('count', 0) > 5:
                recommendations.append(
                    "⭕ 检测到较多假阴性（{}个），建议放宽匹配条件".format(
                        patterns['false_negatives']['count']
                    )
                )
            
            if patterns.get('threshold_issues', {}).get('suggestion'):
                recommendations.append(
                    "🎯 " + patterns['threshold_issues']['suggestion']
                )
        
        # 基于数据量的建议
        total_feedback = analysis.get('score_distribution', {}).get('total', 0)
        if total_feedback < 50:
            recommendations.append(
                f"📊 当前反馈数据较少（{total_feedback}条），建议继续收集至少{50-total_feedback}条再进行优化"
            )
        
        return recommendations
    
    def export_analysis(self, analysis: Dict, output_path: str = None):
        """导出分析结果"""
        if output_path is None:
            output_path = f"feedback_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"分析结果已导出到: {output_path}")
    
    def print_analysis_report(self, analysis: Dict):
        """打印分析报告"""
        print("\n" + "="*60)
        print("📊 反馈数据分析报告")
        print("="*60)
        
        # 基本统计
        dist = analysis.get('score_distribution', {})
        print(f"\n📈 基本统计:")
        print(f"  总反馈数: {dist.get('total', 0)}")
        
        if dist.get('by_feedback'):
            print(f"\n  反馈分布:")
            for feedback_type, stats in dist.get('by_feedback', {}).items():
                print(f"    {feedback_type}: {stats['count']} ({stats['percentage']:.1f}%)")
                print(f"      平均分: {stats['avg_score']:.3f} (±{stats['std_score']:.3f})")
        
        # 分数分离度
        if dist.get('score_separation'):
            print(f"\n  分数分离度: {dist['score_separation']:.3f}")
            if dist['score_separation'] > 0.3:
                print("    ✅ 良好的区分能力")
            elif dist['score_separation'] > 0.15:
                print("    ⚠️ 区分能力一般")
            else:
                print("    ❌ 区分能力较差")
        
        # 组件分析
        comp = analysis.get('component_analysis', {})
        if comp.get('discriminative_power'):
            print(f"\n🔧 组件区分度:")
            for comp_name, stats in comp['discriminative_power'].items():
                print(f"  {comp_name}:")
                print(f"    正反馈均值: {stats['positive_mean']:.3f}")
                print(f"    负反馈均值: {stats['negative_mean']:.3f}")
                print(f"    区分度: {stats['effectiveness']:.3f}")
        
        # 问题模式
        patterns = analysis.get('patterns', {})
        if patterns:
            print(f"\n⚠️ 识别的问题:")
            if patterns.get('false_positives', {}).get('count'):
                print(f"  假阳性: {patterns['false_positives']['count']}个")
            if patterns.get('false_negatives', {}).get('count'):
                print(f"  假阴性: {patterns['false_negatives']['count']}个")
            if patterns.get('threshold_issues', {}).get('suggestion'):
                print(f"  阈值建议: {patterns['threshold_issues']['suggestion']}")
        
        # 优化建议
        recommendations = analysis.get('recommendations', [])
        if recommendations:
            print(f"\n💡 优化建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        
        print("\n" + "="*60 + "\n")
    
    def run_full_analysis(self, user_id: str = None) -> Dict:
        """运行完整分析"""
        logger.info("开始反馈数据分析...")
        
        # 获取数据
        data = self.get_feedback_data(user_id)
        
        if not data:
            logger.warning("没有找到反馈数据")
            return {
                'status': 'no_data',
                'message': '暂无反馈数据，请继续收集'
            }
        
        logger.info(f"加载了 {len(data)} 条反馈数据")
        
        # 执行各项分析
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'score_distribution': self.analyze_score_distribution(data),
            'component_analysis': self.analyze_scoring_components(data),
            'patterns': self.identify_patterns(data),
        }
        
        # 生成建议
        analysis['recommendations'] = self.generate_recommendations(analysis)
        
        return analysis
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='反馈数据分析工具')
    parser.add_argument('--user-id', help='指定用户ID')
    parser.add_argument('--export', help='导出分析结果到文件')
    parser.add_argument('--db', default='user_profiles.db', help='数据库路径')
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = FeedbackAnalyzer(args.db)
    
    try:
        # 运行分析
        analysis = analyzer.run_full_analysis(args.user_id)
        
        # 打印报告
        analyzer.print_analysis_report(analysis)
        
        # 导出结果（如果需要）
        if args.export:
            analyzer.export_analysis(analysis, args.export)
        
    except Exception as e:
        logger.error(f"分析失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        analyzer.close()


if __name__ == "__main__":
    main()