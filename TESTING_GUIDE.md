# 🧪 意图匹配系统测试指南

> **版本**: v2.0 (AI增强版)  
> **日期**: 2025-01-13  
> **状态**: 完整功能测试就绪

## 📋 测试前准备

### **环境要求**
- Python 3.8+
- 已配置通义千问API密钥
- 服务器环境（Ubuntu/CentOS）

### **1. 拉取最新代码**
```bash
cd /root  # 或你的工作目录
rm -rf FriendAI  # 删除旧版本
git clone https://github.com/ConstTyrone/FriendAI.git
cd FriendAI/WeiXinKeFu
```

### **2. 安装依赖**
```bash
# 安装Python依赖
pip3 install -r requirements.txt

# 验证关键依赖
python3 -c "import numpy, scipy, sklearn; print('✅ AI依赖安装成功')"
```

### **3. 配置环境变量**
```bash
# 检查.env文件
ls -la .env*

# 确保.env中包含通义千问API密钥
# 必需配置:
QWEN_API_KEY=your_qwen_api_key
QWEN_API_ENDPOINT=https://dashscope.aliyuncs.com/compatible-mode/v1

# 其他必需配置:
WEWORK_CORP_ID=ww7b4256dcdcea9b3e
WEWORK_SECRET=your_secret
WEWORK_TOKEN=your_token
WEWORK_AES_KEY=your_aes_key
```

## 🚀 阶段性测试流程

### **阶段1: 基础功能测试 (5分钟)**

#### **步骤1.1: 初始化数据库**
```bash
python3 scripts/create_intent_tables.py --sample
```

**期望输出**:
```
✅ 创建用户意图表成功
✅ 创建匹配记录表成功
✅ 创建向量索引表成功
✅ 创建推送历史表成功
✅ 创建用户推送偏好表成功
✅ 添加了 2 个示例意图
🎉 所有意图匹配系统表创建成功！
```

#### **步骤1.2: 测试基础匹配功能**
```bash
python3 test_intent_system.py
```

**期望输出**:
```
✅ 数据库测试完成！
✅ 匹配引擎测试完成！
🎉 所有测试完成！意图匹配系统基础功能正常
```

如果出现 `ModuleNotFoundError: No module named 'numpy'`，说明依赖安装失败，重新执行步骤2。

### **阶段2: AI增强功能测试 (10分钟)**

#### **步骤2.1: 添加向量字段支持**
```bash
python3 scripts/add_vector_columns.py
```

**期望输出**:
```
============================================================
更新数据库以支持向量存储
============================================================
✓ user_intents表更新完成
✓ profiles_xxx表更新完成 (会显示多个用户表)
✓ intent_matches表更新完成
✓ 向量索引表创建完成
============================================================
✅ 数据库更新完成！
============================================================
```

#### **步骤2.2: 初始化向量化**
```bash
python3 scripts/initialize_vectors.py
```

**期望输出**:
```
============================================================
初始化向量化数据
============================================================

1. 向量化意图数据:
   处理意图 1/2: 寻找技术合伙人
      ✓ 成功
   处理意图 2/2: 寻找投资人
      ✓ 成功
   ✓ 意图向量化完成: 2/2

2. 向量化联系人数据:
   处理表: profiles_test_user_001
      ✓ 表 profiles_test_user_001 完成: X/Y
   ✓ 联系人向量化完成: X/Y

3. 向量化统计:
   - 已向量化意图: 2/2
   - 已向量化联系人: X
   - 向量索引总数: X

✅ 向量化初始化完成！
```

**如果失败**:
- 检查API密钥配置
- 网络连接是否正常
- 可以用 `--force` 参数重新运行

#### **步骤2.3: 测试AI增强匹配**
```bash
python3 test_ai_matching.py
```

**期望输出**:
```
🚀 开始测试AI增强意图匹配系统

============================================================
测试向量服务
============================================================
✅ 向量服务测试通过！

============================================================
测试AI增强匹配引擎
============================================================
✅ AI增强匹配测试通过！

🎉 所有AI增强功能测试完成！系统运行正常
```

### **阶段3: 后端服务测试 (5分钟)**

#### **步骤3.1: 启动后端服务**
```bash
python3 run.py
```

**期望输出**:
```
向量服务已启用
AI增强匹配引擎已启用
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using statreload
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**关键指标**:
- ✅ `向量服务已启用` - AI功能就绪
- ✅ `AI增强匹配引擎已启用` - 增强匹配功能就绪
- ✅ 服务在端口8000运行

#### **步骤3.2: 测试API接口**
打开新终端窗口：

```bash
# 测试意图管理API
curl -X GET "http://localhost:8000/api/intents" \
  -H "Authorization: Bearer dGVzdF91c2VyXzAwMQ=="

# 测试匹配API
curl -X POST "http://localhost:8000/api/intents/1/match" \
  -H "Authorization: Bearer dGVzdF91c2VyXzAwMQ=="
```

**期望输出**:
- GET请求返回意图列表（JSON格式）
- POST请求返回匹配结果，包含AI相关字段

### **阶段4: 前端集成测试 (可选)**

如果你有微信开发者工具：

1. **配置服务域名**:
   - 在 `weixi_minimo/utils/constants.js` 中
   - 修改 `BASE_URL` 为你的服务器地址

2. **访问意图管理页面**:
   - 设置页面 → "意图匹配"
   - 应该显示 "AI增强" 标识

3. **创建测试意图**:
   - 意图名称: "寻找合作伙伴"
   - 描述: "寻找技术背景强的创业合伙人"
   - 关键词: "技术", "创业", "合伙人"

4. **查看匹配结果**:
   - 应该显示匹配类型（AI语义匹配/规则匹配）
   - 显示语义相似度评分

## 🐛 故障排除

### **常见问题及解决方案**

#### **问题1: numpy模块未找到**
```bash
# 解决方案
pip3 install numpy scipy scikit-learn
```

#### **问题2: 向量化失败**
```bash
# 检查API配置
python3 -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key配置:', 'OK' if os.getenv('QWEN_API_KEY') else 'Missing')"

# 测试API连接
curl -H "Authorization: Bearer $QWEN_API_KEY" \
  https://dashscope.aliyuncs.com/compatible-mode/v1/models
```

#### **问题3: 服务启动失败**
```bash
# 检查端口占用
netstat -tlnp | grep :8000

# 使用其他端口
LOCAL_SERVER_PORT=8001 python3 run.py
```

#### **问题4: API请求401错误**
```bash
# 使用正确的测试token
curl -X GET "http://localhost:8000/api/intents" \
  -H "Authorization: Bearer dGVzdF91c2VyXzAwMQ=="
```

## 📊 测试验收标准

### **必须通过的测试项**

- [ ] **基础功能**: test_intent_system.py 全部通过
- [ ] **AI功能**: test_ai_matching.py 全部通过  
- [ ] **服务启动**: 显示"向量服务已启用"和"AI增强匹配引擎已启用"
- [ ] **API接口**: 意图CRUD和匹配接口正常响应
- [ ] **数据库**: 至少2个示例意图被成功向量化

### **功能验证清单**

1. ✅ **意图管理**: 创建、查看、更新、删除意图
2. ✅ **基础匹配**: 关键词和条件匹配工作正常
3. ✅ **AI增强匹配**: 语义相似度计算和混合匹配算法
4. ✅ **向量化**: 意图和联系人成功向量化
5. ✅ **匹配结果**: 返回匹配类型和相似度评分

## 🔍 深度测试（可选）

### **性能测试**
```bash
# 批量创建意图测试性能
python3 -c "
import requests, time
start = time.time()
for i in range(10):
    requests.post('http://localhost:8000/api/intents',
        headers={'Authorization': 'Bearer dGVzdF91c2VyXzAwMQ=='},
        json={'name': f'测试意图{i}', 'description': f'描述{i}'})
print(f'创建10个意图耗时: {time.time()-start:.2f}秒')
"
```

### **匹配准确性测试**
```bash
# 测试语义匹配准确性
python3 -c "
# 创建相似意图，测试语义匹配是否准确
# 预期: 语义相似的意图应该匹配到相关联系人
"
```

## 📝 测试报告

测试完成后，请记录：

1. **通过的测试阶段**: 阶段1-4中哪些通过
2. **发现的问题**: 错误信息和解决方案
3. **性能指标**: 响应时间、匹配准确度
4. **建议改进**: 功能或性能改进建议

---

## 🎯 快速测试命令汇总

```bash
# 一键测试脚本 (依次执行)
git clone https://github.com/ConstTyrone/FriendAI.git
cd FriendAI/WeiXinKeFu
pip3 install -r requirements.txt
python3 scripts/create_intent_tables.py --sample
python3 test_intent_system.py
python3 scripts/add_vector_columns.py  
python3 scripts/initialize_vectors.py
python3 test_ai_matching.py
python3 run.py
```

**如果所有命令都成功执行，意图匹配系统就完全可用了！** 🎉