# 调试指南 - 解决编译错误

## 问题描述

微信开发者工具提示找不到页面文件，但文件实际存在。

## 解决方案

### 1. 清除缓存并重新打开项目

1. 关闭微信开发者工具
2. 删除项目根目录下的 `.cache` 和 `.build` 文件夹（如果存在）
3. 重新用微信开发者工具打开项目

### 2. 检查文件完整性

确认以下文件都存在且内容完整：

```
pages/
├── contact-list/
│   ├── contact-list.js
│   ├── contact-list.json  
│   ├── contact-list.wxml
│   └── contact-list.wxss
├── ai-search/
│   ├── ai-search.js
│   ├── ai-search.json
│   ├── ai-search.wxml
│   └── ai-search.wxss
├── contact-detail/
│   ├── contact-detail.js
│   ├── contact-detail.json
│   ├── contact-detail.wxml
│   └── contact-detail.wxss
├── contact-form/
│   ├── contact-form.js
│   ├── contact-form.json
│   ├── contact-form.wxml
│   └── contact-form.wxss
└── settings/
    ├── settings.js
    ├── settings.json
    ├── settings.wxml
    └── settings.wxss
```

### 3. 检查TDesign组件库

确保tdesign-miniprogram文件夹存在且完整：

```bash
# 如果缺少tdesign-miniprogram，需要重新安装
npm install tdesign-miniprogram --production
```

### 4. 项目配置验证

检查 `app.json` 配置：

```json
{
  "pages": [
    "pages/contact-list/contact-list",
    "pages/ai-search/ai-search", 
    "pages/contact-detail/contact-detail",
    "pages/contact-form/contact-form",
    "pages/settings/settings"
  ],
  "tabBar": {
    "list": [
      {
        "pagePath": "pages/contact-list/contact-list",
        "text": "联系人"
      },
      {
        "pagePath": "pages/ai-search/ai-search",
        "text": "AI搜索"
      }
    ]
  }
}
```

### 5. 逐步调试

如果问题仍然存在，可以按以下步骤逐步调试：

1. **临时移除其他页面**：在 `app.json` 中只保留 `pages/contact-list/contact-list`
2. **测试单个页面**：确认联系人列表页面能正常加载
3. **逐个添加页面**：依次添加其他页面到 `app.json`

### 6. 最小化测试配置

使用以下最小化的 `app.json` 进行测试：

```json
{
  "pages": [
    "pages/contact-list/contact-list"
  ],
  "window": {
    "navigationBarTitleText": "社交关系"
  }
}
```

### 7. 开发工具设置

确保微信开发者工具设置正确：

1. **详情 → 本地设置**：
   - 勾选 "不校验合法域名、web-view(业务域名)、TLS 版本以及 HTTPS 证书"
   - 勾选 "启用自定义处理命令"

2. **详情 → 项目配置**：
   - ES6 转 ES5: 开启
   - 增强编译: 开启
   - 上传代码时样式自动补全: 开启

### 8. 错误日志分析

查看微信开发者工具的控制台和编译日志，查找具体的错误信息。

## 常见问题

### Q: 提示找不到 tdesign-miniprogram 组件
A: 检查 `miniprogram_npm` 文件夹是否存在，如果没有，点击工具栏的 "工具 → 构建 npm"

### Q: 页面空白或报错
A: 检查页面的 JS 文件中是否有语法错误，特别是 import 语句

### Q: TabBar 不显示
A: 确保 tabBar 配置正确，并且移除了 iconPath 配置（因为我们没有图标文件）

## 成功标志

当编译成功时，你应该看到：
1. 没有红色错误信息
2. 模拟器中显示联系人列表页面
3. 底部显示 TabBar（联系人、AI搜索）
4. 可以正常切换页面

如果问题仍然存在，请提供具体的错误日志进行进一步排查。