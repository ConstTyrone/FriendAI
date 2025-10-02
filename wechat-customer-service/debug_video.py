#!/usr/bin/env python3
"""调试视频生成API"""
from src.services.seedream_video_service import seedream_video_service
import logging

# 设置详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

print("开始测试视频生成...")
result = seedream_video_service.generate_video(
    prompt='一只柴犬点头同意，Q版卡通风格',
    duration='5s',
    resolution='720p'
)

print("\n" + "="*60)
print("最终结果:")
print(result)
