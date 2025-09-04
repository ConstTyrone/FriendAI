import authManager from './utils/auth-manager';
import dataManager from './utils/data-manager';
import notificationManager from './utils/notification-manager';
import cacheManager from './utils/cache-manager';
import themeManager from './utils/theme-manager';

App({
  globalData: {
    // 用户信息
    isLoggedIn: false,
    userInfo: null,
    
    // 应用配置
    systemInfo: null,
    
    // 通知相关
    hasNewMatches: false,
    unreadMatchCount: 0,
    latestMatches: [],
    
    // 应用状态
    isBackground: false,
    
    // 版本信息
    version: '1.0.0'
  },

  onLaunch(options) {
    console.log('小程序启动', options);
    
    // 获取系统信息
    this.getSystemInfo();
    
    // 初始化主题
    this.initTheme();
    
    // 检查更新
    this.checkForUpdate();
    
    // 检查是否需要显示启动动画
    this.checkSplashScreen();
    
    // 初始化认证状态
    this.initAuth();
    
    // 设置路由拦截
    this.setupRouteGuard();
  },

  onShow(options) {
    console.log('小程序显示', options);
    
    // 标记为前台运行
    this.globalData.isBackground = false;
    
    // 处理场景值
    this.handleScene(options.scene);
    
    // 启动缓存自动清理
    cacheManager.startAutoCleanup();
    
    // 启动内存清理（仅在前台）
    dataManager.startMemoryCleanup();
    dataManager.setAppActive(true);
    
    // 启动自动数据刷新
    dataManager.startAutoRefresh();
    
    // 如果已登录，调整轮询频率为活跃状态
    if (this.globalData.isLoggedIn) {
      notificationManager.adjustPollingInterval(this.getPollingInterval());
    }
  },

  onHide() {
    console.log('小程序隐藏');
    
    // 标记为后台运行
    this.globalData.isBackground = true;
    
    // 停止缓存自动清理
    cacheManager.stopAutoCleanup();
    
    // 暂停内存清理
    dataManager.setAppActive(false);
    
    // 停止自动数据刷新
    dataManager.stopAutoRefresh();
    
    // 调整轮询频率为后台状态
    if (this.globalData.isLoggedIn) {
      notificationManager.adjustPollingInterval(60000); // 后台时60秒轮询
    }
  },

  onError(error) {
    console.error('小程序错误:', error);
    
    // 错误上报
    this.reportError(error);
  },
  
  /**
   * 小程序卸载时清理资源
   */
  onUnload() {
    console.log('小程序卸载，清理资源');
    
    // 停止所有定时器
    notificationManager.stopPolling();
    cacheManager.stopAutoCleanup();
    dataManager.stopMemoryCleanup();
    
    // 清理监听器
    dataManager.removeAllListeners();
  },

  /**
   * 获取系统信息
   */
  getSystemInfo() {
    try {
      const systemInfo = wx.getSystemInfoSync();
      this.globalData.systemInfo = systemInfo;
      
      console.log('系统信息:', systemInfo);
    } catch (error) {
      console.error('获取系统信息失败:', error);
    }
  },

  /**
   * 初始化主题
   */
  initTheme() {
    const theme = themeManager.init();
    this.globalData.theme = theme;
    console.log('当前主题:', theme);
    
    // 设置全局主题管理器引用
    this.themeManager = themeManager;
  },

  /**
   * 检查小程序更新
   */
  checkForUpdate() {
    if (wx.canIUse('getUpdateManager')) {
      const updateManager = wx.getUpdateManager();
      
      updateManager.onCheckForUpdate((res) => {
        console.log('检查更新结果:', res.hasUpdate);
      });
      
      updateManager.onUpdateReady(() => {
        wx.showModal({
          title: '更新提示',
          content: '新版本已准备好，是否重启应用？',
          success: (res) => {
            if (res.confirm) {
              updateManager.applyUpdate();
            }
          }
        });
      });
      
      updateManager.onUpdateFailed(() => {
        console.error('新版本下载失败');
      });
    }
  },

  /**
   * 初始化认证状态
   */
  async initAuth() {
    try {
      // 检查本地存储的认证信息
      const isLoggedIn = authManager.isLoggedIn();
      
      if (isLoggedIn) {
        // 验证token有效性
        const isValid = await authManager.validateToken();
        
        if (isValid) {
          this.globalData.isLoggedIn = true;
          this.globalData.userInfo = authManager.getCurrentUser();
          
          console.log('用户已登录:', this.globalData.userInfo);
          
          // 启动通知轮询
          this.startNotificationPolling();
        } else {
          console.log('Token已失效，需要重新登录');
        }
      } else {
        console.log('用户未登录');
      }
    } catch (error) {
      console.error('初始化认证状态失败:', error);
    }
  },
  
  /**
   * 启动通知轮询
   */
  startNotificationPolling() {
    // 延迟1秒后开始轮询，避免启动时资源竞争
    setTimeout(() => {
      console.log('启动匹配通知轮询...');
      // 智能轮询策略：初始30秒，用户活跃时15秒，后台时60秒
      const pollingInterval = this.getPollingInterval();
      notificationManager.startPolling(pollingInterval);
    }, 1000);
  },
  
  /**
   * 获取智能轮询间隔
   */
  getPollingInterval() {
    // 基础间隔30秒
    let interval = 30000;
    
    // 如果用户刚刚创建了意图，短时间内使用更短的间隔
    const recentIntentCreation = wx.getStorageSync('recent_intent_creation');
    if (recentIntentCreation) {
      const timeSinceCreation = Date.now() - recentIntentCreation;
      if (timeSinceCreation < 5 * 60 * 1000) { // 5分钟内
        interval = 15000; // 15秒轮询
      }
    }
    
    // 如果是后台运行，延长轮询间隔
    if (this.globalData.isBackground) {
      interval = 60000; // 60秒
    }
    
    console.log('通知轮询间隔:', interval / 1000, '秒');
    return interval;
  },
  
  /**
   * 停止通知轮询
   */
  stopNotificationPolling() {
    console.log('停止匹配通知轮询');
    notificationManager.stopPolling();
  },

  /**
   * 处理场景值
   */
  handleScene(scene) {
    console.log('场景值:', scene);
    
    // 根据不同场景值处理相应逻辑
    switch (scene) {
      case 1001: // 发现栏小程序主入口
      case 1089: // 微信聊天主界面下拉
        // 正常启动
        break;
      case 1047: // 扫描二维码
      case 1048: // 长按识别二维码
        // 二维码启动，可能需要特殊处理
        break;
      default:
        break;
    }
  },

  /**
   * 错误上报
   */
  reportError(error) {
    // 这里可以实现错误上报逻辑
    console.log('错误上报:', error);
  },

  /**
   * 获取用户信息
   */
  getUserInfo() {
    return this.globalData.userInfo;
  },

  /**
   * 设置用户信息
   */
  setUserInfo(userInfo) {
    this.globalData.userInfo = userInfo;
    this.globalData.isLoggedIn = !!userInfo;
  },

  /**
   * 清除用户信息
   */
  clearUserInfo() {
    this.globalData.userInfo = null;
    this.globalData.isLoggedIn = false;
    
    // 停止通知轮询
    this.stopNotificationPolling();
    
    // 清除通知相关状态
    this.globalData.hasNewMatches = false;
    this.globalData.unreadMatchCount = 0;
    this.globalData.latestMatches = [];
  },

  /**
   * 设置路由拦截
   */
  setupRouteGuard() {
    // 保存原始的wx.navigateTo方法
    const originalNavigateTo = wx.navigateTo;
    const originalSwitchTab = wx.switchTab;
    const originalRedirectTo = wx.redirectTo;
    
    // 需要登录才能访问的页面
    const protectedPages = [
      'pages/contact-list/contact-list',
      'pages/intent-manager/intent-manager', 
      'pages/contact-detail/contact-detail',
      'pages/contact-form/contact-form',
      'pages/matches/matches'
    ];
    
    // 重写wx.navigateTo
    wx.navigateTo = (options) => {
      console.log('导航到:', options.url);
      
      const pagePath = options.url.split('?')[0];
      
      if (protectedPages.includes(pagePath)) {
        if (!authManager.isLoggedIn()) {
          console.log('未登录，跳转到设置页面');
          wx.showModal({
            title: '需要登录',
            content: '请先登录后再使用此功能',
            showCancel: false,
            success: () => {
              wx.switchTab({
                url: '/pages/settings/settings'
              });
            }
          });
          return;
        }
        
        // 检查绑定状态
        const userInfo = authManager.getCurrentUser();
        if (userInfo && !userInfo.isBound) {
          console.log('未绑定企微客服，跳转到绑定页面');
          wx.showModal({
            title: '需要绑定',
            content: '请先绑定企业微信客服账号后再使用此功能',
            showCancel: false,
            success: () => {
              wx.navigateTo({
                url: '/pages/bind-account/bind-account'
              });
            }
          });
          return;
        }
      }
      
      originalNavigateTo.call(wx, options);
    };
    
    // 重写wx.switchTab  
    wx.switchTab = (options) => {
      console.log('切换Tab到:', options.url);
      
      const pagePath = options.url.split('?')[0];
      
      if (protectedPages.includes(pagePath)) {
        if (!authManager.isLoggedIn()) {
          console.log('未登录，跳转到设置页面');
          wx.showModal({
            title: '需要登录',
            content: '请先登录后再使用此功能',
            showCancel: false,
            success: () => {
              originalSwitchTab.call(wx, {
                url: '/pages/settings/settings'
              });
            }
          });
          return;
        }
        
        // 检查绑定状态
        const userInfo = authManager.getCurrentUser();
        if (userInfo && !userInfo.isBound) {
          console.log('未绑定企微客服，跳转到绑定页面');
          wx.showModal({
            title: '需要绑定',
            content: '请先绑定企业微信客服账号后再使用此功能',
            showCancel: false,
            success: () => {
              wx.navigateTo({
                url: '/pages/bind-account/bind-account'
              });
            }
          });
          return;
        }
      }
      
      originalSwitchTab.call(wx, options);
    };
    
    // 重写wx.redirectTo
    wx.redirectTo = (options) => {
      console.log('重定向到:', options.url);
      
      const pagePath = options.url.split('?')[0];
      
      if (protectedPages.includes(pagePath)) {
        if (!authManager.isLoggedIn()) {
          console.log('未登录，跳转到设置页面');
          options.url = '/pages/settings/settings';
        } else {
          // 检查绑定状态
          const userInfo = authManager.getUserInfo();
          if (userInfo && !userInfo.isBound) {
            console.log('未绑定企微客服，跳转到绑定页面');
            options.url = '/pages/bind-account/bind-account';
          }
        }
      }
      
      originalRedirectTo.call(wx, options);
    };
  },

  /**
   * 检查页面访问权限
   */
  checkPageAccess(pagePath) {
    const protectedPages = [
      'pages/contact-list/contact-list',
      'pages/intent-manager/intent-manager',
      'pages/contact-detail/contact-detail', 
      'pages/contact-form/contact-form',
      'pages/matches/matches'
    ];
    
    if (protectedPages.includes(pagePath)) {
      if (!authManager.isLoggedIn()) {
        return false;
      }
      
      // 检查绑定状态
      const userInfo = authManager.getUserInfo();
      if (userInfo && !userInfo.isBound) {
        return false;
      }
      
      return true;
    }
    
    return true;
  },

  /**
   * 检查是否需要显示启动动画
   */
  checkSplashScreen() {
    try {
      // 检查是否是第一次启动或需要显示启动动画
      const lastSplashTime = wx.getStorageSync('last_splash_time') || 0;
      const currentTime = Date.now();
      
      // 间隔超过24小时或从未显示过，则显示启动动画
      const shouldShowSplash = (currentTime - lastSplashTime) > 24 * 60 * 60 * 1000;
      
      if (shouldShowSplash) {
        console.log('需要显示启动动画');
        wx.setStorageSync('last_splash_time', currentTime);
        
        // 延迟一点时间显示，避免与其他初始化冲突
        setTimeout(() => {
          wx.reLaunch({
            url: '/pages/splash/splash'
          });
        }, 100);
      }
    } catch (error) {
      console.error('检查启动动画失败:', error);
    }
  }
});
