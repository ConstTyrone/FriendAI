// 匹配结果页面
import apiClient from '../../utils/api-client';
import authManager from '../../utils/auth-manager';

Page({
  data: {
    matches: [],
    loading: false,
    intentId: null,
    intentName: '',
    filters: {
      minScore: 0,
      status: 'pending'
    }
  },

  onLoad(options) {
    // 获取意图ID
    if (options.intentId) {
      this.setData({
        intentId: options.intentId
      });
    }
    
    // 检查登录状态
    if (!authManager.isLoggedIn()) {
      wx.showModal({
        title: '需要登录',
        content: '请先登录',
        showCancel: false,
        success: () => {
          wx.switchTab({
            url: '/pages/settings/settings'
          });
        }
      });
      return;
    }
    
    // 加载匹配结果
    this.loadMatches();
  },

  /**
   * 加载匹配结果
   */
  async loadMatches() {
    try {
      this.setData({ loading: true });
      
      const params = {
        page: 1,
        size: 50
      };
      
      if (this.data.intentId) {
        params.intent_id = this.data.intentId;
      }
      
      const response = await apiClient.request({
        url: '/api/matches',
        method: 'GET',
        data: params
      });
      
      if (response.success && response.data) {
        const matches = response.data.matches || [];
        
        // 处理匹配数据
        const processedMatches = matches.map(match => ({
          ...match,
          scorePercent: Math.round((match.match_score || 0) * 100),
          profileInitial: this.getInitial(match.profile_name),
          createdAtFormat: this.formatDate(match.created_at)
        }));
        
        this.setData({
          matches: processedMatches
        });
        
        // 如果有意图ID，获取意图名称
        if (this.data.intentId && matches.length > 0) {
          this.setData({
            intentName: matches[0].intent_name || ''
          });
        }
      }
    } catch (error) {
      console.error('加载匹配结果失败:', error);
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      });
    } finally {
      this.setData({ loading: false });
    }
  },

  /**
   * 查看联系人详情
   */
  viewProfile(e) {
    const profileId = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/contact-detail/contact-detail?id=${profileId}`
    });
  },

  /**
   * 获取姓名首字母
   */
  getInitial(name) {
    if (!name) return '?';
    return name.charAt(0).toUpperCase();
  },

  /**
   * 格式化日期
   */
  formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) {
      return '刚刚';
    } else if (diff < 3600000) {
      return Math.floor(diff / 60000) + '分钟前';
    } else if (diff < 86400000) {
      return Math.floor(diff / 3600000) + '小时前';
    } else {
      return Math.floor(diff / 86400000) + '天前';
    }
  },

  /**
   * 返回
   */
  onBack() {
    wx.navigateBack();
  }
});