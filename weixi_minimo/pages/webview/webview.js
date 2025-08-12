// pages/webview/webview.js
Page({
  data: {
    url: '',
    title: ''
  },

  onLoad(options) {
    console.log('[WebView] onLoad with options:', options);
    
    const url = decodeURIComponent(options.url || '');
    const title = decodeURIComponent(options.title || '加载中...');
    
    if (!url) {
      wx.showModal({
        title: '错误',
        content: '缺少必要的URL参数',
        showCancel: false,
        success: () => {
          wx.navigateBack();
        }
      });
      return;
    }
    
    // 设置页面标题
    wx.setNavigationBarTitle({
      title: title
    });
    
    this.setData({
      url: url,
      title: title,
      isKfPage: url.includes('work.weixin.qq.com/kfid')
    });
    
    console.log('[WebView] Loading URL:', url);
    
    // 如果是企微客服页面，显示操作指引
    if (url.includes('work.weixin.qq.com/kfid')) {
      // 立即显示提示
      wx.showModal({
        title: '操作提示',
        content: '请在企微客服中发送验证码，完成后点击返回按钮查看绑定状态',
        showCancel: false,
        confirmText: '我知道了',
        success: () => {
          // 设置导航栏返回按钮提示
          wx.setNavigationBarTitle({
            title: '企微客服(发送验证码)'
          });
        }
      });
    }
  },

  // 网页加载成功
  onWebViewLoad(e) {
    console.log('[WebView] Page loaded:', e.detail.src);
  },

  // 网页加载失败
  onWebViewError(e) {
    console.error('[WebView] Load error:', e);
    wx.showModal({
      title: '加载失败',
      content: '页面加载失败，请稍后重试',
      showCancel: false,
      success: () => {
        wx.navigateBack();
      }
    });
  },

  // 监听网页消息
  onWebViewMessage(e) {
    console.log('[WebView] Received message:', e.detail);
    
    // 处理来自网页的消息
    const messages = e.detail.data;
    if (messages && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      
      // 根据消息类型处理
      if (lastMessage.type === 'binding_complete') {
        // 绑定完成，返回上一页
        wx.navigateBack();
      }
    }
  }
});