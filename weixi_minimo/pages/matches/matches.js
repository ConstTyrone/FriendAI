// 匹配结果页面
import apiClient from '../../utils/api-client';
import authManager from '../../utils/auth-manager';
import themeManager from '../../utils/theme-manager';

Page({
  data: {
    matches: [],
    loading: false,
    intentId: null,
    intentName: '',
    filters: {
      minScore: 0,
      status: 'pending'
    },
    aiEnabled: false,
    vectorStatus: null,
    themeClass: '',
    showBottomTrigger: false
  },

  onLoad(options) {
    // 获取意图ID和高亮ID
    if (options.intentId) {
      this.setData({
        intentId: options.intentId
      });
    }
    
    // 保存需要高亮的匹配ID
    if (options.highlightId) {
      this.highlightMatchId = options.highlightId;
    }
    
    // 设置页面标题
    if (options.intentId) {
      wx.setNavigationBarTitle({
        title: '意图匹配结果'
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
    
    // 应用主题
    themeManager.applyToPage(this);
    
    // 加载AI状态
    this.loadAIStatus();
    
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
          createdAtFormat: this.formatDate(match.created_at),
          // AI增强标识
          isAIMatch: match.match_type === 'hybrid' || match.match_type === 'vector',
          hasVectorSimilarity: match.vector_similarity !== undefined && match.vector_similarity > 0,
          vectorSimilarity: match.vector_similarity ? Math.round(match.vector_similarity * 100) : 0,
          matchTypeDisplay: this.getMatchTypeDisplay(match.match_type),
          // 高亮标记
          isHighlighted: this.highlightMatchId && String(match.id) === String(this.highlightMatchId)
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
      
      // 延迟检查是否需要显示底部按钮
      setTimeout(() => {
        this.checkScrollPosition();
      }, 500);
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
   * 加载AI状态
   */
  async loadAIStatus() {
    try {
      const response = await apiClient.request({
        url: '/api/ai/vector-status',
        method: 'GET'
      });
      
      if (response.success && response.data) {
        this.setData({
          aiEnabled: response.data.aiEnabled,
          vectorStatus: response.data
        });
      }
    } catch (error) {
      console.log('AI状态获取失败:', error);
      // 不显示错误提示，AI功能是可选的
    }
  },

  /**
   * 获取匹配类型显示文本
   */
  getMatchTypeDisplay(matchType) {
    switch (matchType) {
      case 'vector':
        return 'AI语义匹配';
      case 'hybrid':
        return 'AI增强匹配';
      case 'rule':
      default:
        return '规则匹配';
    }
  },

  /**
   * 手动触发意图匹配
   */
  async triggerMatch() {
    if (!this.data.intentId) {
      wx.showToast({
        title: '无法触发匹配',
        icon: 'error'
      });
      return;
    }

    try {
      wx.showLoading({
        title: '匹配中...'
      });

      const response = await apiClient.request({
        url: `/api/intents/${this.data.intentId}/match`,
        method: 'POST',
        timeout: 60000  // AI匹配需要更长时间
      });

      wx.hideLoading();

      if (response.success) {
        wx.showToast({
          title: response.message || '匹配完成',
          icon: 'success'
        });
        
        // 重新加载匹配结果
        setTimeout(() => {
          this.loadMatches();
        }, 1000);
      }
    } catch (error) {
      wx.hideLoading();
      console.error('触发匹配失败:', error);
      wx.showToast({
        title: '匹配失败',
        icon: 'error'
      });
    }
  },

  /**
   * 查看AI状态详情
   */
  showAIStatus() {
    if (!this.data.vectorStatus) {
      wx.showToast({
        title: '数据未加载',
        icon: 'none'
      });
      return;
    }

    const status = this.data.vectorStatus;
    const content = `AI功能: ${status.aiEnabled ? '已启用' : '未启用'}\n` +
                   `意图向量化: ${status.intents.vectorized}/${status.intents.total} (${status.intents.percentage}%)\n` +
                   `联系人向量化: ${status.profiles.vectorized}/${status.profiles.total} (${status.profiles.percentage}%)`;

    wx.showModal({
      title: 'AI增强状态',
      content: content,
      showCancel: false,
      confirmText: '知道了'
    });
  },

  /**
   * 检查滚动位置
   */
  checkScrollPosition() {
    const query = wx.createSelectorQuery().in(this);
    query.select('.matches-page').scrollOffset();
    query.exec((res) => {
      if (res && res[0]) {
        const { scrollTop, scrollHeight } = res[0];
        const systemInfo = wx.getSystemInfoSync();
        const screenHeight = systemInfo.windowHeight;
        
        const isNearBottom = scrollTop + screenHeight >= scrollHeight - 150;
        console.log('Check position:', { scrollTop, scrollHeight, screenHeight, isNearBottom });
        
        this.setData({
          showBottomTrigger: isNearBottom
        });
      }
    });
  },

  /**
   * 页面滚动监听
   */
  onPageScroll(e) {
    try {
      const { scrollTop, scrollHeight } = e.detail;
      
      // 获取屏幕高度
      const systemInfo = wx.getSystemInfoSync();
      const screenHeight = systemInfo.windowHeight;
      
      // 计算是否滑动到底部附近（距离底部150px以内）
      const isNearBottom = scrollTop + screenHeight >= scrollHeight - 150;
      
      // 调试日志
      console.log('Scroll:', { scrollTop, scrollHeight, screenHeight, isNearBottom });
      
      // 只有当状态改变时才更新
      if (isNearBottom !== this.data.showBottomTrigger) {
        this.setData({
          showBottomTrigger: isNearBottom
        });
      }
    } catch (error) {
      console.error('滚动监听错误:', error);
    }
  },

  /**
   * 提交反馈
   */
  async submitFeedback(e) {
    const { matchId, feedback } = e.currentTarget.dataset;
    
    if (!matchId) {
      wx.showToast({
        title: '无效的匹配ID',
        icon: 'none'
      });
      return;
    }

    // 获取当前匹配项的旧反馈
    const matchIndex = this.data.matches.findIndex(item => item.id === matchId);
    if (matchIndex === -1) {
      wx.showToast({
        title: '找不到匹配项',
        icon: 'none'
      });
      return;
    }

    const oldFeedback = this.data.matches[matchIndex].user_feedback;

    // 如果点击相同的反馈，则取消反馈
    const newFeedback = oldFeedback === feedback ? null : feedback;

    // 立即更新UI，提供即时反馈
    const updatedMatches = [...this.data.matches];
    updatedMatches[matchIndex].user_feedback = newFeedback;
    this.setData({ matches: updatedMatches });

    try {
      // 调用API更新反馈
      const result = await apiClient.request({
        url: `/api/matches/${matchId}/feedback`,
        method: 'PUT',
        data: {
          feedback: newFeedback
        }
      });

      if (result.success) {
        // 显示轻量级反馈提示
        const message = newFeedback ? 
          (newFeedback === 'positive' ? '👍 已标记为好匹配' :
           newFeedback === 'negative' ? '👎 已标记为不准确' :
           '⏭ 已忽略') :
          '已取消反馈';
          
        wx.showToast({
          title: message,
          icon: 'none',
          duration: 1500
        });

        // 记录分析事件
        console.log('反馈提交成功:', {
          matchId,
          oldFeedback,
          newFeedback,
          userId: authManager.getUserInfo()?.openid
        });
      } else {
        // 如果失败，恢复原状态
        updatedMatches[matchIndex].user_feedback = oldFeedback;
        this.setData({ matches: updatedMatches });
        
        wx.showToast({
          title: result.message || '反馈提交失败',
          icon: 'none'
        });
      }
    } catch (error) {
      console.error('提交反馈失败:', error);
      
      // 恢复原状态
      const revertMatches = [...this.data.matches];
      revertMatches[matchIndex].user_feedback = oldFeedback;
      this.setData({ matches: revertMatches });
      
      wx.showToast({
        title: '网络错误，请重试',
        icon: 'none'
      });
    }
  },

  /**
   * 返回
   */
  onBack() {
    wx.navigateBack();
  }
});