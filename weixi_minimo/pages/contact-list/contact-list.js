import { UI_CONFIG, PAGE_ROUTES, EVENT_TYPES, SEARCH_SUGGESTIONS } from '../../utils/constants';
import { formatContactDisplayName, getNameInitial, getAvatarColor } from '../../utils/format-utils';
import { isValidSearchQuery } from '../../utils/validator';
import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';
import themeManager from '../../utils/theme-manager';

Page({
  data: {
    // 联系人数据
    contacts: [],
    searchQuery: '',
    
    // 分页数据
    currentPage: 1,
    hasMore: true,
    loading: false,
    loadingMore: false,
    
    // 统计信息
    stats: {},
    
    // 操作菜单
    showActionMenu: false,
    selectedContact: null,
    
    // 搜索防抖定时器
    searchTimer: null,
    
    // 智能搜索相关
    searchMode: 'simple', // 'simple' | 'intelligent'
    showSearchPanel: false,
    searchSuggestions: SEARCH_SUGGESTIONS,
    searchHistory: [],
    aiAnalysis: '',
    isIntelligentSearch: false,
    searchFocused: false
  },

  onLoad(options) {
    console.log('联系人列表页面加载', options);
    
    // 应用主题
    themeManager.applyToPage(this);
    
    // 检查登录状态
    if (!authManager.isLoggedIn()) {
      console.log('用户未登录，跳转到设置页面');
      wx.showModal({
        title: '需要登录',
        content: '请先登录后再查看联系人列表',
        showCancel: false,
        success: () => {
          wx.switchTab({
            url: '/pages/settings/settings'
          });
        }
      });
      return;
    }
    
    // 添加数据管理器监听器
    this.addDataListeners();
    
    // 检查登录状态
    this.checkLoginStatus();
  },

  onShow() {
    console.log('联系人列表页面显示');
    
    // 每次显示时刷新数据
    this.refreshData();
    
    // 加载搜索历史
    this.loadSearchHistory();
    
    // 设置页面标题
    wx.setNavigationBarTitle({
      title: '联系人'
    });
  },

  onReady() {
    console.log('联系人列表页面准备就绪');
  },

  onHide() {
    console.log('联系人列表页面隐藏');
    
    // 关闭操作菜单
    this.closeActionMenu();
  },

  onUnload() {
    console.log('联系人列表页面卸载');
    
    // 移除监听器
    this.removeDataListeners();
    
    // 清理定时器
    if (this.data.searchTimer) {
      clearTimeout(this.data.searchTimer);
    }
  },

  /**
   * 下拉刷新
   */
  onPullDownRefresh() {
    console.log('下拉刷新');
    this.refreshData(true);
  },

  /**
   * 上拉加载
   */
  onReachBottom() {
    console.log('触底加载更多');
    this.loadMore();
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
          // 自动登录失败，跳转到设置页面进行登录
          wx.switchTab({
            url: '/pages/settings/settings'
          });
          return;
        }
      }
      
      // 登录成功，加载数据
      this.loadInitialData();
    } catch (error) {
      console.error('检查登录状态失败:', error);
      wx.showToast({
        title: '登录检查失败',
        icon: 'error'
      });
    }
  },

  /**
   * 加载初始数据
   */
  async loadInitialData(forceRefresh = false) {
    try {
      this.setData({ loading: true });
      
      // 并行加载联系人数据和统计信息
      const [contactsResult] = await Promise.allSettled([
        this.loadContacts(1, false, forceRefresh),
        this.loadStats()
      ]);
      
      if (contactsResult.status === 'fulfilled') {
        console.log('初始数据加载完成');
      } else {
        console.error('加载联系人数据失败:', contactsResult.reason);
        wx.showToast({
          title: '数据加载失败',
          icon: 'error'
        });
      }
    } catch (error) {
      console.error('加载初始数据失败:', error);
      wx.showToast({
        title: '数据加载失败',
        icon: 'error'
      });
    } finally {
      this.setData({ loading: false });
      wx.stopPullDownRefresh();
    }
  },

  /**
   * 加载联系人数据
   */
  async loadContacts(page = 1, append = false, forceRefresh = false) {
    try {
      const params = {
        page,
        pageSize: UI_CONFIG.PAGE_SIZE,
        search: this.data.searchQuery,
        forceRefresh: forceRefresh || (page === 1 && !append)
      };
      
      const result = await dataManager.getContacts(params);
      
      // 处理联系人数据
      const processedContacts = this.processContacts(result.profiles || []);
      
      // 调试：打印第一个联系人的数据
      if (processedContacts.length > 0) {
        console.log('第一个联系人数据:', processedContacts[0]);
        console.log('手机号:', processedContacts[0].phone);
      }
      
      this.setData({
        contacts: append ? [...this.data.contacts, ...processedContacts] : processedContacts,
        currentPage: page,
        hasMore: page < (result.total_pages || 1),
        loading: false,
        loadingMore: false
      });
      
      return result;
    } catch (error) {
      console.error('加载联系人失败:', error);
      throw error;
    }
  },

  /**
   * 处理联系人数据
   */
  processContacts(contacts) {
    return contacts.map(contact => ({
      ...contact,
      displayName: formatContactDisplayName(contact),
      initial: getNameInitial(contact.profile_name || contact.name),
      avatarColor: getAvatarColor(contact.profile_name || contact.name),
      formattedTags: this.formatContactTags(contact)
    }));
  },

  /**
   * 格式化联系人标签
   */
  formatContactTags(contact) {
    const tags = [];
    
    // 添加性别和年龄
    if (contact.gender) tags.push(contact.gender);
    if (contact.age) tags.push(`${contact.age}岁`);
    
    // 添加位置
    if (contact.location) {
      // 简化位置显示，只显示城市
      const location = contact.location.replace(/市.*区/, '').replace(/省/, '');
      tags.push(location);
    }
    
    // 添加公司或职位
    if (contact.position) {
      tags.push(contact.position);
    } else if (contact.company) {
      // 简化公司名，去掉"有限公司"等后缀
      const company = contact.company.replace(/有限公司|股份有限公司|公司/, '');
      tags.push(company);
    }
    
    // 添加婚姻状况
    if (contact.marital_status && contact.marital_status !== '未知') {
      tags.push(contact.marital_status);
    }
    
    // 添加资产水平
    if (contact.asset_level && contact.asset_level !== '未知') {
      tags.push(contact.asset_level);
    }
    
    return tags.slice(0, 4); // 最多显示4个标签
  },

  /**
   * 加载统计信息
   */
  async loadStats() {
    try {
      const stats = await dataManager.getStats();
      this.setData({ stats });
      return stats;
    } catch (error) {
      console.error('加载统计信息失败:', error);
      return {};
    }
  },

  /**
   * 刷新数据
   */
  async refreshData(showToast = false) {
    try {
      this.setData({ 
        currentPage: 1,
        hasMore: true 
      });
      
      // 强制刷新数据，不使用缓存
      await this.loadInitialData(true);
      
      if (showToast) {
        wx.showToast({
          title: '刷新完成',
          icon: 'success',
          duration: 1500
        });
      }
    } catch (error) {
      console.error('刷新数据失败:', error);
      if (showToast) {
        wx.showToast({
          title: '刷新失败',
          icon: 'error'
        });
      }
    }
  },

  /**
   * 加载更多
   */
  async loadMore() {
    if (this.data.loadingMore || !this.data.hasMore) {
      return;
    }
    
    try {
      this.setData({ loadingMore: true });
      
      const nextPage = this.data.currentPage + 1;
      await this.loadContacts(nextPage, true);
      
    } catch (error) {
      console.error('加载更多失败:', error);
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      });
    }
  },

  /**
   * 搜索输入变化
   */
  onSearchChange(event) {
    const query = event.detail.value;
    this.setData({ searchQuery: query });
    
    // 防抖搜索
    if (this.data.searchTimer) {
      clearTimeout(this.data.searchTimer);
    }
    
    this.data.searchTimer = setTimeout(() => {
      this.performSearch(query);
    }, UI_CONFIG.SEARCH_DEBOUNCE);
  },

  /**
   * 搜索提交
   */
  onSearchSubmit(event) {
    const query = event.detail.value;
    this.performSearch(query);
  },

  /**
   * 清除搜索
   */
  onSearchClear() {
    this.setData({ searchQuery: '' });
    this.performSearch('');
  },

  /**
   * 执行搜索
   */
  async performSearch(query) {
    try {
      this.setData({ 
        loading: true,
        currentPage: 1,
        hasMore: true,
        showSearchPanel: false
      });
      
      // 判断是否使用智能搜索
      if (query.trim() && this.data.searchMode === 'intelligent') {
        await this.performIntelligentSearch(query.trim());
      } else {
        // 普通搜索，使用现有逻辑
        await this.loadContacts(1, false, true);
        this.setData({ 
          isIntelligentSearch: false,
          aiAnalysis: ''
        });
      }
      
      // 保存搜索历史
      if (query.trim()) {
        dataManager.addSearchHistory(query.trim());
        this.loadSearchHistory();
      }
      
    } catch (error) {
      console.error('搜索失败:', error);
      wx.showToast({
        title: '搜索失败',
        icon: 'error'
      });
    }
  },

  /**
   * 智能搜索执行
   */
  async performIntelligentSearch(query) {
    try {
      // 验证搜索关键词
      if (!isValidSearchQuery(query)) {
        wx.showToast({
          title: '搜索内容格式不正确',
          icon: 'none'
        });
        return;
      }

      // 调用语义搜索API
      const result = await dataManager.searchContacts(query);
      
      // 智能匹配度计算和结果处理
      const processedResults = this.processSearchResults(result.profiles || [], query);
      
      // 生成AI分析
      const analysis = this.generateAIAnalysis(processedResults, query);
      
      this.setData({
        contacts: processedResults,
        aiAnalysis: analysis,
        isIntelligentSearch: true,
        loading: false,
        hasMore: false // 搜索结果不分页
      });

      // 显示搜索完成提示
      wx.showToast({
        title: `找到${processedResults.length}个结果`,
        icon: 'success',
        duration: 1500
      });
      
    } catch (error) {
      console.error('智能搜索失败:', error);
      
      this.setData({
        loading: false,
        contacts: [],
        aiAnalysis: ''
      });
      
      wx.showToast({
        title: '搜索失败，请重试',
        icon: 'error'
      });
    }
  },

  /**
   * 处理搜索结果（从AI搜索页面移植）
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
   * 计算匹配度（从AI搜索页面移植）
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
   * 格式化联系人标签（从AI搜索页面移植）
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
   * 生成AI分析（从AI搜索页面移植）
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
   * 搜索模式切换
   */
  onToggleSearchMode() {
    const newMode = this.data.searchMode === 'simple' ? 'intelligent' : 'simple';
    this.setData({ searchMode: newMode });
    
    // 如果当前有搜索词，重新执行搜索
    if (this.data.searchQuery.trim()) {
      this.performSearch(this.data.searchQuery);
    }
    
    wx.showToast({
      title: newMode === 'intelligent' ? '已切换到智能搜索' : '已切换到简单搜索',
      icon: 'success',
      duration: 1500
    });
  },

  /**
   * 搜索面板切换
   */
  onToggleSearchPanel() {
    this.setData({ 
      showSearchPanel: !this.data.showSearchPanel 
    });
  },

  /**
   * 搜索框聚焦
   */
  onSearchFocus() {
    this.setData({ 
      searchFocused: true,
      showSearchPanel: true 
    });
  },

  /**
   * 搜索框失焦
   */
  onSearchBlur() {
    // 延迟设置，避免点击建议时立即失焦
    setTimeout(() => {
      this.setData({ 
        searchFocused: false,
        showSearchPanel: false 
      });
    }, 200);
  },

  /**
   * 搜索建议点击
   */
  onSuggestionTap(event) {
    const suggestion = event.currentTarget.dataset.text;
    this.setData({ 
      searchQuery: suggestion,
      searchMode: 'intelligent' // 自动切换到智能搜索
    });
    this.performSearch(suggestion);
  },

  /**
   * 搜索历史点击
   */
  onHistoryTap(event) {
    const history = event.currentTarget.dataset.text;
    this.setData({ 
      searchQuery: history,
      searchMode: 'intelligent' // 自动切换到智能搜索
    });
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
    const contact = event.detail.contact || event.currentTarget.dataset.contact;
    
    if (!contact) return;
    
    console.log('点击联系人:', contact);
    
    wx.navigateTo({
      url: `${PAGE_ROUTES.CONTACT_DETAIL}?id=${contact.id}`
    });
  },

  /**
   * 联系人长按
   */
  onContactLongPress(event) {
    const contact = event.detail.contact || event.currentTarget.dataset.contact;
    
    if (!contact) return;
    
    console.log('长按联系人:', contact);
    
    // 显示操作菜单
    this.showActionMenu(contact);
    
    // 触觉反馈
    wx.vibrateShort();
  },

  /**
   * 显示操作菜单
   */
  showActionMenu(contact) {
    this.setData({
      selectedContact: {
        ...contact,
        initial: getNameInitial(contact.profile_name || contact.name),
        avatarColor: getAvatarColor(contact.profile_name || contact.name)
      },
      showActionMenu: true
    });
  },

  /**
   * 关闭操作菜单
   */
  closeActionMenu() {
    this.setData({
      showActionMenu: false,
      selectedContact: null
    });
  },

  /**
   * 操作菜单相关事件
   */
  onCloseActionMenu() {
    this.closeActionMenu();
  },

  onStopPropagation() {
    // 阻止事件冒泡
  },

  /**
   * 查看详情
   */
  onViewDetail() {
    const contact = this.data.selectedContact;
    this.closeActionMenu();
    
    if (contact) {
      wx.navigateTo({
        url: `${PAGE_ROUTES.CONTACT_DETAIL}?id=${contact.id}`
      });
    }
  },

  /**
   * 编辑联系人
   */
  onEditContact() {
    const contact = this.data.selectedContact;
    this.closeActionMenu();
    
    if (contact) {
      wx.navigateTo({
        url: `${PAGE_ROUTES.CONTACT_FORM}?id=${contact.id}&mode=edit`
      });
    }
  },

  /**
   * 删除联系人
   */
  onDeleteContact() {
    const contact = this.data.selectedContact;
    this.closeActionMenu();
    
    if (!contact) return;
    
    wx.showModal({
      title: '确认删除',
      content: `确定要删除联系人"${contact.profile_name || contact.name}"吗？`,
      confirmColor: '#ff4757',
      success: (res) => {
        if (res.confirm) {
          this.deleteContact(contact.id);
        }
      }
    });
  },

  /**
   * 执行删除联系人
   */
  async deleteContact(contactId) {
    try {
      wx.showLoading({ title: '删除中...' });
      
      await dataManager.deleteContact(contactId);
      
      wx.hideLoading();
      wx.showToast({
        title: '删除成功',
        icon: 'success'
      });
      
      // 刷新列表
      this.refreshData();
      
    } catch (error) {
      wx.hideLoading();
      console.error('删除联系人失败:', error);
      
      wx.showToast({
        title: '删除失败',
        icon: 'error'
      });
    }
  },

  /**
   * 添加联系人
   */
  onAddContact() {
    wx.navigateTo({
      url: `${PAGE_ROUTES.CONTACT_FORM}?mode=add`
    });
  },

  /**
   * 刷新数据按钮点击
   */
  onRefreshData() {
    this.refreshData(true);
  },

  /**
   * 手动加载更多
   */
  onLoadMore() {
    this.loadMore();
  },

  /**
   * 获取标签类型
   */
  getTagType(tag) {
    if (!tag) return 'default';
    
    // 性别
    if (tag === '男' || tag === '女') return 'gender';
    
    // 年龄
    if (tag.includes('岁')) return 'age';
    
    // 位置
    if (tag.includes('北京') || tag.includes('上海') || tag.includes('广州') || 
        tag.includes('深圳') || tag.includes('杭州') || tag.includes('成都') ||
        tag.includes('天津') || tag.includes('重庆')) return 'location';
    
    // 婚姻状况
    if (tag === '已婚' || tag === '未婚' || tag === '离异') return 'marital';
    
    // 资产
    if (tag.includes('万')) return 'asset';
    
    // 默认为职位/公司
    return 'position';
  },

  /**
   * 添加数据监听器
   */
  addDataListeners() {
    this.dataListener = (eventType, data) => {
      switch (eventType) {
        case 'contactsUpdated':
          console.log('联系人数据更新:', data?.length);
          // 更新页面联系人数据
          if (data && Array.isArray(data)) {
            const processedContacts = this.processContacts(data);
            this.setData({ 
              contacts: processedContacts,
              loading: false,
              loadingMore: false 
            });
          }
          break;
          
        case 'contactDeleted':
          console.log('联系人已删除:', data);
          // 从列表中移除已删除的联系人
          if (data && data.id) {
            const updatedContacts = this.data.contacts.filter(contact => contact.id !== data.id);
            this.setData({ contacts: updatedContacts });
          }
          break;
          
        case 'contactCreated':
          console.log('新增联系人:', data);
          // 将新联系人添加到列表开头
          if (data) {
            const processedContact = this.processContacts([data]);
            this.setData({ 
              contacts: [...processedContact, ...this.data.contacts]
            });
          }
          break;
          
        case 'contactUpdated':
          console.log('联系人已更新:', data);
          // 更新列表中的联系人
          if (data && data.id) {
            const updatedContacts = this.data.contacts.map(contact => 
              contact.id === data.id ? this.processContacts([data])[0] : contact
            );
            this.setData({ contacts: updatedContacts });
          }
          break;
          
        case 'statsUpdated':
          console.log('统计信息更新:', data);
          this.setData({ stats: data });
          break;
          
        case 'searchPerformed':
          console.log('搜索执行:', data);
          break;
      }
    };
    
    dataManager.addListener(this.dataListener);
  },

  /**
   * 移除数据监听器
   */
  removeDataListeners() {
    if (this.dataListener) {
      dataManager.removeListener(this.dataListener);
      this.dataListener = null;
    }
  }
});