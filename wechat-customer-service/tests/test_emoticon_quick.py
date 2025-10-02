#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试Prompt v2.0和动态表情包功能
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.emoticon_service import emoticon_service
from src.services.seedream_video_service import seedream_video_service


def test_prompt_v2():
    """测试Prompt v2.0生成"""
    print("=" * 60)
    print("🎨 测试 Prompt v2.0")
    print("=" * 60)

    test_cases = [
        "YYDS",
        "打工人",
        "微笑",
        "开心"
    ]

    for emotion in test_cases:
        print(f"\n测试: {emotion}")
        print("-" * 60)

        result = emoticon_service.generate_emoticon_prompt(emotion)

        if result.get('success'):
            prompt = result.get('prompt', '')
            print(f"✅ 生成成功")
            print(f"长度: {len(prompt)}字")
            print(f"内容: {prompt[:150]}...")

            # 检查是否有文字
            has_text = '"' in prompt or '文字' in prompt
            print(f"文字: {'有' if has_text else '无'}")
        else:
            print(f"❌ 生成失败: {result.get('error')}")


def test_video_generation():
    """测试动态表情包生成"""
    print("\n\n")
    print("=" * 60)
    print("🎬 测试动态表情包生成")
    print("=" * 60)

    prompt = "一只柴犬点头同意，Q版卡通风格"

    print(f"\n提示词: {prompt}")
    print("开始生成视频...")
    print("⏳ 预计耗时: 30-60秒")
    print("-" * 60)

    result = seedream_video_service.generate_video(
        prompt=prompt,
        duration="5s",
        resolution="720p"
    )

    if result.get('success'):
        video_path = result.get('video_path', '')
        video_url = result.get('video_url', '')

        print(f"\n✅ 视频生成成功!")
        print(f"本地路径: {video_path}")
        print(f"视频URL: {video_url[:80]}...")

        # 检查文件是否存在
        if os.path.exists(video_path):
            file_size = os.path.getsize(video_path) / (1024 * 1024)
            print(f"文件大小: {file_size:.2f} MB")

        # 测试视频转GIF
        print("\n开始转换为GIF...")
        gif_result = seedream_video_service.convert_video_to_gif(video_path)

        if gif_result.get('success'):
            gif_path = gif_result.get('gif_path', '')
            print(f"✅ GIF转换成功!")
            print(f"GIF路径: {gif_path}")

            if os.path.exists(gif_path):
                gif_size = os.path.getsize(gif_path) / (1024 * 1024)
                print(f"GIF大小: {gif_size:.2f} MB")
        else:
            print(f"❌ GIF转换失败: {gif_result.get('error')}")
    else:
        print(f"❌ 视频生成失败: {result.get('error')}")


def test_one_click_animated():
    """测试一键生成动态表情包"""
    print("\n\n")
    print("=" * 60)
    print("🎭 测试一键生成动态表情包")
    print("=" * 60)

    prompt = "一只小猫咪挥手告别，可爱卡通风格"

    print(f"\n提示词: {prompt}")
    print("⏳ 预计耗时: 60-90秒（生成视频+转换GIF）")
    print("-" * 60)

    result = seedream_video_service.generate_animated_emoticon(prompt)

    if result.get('success'):
        print(f"\n✅ 动态表情包生成完成!")
        print(f"视频: {result.get('video_path', '')}")
        print(f"GIF: {result.get('gif_path', '')}")

        # 显示文件大小
        video_path = result.get('video_path', '')
        gif_path = result.get('gif_path', '')

        if os.path.exists(video_path):
            video_size = os.path.getsize(video_path) / (1024 * 1024)
            print(f"\n视频大小: {video_size:.2f} MB")

        if os.path.exists(gif_path):
            gif_size = os.path.getsize(gif_path) / (1024 * 1024)
            print(f"GIF大小: {gif_size:.2f} MB")
    else:
        print(f"❌ 生成失败: {result.get('error')}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='快速测试表情包功能')
    parser.add_argument('--mode', choices=['prompt', 'video', 'gif', 'all'],
                        default='prompt',
                        help='测试模式: prompt=测试Prompt v2.0, video=测试视频生成, gif=测试一键生成GIF, all=全部测试')

    args = parser.parse_args()

    if args.mode == 'prompt':
        test_prompt_v2()
    elif args.mode == 'video':
        test_video_generation()
    elif args.mode == 'gif':
        test_one_click_animated()
    elif args.mode == 'all':
        test_prompt_v2()

        # 询问是否继续测试视频
        print("\n\n" + "=" * 60)
        response = input("继续测试视频生成功能吗？(会调用付费API，y/n): ")
        if response.lower() == 'y':
            test_video_generation()
            test_one_click_animated()
        else:
            print("跳过视频测试")

    print("\n\n✅ 测试完成!")
