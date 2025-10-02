# 双模型表情包生成对比功能

## 功能概述

系统现已支持同时使用两个AI图片生成模型来生成表情包，方便对比效果：

1. **Gemini 2.5 Flash Image Preview** (Google)
2. **通义千问 Qwen-Image-Plus** (阿里云)

当用户请求生成表情包时，系统会自动使用两个模型生成图片，并依次发送给用户进行对比。

## 使用方式

### 微信客服端

用户在微信客服对话中发送：
- `表情包：开心`
- `生成表情包：累了`
- `/表情包 加油`

系统会：
1. 发送说明文本："✨ 为您生成了【开心】表情包，使用两个AI模型对比："
2. 依次发送两张图片：
   - 【1】Gemini 2.5 Flash
   - 【2】通义千问 Qwen-Image-Plus

### 测试脚本

运行测试脚本验证功能：

```bash
# 测试单个表情包
python test_dual_model.py "表情包：开心"

# 运行所有预设测试用例
python test_dual_model.py
```

## 技术实现

### 新增文件

1. **src/services/qwen_image_service.py**
   - 阿里云通义千问图片生成服务
   - 使用同步接口（`/multimodal-generation/generation`）
   - 自动下载生成的图片到本地
   - 支持参数：
     - `size`: 图片分辨率（默认1328*1328）
     - `watermark`: 是否添加水印（默认关闭）
     - `prompt_extend`: 智能改写（默认开启）

### 修改文件

1. **src/services/emoticon_service.py**
   - `create_emoticon()` 返回格式改为多图片：
     ```python
     {
         'success': True,
         'images': [
             {'path': '...', 'model_name': 'Gemini 2.5 Flash'},
             {'path': '...', 'model_name': '通义千问 Qwen-Image-Plus'}
         ],
         'emotion': '开心',
         'errors': []  # 部分失败时的错误信息
     }
     ```

2. **src/handlers/message_handler.py**
   - `process_message_and_reply()` 返回类型新增 `'images'`
   - `handle_wechat_kf_event()` 支持发送多张图片：
     - 先发送说明文本
     - 依次发送每张图片及标注
     - 发送部分失败提示（如果有）

## API配置

### 环境变量

系统使用现有的通义千问配置（无需新增）：

```bash
# .env 文件
QWEN_API_KEY=sk-xxxxxx  # 阿里云百炼API Key
```

### 阿里云通义千问配置

- **API端点**: `https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`
- **模型**: `qwen-image-plus`
- **超时时间**: 60秒
- **图片有效期**: 24小时（自动下载到本地）

## 对比维度

用户可以从以下维度对比两个模型的效果：

### 1. 图片质量
- 清晰度
- 色彩饱和度
- 细节表现

### 2. 表情表现力
- 情绪传递准确性
- 动作夸张程度
- 角色可爱度

### 3. 文字处理
- 中文文字清晰度
- 描边效果
- 位置布局

### 4. 风格一致性
- 是否符合表情包风格
- Q版卡通效果
- 背景简洁性

### 5. 创意性
- 角色选择创意
- 场景设计
- 细节丰富度

## 性能考虑

### 生成时间
- **Gemini 2.5 Flash**: ~10-15秒
- **通义千问**: ~15-20秒
- **总计**: 约25-35秒（并发执行可能更快）

### 容错处理
- 如果某个模型失败，另一个成功，仍会发送成功的图片
- 部分失败时会发送错误提示
- 所有模型都失败时，返回错误消息

### 资源占用
- 图片临时存储在 `data/temp_images/` 目录
- 文件命名格式：
  - Gemini: `generated_{timestamp}.png`
  - 通义千问: `qwen_generated_{timestamp}.png`

## 后续优化方向

1. **并发生成**: 同时调用两个API，减少总耗时
2. **缓存机制**: 相同prompt的结果缓存
3. **用户投票**: 收集用户反馈，统计哪个模型效果更好
4. **模型切换**: 根据统计结果，优先使用效果好的模型
5. **更多模型**: 接入更多图片生成模型（如Stable Diffusion、DALL-E等）

## 常见问题

### Q: 两个模型都需要API Key吗？
A: 不需要。Gemini使用已配置的 `IMAGE_API_URL` 和 `IMAGE_API_TOKEN`，通义千问使用 `QWEN_API_KEY`，都是已有配置。

### Q: 可以只使用一个模型吗？
A: 可以。修改 `emoticon_service.py` 中的 `create_emoticon()` 方法，注释掉不需要的模型即可。

### Q: 图片生成失败怎么办？
A: 系统有容错机制，会发送成功的图片和失败提示。检查日志了解具体错误原因。

### Q: 图片质量可以调整吗？
A: 可以。在 `qwen_image_service.py` 中修改 `size` 参数，支持的分辨率见API文档。

## 示例效果

```
用户: 表情包：开心

系统回复:
✨ 为您生成了【开心】表情包，使用两个AI模型对比：

【1】Gemini 2.5 Flash
[图片1]

【2】通义千问 Qwen-Image-Plus
[图片2]
```
