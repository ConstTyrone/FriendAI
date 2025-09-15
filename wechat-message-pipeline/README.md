# 微信消息处理管道 (WeChat Message Pipeline)

一个高度可扩展、模块化的微信/企微消息处理框架，基于管道模式设计，支持消息的接收、解密、解析、路由、业务处理和响应。

## 🚀 特性

- **🔧 高度可扩展**: 基于处理器管道模式，轻松添加新的处理逻辑
- **🔒 安全可靠**: 完整的签名验证和AES加解密支持
- **🌐 多平台支持**: 兼容企业微信和微信客服两个平台
- **⚡ 异步处理**: 全异步处理架构，高性能
- **📊 性能监控**: 内置性能指标和处理统计
- **🛡️ 错误处理**: 完善的错误处理和重试机制
- **🧪 易于测试**: 每个组件独立可测

## 📁 项目结构

```
wechat-message-pipeline/
├── src/                     # 源代码
│   ├── core/               # 核心抽象类
│   │   ├── context.py      # 消息上下文
│   │   ├── handler.py      # 处理器基类
│   │   ├── pipeline.py     # 消息管道
│   │   └── exceptions.py   # 自定义异常
│   ├── handlers/           # 具体处理器实现
│   │   ├── crypto/         # 加解密处理器
│   │   ├── parsing/        # 解析处理器
│   │   ├── validation/     # 验证处理器
│   │   ├── routing/        # 路由处理器
│   │   ├── business/       # 业务处理器
│   │   └── response/       # 响应处理器
│   ├── platforms/          # 平台适配器
│   ├── config/             # 配置管理
│   └── utils/              # 工具类
├── examples/               # 使用示例
├── tests/                  # 测试用例
└── migration/              # 迁移工具
```

## 🏗️ 核心架构

### 消息处理流程

```
接收消息 → 签名验证 → 消息解密 → 消息解析 → 消息验证 → 路由分发 → 业务处理 → 响应构建 → 消息加密 → 发送响应
```

### 核心组件

1. **MessageContext**: 贯穿整个处理链的消息上下文
2. **MessageHandler**: 处理器抽象基类
3. **MessagePipeline**: 管道管理器，串联所有处理器
4. **处理器实现**: 各种具体的处理器实现

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基础用法

```python
import asyncio
from src.core import MessagePipeline, MessageContext
from src.handlers.crypto import SignatureVerificationHandler, MessageDecryptionHandler
from src.handlers.parsing import XMLMessageParser

# 创建消息处理管道
pipeline = MessagePipeline(name="WeChat处理管道")

# 添加处理器
pipeline.use(SignatureVerificationHandler(token="your_token"))
pipeline.use(MessageDecryptionHandler(encoding_aes_key="your_aes_key"))
pipeline.use(XMLMessageParser())

# 处理消息
async def handle_message():
    # 创建消息上下文
    context = MessageContext(
        platform="wework",
        query_params={
            "msg_signature": "signature",
            "timestamp": "1234567890",
            "nonce": "random_string"
        },
        encrypted_message="encrypted_xml_content"
    )

    # 处理消息
    result = await pipeline.process(context)

    # 查看处理结果
    print(f"处理结果: {result.summary()}")

# 运行示例
asyncio.run(handle_message())
```

## 📊 处理器说明

### 加密处理器 (crypto/)

- **SignatureVerificationHandler**: 验证消息签名
- **MessageDecryptionHandler**: 解密消息内容
- **MessageEncryptionHandler**: 加密回复消息

### 解析处理器 (parsing/)

- **XMLMessageParser**: 解析XML格式消息
- **JSONMessageParser**: 解析JSON格式消息（扩展用）

### 业务处理器 (business/)

- **VerifyCodeHandler**: 处理验证码绑定
- **ChatHandler**: 处理聊天消息
- **EventHandler**: 处理事件通知
- **MediaHandler**: 处理媒体消息

## 🔧 配置

### 环境变量

```bash
# 企微/微信客服配置
WEWORK_TOKEN=your_token
WEWORK_AES_KEY=your_aes_key
WEWORK_CORP_ID=your_corp_id

# 日志配置
LOG_LEVEL=INFO
```

## 🧪 测试

```bash
# 运行测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_pipeline.py

# 生成覆盖率报告
python -m pytest --cov=src tests/
```

## 📈 性能监控

```python
# 获取管道性能指标
metrics = pipeline.get_metrics()
print(f"总处理数: {metrics['pipeline_metrics']['total_processed']}")
print(f"平均处理时间: {metrics['pipeline_metrics']['avg_processing_time']:.3f}s")
print(f"错误率: {metrics['pipeline_metrics']['error_rate']:.2%}")

# 获取处理器指标
for handler_metric in metrics['handler_metrics']:
    print(f"处理器 {handler_metric['name']}: {handler_metric['avg_processing_time']:.3f}s")
```

## 🔌 扩展开发

### 创建自定义处理器

```python
from src.core import MessageHandler, MessageContext

class CustomHandler(MessageHandler):
    def __init__(self, **kwargs):
        super().__init__(name="CustomHandler", priority=50, **kwargs)

    async def process(self, context: MessageContext) -> MessageContext:
        # 自定义处理逻辑
        context.add_log("执行自定义处理")
        return context

    def can_process(self, context: MessageContext) -> bool:
        # 处理条件判断
        return context.message_type == "custom"

# 使用自定义处理器
pipeline.use(CustomHandler())
```

### 添加事件钩子

```python
# 添加处理前钩子
pipeline.add_hook('before_process', lambda ctx: print(f"开始处理: {ctx.request_id}"))

# 添加错误处理钩子
pipeline.add_hook('on_error', lambda ctx: print(f"处理出错: {ctx.errors}"))
```

## 🤝 贡献

欢迎提交 Issues 和 Pull Requests！

## 📄 许可证

MIT License

## 🔗 相关项目

- [原始微信客服系统](../WeiXinKeFu/) - 基于此项目抽象而来的消息处理系统