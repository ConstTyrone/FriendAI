#!/bin/bash
# 一键运行完整测试流程

echo "🚀 Prompt v2.0 完整测试流程"
echo "=========================================="

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "❌ 错误: 未找到Python，请先安装Python 3.7+"
    exit 1
fi

# 创建结果目录
mkdir -p tests/results

# 步骤1: 运行自动化对比测试
echo ""
echo "📊 步骤1: 运行自动化对比测试..."
echo "预计耗时: 30分钟"
echo "=========================================="

python tests/test_prompt_comparison.py --confirm

if [ $? -ne 0 ]; then
    echo "❌ 测试失败，请检查错误信息"
    exit 1
fi

# 找到最新的测试结果文件
LATEST_RESULT=$(ls -t tests/results/prompt_comparison_*.json 2>/dev/null | head -1)

if [ -z "$LATEST_RESULT" ]; then
    echo "❌ 错误: 未找到测试结果文件"
    exit 1
fi

echo "✅ 测试完成，结果文件: $LATEST_RESULT"

# 步骤2: 生成对比报告
echo ""
echo "📝 步骤2: 生成对比报告..."
echo "=========================================="

python tests/generate_comparison_report.py "$LATEST_RESULT"

if [ $? -ne 0 ]; then
    echo "❌ 报告生成失败"
    exit 1
fi

REPORT_FILE="${LATEST_RESULT%.json}_report.md"

# 步骤3: 显示报告摘要
echo ""
echo "📖 步骤3: 报告摘要"
echo "=========================================="

if command -v cat &> /dev/null; then
    cat "$REPORT_FILE" | head -50
fi

# 完成
echo ""
echo "=========================================="
echo "✅ 测试流程完成！"
echo ""
echo "📂 生成的文件:"
echo "  - 测试结果: $LATEST_RESULT"
echo "  - 对比报告: $REPORT_FILE"
echo "  - 人工评分模板: tests/manual_evaluation_template.csv"
echo ""
echo "🎯 下一步:"
echo "  1. 查看完整报告: cat $REPORT_FILE"
echo "  2. （可选）填写人工评分: 打开 tests/manual_evaluation_template.csv"
echo "  3. （可选）生成实际图片验证视觉效果"
echo ""
