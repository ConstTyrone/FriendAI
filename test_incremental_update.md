# 联系人增量更新修复验证

## 问题描述
联系人编辑时出现信息覆盖问题，之前的信息会被空值覆盖。

## 根本原因分析

### 1. 前端问题
- `contact-form.js` 第502-519行发送完整的 `submitData`
- 即使字段为空，也会发送空字符串，如 `phone: (formData.phone || '').trim()`
- 导致后端接收到空字符串并更新数据库

### 2. 后端问题  
- API层只检查 `request.phone is not None`，空字符串被认为是"有效值"
- 数据库用空字符串覆盖原有有效数据

### 3. AI处理问题
- 语音解析在编辑模式下无法正确获取现有数据
- 字段访问方式错误，数据库访问不一致

## 修复方案

### 前端修复 (contact-form.js)
```javascript
// 修复前：发送所有字段（包括空值）
const submitData = {
  name: (formData.name || '').trim(),
  phone: (formData.phone || '').trim(),
  // ... 所有字段
};

// 修复后：只发送有值且变化的字段
const submitData = {};
if (mode === 'edit') {
  // 编辑模式：只发送有值且与原始数据不同的字段
  if (value && value !== originalValue) {
    submitData[field] = value;
  }
} else {
  // 新增模式：只发送有值的字段
  if (value) {
    submitData[field] = value;
  }
}
```

### 后端修复 (main.py)
```python
# 修复前：只检查非None
if request.phone is not None:
    update_data["phone"] = request.phone

# 修复后：过滤空值和"未知"
def is_valid_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ''
    return True

if is_valid_value(request.phone):
    update_data["phone"] = request.phone.strip()
```

### AI语音解析修复 (main.py)
```python
# 修复前：数据库访问不一致，字段访问错误
db = db_manager.get_database(current_user)
gender = existing_profile.get('basic_info', {}).get('gender', '未知')

# 修复后：统一数据库访问，正确字段访问
query_user_id = get_query_user_id(current_user)
existing_profile = db.get_user_profile_detail(query_user_id, int(contact_id))
gender = existing_profile.get('gender', '未知')
```

## 验证步骤

### 1. 前端验证
1. 打开微信开发者工具
2. 进入联系人编辑页面
3. 只修改一个字段（如电话号码）
4. 查看网络请求，确认只发送了修改的字段

### 2. 后端验证  
1. 启动后端服务：`cd WeiXinKeFu && python run.py`
2. 使用测试用户 `wm0gZOdQAAv-phiLJWS77wmzQQSOrL1Q`
3. 创建一个完整的联系人信息
4. 编辑时只修改一个字段，确认其他字段未被覆盖

### 3. 语音解析验证
1. 编辑现有联系人
2. 使用语音输入补充信息
3. 确认AI正确整合了现有数据和新语音信息

## 预期结果
- ✅ 编辑联系人时，只更新修改的字段
- ✅ 未修改的字段保持原有值不被覆盖  
- ✅ 语音输入正确合并现有数据
- ✅ 空值和"未知"不会覆盖有效数据

## 测试用例

### 测试用例1：基本编辑功能
1. 创建联系人：张三，男，30岁，电话13800138000，公司腾讯
2. 编辑联系人：只修改电话为13900139000
3. 验证：姓名、性别、年龄、公司等其他字段保持不变

### 测试用例2：语音输入合并
1. 现有联系人：李四，女，25岁，公司阿里巴巴
2. 语音输入："她是产品经理，住在杭州"
3. 验证：姓名、性别、年龄、公司保持不变，新增职位和地址

### 测试用例3：空值过滤
1. API请求包含空字符串字段
2. 验证：空字符串不会更新数据库
3. 验证："未知"值不会覆盖现有有效数据