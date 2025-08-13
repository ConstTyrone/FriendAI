# AI增强匹配功能 - 快速部署指南

## 📋 前提条件

1. **基础系统已运行**
   - 意图匹配系统第一阶段已完成
   - 后端服务正常运行
   - 小程序可以正常访问

2. **API密钥配置**
   ```bash
   # 在 .env 文件中添加
   QWEN_API_KEY=your_qwen_api_key
   ```

## 🚀 快速部署流程

### 第1步：运行测试验证
```bash
cd WeiXinKeFu
python test_ai_matching.py
```

如果测试失败，请检查：
- API密钥是否正确配置
- 依赖包是否完整安装
- 网络连接是否正常

### 第2步：数据库迁移
```bash
# 添加向量存储支持
python scripts/add_vector_columns.py

# 查看迁移结果
python scripts/add_vector_columns.py --db user_profiles.db
```

预期输出：
```
✅ 数据库更新完成！
- 意图总数: X
- 用户表数量: X  
- 匹配记录总数: X
```

### 第3步：向量化初始化
```bash
# 为现有数据生成向量
python scripts/initialize_vectors.py

# 强制重新生成所有向量（可选）
python scripts/initialize_vectors.py --force
```

预期输出：
```
✅ 向量化初始化完成！
- 已向量化意图: X/X (100%)
- 已向量化联系人: X/X (100%)
```

### 第4步：重启后端服务
```bash
# 停止当前服务（Ctrl+C）
# 重新启动
python run.py
```

启动后应该看到：
```
向量服务已启用
AI增强匹配引擎已启用
```

### 第5步：测试AI增强功能

1. **在小程序中创建新意图**
   - 进入设置页面 → 意图匹配
   - 创建一个描述性较强的意图
   - 观察是否显示"AI增强"标识

2. **查看匹配结果**
   - 触发意图匹配
   - 检查匹配结果页面是否显示：
     - AI标识徽章
     - 语义相似度评分
     - 匹配类型标签

3. **验证API功能**
   ```bash
   # 测试AI状态API
   curl -X GET "http://localhost:8000/api/ai/vector-status" \
        -H "Authorization: Bearer YOUR_TOKEN"
   ```

## 🔧 故障排除

### 常见问题

**问题1：向量化失败**
```
❌ 向量化API错误: 401
```
解决方案：
- 检查QWEN_API_KEY是否正确
- 确认API密钥有足够余额
- 检查网络连接

**问题2：数据库迁移失败**
```
❌ 更新失败: no such table
```
解决方案：
- 确认已运行第一阶段的建表脚本
- 检查数据库文件路径是否正确

**问题3：匹配结果无AI标识**
```
匹配成功但未显示AI标识
```
解决方案：
- 确认向量初始化已完成
- 检查意图和联系人是否已向量化
- 重启后端服务

**问题4：语义相似度为0**
```
向量相似度显示为0%
```
解决方案：
- 检查向量数据是否正确存储
- 确认向量维度一致（1536维）
- 重新运行向量化初始化

### 检查命令

```bash
# 检查向量化状态
python -c "
import sqlite3
conn = sqlite3.connect('user_profiles.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM user_intents WHERE embedding IS NOT NULL')
print('已向量化意图:', cursor.fetchone()[0])
cursor.execute('SELECT COUNT(*) FROM vector_index')
print('向量索引数量:', cursor.fetchone()[0])
conn.close()
"

# 测试向量服务
python -c "
import asyncio
import os
if os.getenv('QWEN_API_KEY'):
    print('✅ API密钥已配置')
    from src.services.vector_service import vector_service
    print('✅ 向量服务可导入')
else:
    print('❌ 未配置API密钥')
"
```

## 📊 性能调优

### 批量处理优化
```bash
# 批量向量化（每次最多20个联系人）
python scripts/initialize_vectors.py

# 如有大量数据，可分批执行
python -c "
from scripts.initialize_vectors import initialize_vectors
import asyncio
# 处理特定用户
asyncio.run(initialize_vectors('user_profiles.db', False))
"
```

### 内存优化
- 单次API调用限制：最多10个文本
- 向量存储：使用pickle序列化
- 缓存策略：向量计算结果缓存5分钟

## 🎉 验收标准

部署成功的标志：

1. **测试脚本100%通过**
   ```
   总结: 7/7 项测试通过 (100.0%)
   🎉 所有测试通过！AI增强匹配功能正常工作
   ```

2. **小程序显示AI功能**
   - 匹配结果页面显示"AI增强"徽章
   - 匹配卡片显示语义相似度评分
   - 匹配类型显示为"AI增强匹配"

3. **API返回AI数据**
   - `/api/matches` 返回 `match_type: "hybrid"`
   - `/api/ai/vector-status` 返回 `aiEnabled: true`
   - 向量化百分比 > 0%

## 🔄 后续维护

### 定期任务
```bash
# 每周检查向量化状态
python scripts/initialize_vectors.py

# 监控API调用量
grep "向量化API" logs/*.log | wc -l
```

### 性能监控
- 向量化成功率
- API响应时间
- 匹配质量评分

---

**完成时间预估**：15-30分钟
**依赖**：网络连接，通义千问API访问权限
**支持**：如遇问题可查看详细日志或联系技术支持