import { STORAGE_KEYS } from '../../utils/constants';
import { formatDate } from '../../utils/format-utils';
import { isValidSearchQuery } from '../../utils/validator';
import { getStorageSync, setStorageSync, defaultStorage } from '../../utils/storage-utils';
import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';
import themeManager from '../../utils/theme-manager';

Page({
  data: {
    // 用户状态
    isLoggedIn: false,
    userInfo: null,
    stats: {},
    
    // 登录表单
    wechatIdInput: '',  // 微信ID输入
    loginUserId: '',
    loginLoading: false,
    testLoginLoading: false,
    
    // 应用设置
    settings: {
      autoSync: true,
      notifications: true,
      darkMode: false
    },
    
    // 主题色设置
    showThemeColorModal: false,
    availableColors: [],
    selectedThemeColor: 'default', // 当前选择的主题色
    
    // 对话框状态
    showLogoutDialog: false,
    
    // 应用信息
    appVersion: '1.0.0'
  },

  onLoad(options) {
    console.log('设置页面加载', options);
    
    // 应用主题
    themeManager.applyToPage(this);
    
    // 初始化页面数据
    this.initPageData();
    
    // 添加认证监听器
    this.addAuthListener();
  },

  onShow() {
    console.log('设置页面显示');
    
    // 刷新用户状态
    this.refreshUserStatus();
    
    // 设置页面标题
    wx.setNavigationBarTitle({
      title: '设置'
    });
  },

  onReady() {
    console.log('设置页面准备就绪');
  },

  onHide() {
    console.log('设置页面隐藏');
  },

  onUnload() {
    console.log('设置页面卸载');
    
    // 移除监听器
    this.removeAuthListener();
  },

  /**
   * 初始化页面数据
   */
  initPageData() {
    try {
      // 获取应用版本
      const app = getApp();
      this.setData({
        appVersion: app.globalData.version || '1.0.0'
      });
      
      // 加载设置
      this.loadSettings();
      
      // 初始化主题色数据
      this.initThemeColors();
      
      console.log('页面数据初始化完成');
    } catch (error) {
      console.error('初始化页面数据失败:', error);
    }
  },

  /**
   * 加载应用设置
   */
  loadSettings() {
    try {
      const savedSettings = getStorageSync(STORAGE_KEYS.APP_SETTINGS, {});
      const currentTheme = themeManager.getTheme();
      
      this.setData({
        settings: {
          autoSync: savedSettings.autoSync !== false, // 默认true
          notifications: savedSettings.notifications !== false, // 默认true
          darkMode: currentTheme === 'dark' // 使用主题管理器的当前主题
        }
      });
      
      console.log('设置加载完成:', this.data.settings);
    } catch (error) {
      console.error('加载设置失败:', error);
    }
  },

  /**
   * 保存应用设置
   */
  saveSettings() {
    try {
      setStorageSync(STORAGE_KEYS.APP_SETTINGS, this.data.settings);
      console.log('设置保存完成:', this.data.settings);
    } catch (error) {
      console.error('保存设置失败:', error);
    }
  },

  /**
   * 刷新用户状态
   */
  async refreshUserStatus() {
    try {
      const isLoggedIn = authManager.isLoggedIn();
      const userInfo = authManager.getCurrentUser();
      
      this.setData({
        isLoggedIn,
        userInfo
      });
      
      // 如果已登录，获取统计信息
      if (isLoggedIn) {
        await this.loadUserStats();
      }
      
      console.log('用户状态刷新完成:', { isLoggedIn, userInfo });
    } catch (error) {
      console.error('刷新用户状态失败:', error);
    }
  },

  /**
   * 加载用户统计信息
   */
  async loadUserStats() {
    try {
      const stats = await dataManager.getStats();
      this.setData({ stats });
      
      console.log('用户统计加载完成:', stats);
    } catch (error) {
      console.error('加载用户统计失败:', error);
    }
  },

  /**
   * 用户ID输入变化
   */
  onUserIdChange(event) {
    this.setData({
      loginUserId: event.detail.value
    });
  },

  /**
   * 微信ID输入变化
   */
  onWechatIdChange(event) {
    this.setData({
      wechatIdInput: event.detail.value
    });
  },

  /**
   * 快速登录
   */
  onQuickLogin(event) {
    const userId = event.currentTarget.dataset.userId;
    this.setData({ loginUserId: userId });
    this.performTestLogin(userId);
  },

  /**
   * 快速选择微信ID
   */
  onQuickWechatId(event) {
    const wechatId = event.currentTarget.dataset.wechatId;
    this.setData({ wechatIdInput: wechatId });
  },

  /**
   * 真正的微信登录（使用wx.login）
   */
  async onRealWechatLogin() {
    console.log('===== 开始真正的微信登录流程 =====');
    if (this.data.loginLoading) return;
    
    try {
      this.setData({ loginLoading: true });
      
      wx.showLoading({
        title: '微信登录中...',
        mask: true
      });
      
      // 调用认证管理器的微信登录（不传参数，使用wx.login）
      console.log('调用 authManager.wechatLogin() - 真正的微信登录');
      const result = await authManager.wechatLogin();  // 不传参数
      console.log('登录结果:', result);
      
      wx.hideLoading();
      
      if (result.success) {
        // 登录成功
        this.setData({ loginLoading: false });
        
        // 刷新用户状态
        await this.refreshUserStatus();
        
        wx.showToast({
          title: '登录成功',
          icon: 'success',
          duration: 1500
        });
        
        console.log('微信登录成功，OpenID:', result.wechat_user_id);
        
        // 登录成功后跳转到联系人列表
        setTimeout(() => {
          wx.switchTab({
            url: '/pages/contact-list/contact-list'
          });
        }, 1500);
      } else {
        throw new Error(result.error || '登录失败');
      }
    } catch (error) {
      wx.hideLoading();
      
      this.setData({ loginLoading: false });
      
      console.error('微信登录失败:', error);
      
      wx.showModal({
        title: '登录失败',
        content: error.message || '微信登录失败，请重试',
        showCancel: false
      });
    }
  },

  /**
   * 微信ID登录
   */
  async onWechatLogin() {
    console.log('===== 开始微信ID登录流程 =====');
    if (this.data.loginLoading) return;
    
    const wechatId = this.data.wechatIdInput.trim();
    if (!wechatId) {
      wx.showToast({
        title: '请输入微信ID',
        icon: 'none'
      });
      return;
    }
    
    try {
      this.setData({ loginLoading: true });
      
      wx.showLoading({
        title: '登录中...',
        mask: true
      });
      
      // 使用输入的微信ID登录
      console.log('使用微信ID登录:', wechatId);
      const result = await authManager.wechatLogin(wechatId);
      console.log('登录结果:', result);
      
      wx.hideLoading();
      
      if (result.success) {
        // 登录成功
        this.setData({ 
          loginLoading: false,
          wechatIdInput: ''  // 清空输入
        });
        
        // 刷新用户状态
        await this.refreshUserStatus();
        
        wx.showToast({
          title: '登录成功',
          icon: 'success',
          duration: 1500
        });
        
        console.log('微信用户登录成功:', result);
        
        // 登录成功后跳转到联系人列表
        setTimeout(() => {
          wx.switchTab({
            url: '/pages/contact-list/contact-list'
          });
        }, 1500);
      } else {
        throw new Error(result.error || '登录失败');
      }
    } catch (error) {
      wx.hideLoading();
      
      this.setData({ loginLoading: false });
      
      console.error('登录失败 - 详细错误:', error);
      console.error('错误堆栈:', error.stack);
      
      wx.showModal({
        title: '登录失败',
        content: error.message || '登录失败，请检查微信ID是否正确',
        showCancel: false
      });
    }
  },

  /**
   * 测试账户登录按钮点击
   */
  onLogin() {
    const userId = this.data.loginUserId.trim();
    
    if (!userId) {
      wx.showToast({
        title: '请输入用户ID',
        icon: 'none'
      });
      return;
    }
    
    this.performTestLogin(userId);
  },

  /**
   * Mock用户登录
   */
  async onMockLogin() {
    try {
      this.setData({ loginLoading: true });
      
      wx.showLoading({
        title: 'Mock登录中...',
        mask: true
      });
      
      const result = await authManager.mockLogin();
      
      wx.hideLoading();
      
      if (result.success) {
        this.setData({ loginLoading: false });
        
        // 刷新用户状态
        await this.refreshUserStatus();
        
        wx.showToast({
          title: 'Mock登录成功',
          icon: 'success',
          duration: 1500
        });
        
        console.log('Mock用户登录成功:', result);
        
        // 登录成功后跳转到联系人列表
        setTimeout(() => {
          wx.switchTab({
            url: '/pages/contact-list/contact-list'
          });
        }, 1500);
      } else {
        throw new Error(result.error || 'Mock登录失败');
      }
    } catch (error) {
      wx.hideLoading();
      
      this.setData({ loginLoading: false });
      
      console.error('Mock登录失败:', error);
      
      wx.showModal({
        title: '登录失败',
        content: error.message || 'Mock登录失败，请重试',
        showCancel: false
      });
    }
  },

  /**
   * 执行测试账户登录
   */
  async performTestLogin(userId) {
    if (this.data.testLoginLoading) return;
    
    try {
      this.setData({ testLoginLoading: true });
      
      wx.showLoading({
        title: '登录中...',
        mask: true
      });
      
      // 调用认证管理器快速登录
      const result = await authManager.quickLogin(userId);
      
      wx.hideLoading();
      
      if (result.success) {
        // 登录成功
        this.setData({
          testLoginLoading: false,
          loginUserId: ''
        });
        
        // 刷新用户状态
        await this.refreshUserStatus();
        
        wx.showToast({
          title: '登录成功',
          icon: 'success',
          duration: 1500
        });
        
        console.log('测试用户登录成功:', result);
        
        // 登录成功后跳转到联系人列表
        setTimeout(() => {
          wx.switchTab({
            url: '/pages/contact-list/contact-list'
          });
        }, 1500);
      } else {
        throw new Error(result.detail || '登录失败');
      }
    } catch (error) {
      wx.hideLoading();
      
      this.setData({ testLoginLoading: false });
      
      console.error('测试登录失败:', error);
      
      wx.showModal({
        title: '登录失败',
        content: error.message || '请检查网络连接或用户ID',
        showCancel: false
      });
    }
  },

  /**
   * 执行登录（兼容旧版本）
   */
  async performLogin(userId) {
    return this.performTestLogin(userId);
  },

  /**
   * 刷新用户信息
   */
  async onRefreshUserInfo() {
    try {
      wx.showLoading({
        title: '刷新中...'
      });
      
      // 刷新用户信息和统计数据
      await authManager.refreshUserInfo();
      await this.loadUserStats();
      
      // 刷新页面状态
      await this.refreshUserStatus();
      
      wx.hideLoading();
      
      wx.showToast({
        title: '刷新完成',
        icon: 'success'
      });
      
    } catch (error) {
      wx.hideLoading();
      
      console.error('刷新用户信息失败:', error);
      
      wx.showToast({
        title: '刷新失败',
        icon: 'error'
      });
    }
  },

  /**
   * 清除缓存
   */
  onClearCache() {
    wx.showModal({
      title: '确认清除',
      content: '清除缓存后，需要重新从服务器加载数据。确定要清除吗？',
      success: (res) => {
        if (res.confirm) {
          this.performClearCache();
        }
      }
    });
  },

  /**
   * 执行清除缓存
   */
  async performClearCache() {
    try {
      wx.showLoading({
        title: '清除中...'
      });
      
      // 清除数据管理器缓存
      dataManager.clearCache();
      
      // 清除其他缓存（保留用户认证信息）
      const keysToKeep = [
        STORAGE_KEYS.AUTH_TOKEN,
        STORAGE_KEYS.WECHAT_USER_ID,
        STORAGE_KEYS.USER_INFO,
        STORAGE_KEYS.APP_SETTINGS
      ];
      
      // 这里可以添加更精细的缓存清理逻辑
      
      wx.hideLoading();
      
      wx.showToast({
        title: '缓存已清除',
        icon: 'success'
      });
      
      console.log('缓存清除完成');
    } catch (error) {
      wx.hideLoading();
      
      console.error('清除缓存失败:', error);
      
      wx.showToast({
        title: '清除失败',
        icon: 'error'
      });
    }
  },

  /**
   * 退出登录
   */
  onLogout() {
    this.setData({ showLogoutDialog: true });
  },

  /**
   * 确认退出登录
   */
  onConfirmLogout() {
    this.setData({ showLogoutDialog: false });
    this.performLogout();
  },

  /**
   * 取消退出登录
   */
  onCancelLogout() {
    this.setData({ showLogoutDialog: false });
  },

  /**
   * 执行退出登录
   */
  async performLogout() {
    try {
      wx.showLoading({
        title: '退出中...'
      });
      
      // 调用认证管理器退出
      const success = authManager.logout();
      
      if (success) {
        // 清除数据管理器缓存
        dataManager.clearCache();
        
        // 更新页面状态
        this.setData({
          isLoggedIn: false,
          userInfo: null,
          stats: {}
        });
        
        wx.hideLoading();
        
        wx.showToast({
          title: '已退出登录',
          icon: 'success'
        });
        
        console.log('用户退出登录');
      } else {
        throw new Error('退出登录失败');
      }
    } catch (error) {
      wx.hideLoading();
      
      console.error('退出登录失败:', error);
      
      wx.showToast({
        title: '退出失败',
        icon: 'error'
      });
    }
  },

  /**
   * 自动同步开关变化
   */
  onAutoSyncChange(event) {
    const autoSync = event.detail.value;
    
    this.setData({
      'settings.autoSync': autoSync
    });
    
    this.saveSettings();
    
    console.log('自动同步设置:', autoSync);
  },

  /**
   * 消息通知开关变化
   */
  onNotificationsChange(event) {
    const notifications = event.detail.value;
    
    this.setData({
      'settings.notifications': notifications
    });
    
    this.saveSettings();
    
    console.log('消息通知设置:', notifications);
  },

  /**
   * 深色模式开关变化
   */
  onDarkModeChange(event) {
    const darkMode = event.detail.value;
    
    // 使用主题管理器切换主题
    const newTheme = darkMode ? 'dark' : 'light';
    themeManager.setTheme(newTheme);
    
    this.setData({
      'settings.darkMode': darkMode
    });
    
    this.saveSettings();
    
    console.log(`切换到${darkMode ? '深色' : '浅色'}模式`);
    
    // 显示提示
    wx.showToast({
      title: darkMode ? '已启用深色模式' : '已启用浅色模式',
      icon: 'success',
      duration: 1500
    });
  },

  /**
   * 查看存储信息
   */
  async onViewStorageInfo() {
    try {
      const storageInfo = await wx.getStorageInfo();
      const dataOverview = dataManager.getDataOverview();
      
      const message = `存储使用情况:
当前大小: ${(storageInfo.currentSize / 1024).toFixed(2)} KB
存储上限: ${(storageInfo.limitSize / 1024).toFixed(2)} KB
联系人数量: ${dataOverview.contactCount}
搜索历史: ${dataOverview.searchHistoryCount}`;
      
      wx.showModal({
        title: '存储信息',
        content: message,
        showCancel: false
      });
    } catch (error) {
      console.error('获取存储信息失败:', error);
      
      wx.showToast({
        title: '获取失败',
        icon: 'error'
      });
    }
  },

  /**
   * 查看API统计
   */
  onViewAPIStats() {
    // 这里可以显示API调用统计信息
    wx.showModal({
      title: 'API统计',
      content: '功能开发中，敬请期待...',
      showCancel: false
    });
  },

  /**
   * 查看版本信息
   */
  onViewVersion() {
    const app = getApp();
    const systemInfo = app.globalData.systemInfo;
    
    const message = `应用版本: ${this.data.appVersion}
微信版本: ${systemInfo?.version || 'Unknown'}
系统版本: ${systemInfo?.system || 'Unknown'}
设备型号: ${systemInfo?.model || 'Unknown'}`;
    
    wx.showModal({
      title: '版本信息',
      content: message,
      showCancel: false
    });
  },

  /**
   * 查看帮助
   */
  onViewHelp() {
    wx.showModal({
      title: '使用帮助',
      content: '1. 使用测试账户登录体验功能\n2. 在联系人页面查看和管理联系人\n3. 使用AI搜索快速找到目标联系人\n4. 支持多种搜索方式和智能建议',
      showCancel: false
    });
  },

  /**
   * 反馈建议
   */
  onViewFeedback() {
    wx.showModal({
      title: '反馈建议',
      content: '感谢您的使用！如有问题或建议，请通过以下方式联系我们：\n\n• 邮箱: feedback@example.com\n• 微信群: 开发者交流群',
      showCancel: false
    });
  },

  /**
   * 格式化登录时间
   */
  formatLoginTime(timestamp) {
    if (!timestamp) return '未知';
    
    return formatDate(new Date(timestamp), 'MM-DD HH:mm');
  },

  /**
   * 添加认证监听器
   */
  addAuthListener() {
    this.authListener = (eventType, data) => {
      switch (eventType) {
        case 'loginSuccess':
          console.log('监听到登录成功事件:', data);
          this.refreshUserStatus();
          break;
          
        case 'logout':
          console.log('监听到登出事件');
          this.setData({
            isLoggedIn: false,
            userInfo: null,
            stats: {}
          });
          break;
      }
    };
    
    authManager.addListener(this.authListener);
  },

  /**
   * 移除认证监听器
   */
  removeAuthListener() {
    if (this.authListener) {
      // authManager.removeListener(this.authListener);
      this.authListener = null;
    }
  },

  /**
   * 初始化主题色数据
   */
  initThemeColors() {
    try {
      const availableColors = themeManager.getAvailableAccentColors();
      const currentAccentColor = themeManager.getAccentColor();
      
      this.setData({
        availableColors: availableColors,
        selectedThemeColor: currentAccentColor
      });
      
      console.log('主题色数据初始化完成:', { availableColors: availableColors.length, current: currentAccentColor });
    } catch (error) {
      console.error('初始化主题色数据失败:', error);
    }
  },

  /**
   * 点击主题色选项
   */
  onThemeColorTap() {
    console.log('打开主题色选择弹窗');
    this.setData({
      showThemeColorModal: true,
      selectedThemeColor: themeManager.getAccentColor() // 重置为当前主题色
    });
  },

  /**
   * 关闭主题色选择弹窗
   */
  onCloseThemeColorModal() {
    console.log('关闭主题色选择弹窗');
    this.setData({
      showThemeColorModal: false,
      selectedThemeColor: themeManager.getAccentColor() // 重置为当前主题色
    });
  },

  /**
   * 选择主题色
   */
  onSelectThemeColor(e) {
    const colorKey = e.currentTarget.dataset.color;
    console.log('选择主题色:', colorKey);
    
    this.setData({
      selectedThemeColor: colorKey
    });
  },

  /**
   * 确认主题色选择
   */
  onConfirmThemeColor() {
    const { selectedThemeColor } = this.data;
    
    console.log('确认应用主题色:', selectedThemeColor);
    
    // 应用主题色
    const success = themeManager.setAccentColor(selectedThemeColor);
    
    if (success) {
      wx.showToast({
        title: '主题色已更新',
        icon: 'success',
        duration: 1500
      });
      
      // 关闭弹窗
      this.setData({
        showThemeColorModal: false
      });
    } else {
      wx.showToast({
        title: '设置失败',
        icon: 'error',
        duration: 2000
      });
    }
  },

  /**
   * 阻止事件冒泡
   */
  onStopPropagation() {
    // 阻止事件冒泡，用于模态框内容区域
  }
});