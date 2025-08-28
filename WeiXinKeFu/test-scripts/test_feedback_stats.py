#!/usr/bin/env python3
"""
测试反馈统计API
从服务器获取反馈数据统计
"""

import requests
import json
from datetime import datetime

# 服务器配置
SERVER_URL = "https://weixin.dataelem.com"  # 生产服务器
# SERVER_URL = "http://localhost:8000"  # 本地测试

# 测试用户
TEST_USER_ID = "wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q"

def get_feedback_stats(user_id=None):
    """获取反馈统计"""
    # 先登录获取token
    login_response = requests.post(
        f"{SERVER_URL}/api/login",
        json={"wechat_user_id": user_id or TEST_USER_ID}
    )
    
    if login_response.status_code != 200:
        print(f"登录失败: {login_response.text}")
        return None
    
    token = login_response.json().get("token")
    if not token:
        print("未获取到token")
        return None
    
    # 调用反馈统计API
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    stats_response = requests.get(
        f"{SERVER_URL}/api/feedback/stats",
        headers=headers
    )
    
    if stats_response.status_code == 200:
        return stats_response.json()
    else:
        print(f"获取统计失败: {stats_response.status_code}")
        print(stats_response.text)
        return None

def print_stats(stats):
    """打印统计结果"""
    if not stats or stats.get('status') == 'no_data':
        print("\n📊 暂无反馈数据")
        return
    
    print("\n" + "="*60)
    print("📊 反馈数据统计报告")
    print("="*60)
    
    data = stats.get('data', {})
    
    # 基本统计
    print(f"\n📈 基本信息:")
    print(f"  总反馈数: {data.get('total_feedback', 0)}")
    print(f"  正面反馈: {data.get('positive_count', 0)} ({data.get('positive_rate', 0):.1f}%)")
    print(f"  负面反馈: {data.get('negative_count', 0)} ({data.get('negative_rate', 0):.1f}%)")
    print(f"  忽略反馈: {data.get('ignored_count', 0)} ({data.get('ignored_rate', 0):.1f}%)")
    
    # 分数统计
    print(f"\n📊 分数分布:")
    print(f"  正面反馈平均分: {data.get('positive_avg_score', 0):.3f}")
    print(f"  负面反馈平均分: {data.get('negative_avg_score', 0):.3f}")
    print(f"  分数分离度: {data.get('score_separation', 0):.3f}")
    
    # 状态判断
    separation = data.get('score_separation', 0)
    if separation > 0.3:
        print("  ✅ 良好的区分能力")
    elif separation > 0.15:
        print("  ⚠️ 区分能力一般")
    else:
        print("  ❌ 区分能力较差，需要优化算法")
    
    # 建议
    recommendations = data.get('recommendations', [])
    if recommendations:
        print(f"\n💡 优化建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
    
    # 数据收集进度
    total = data.get('total_feedback', 0)
    if total < 50:
        print(f"\n📝 数据收集进度: {total}/50 (建议至少收集50条反馈)")
        print(f"  还需要 {50-total} 条反馈数据")
    else:
        print(f"\n✅ 已收集足够数据 ({total}条)，可以开始分析优化")
    
    print("\n" + "="*60)

def main():
    """主函数"""
    print(f"服务器: {SERVER_URL}")
    print(f"测试用户: {TEST_USER_ID}")
    print(f"时间: {datetime.now()}")
    
    # 获取统计
    stats = get_feedback_stats()
    
    if stats:
        print_stats(stats)
        
        # 保存到文件
        with open(f"feedback_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
            print(f"\n统计结果已保存到文件")
    else:
        print("\n获取统计失败")

if __name__ == "__main__":
    main()