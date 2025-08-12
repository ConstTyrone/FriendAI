// pages/bind-account/bind-account.js
const app = getApp();
import authManager from '../../utils/auth-manager';
import apiClient from '../../utils/api-client';
import { STORAGE_KEYS, ERROR_MESSAGES, UI_CONFIG } from '../../utils/constants';

Page({
  data: {
    bindToken: '',
    openid: '',
    bindStatus: 'pending', // pending, checking, bound, failed
    errorMessage: '',
    checkCount: 0,
    maxCheckCount: 30, // 最多检查30次（60秒）
    
    // 企微客服配置
    corpId: '', // 将从配置中读取
    kfId: '', // 客服ID
    
    // UI状态
    loading: false,
    showRetry: false,
    
    // 验证码（6位数字）
    verifyCode: ''
  },

  bindingTimer: null,

  // 统一更新验证码到后端
  async updateVerifyCodeToBackend(verifyCode) {
    const { bindToken } = this.data;
    if (!bindToken || !verifyCode) {
      console.log('[BindAccount] Skip updating verify code, missing token or code');
      return;
    }
    
    try {
      console.log('[BindAccount] Updating verify code to backend:', verifyCode);
      const updateResult = await apiClient.updateBindingSession({
        token: bindToken,
        verify_code: verifyCode
      });
      
      if (updateResult.success) {
        console.log('[BindAccount] Successfully updated verify code to backend');
      } else {
        console.error('[BindAccount] Failed to update verify code:', updateResult.message);
      }
    } catch (error) {
      console.error('[BindAccount] Error updating verify code:', error);
    }
  },

  onLoad(options) {
    console.log('[BindAccount] onLoad with options:', options);
    
    // 如果URL中有验证码，使用它；否则保持为空
    const verifyCode = options.verifyCode || '';
    
    this.setData({
      bindToken: options.token || '',
      openid: options.openid || '',
      verifyCode: verifyCode,  // 使用后端提供的验证码
      corpId: UI_CONFIG.CORP_ID || '',
      kfId: UI_CONFIG.KF_ID || ''
    });
    
    if (verifyCode) {
      console.log('[BindAccount] Using backend verify code:', verifyCode);
    }

    // 如果没有token，说明是异常访问
    if (!options.token) {
      wx.showModal({
        title: '访问错误',
        content: '缺少必要的绑定参数，请重新登录',
        showCancel: false,
        success: () => {
          wx.switchTab({
            url: '/pages/settings/settings'
          });
        }
      });
      return;
    }
    
    // 自动跳转到企微客服
    if (options.autoOpen === 'true') {
      setTimeout(() => {
        this.autoOpenCustomerService();
      }, 500);
    }
  },

  onUnload() {
    // 清理定时器
    if (this.bindingTimer) {
      clearInterval(this.bindingTimer);
      this.bindingTimer = null;
    }
  },

  // 自动打开客服（页面加载时调用）
  autoOpenCustomerService() {
    console.log('[BindAccount] Auto opening customer service');
    
    const { kfId, bindToken } = this.data;
    
    if (!kfId) {
      console.error('[BindAccount] Missing kfId');
      return;
    }
    
    // 使用后端提供的验证码
    let verifyCode = this.data.verifyCode;
    if (!verifyCode) {
      console.error('[BindAccount] No verify code available! This should not happen.');
      wx.showModal({
        title: '错误',
        content: '验证码未生成，请重新登录',
        showCancel: false,
        success: () => {
          wx.switchTab({
            url: '/pages/settings/settings'
          });
        }
      });
      return;
    } else {
      console.log('[BindAccount] Using verify code:', verifyCode);
    }
    
    // 设置状态为检查中，显示验证码
    this.setData({
      bindStatus: 'checking',
      verifyCode: verifyCode,
      loading: false
    });
    
    // 更新验证码到后端
    this.updateVerifyCodeToBackend(verifyCode);
    
    // 启动后台状态检查
    this.startBindingCheck();
    
    // 构建企微客服URL
    const customerServiceUrl = `https://work.weixin.qq.com/kfid/${kfId}`;
    
    // 由于企微域名无法配置为业务域名，直接显示操作指引
    wx.showModal({
      title: '请完成绑定',
      content: `验证码：${verifyCode}\n\n请复制链接在浏览器中打开企微客服，并发送验证码`,
      confirmText: '复制链接',
      cancelText: '复制验证码',
      success: (res) => {
        if (res.confirm) {
          // 复制链接
          wx.setClipboardData({
            data: customerServiceUrl,
            success: () => {
              wx.showModal({
                title: '链接已复制',
                content: '请在手机浏览器中粘贴并打开链接，然后发送验证码完成绑定',
                showCancel: false,
                confirmText: '我知道了'
              });
            }
          });
        } else if (res.cancel) {
          // 复制验证码
          wx.setClipboardData({
            data: verifyCode,
            success: () => {
              wx.showToast({
                title: '验证码已复制',
                icon: 'none',
                duration: 2000
              });
            }
          });
        }
      }
    });
  },
  
  // 开始绑定流程（手动点击按钮）
  async startBinding() {
    console.log('[BindAccount] Starting binding process');
    
    const { kfId } = this.data;
    
    if (!kfId) {
      wx.showToast({
        title: '客服配置缺失',
        icon: 'none'
      });
      return;
    }
    
    // 使用后端提供的验证码
    let verifyCode = this.data.verifyCode;
    if (!verifyCode) {
      console.error('[BindAccount] No verify code available! This should not happen.');
      wx.showModal({
        title: '错误',
        content: '验证码未生成，请重新登录',
        showCancel: false,
        success: () => {
          wx.switchTab({
            url: '/pages/settings/settings'
          });
        }
      });
      return;
    } else {
      console.log('[BindAccount] Using verify code:', verifyCode);
    }
    
    // 立即显示验证码并开始检查
    this.setData({
      bindStatus: 'checking',
      verifyCode: verifyCode,
      loading: false,
      errorMessage: '',
      showRetry: false
    });
    
    // 更新验证码到后端
    this.updateVerifyCodeToBackend(verifyCode);
    
    // 启动状态检查
    this.startBindingCheck();
    
    // 构建企微客服URL
    const customerServiceUrl = `https://work.weixin.qq.com/kfid/${kfId}`;
    
    // 显示操作选项
    wx.showActionSheet({
      itemList: ['复制企微链接', '复制验证码', '查看操作说明'],
      success: (res) => {
        if (res.tapIndex === 0) {
          // 复制链接
          wx.setClipboardData({
            data: customerServiceUrl,
            success: () => {
              wx.showToast({
                title: '链接已复制，请在浏览器打开',
                icon: 'none',
                duration: 3000
              });
            }
          });
        } else if (res.tapIndex === 1) {
          // 复制验证码
          wx.setClipboardData({
            data: verifyCode,
            success: () => {
              wx.showToast({
                title: '验证码已复制',
                icon: 'none',
                duration: 2000
              });
            }
          });
        } else if (res.tapIndex === 2) {
          // 显示操作说明
          wx.showModal({
            title: '操作说明',
            content: `1. 复制企微链接\n2. 在浏览器中打开\n3. 发送验证码：${verifyCode}\n4. 返回小程序查看状态`,
            showCancel: false,
            confirmText: '我知道了'
          });
        }
      }
    });
  },
  
  // 复制客服URL
  copyCustomerServiceUrl() {
    const { kfId } = this.data;
    const customerServiceUrl = `https://work.weixin.qq.com/kfid/${kfId}`;
    
    wx.setClipboardData({
      data: customerServiceUrl,
      success: () => {
        wx.showToast({
          title: '链接已复制，请在浏览器打开',
          icon: 'none',
          duration: 3000
        });
      }
    });
  },
  
  // 复制客服链接
  copyCustomerServiceLink() {
    const { kfId, bindToken } = this.data;
    
    if (!kfId) {
      wx.showToast({
        title: '客服配置信息缺失',
        icon: 'none'
      });
      return;
    }
    
    // 构建企微客服URL
    let customerServiceUrl = `https://work.weixin.qq.com/kfid/${kfId}`;
    if (bindToken) {
      customerServiceUrl += `?state=${bindToken}`;
    }
    
    wx.setClipboardData({
      data: customerServiceUrl,
      success: () => {
        wx.showModal({
          title: '链接已复制',
          content: '请在手机浏览器中粘贴链接并打开，完成身份确认后返回小程序查看绑定状态',
          showCancel: false,
          success: () => {
            // 启动状态检查
            this.startBindingCheck();
            
            // 设置loading状态为false，让用户能看到状态
            this.setData({
              loading: false
            });
          }
        });
      }
    });
  },

  // 跳转到企微客服
  async navigateToCustomerService() {
    const { kfId, bindToken, openid } = this.data;
    
    if (!kfId) {
      throw new Error('客服配置信息缺失，请联系管理员');
    }

    // 使用后端提供的验证码
    let verifyCode = this.data.verifyCode;
    if (!verifyCode) {
      console.error('[BindAccount] No verify code in navigateToCustomerService!');
      wx.showModal({
        title: '错误',
        content: '验证码未生成，请重新登录',
        showCancel: false,
        success: () => {
          wx.switchTab({
            url: '/pages/settings/settings'
          });
        }
      });
      return;
    } else {
      console.log('[BindAccount] Using verify code:', verifyCode);
    }
    
    // 更新验证码到后端
    await this.updateVerifyCodeToBackend(verifyCode);
    
    // 构建企微客服链接
    const customerServiceUrl = `https://work.weixin.qq.com/kfid/${kfId}`;
    
    console.log('[BindAccount] Customer service URL:', customerServiceUrl);
    console.log('[BindAccount] Verify code:', verifyCode || bindToken);
    console.log('[BindAccount] OpenID:', openid);

    // 更新验证码显示
    this.setData({
      verifyCode: verifyCode || bindToken.substring(0, 6)
    });

    // 显示操作指引
    wx.showModal({
      title: '绑定步骤',
      content: `1. 记住验证码：${verifyCode || bindToken.substring(0, 6)}\n2. 在企微客服中发送此验证码\n3. 返回小程序查看绑定状态`,
      confirmText: '复制验证码并打开',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          // 复制验证码
          wx.setClipboardData({
            data: verifyCode || bindToken.substring(0, 6),
            success: () => {
              // 启动状态检查（在后台运行）
              this.startBindingCheck();
              
              // 设置状态为检查中
              this.setData({
                bindStatus: 'checking',
                loading: false
              });
              
              // 延迟后打开企微（让用户看到状态页面）
              setTimeout(() => {
                // 使用web-view打开企微客服
                wx.navigateTo({
                  url: `/pages/webview/webview?url=${encodeURIComponent(customerServiceUrl)}&title=${encodeURIComponent('企业微信客服')}`,
                  fail: (error) => {
                    console.error('[BindAccount] Failed to navigate to webview:', error);
                    // 如果无法打开，提示用户手动打开
                    wx.showModal({
                      title: '请手动打开',
                      content: '验证码已复制，请在浏览器中打开企微客服链接',
                      showCancel: false
                    });
                  }
                });
              }, 500);
            }
          });
        } else {
          this.setData({
            loading: false
          });
        }
      }
    });
  },

  // 开始轮询检查绑定状态
  startBindingCheck() {
    console.log('[BindAccount] Starting binding status check');
    
    this.setData({
      bindStatus: 'checking',
      checkCount: 0
    });

    // 立即检查一次
    this.checkBindingStatus();

    // 设置定时器，每2秒检查一次
    this.bindingTimer = setInterval(() => {
      this.checkBindingStatus();
    }, 2000);
  },

  // 检查绑定状态
  async checkBindingStatus() {
    const { bindToken, checkCount, maxCheckCount } = this.data;
    
    // 超过最大检查次数
    if (checkCount >= maxCheckCount) {
      this.onBindingTimeout();
      return;
    }

    try {
      console.log(`[BindAccount] Checking binding status (${checkCount + 1}/${maxCheckCount})`);
      
      const result = await apiClient.checkBindingStatus(bindToken);
      
      this.setData({
        checkCount: checkCount + 1
      });

      if (result.status === 'bound') {
        // 绑定成功
        this.onBindingSuccess(result);
      } else if (result.status === 'expired') {
        // Token过期
        this.onBindingExpired();
      } else if (result.status === 'failed') {
        // 绑定失败
        this.onBindingFailed(result.message);
      }
      // pending状态继续等待
    } catch (error) {
      console.error('[BindAccount] Check status error:', error);
      // 检查失败不立即停止，可能是网络问题
      this.setData({
        checkCount: checkCount + 1
      });
    }
  },

  // 绑定成功
  async onBindingSuccess(result) {
    console.log('[BindAccount] Binding successful:', result);
    
    // 停止检查
    if (this.bindingTimer) {
      clearInterval(this.bindingTimer);
      this.bindingTimer = null;
    }

    this.setData({
      bindStatus: 'bound',
      loading: false
    });

    wx.showToast({
      title: '绑定成功',
      icon: 'success',
      duration: 2000
    });

    // 更新本地存储的绑定状态
    try {
      const userInfo = wx.getStorageSync(STORAGE_KEYS.USER_INFO) || {};
      userInfo.isBound = true;
      userInfo.externalUserId = result.externalUserId;
      wx.setStorageSync(STORAGE_KEYS.USER_INFO, userInfo);
    } catch (error) {
      console.error('[BindAccount] Failed to update storage:', error);
    }

    // 延迟后跳转到设置页面
    setTimeout(() => {
      console.log('[BindAccount] Redirecting to settings page after successful binding');
      wx.showModal({
        title: '绑定成功',
        content: '企业微信账号绑定成功！现在可以开始同步联系人信息了。',
        showCancel: false,
        confirmText: '返回设置',
        success: () => {
          wx.redirectTo({
            url: '/pages/settings/settings',
            success: () => {
              console.log('[BindAccount] Successfully redirected to settings');
            }
          });
        }
      });
    }, 1500);
  },

  // 绑定超时
  onBindingTimeout() {
    console.log('[BindAccount] Binding timeout');
    
    if (this.bindingTimer) {
      clearInterval(this.bindingTimer);
      this.bindingTimer = null;
    }

    this.setData({
      bindStatus: 'failed',
      loading: false,
      errorMessage: '绑定超时，请重试',
      showRetry: true
    });

    wx.showToast({
      title: '绑定超时',
      icon: 'none',
      duration: 2000
    });
  },

  // Token过期
  onBindingExpired() {
    console.log('[BindAccount] Binding token expired');
    
    if (this.bindingTimer) {
      clearInterval(this.bindingTimer);
      this.bindingTimer = null;
    }

    this.setData({
      bindStatus: 'failed',
      loading: false,
      errorMessage: '绑定会话已过期，请重新登录',
      showRetry: false
    });

    wx.showModal({
      title: '会话过期',
      content: '绑定会话已过期，请重新登录',
      showCancel: false,
      success: () => {
        wx.redirectTo({
          url: '/pages/settings/settings'
        });
      }
    });
  },

  // 绑定失败
  onBindingFailed(message) {
    console.log('[BindAccount] Binding failed:', message);
    
    if (this.bindingTimer) {
      clearInterval(this.bindingTimer);
      this.bindingTimer = null;
    }

    this.setData({
      bindStatus: 'failed',
      loading: false,
      errorMessage: message || '绑定失败，请重试',
      showRetry: true
    });
  },

  // 手动刷新状态
  async onRefreshStatus() {
    console.log('[BindAccount] Manual refresh status');
    
    this.setData({
      loading: true,
      errorMessage: ''
    });

    try {
      const result = await apiClient.checkBindingStatus(this.data.bindToken);
      
      if (result.status === 'bound') {
        this.onBindingSuccess(result);
      } else if (result.status === 'expired') {
        this.onBindingExpired();
      } else {
        this.setData({
          loading: false
        });
        wx.showToast({
          title: '尚未完成绑定',
          icon: 'none'
        });
      }
    } catch (error) {
      console.error('[BindAccount] Refresh failed:', error);
      this.setData({
        loading: false
      });
      wx.showToast({
        title: '刷新失败',
        icon: 'none'
      });
    }
  },

  // 重试绑定
  onRetry() {
    console.log('[BindAccount] Retry binding');
    // 重试时生成新的验证码
    const newVerifyCode = Math.floor(100000 + Math.random() * 900000).toString();
    console.log('[BindAccount] Generated new verify code for retry:', newVerifyCode);
    
    this.setData({
      bindStatus: 'pending',
      errorMessage: '',
      showRetry: false,
      checkCount: 0,
      verifyCode: newVerifyCode  // 重置验证码
    });
    this.startBinding();
  },

  // 返回设置页
  onBack() {
    wx.redirectTo({
      url: '/pages/settings/settings'
    });
  },

  // 复制验证码
  copyVerifyCode() {
    const { verifyCode, bindToken } = this.data;
    const codeToUse = verifyCode || bindToken;
    
    if (codeToUse) {
      wx.setClipboardData({
        data: codeToUse,
        success: () => {
          wx.showToast({
            title: '验证码已复制',
            icon: 'success'
          });
        }
      });
    }
  },
  
  // 复制企微链接
  onCopyUrl() {
    const { kfId } = this.data;
    const customerServiceUrl = `https://work.weixin.qq.com/kfid/${kfId}`;
    
    wx.setClipboardData({
      data: customerServiceUrl,
      success: () => {
        wx.showToast({
          title: '链接已复制，请在浏览器打开',
          icon: 'none',
          duration: 3000
        });
      }
    });
  },
  
  // 复制企微客服ID（用于调试）
  onCopyKfId() {
    wx.setClipboardData({
      data: this.data.kfId,
      success: () => {
        wx.showToast({
          title: '已复制客服ID',
          icon: 'none'
        });
      }
    });
  }
});