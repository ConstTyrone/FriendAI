import { STORAGE_KEYS } from '../../utils/constants';
import { formatDate } from '../../utils/format-utils';
import { isValidSearchQuery } from '../../utils/validator';
import { getStorageSync, setStorageSync, defaultStorage } from '../../utils/storage-utils';
import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';
import apiClient from '../../utils/api-client';
import themeManager from '../../utils/theme-manager';
import debugHelper from '../../utils/debug-helper';
import contactImporter from '../../utils/contact-importer';

Page({
  data: {
    // 用户状态
    isLoggedIn: false,
    userInfo: null,
    userProfile: {},
    stats: {},
    
    // 登录表单
    loginLoading: false,
    
    // 应用设置
    settings: {
      autoSync: true,
      notifications: true,
      darkMode: false
    },
    
    // 对话框状态
    showLogoutDialog: false,
    showProfileEditor: false,
    
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
   * 显示可选绑定对话框
   */
  showOptionalBindingDialog(wechatUserId) {
    wx.showModal({
      title: '选择使用模式',
      content: '您可以绑定企业微信客服获得消息自动分析功能，也可以直接使用小程序手动管理联系人。',
      confirmText: '绑定客服',
      cancelText: '直接使用',
      success: (res) => {
        if (res.confirm) {
          // 用户选择绑定
          this.createBindingSessionAndNavigate(wechatUserId);
        } else {
          // 用户选择跳过绑定，直接使用小程序功能
          console.log('用户选择直接使用小程序，跳过绑定');
          this.refreshUserStatus();
          
          // 显示提示信息
          wx.showToast({
            title: '欢迎使用！',
            icon: 'success',
            duration: 2000
          });
        }
      }
    });
  },

  /**
   * 创建绑定会话并跳转到绑定页面
   */
  async createBindingSessionAndNavigate(wechatUserId) {
    try {
      console.log('开始创建绑定会话，openid:', wechatUserId);
      
      const result = await apiClient.createBindingSession({
        openid: wechatUserId
      });
      
      console.log('绑定会话创建结果:', result);
      
      if (result.success && result.token) {
        // 创建成功，跳转到绑定页面
        const bindUrl = `/pages/bind-account/bind-account?token=${result.token}&openid=${wechatUserId}&verifyCode=${result.verify_code || ''}`;
        
        wx.showModal({
          title: '绑定企业微信客服',
          content: '绑定后可以接收微信消息并自动分析联系人信息',
          showCancel: true,
          cancelText: '取消',
          confirmText: '去绑定',
          success: (res) => {
            if (res.confirm) {
              console.log('跳转到绑定页面:', bindUrl);
              wx.navigateTo({
                url: bindUrl
              });
            } else {
              // 用户取消绑定，直接使用小程序
              this.refreshUserStatus();
            }
          }
        });
      } else {
        // 创建失败，显示错误信息
        wx.showModal({
          title: '绑定会话创建失败',
          content: result.detail || '无法创建绑定会话，请稍后重试',
          showCancel: true,
          cancelText: '直接使用',
          confirmText: '重试',
          success: (res) => {
            if (!res.confirm) {
              // 用户选择直接使用
              this.refreshUserStatus();
            }
          }
        });
      }
    } catch (error) {
      console.error('创建绑定会话失败:', error);
      wx.showModal({
        title: '网络错误',
        content: '创建绑定会话失败，您仍可以直接使用小程序功能',
        showCancel: true,
        cancelText: '直接使用',
        confirmText: '重试',
        success: (res) => {
          if (!res.confirm) {
            // 用户选择直接使用
            this.refreshUserStatus();
          }
        }
      });
    }
  },

  /**
   * 刷新用户状态
   */
  async refreshUserStatus() {
    try {
      const isLoggedIn = authManager.isLoggedIn();
      const userInfo = authManager.getCurrentUser();
      
      // 获取用户个人资料
      let userProfile = {};
      if (isLoggedIn) {
        userProfile = authManager.getUserProfile() || {};
        // 确保有头像颜色
        if (!userProfile.avatarColor) {
          userProfile.avatarColor = authManager.getAvatarColor();
        }
      }
      
      this.setData({
        isLoggedIn,
        userInfo,
        userProfile
      });
      
      // 如果已登录，获取统计信息
      if (isLoggedIn) {
        await this.loadUserStats();
      }
      
      console.log('用户状态刷新完成:', { isLoggedIn, userInfo, userProfile });
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
   * 手动绑定微信客服
   */
  onBindWechatService() {
    const userInfo = authManager.getCurrentUser();
    if (userInfo && userInfo.wechatUserId) {
      this.createBindingSessionAndNavigate(userInfo.wechatUserId);
    } else {
      wx.showToast({
        title: '用户信息异常',
        icon: 'error'
      });
    }
  },

  /**
   * 管理微信客服绑定
   */
  onManageWechatBinding() {
    const userInfo = authManager.getCurrentUser();
    if (!userInfo || !userInfo.wechatUserId) {
      wx.showToast({
        title: '用户信息异常',
        icon: 'error'
      });
      return;
    }

    wx.showModal({
      title: '解除微信客服绑定',
      content: '解除绑定后，您将无法接收微信消息分析服务，但仍可使用小程序功能。如需重新绑定，请在解除后使用"绑定微信客服"功能。',
      confirmText: '解除绑定',
      cancelText: '取消',
      confirmColor: '#ff4757',
      success: (res) => {
        if (res.confirm) {
          // 解除绑定
          this.performUnbind();
        }
      }
    });
  },


  /**
   * 执行解绑操作
   */
  async performUnbind() {
    try {
      wx.showLoading({
        title: '解除绑定中...',
        mask: true
      });

      const userInfo = authManager.getCurrentUser();
      
      // 调用解绑API
      const result = await apiClient.unbindAccount(userInfo.wechatUserId);

      wx.hideLoading();

      if (result.success) {
        // 更新用户信息
        const updatedUserInfo = {
          ...userInfo,
          isBound: false,
          external_userid: null
        };
        
        // 更新认证管理器中的用户信息
        authManager.updateUserInfo(updatedUserInfo);
        
        // 刷新页面状态
        await this.refreshUserStatus();

        wx.showToast({
          title: '解绑成功',
          icon: 'success',
          duration: 2000
        });
      } else {
        throw new Error(result.detail || '解绑失败');
      }
    } catch (error) {
      wx.hideLoading();
      console.error('解绑失败:', error);
      
      wx.showModal({
        title: '解绑失败',
        content: error.message || '网络错误，请稍后重试',
        showCancel: false,
        confirmText: '知道了'
      });
    }
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
          
          // 检查绑定状态，提供可选绑定
          if (data && data.isBound === false) {
            console.log('用户未绑定微信客服，提供可选绑定');
            this.showOptionalBindingDialog(data.wechatUserId);
          } else {
            console.log('用户已绑定或绑定状态未知，继续正常流程');
            this.refreshUserStatus();
          }
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
   * 测试批量导入功能
   */
  async onTestBatchImport() {
    try {
      wx.showLoading({
        title: '🧪 运行导入测试...',
        mask: true
      });

      console.log('🧪 开始运行联系人导入测试...');
      
      // 简化的测试逻辑，不使用动态导入
      const testContacts = [
        { name: '张三(测试)', phone: '13800138001' },
        { name: '李四(测试)', phone: '13800138002' },
        { name: '王五(测试)', phone: '13800138003' }
      ];
      
      // 测试数据验证
      console.log('📋 测试数据验证...');
      let validationPassed = true;
      
      for (const contact of testContacts) {
        const isValid = contact.name && contact.name.trim() && contact.phone && contact.phone.trim();
        if (!isValid) {
          validationPassed = false;
          console.error('❌ 数据验证失败:', contact);
        } else {
          console.log('✅ 数据验证通过:', contact);
        }
      }
      
      // 测试导入模块状态
      console.log('🔍 检查导入模块状态...');
      const importerStatus = {
        contactImporter: !!contactImporter,
        isCurrentlyImporting: typeof contactImporter?.isCurrentlyImporting,
        importFromPhoneBook: typeof contactImporter?.importFromPhoneBook,
        quickBatchImportFromPhoneBook: typeof contactImporter?.quickBatchImportFromPhoneBook
      };
      
      console.log('📊 导入模块状态:', importerStatus);
      
      wx.hideLoading();
      
      const statusText = validationPassed ? '✅ 所有测试通过' : '⚠️ 部分测试未通过';
      
      wx.showModal({
        title: statusText,
        content: `批量导入功能测试已完成！\n\n数据验证: ${validationPassed ? '通过' : '失败'}\n导入模块: ${importerStatus.contactImporter ? '可用' : '不可用'}\n\n请查看控制台获取详细测试结果。`,
        showCancel: false,
        confirmText: '查看控制台'
      });
      
    } catch (error) {
      wx.hideLoading();
      console.error('测试失败:', error);
      
      wx.showModal({
        title: '❌ 测试失败',
        content: `测试过程中出现错误：\n\n${error.message}\n\n请检查控制台获取详细信息。`,
        showCancel: false,
        confirmText: '知道了',
        confirmColor: '#ff4757'
      });
    }
  },

  /**
   * 开发者选项 - 重置批量导入配置
   */
  onResetBatchImportConfig() {
    wx.showModal({
      title: '🔧 重置批量导入配置',
      content: '将重置以下配置到默认值：\n\n• 最大重试次数: 3\n• 批处理大小: 5\n• 最大选择数量: 20\n\n确定重置吗？',
      confirmText: '重置',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          // 重置配置
          const contactImporter = require('../../utils/contact-importer').default;
          contactImporter.maxRetries = 3;
          contactImporter.batchSize = 5;
          contactImporter.maxSelectionsPerSession = 20;
          
          wx.showToast({
            title: '✅ 配置已重置',
            icon: 'none',
            duration: 2000
          });
        }
      }
    });
  },

  /**
   * 系统诊断
   */
  async onSystemDiagnosis() {
    try {
      wx.showLoading({
        title: '🏥 正在诊断...',
        mask: true
      });

      console.log('🏥 [Settings] 开始系统诊断');
      
      // 运行完整诊断
      const results = await debugHelper.runFullDiagnosis();
      
      wx.hideLoading();
      
      // 显示诊断结果
      debugHelper.showDiagnosisResults(results);
      
    } catch (error) {
      wx.hideLoading();
      console.error('❌ [Settings] 系统诊断失败:', error);
      
      wx.showModal({
        title: '❌ 诊断失败',
        content: `系统诊断过程中出现错误：\n\n${error.message}\n\n请查看控制台获取详细信息。`,
        showCancel: false,
        confirmText: '知道了',
        confirmColor: '#ff4757'
      });
    }
  },

  /**
   * 权限管理
   */
  async onPermissionManager() {
    try {
      wx.showLoading({
        title: '🔐 检查权限...',
        mask: true
      });

      // 检查当前权限状态
      const permissionStatus = await debugHelper.testContactPermission();
      
      wx.hideLoading();
      
      if (permissionStatus.status === 'granted') {
        wx.showModal({
          title: '✅ 权限状态',
          content: '通讯录权限已授权，可以正常使用导入功能。',
          showCancel: false,
          confirmText: '知道了'
        });
      } else if (permissionStatus.status === 'denied') {
        wx.showModal({
          title: '❌ 权限被拒绝',
          content: '通讯录权限被拒绝，无法使用导入功能。\n\n点击"去设置"可以重新授权。',
          confirmText: '去设置',
          cancelText: '取消',
          success: (res) => {
            if (res.confirm) {
              wx.openSetting();
            }
          }
        });
      } else {
        wx.showModal({
          title: '📋 权限未请求',
          content: '尚未请求通讯录权限。\n\n点击"立即授权"申请权限。',
          confirmText: '立即授权',
          cancelText: '取消',
          success: async (res) => {
            if (res.confirm) {
              const result = await debugHelper.requestContactPermission();
              console.log('权限申请结果:', result);
            }
          }
        });
      }
      
    } catch (error) {
      wx.hideLoading();
      console.error('❌ [Settings] 权限检查失败:', error);
      
      wx.showModal({
        title: '❌ 权限检查失败',
        content: `权限检查过程中出现错误：\n\n${error.message}`,
        showCancel: false,
        confirmText: '知道了'
      });
    }
  },

  /**
   * 编辑个人资料
   */
  onEditProfile() {
    console.log('打开个人资料编辑器');
    this.setData({
      showProfileEditor: true
    });
  },

  /**
   * 保存个人资料
   */
  async onProfileSave(e) {
    try {
      const { profileData } = e.detail;
      console.log('保存个人资料:', profileData);

      // 使用 authManager 更新个人资料
      authManager.updateUserProfile(profileData);

      // 刷新页面显示
      await this.refreshUserStatus();

      // 关闭编辑器
      this.setData({
        showProfileEditor: false
      });

      // 显示成功提示
      wx.showToast({
        title: '个人资料已保存',
        icon: 'success',
        duration: 2000
      });

    } catch (error) {
      console.error('保存个人资料失败:', error);
      
      wx.showModal({
        title: '保存失败',
        content: error.message || '保存个人资料时发生错误，请重试',
        showCancel: false,
        confirmText: '知道了'
      });
    }
  },

  /**
   * 取消编辑个人资料
   */
  onProfileCancel() {
    console.log('取消编辑个人资料');
    this.setData({
      showProfileEditor: false
    });
  }

});