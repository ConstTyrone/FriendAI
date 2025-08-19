import { UI_CONFIG, PAGE_ROUTES, SEARCH_SUGGESTIONS } from '../../utils/constants';
import { formatContactDisplayName, getNameInitial, getAvatarColor } from '../../utils/format-utils';
import { isValidSearchQuery } from '../../utils/validator';
import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';
import themeManager from '../../utils/theme-manager';

Page({
  data: {
    // 搜索相关
    searchQuery: '',
    lastSearchQuery: '',
    searching: false,
    searchFocused: false,
    hasSearched: false,
    
    // 搜索结果
    searchResults: [],
    aiAnalysis: '',
    
    // 建议和历史
    suggestions: SEARCH_SUGGESTIONS,
    searchHistory: [],
    
    // 防抖定时器
    searchTimer: null
  },

  onLoad(options) {
    console.log('AI搜索页面加载', options);
    
    // 应用主题
    themeManager.applyToPage(this);
    
    // 检查登录状态
    if (!authManager.isLoggedIn()) {
      console.log('用户未登录，跳转到设置页面');
      wx.showModal({
        title: '需要登录',
        content: '请先登录后再使用AI搜索功能',
        showCancel: false,
        success: () => {
          wx.switchTab({
            url: '/pages/settings/settings'
          });
        }
      });
      return;
    }
    
    // 检查登录状态
    this.checkLoginStatus();
    
    // 处理来自其他页面的搜索参数
    if (options.query) {
      this.setData({
        searchQuery: decodeURIComponent(options.query)
      }, () => {
        this.performSearch(this.data.searchQuery);
      });
    }
  },

  onShow() {
    console.log('AI搜索页面显示');
    
    // 加载搜索历史
    this.loadSearchHistory();
    
    // 设置页面标题
    wx.setNavigationBarTitle({
      title: 'AI搜索'
    });
  },

  onReady() {
    console.log('AI搜索页面准备就绪');
  },

  onHide() {
    console.log('AI搜索页面隐藏');
    
    // 清理搜索状态
    this.setData({
      searchFocused: false
    });
  },

  onUnload() {
    console.log('AI搜索页面卸载');
    
    // 清理定时器
    if (this.data.searchTimer) {
      clearTimeout(this.data.searchTimer);
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    console.log('下拉刷新搜索结果');
    
    if (this.data.lastSearchQuery) {
      this.performSearch(this.data.lastSearchQuery, true);
    } else {
      wx.stopPullDownRefresh();
    }
  },

  /**
   * 检查登录状态
   */
  async checkLoginStatus() {
    try {
      const isLoggedIn = authManager.isLoggedIn();
      
      if (!isLoggedIn) {
        // 尝试自动登录
        const autoLoginSuccess = await authManager.checkAutoLogin();
        
        if (!autoLoginSuccess) {
          wx.showModal({
            title: '需要登录',
            content: '请先登录后使用AI搜索功能',
            confirmText: '去登录',
            success: (res) => {
              if (res.confirm) {
                wx.switchTab({
                  url: '/pages/settings/settings'
                });
              }
            }
          });
          return;
        }
      }
      
      console.log('用户已登录，可以使用搜索功能');
    } catch (error) {
      console.error('检查登录状态失败:', error);
      wx.showToast({
        title: '登录检查失败',
        icon: 'error'
      });
    }
  },

  /**
   * 加载搜索历史
   */
  loadSearchHistory() {
    try {
      const history = dataManager.getSearchHistory();
      this.setData({
        searchHistory: history.slice(0, 10) // 最多显示10条历史
      });
      
      console.log('搜索历史加载完成:', history.length);
    } catch (error) {
      console.error('加载搜索历史失败:', error);
    }
  },

  /**
   * 搜索输入变化
   */
  onSearchChange(event) {
    const query = event.detail.value;
    this.setData({ searchQuery: query });
    
    // 防抖搜索（仅在输入内容时）
    if (query.trim()) {
      if (this.data.searchTimer) {
        clearTimeout(this.data.searchTimer);
      }
      
      this.data.searchTimer = setTimeout(() => {
        // 这里可以实现实时搜索建议
        this.generateSearchSuggestions(query);
      }, UI_CONFIG.SEARCH_DEBOUNCE);
    }
  },

  /**
   * 搜索提交
   */
  onSearchSubmit(event) {
    const query = event?.detail?.value || this.data.searchQuery;
    this.performSearch(query);
  },

  /**
   * 清除搜索
   */
  onSearchClear() {
    this.setData({
      searchQuery: '',
      hasSearched: false,
      searchResults: [],
      aiAnalysis: '',
      lastSearchQuery: ''
    });
  },

  /**
   * 搜索框聚焦
   */
  onSearchFocus() {
    this.setData({ searchFocused: true });
  },

  /**
   * 搜索框失焦
   */
  onSearchBlur() {
    // 延迟设置，避免点击建议时立即失焦
    setTimeout(() => {
      this.setData({ searchFocused: false });
    }, 200);
  },

  /**
   * 执行搜索
   */
  async performSearch(query, forceRefresh = false) {
    if (!query || !query.trim()) {
      wx.showToast({
        title: '请输入搜索内容',
        icon: 'none'
      });
      return;
    }
    
    const trimmedQuery = query.trim();
    
    // 验证搜索关键词
    if (!isValidSearchQuery(trimmedQuery)) {
      wx.showToast({
        title: '搜索内容格式不正确',
        icon: 'none'
      });
      return;
    }
    
    try {
      this.setData({
        searching: true,
        hasSearched: true,
        lastSearchQuery: trimmedQuery,
        searchQuery: trimmedQuery
      });
      
      // 调用搜索API
      const result = await dataManager.searchContacts(trimmedQuery);
      
      // 处理搜索结果
      const processedResults = this.processSearchResults(result.profiles || [], trimmedQuery);
      
      // 生成AI分析
      const analysis = this.generateAIAnalysis(processedResults, trimmedQuery);
      
      this.setData({
        searchResults: processedResults,
        aiAnalysis: analysis,
        searching: false
      });
      
      // 刷新搜索历史
      this.loadSearchHistory();
      
      // 显示搜索完成提示
      if (!forceRefresh) {
        wx.showToast({
          title: `找到${processedResults.length}个结果`,
          icon: 'success',
          duration: 1500
        });
      }
      
      console.log('搜索完成:', {
        query: trimmedQuery,
        resultCount: processedResults.length
      });
      
    } catch (error) {
      console.error('搜索失败:', error);
      
      this.setData({
        searching: false,
        searchResults: [],
        aiAnalysis: ''
      });
      
      wx.showToast({
        title: '搜索失败，请重试',
        icon: 'error'
      });
    } finally {
      wx.stopPullDownRefresh();
    }
  },

  /**
   * 处理搜索结果
   */
  processSearchResults(results, query) {
    return results.map(contact => {
      // 计算匹配度
      const matchScore = this.calculateMatchScore(contact, query);
      
      return {
        ...contact,
        displayName: formatContactDisplayName(contact),
        initial: getNameInitial(contact.profile_name || contact.name),
        avatarColor: getAvatarColor(contact.profile_name || contact.name),
        matchScore,
        isHighMatch: matchScore > 0.8,
        formattedTags: this.formatContactTags(contact)
      };
    }).sort((a, b) => b.matchScore - a.matchScore); // 按匹配度排序
  },

  /**
   * 计算匹配度
   */
  calculateMatchScore(contact, query) {
    const lowerQuery = query.toLowerCase();
    let score = 0;
    
    // 姓名匹配（权重最高）
    if (contact.profile_name && contact.profile_name.toLowerCase().includes(lowerQuery)) {
      score += 1.0;
    }
    
    // 公司匹配
    if (contact.company && contact.company.toLowerCase().includes(lowerQuery)) {
      score += 0.7;
    }
    
    // 职位匹配
    if (contact.position && contact.position.toLowerCase().includes(lowerQuery)) {
      score += 0.6;
    }
    
    // 地区匹配
    if (contact.location && contact.location.toLowerCase().includes(lowerQuery)) {
      score += 0.5;
    }
    
    // AI摘要匹配
    if (contact.ai_summary && contact.ai_summary.toLowerCase().includes(lowerQuery)) {
      score += 0.4;
    }
    
    // 其他字段匹配
    const otherFields = [contact.education, contact.marital_status, contact.personality];
    otherFields.forEach(field => {
      if (field && field.toLowerCase().includes(lowerQuery)) {
        score += 0.2;
      }
    });
    
    return Math.min(score, 1.0); // 最大值为1.0
  },

  /**
   * 格式化联系人标签
   */
  formatContactTags(contact) {
    const tags = [];
    
    if (contact.age) tags.push(`${contact.age}岁`);
    if (contact.gender) tags.push(contact.gender);
    if (contact.location) tags.push(contact.location);
    if (contact.asset_level) tags.push(`${contact.asset_level}资产`);
    if (contact.marital_status) tags.push(contact.marital_status);
    
    return tags.slice(0, 4); // 最多显示4个标签
  },

  /**
   * 生成AI分析
   */
  generateAIAnalysis(results, query) {
    if (results.length === 0) {
      return `抱歉，没有找到与"${query}"相关的联系人。建议尝试其他关键词或使用更具体的描述。`;
    }
    
    const highMatchCount = results.filter(r => r.isHighMatch).length;
    const locations = [...new Set(results.map(r => r.location).filter(Boolean))];
    const companies = [...new Set(results.map(r => r.company).filter(Boolean))];
    
    let analysis = `找到 ${results.length} 个相关联系人`;
    
    if (highMatchCount > 0) {
      analysis += `，其中 ${highMatchCount} 个高度匹配`;
    }
    
    if (locations.length > 0) {
      analysis += `。主要分布在：${locations.slice(0, 3).join('、')}`;
    }
    
    if (companies.length > 0) {
      analysis += `。主要来自：${companies.slice(0, 3).join('、')}等公司`;
    }
    
    analysis += '。';
    
    return analysis;
  },

  /**
   * 生成搜索建议
   */
  generateSearchSuggestions(query) {
    // 这里可以根据输入内容生成动态建议
    // 暂时使用静态建议
    console.log('生成搜索建议:', query);
  },

  /**
   * 建议词点击
   */
  onSuggestionTap(event) {
    const suggestion = event.currentTarget.dataset.text;
    this.setData({ searchQuery: suggestion });
    this.performSearch(suggestion);
  },

  /**
   * 历史记录点击
   */
  onHistoryTap(event) {
    const history = event.currentTarget.dataset.text;
    this.setData({ searchQuery: history });
    this.performSearch(history);
  },

  /**
   * 清除搜索历史
   */
  onClearHistory() {
    wx.showModal({
      title: '确认清除',
      content: '确定要清除所有搜索历史吗？',
      success: (res) => {
        if (res.confirm) {
          dataManager.clearSearchHistory();
          this.setData({ searchHistory: [] });
          
          wx.showToast({
            title: '已清除历史',
            icon: 'success'
          });
        }
      }
    });
  },

  /**
   * 联系人点击
   */
  onContactTap(event) {
    const contact = event.currentTarget.dataset.contact;
    
    if (!contact) return;
    
    console.log('点击搜索结果联系人:', contact);
    
    wx.navigateTo({
      url: `${PAGE_ROUTES.CONTACT_DETAIL}?id=${contact.id}`
    });
  },

  /**
   * 快速搜索
   */
  onQuickSearch(event) {
    const query = event.currentTarget.dataset.query;
    this.setData({ searchQuery: query });
    this.performSearch(query);
  },

  /**
   * 尝试其他搜索
   */
  onTryOtherSearch() {
    this.setData({
      searchQuery: '',
      hasSearched: false,
      searchResults: [],
      aiAnalysis: '',
      lastSearchQuery: ''
    });
    
    // 聚焦搜索框
    // 注意：小程序中无法直接调用input的focus方法
  }
});