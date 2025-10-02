# 动态表情包功能说明文档

## 功能概述

基于火山引擎 **Seedance-1.0-pro** 视频生成模型，实现了动态表情包（GIF）生成功能。

### 核心特性

- ✅ **文本生成视频**：根据文字描述生成5秒或10秒短视频
- ✅ **图片生成视频**：基于参考图片生成动态视频
- ✅ **视频转GIF**：自动将视频转换为动图表情包
- ✅ **一键生成**：`generate_animated_emoticon()` 一站式流程

## 技术架构

```
用户输入（文字描述）
    ↓
Seedance-1.0-pro API
    ↓
生成视频（5s/10s，480p/720p）
    ↓
FFmpeg转换
    ↓
压缩GIF（480px宽，10fps）
    ↓
返回给用户
```

## API使用方法

### 方法1：一键生成动态表情包（推荐）

```python
from src.services.seedream_video_service import seedream_video_service

# 生成动态表情包
result = seedream_video_service.generate_animated_emoticon(
    prompt="一只柴犬点头表示同意，Q版卡通风格"
)

if result['success']:
    print(f"视频: {result['video_path']}")
    print(f"GIF: {result['gif_path']}")
else:
    print(f"失败: {result['error']}")
```

### 方法2：分步操作

```python
# 步骤1: 生成视频
video_result = seedream_video_service.generate_video(
    prompt="一只小猫咪挥手告别，可爱卡通风格",
    duration="5s",    # 5秒或10秒
    resolution="720p" # 480p或720p
)

if video_result['success']:
    video_path = video_result['video_path']

    # 步骤2: 转换为GIF
    gif_result = seedream_video_service.convert_video_to_gif(video_path)

    if gif_result['success']:
        print(f"GIF生成成功: {gif_result['gif_path']}")
```

### 方法3：图生视频（高级）

```python
# 基于现有图片生成动态效果
result = seedream_video_service.generate_video(
    prompt="让这个角色跳跃起来，表达开心",
    image_url="https://example.com/image.jpg",  # 参考图片URL
    duration="5s",
    resolution="720p"
)
```

## Prompt编写建议

### 适合动态表情包的动作

#### ✅ 简单重复动作（效果最好）
- **点头** → "一只小熊不断点头，Q版卡通"
- **摇头** → "一只小狗摇头拒绝，可爱风格"
- **挥手** → "一只小兔子挥手打招呼，友好姿态"
- **跳跃** → "一只小猫咪原地跳跃表达开心"
- **转圈** → "一只柴犬开心地转圈圈"

#### ✅ 表情变化
- **眨眼** → "一只小猫咪可爱地眨眼睛"
- **微笑** → "一只小熊从平静到露出微笑"
- **惊讶** → "一只小兔子眼睛逐渐瞪大表示惊讶"

#### ❌ 不建议的复杂动作
- ❌ 多步骤组合动作（如"走过来然后坐下再挥手"）
- ❌ 精细手部动作（如"比心手势"可能不准确）
- ❌ 复杂场景切换

### Prompt模板

```
[动物] + [动作] + [情绪] + [风格]

示例：
- "一只橘色小猫咪点头同意，开心表情，Q版卡通风格"
- "一只柴犬摇尾巴表示兴奋，可爱萌系风格"
- "一只粉色小兔子蹦蹦跳跳，活泼姿态，卡通表情包风格"
```

## 成本与性能

### API调用成本

| 模型 | 时长 | 分辨率 | 预估成本 | 生成时间 |
|------|------|--------|----------|----------|
| Seedance-1.0-pro | 5s | 480p | 低 | ~20-40秒 |
| Seedance-1.0-pro | 5s | 720p | 中 | ~30-60秒 |
| Seedance-1.0-pro | 10s | 720p | 高 | ~60-120秒 |

**建议**：表情包使用5秒720p即可，成本适中，效果足够。

### 文件大小

| 格式 | 尺寸 | 时长 | 大小 |
|------|------|------|------|
| 视频（MP4） | 720p | 5s | ~2-5 MB |
| GIF（压缩） | 480px宽 | 5s (10fps) | ~500KB-2MB |

### 用户限流建议

- **每用户每天**: 最多3次动态表情包生成
- **全局并发**: 最多同时2个视频生成请求
- **缓存策略**: 热门动作预生成（点头、挥手等）

## 环境配置

### 1. 环境变量（已配置）

```bash
# .env 文件
SEEDREAM_API_KEY=4f3d9b80-3a62-4ef8-9902-5d6742113c91  # 复用现有Key
```

### 2. 安装FFmpeg（必需）

#### macOS
```bash
brew install ffmpeg
```

#### Ubuntu/Debian
```bash
sudo apt-get install ffmpeg
```

#### Windows
1. 下载: https://ffmpeg.org/download.html
2. 解压到 `D:\software\ffmpeg\`
3. 添加到环境变量 `PATH`

#### 验证安装
```bash
ffmpeg -version
```

### 3. 配置FFmpeg路径（可选）

如果ffmpeg不在PATH中，在`.env`配置：
```bash
FFMPEG_PATH=/usr/local/bin/ffmpeg  # macOS/Linux
# 或
FFMPEG_PATH=D:\software\ffmpeg\bin\ffmpeg.exe  # Windows
```

## 错误处理

### 常见错误及解决方案

#### 1. API请求超时
```
错误: 视频生成API请求超时（120秒）
原因: 网络慢或模型负载高
解决: 重试或使用5秒时长
```

#### 2. FFmpeg未找到
```
错误: FFmpeg未安装或路径配置错误
原因: 系统未安装FFmpeg
解决: 按上述步骤安装FFmpeg
```

#### 3. 视频下载失败
```
错误: 下载视频失败
原因: 视频URL过期（通常24小时）
解决: 立即下载，不要延迟
```

#### 4. GIF文件过大
```
问题: GIF文件>5MB，微信发送困难
解决: 调整FFmpeg参数
```
```python
# 降低帧率和分辨率
'-vf', 'fps=8,scale=360:-1:flags=lanczos'  # 8fps, 360px宽
```

## 集成到表情包系统

### 扩展emoticon_service.py

```python
# src/services/emoticon_service.py

from .seedream_video_service import seedream_video_service

class EmoticonService:
    def create_animated_emoticon(self, user_text: str) -> dict:
        """
        生成动态表情包

        Returns:
            dict: {
                'success': bool,
                'video_path': str,
                'gif_path': str,
                'emotion': str,
                'error': str
            }
        """
        # 1. 提取情绪
        emotion = self.extract_emotion(user_text)

        # 2. 生成prompt（复用现有的generate_emoticon_prompt）
        prompt_result = self.generate_emoticon_prompt(emotion)
        if not prompt_result.get('success'):
            return {'success': False, 'error': '生成描述失败'}

        prompt = prompt_result.get('prompt')

        # 3. 添加动作提示
        animated_prompt = f"{prompt}，动作流畅自然，循环播放"

        # 4. 生成动态表情包
        result = seedream_video_service.generate_animated_emoticon(animated_prompt)
        result['emotion'] = emotion

        return result
```

### 消息处理集成

```python
# src/handlers/message_handler.py

def process_message_and_reply(message: Dict[str, Any], open_kfid: str = None) -> dict:
    # 检测动态表情包请求
    if '动态表情包' in text_content or '/gif' in text_content:
        logger.info("检测到动态表情包请求")

        result = emoticon_service.create_animated_emoticon(text_content)

        if result.get('success'):
            return {
                'type': 'gif',
                'content': result.get('gif_path'),
                'video_path': result.get('video_path')  # 备用
            }
```

## 测试用例

### 基础测试

```python
# tests/test_animated_emoticon.py

import unittest
from src.services.seedream_video_service import seedream_video_service

class TestAnimatedEmoticon(unittest.TestCase):

    def test_generate_video(self):
        """测试视频生成"""
        result = seedream_video_service.generate_video(
            prompt="一只小猫咪点头，Q版卡通",
            duration="5s",
            resolution="720p"
        )
        self.assertTrue(result['success'])
        self.assertIn('video_path', result)

    def test_video_to_gif(self):
        """测试视频转GIF"""
        # 先生成视频
        video_result = seedream_video_service.generate_video(
            prompt="一只小狗摇尾巴",
            duration="5s"
        )

        # 转换为GIF
        gif_result = seedream_video_service.convert_video_to_gif(
            video_result['video_path']
        )
        self.assertTrue(gif_result['success'])

    def test_one_click_generation(self):
        """测试一键生成"""
        result = seedream_video_service.generate_animated_emoticon(
            prompt="一只小兔子跳跃，开心表情，卡通风格"
        )
        self.assertTrue(result['success'])
        self.assertIn('gif_path', result)

if __name__ == '__main__':
    unittest.main()
```

### 手动测试

```bash
# 运行测试
python -m pytest tests/test_animated_emoticon.py -v
```

## 最佳实践

### 1. Prompt优化

✅ **推荐**:
```python
"一只橘色小猫咪点头同意，眼睛微眯，嘴角上扬，Q版卡通风格，循环动作"
```

❌ **不推荐**:
```python
"一只猫先走过来然后坐下再点头最后挥手告别"  # 太复杂
```

### 2. 性能优化

```python
# 预生成热门动作
POPULAR_ACTIONS = ['点头', '摇头', '挥手', '跳跃', '转圈']

# 启动时预生成
async def pregenerate_popular_gifs():
    for action in POPULAR_ACTIONS:
        prompt = f"一只可爱小动物{action}，Q版卡通风格"
        await seedream_video_service.generate_animated_emoticon(prompt)
```

### 3. 用户体验

```python
# 流式反馈
async def generate_with_feedback(user_id, prompt):
    # 1. 立即回复
    send_message(user_id, "🎬 正在生成动态表情包...")

    # 2. 生成视频
    send_message(user_id, "⏳ 视频生成中（预计30秒）...")
    video_result = await generate_video(prompt)

    # 3. 转换GIF
    send_message(user_id, "🔄 正在转换为GIF...")
    gif_result = convert_to_gif(video_result['video_path'])

    # 4. 发送结果
    send_gif(user_id, gif_result['gif_path'])
```

## 下一步扩展

### 短期优化
- [ ] 添加GIF压缩优化（目标<1MB）
- [ ] 实现本地缓存机制
- [ ] 添加生成进度条

### 中期功能
- [ ] 支持更多动作模板
- [ ] 用户自定义角色（猫/狗/熊选择）
- [ ] 批量生成（一套动作系列）

### 长期愿景
- [ ] AI自动判断最佳动作
- [ ] 表情包编辑器（调整速度、循环次数）
- [ ] 社区分享热门动图

## 技术支持

- **火山引擎文档**: https://www.volcengine.com/docs/82379/1366800
- **FFmpeg文档**: https://ffmpeg.org/documentation.html
- **项目Issue**: GitHub Issues

---

**版本**: v1.0
**更新时间**: 2025-10-02
**维护者**: FriendAI团队
