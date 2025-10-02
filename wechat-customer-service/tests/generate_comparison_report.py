# generate_comparison_report.py
"""
生成Prompt对比测试的Markdown报告
"""
import json
import sys
from datetime import datetime


def generate_markdown_report(results_file: str):
    """从JSON结果生成Markdown报告"""

    # 读取测试结果
    with open(results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)

    metadata = results['metadata']
    stats = results['statistics']
    test_cases = results['test_cases']

    # 生成报告文件名
    report_file = results_file.replace('.json', '_report.md')

    with open(report_file, 'w', encoding='utf-8') as f:
        # 标题
        f.write(f"# Prompt v2.0 对比测试报告\n\n")
        f.write(f"**测试时间**: {metadata['test_time']}\n\n")
        f.write(f"**测试用例**: {metadata['total_cases']}个\n\n")

        # 整体表现
        f.write("## 📊 整体表现对比\n\n")

        f.write("| 指标 | v1.0 | v2.0 | 改进 |\n")
        f.write("|------|------|------|------|\n")

        # 文字准确率
        v1_text = stats['v1']['text_correct_rate']
        v2_text = stats['v2']['text_correct_rate']
        text_diff = v2_text - v1_text
        text_arrow = "↑" if text_diff > 0 else "↓" if text_diff < 0 else "→"
        f.write(f"| 文字判断准确率 | {v1_text:.1f}% | {v2_text:.1f}% | {text_diff:+.1f}% {text_arrow} |\n")

        # 平均长度
        v1_len = stats['v1']['avg_length']
        v2_len = stats['v2']['avg_length']
        len_diff = v2_len - v1_len
        len_percent = (len_diff / v1_len * 100) if v1_len > 0 else 0
        len_arrow = "↓" if len_diff < 0 else "↑" if len_diff > 0 else "→"
        f.write(f"| 平均Prompt长度 | {v1_len:.0f}字 | {v2_len:.0f}字 | {len_percent:+.1f}% {len_arrow} |\n")

        # 平均问题数
        v1_issues = stats['v1']['avg_issues']
        v2_issues = stats['v2']['avg_issues']
        issues_diff = v2_issues - v1_issues
        issues_arrow = "↓" if issues_diff < 0 else "↑" if issues_diff > 0 else "→"
        f.write(f"| 平均质量问题数 | {v1_issues:.2f} | {v2_issues:.2f} | {issues_diff:+.2f} {issues_arrow} |\n")

        f.write("\n")

        # 分类表现
        f.write("## 📈 分类表现分析\n\n")

        for category, data in stats['categories'].items():
            total = data['total']
            v1_correct = data['v1_correct']
            v2_correct = data['v2_correct']
            v1_rate = v1_correct / total * 100
            v2_rate = v2_correct / total * 100
            improvement = v2_rate - v1_rate

            f.write(f"### {category}\n\n")
            f.write(f"- **v1.0**: {v1_rate:.0f}% ({v1_correct}/{total})\n")
            f.write(f"- **v2.0**: {v2_rate:.0f}% ({v2_correct}/{total})\n")

            if improvement > 0:
                f.write(f"- **改进**: +{improvement:.0f}% ✅ 显著提升\n")
            elif improvement < 0:
                f.write(f"- **变化**: {improvement:.0f}% ⚠️ 需要关注\n")
            else:
                f.write(f"- **保持**: 持平\n")

            f.write("\n")

        # 优秀案例
        f.write("## ✨ 优秀案例展示\n\n")

        # 找出v2.0表现优秀的案例
        excellent_cases = [
            case for case in test_cases
            if case['v2'].get('analysis', {}).get('text_correct') == True
            and len(case['v2'].get('analysis', {}).get('issues', [])) == 0
        ]

        for case in excellent_cases[:3]:  # 展示前3个
            emotion = case['emotion']
            category = case['category']
            v2_prompt = case['v2']['prompt']

            f.write(f"### {emotion}（{category}）\n\n")
            f.write(f"```\n{v2_prompt}\n```\n\n")

            # 分析亮点
            f.write("**亮点**:\n")
            if case['v2'].get('analysis', {}).get('has_text'):
                f.write("- ✅ 正确添加文字\n")
            else:
                f.write("- ✅ 正确不添加文字\n")
            f.write("- ✅ 包含可爱动物角色\n")
            f.write("- ✅ 表情动作生动\n")
            f.write("- ✅ 风格标签完整\n")
            f.write("\n")

        # 需要改进的案例
        f.write("## ⚠️ 需要改进的案例\n\n")

        problem_cases = [
            case for case in test_cases
            if case['v2'].get('analysis', {}).get('text_correct') == False
            or len(case['v2'].get('analysis', {}).get('issues', [])) > 0
        ]

        if problem_cases:
            for case in problem_cases[:3]:  # 展示前3个
                emotion = case['emotion']
                v2_issues = case['v2'].get('analysis', {}).get('issues', [])

                f.write(f"### {emotion}\n\n")
                f.write(f"**问题**:\n")
                for issue in v2_issues:
                    f.write(f"- ❌ {issue}\n")

                # 如果文字判断错误
                if case['v2'].get('analysis', {}).get('text_correct') == False:
                    expected = case['expected_text']
                    actual = case['v2'].get('analysis', {}).get('has_text')
                    if expected and not actual:
                        f.write(f"- ❌ 应该添加文字但未添加\n")
                    elif not expected and actual:
                        f.write(f"- ❌ 不应该添加文字但添加了\n")

                f.write("\n")
        else:
            f.write("🎉 没有发现明显问题！\n\n")

        # 对比详情表
        f.write("## 📋 详细对比表\n\n")

        f.write("| 情绪 | 分类 | v1文字 | v2文字 | 判断 | v1长度 | v2长度 | v2问题数 |\n")
        f.write("|------|------|--------|--------|------|--------|--------|----------|\n")

        for case in test_cases:
            emotion = case['emotion']
            category = case['category']

            v1_text = "✅" if case['v1'].get('analysis', {}).get('has_text') else "❌"
            v2_text = "✅" if case['v2'].get('analysis', {}).get('has_text') else "❌"

            v2_correct = case['v2'].get('analysis', {}).get('text_correct')
            correct_icon = "✅" if v2_correct == True else "❌" if v2_correct == False else "?"

            v1_len = case['v1'].get('analysis', {}).get('length', 0)
            v2_len = case['v2'].get('analysis', {}).get('length', 0)

            v2_issues = len(case['v2'].get('analysis', {}).get('issues', []))

            f.write(f"| {emotion} | {category} | {v1_text} | {v2_text} | {correct_icon} | {v1_len} | {v2_len} | {v2_issues} |\n")

        f.write("\n")

        # 总结建议
        f.write("## 💡 总结与建议\n\n")

        # 根据改进情况给出建议
        text_improvement = stats['improvement']['text_accuracy']

        f.write("### 改进效果\n\n")

        if text_improvement >= 10:
            f.write(f"- ✅ 文字判断准确率提升{text_improvement:.1f}%，效果显著\n")
        elif text_improvement >= 5:
            f.write(f"- ✅ 文字判断准确率提升{text_improvement:.1f}%，效果良好\n")
        elif text_improvement >= 0:
            f.write(f"- ⚖️ 文字判断准确率提升{text_improvement:.1f}%，略有改进\n")
        else:
            f.write(f"- ⚠️ 文字判断准确率下降{abs(text_improvement):.1f}%，需要优化\n")

        if len_percent < -20:
            f.write(f"- ✅ Prompt长度减少{abs(len_percent):.1f}%，Token效率显著提升\n")
        elif len_percent < -10:
            f.write(f"- ✅ Prompt长度减少{abs(len_percent):.1f}%，Token效率提升\n")

        quality_improvement = stats['improvement']['quality_issues']
        if quality_improvement < -0.3:
            f.write(f"- ✅ 质量问题减少{abs(quality_improvement):.2f}个，生成质量提升\n")

        f.write("\n### 下一步行动\n\n")

        # 根据问题案例数量给建议
        if len(problem_cases) == 0:
            f.write("- ✅ 测试全部通过，可以正式上线v2.0\n")
            f.write("- 📊 建议收集真实用户反馈，持续优化\n")
        elif len(problem_cases) <= 3:
            f.write("- ⚠️ 少数案例需要优化，建议针对性调整Prompt\n")
            f.write("- 🔧 优化后重新测试问题案例\n")
        else:
            f.write("- ⚠️ 较多案例存在问题，建议全面review Prompt设计\n")
            f.write("- 🔍 重点检查文字判断逻辑和示例覆盖\n")

        f.write("- 🎨 可选：生成实际图片进行人工视觉评估\n")
        f.write("- 📈 建议设置监控指标，持续跟踪生成质量\n")

        f.write("\n---\n\n")
        f.write(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    print(f"✅ 报告已生成: {report_file}")
    return report_file


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python generate_comparison_report.py <results.json>")
        print("示例: python generate_comparison_report.py tests/results/prompt_comparison_20251002_143000.json")
        sys.exit(1)

    results_file = sys.argv[1]

    if not results_file.endswith('.json'):
        print("❌ 错误: 需要JSON文件")
        sys.exit(1)

    try:
        report_file = generate_markdown_report(results_file)
        print(f"\n📖 查看报告: cat {report_file}")
    except FileNotFoundError:
        print(f"❌ 错误: 文件不存在 {results_file}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
