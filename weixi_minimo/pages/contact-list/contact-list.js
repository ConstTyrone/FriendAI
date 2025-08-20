import { UI_CONFIG, PAGE_ROUTES, EVENT_TYPES } from '../../utils/constants';
import { formatContactDisplayName, getNameInitial, getAvatarColor } from '../../utils/format-utils';
import { isValidSearchQuery } from '../../utils/validator';
import authManager from '../../utils/auth-manager';
import dataManager from '../../utils/data-manager';
import themeManager from '../../utils/theme-manager';
import semanticSearchEngine from '../../utils/semantic-search';

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
    showSearchPanel: false,
    searchSuggestions: [
      '30岁的程序员',
      '在北京做金融的',
      '年轻的设计师',
      '有经验的销售',
      '做医生的朋友',
      '互联网行业',
      '从事教育工作',
      '上海的律师'
    ],
    searchHistory: [],
    searchAnalysis: '',
    allContacts: [], // 缓存所有联系人用于本地搜索
    isSearching: false,
    searchFocused: false,
    
    // 手势操作状态
    swipeStates: {}, // 每个item的滑动状态 {index: boolean}
    touchStartX: 0,
    touchStartY: 0,
    touchStartTime: 0,
    currentSwipeIndex: -1, // 当前正在滑动的item索引
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
      const [contactsResult, statsResult] = await Promise.allSettled([
        this.loadContacts(1, false, forceRefresh),
        this.loadStats()
      ]);
      
      if (contactsResult.status === 'fulfilled') {
        console.log('初始数据加载完成');
        
        // 在后台预加载所有联系人数据用于智能搜索
        this.ensureAllContactsLoaded().catch(error => {
          console.error('预加载搜索数据失败:', error);
        });
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
   * 执行智能搜索
   */
  async performSearch(query) {
    try {
      this.setData({ 
        isSearching: true,
        showSearchPanel: false
      });

      if (!query.trim()) {
        // 空查询，显示所有联系人
        this.setData({
          contacts: this.data.allContacts,
          searchAnalysis: '',
          isSearching: false
        });
        return;
      }

      // 确保有完整的联系人数据用于本地搜索
      await this.ensureAllContactsLoaded();

      // 使用语义搜索引擎进行本地搜索
      const searchResult = semanticSearchEngine.search(this.data.allContacts, query.trim());
      
      // 处理搜索结果，添加显示所需的字段
      const processedResults = searchResult.results.map(contact => ({
        ...contact,
        displayName: formatContactDisplayName(contact),
        initial: getNameInitial(contact.profile_name || contact.name),
        avatarColor: getAvatarColor(contact.profile_name || contact.name),
        matchPercentage: Math.round(contact.matchScore * 100),
        isHighMatch: contact.matchScore > 0.7,
        formattedTags: this.formatContactTags(contact)
      }));

      this.setData({
        contacts: processedResults,
        searchAnalysis: searchResult.analysis,
        isSearching: false,
        hasMore: false // 搜索结果不分页
      });

      // 保存搜索历史
      dataManager.addSearchHistory(query.trim());
      this.loadSearchHistory();

      // 显示搜索完成提示
      wx.showToast({
        title: `找到${processedResults.length}个结果`,
        icon: 'success',
        duration: 1500
      });
      
    } catch (error) {
      console.error('智能搜索失败:', error);
      
      this.setData({
        isSearching: false,
        contacts: [],
        searchAnalysis: ''
      });
      
      wx.showToast({
        title: '搜索失败，请重试',
        icon: 'error'
      });
    }
  },

  /**
   * 确保所有联系人都已加载到本地缓存
   */
  async ensureAllContactsLoaded() {
    if (this.data.allContacts.length > 0) {
      return; // 已有缓存数据
    }

    try {
      // 获取所有联系人数据（不分页）
      const result = await dataManager.getContacts({
        page: 1,
        pageSize: 1000, // 获取足够大的数量
        search: '', // 空搜索获取所有数据
        forceRefresh: false
      });

      const processedContacts = this.processContacts(result.profiles || []);
      
      this.setData({
        allContacts: processedContacts
      });

      console.log(`已缓存 ${processedContacts.length} 个联系人用于本地搜索`);
      
    } catch (error) {
      console.error('加载所有联系人失败:', error);
      throw error;
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
      searchQuery: suggestion
    });
    this.performSearch(suggestion);
  },

  /**
   * 搜索历史点击
   */
  onHistoryTap(event) {
    const history = event.currentTarget.dataset.text;
    this.setData({ 
      searchQuery: history
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
    
    // 检查是否有打开的滑动菜单，如果有则先关闭
    const hasOpenMenus = Object.values(this.data.swipeStates).some(state => state);
    if (hasOpenMenus) {
      this.closeAllSwipeMenus();
      return; // 第一次点击关闭菜单，不跳转
    }
    
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
  onEditContact(e) {
    e && e.stopPropagation && e.stopPropagation(); // 阻止事件冒泡
    
    let contact;
    
    // 如果有事件对象，说明是从滑动菜单点击
    if (e && e.currentTarget && e.currentTarget.dataset) {
      contact = e.currentTarget.dataset.contact;
      const index = e.currentTarget.dataset.index;
      console.log('从滑动菜单编辑联系人:', { contact, index });
      this.closeAllSwipeMenus();
    } else {
      // 从长按菜单点击
      contact = this.data.selectedContact;
      this.closeActionMenu();
    }
    
    if (contact && contact.id) {
      wx.navigateTo({
        url: `${PAGE_ROUTES.CONTACT_FORM}?id=${contact.id}&mode=edit`
      });
    } else {
      console.error('编辑联系人失败：联系人数据不完整', contact);
      wx.showToast({
        title: '联系人数据错误',
        icon: 'none'
      });
    }
  },

  /**
   * 删除联系人
   */
  onDeleteContact(e) {
    e && e.stopPropagation && e.stopPropagation(); // 阻止事件冒泡
    
    let contact;
    
    // 如果有事件对象，说明是从滑动菜单点击
    if (e && e.currentTarget && e.currentTarget.dataset) {
      contact = e.currentTarget.dataset.contact;
      const index = e.currentTarget.dataset.index;
      console.log('从滑动菜单删除联系人:', { contact, index });
      this.closeAllSwipeMenus();
    } else {
      // 从长按菜单点击
      contact = this.data.selectedContact;
      this.closeActionMenu();
    }
    
    if (!contact || !contact.id) {
      console.error('删除联系人失败：联系人数据不完整', contact);
      wx.showToast({
        title: '联系人数据错误',
        icon: 'none'
      });
      return;
    }
    
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
    if (this.dataListener && dataManager.removeListener) {
      try {
        dataManager.removeListener(this.dataListener);
        this.dataListener = null;
        console.log('联系人页面监听器已移除');
      } catch (error) {
        console.error('移除监听器失败:', error);
        this.dataListener = null;
      }
    }
  },

  /**
   * 手势操作 - 触摸开始
   */
  onTouchStart(e) {
    const { clientX, clientY } = e.touches[0];
    const index = parseInt(e.currentTarget.dataset.index);
    
    this.setData({
      touchStartX: clientX,
      touchStartY: clientY,
      touchStartTime: Date.now(),
      isMoving: false
    });
    
    console.log('触摸开始:', { index, x: clientX, y: clientY });
  },

  /**
   * 手势操作 - 触摸移动
   */
  onTouchMove(e) {
    // 只记录移动状态，不进行任何滑动判断
    this.setData({ isMoving: true });
  },

  /**
   * 手势操作 - 触摸结束
   */
  onTouchEnd(e) {
    const { clientX, clientY } = e.changedTouches[0];
    const index = parseInt(e.currentTarget.dataset.index);
    const { touchStartX, touchStartY, touchStartTime, isMoving } = this.data;
    
    // 重置移动状态
    this.setData({ isMoving: false });
    
    if (isNaN(index)) return;
    
    const deltaX = clientX - touchStartX;
    const deltaY = clientY - touchStartY;
    const deltaTime = Date.now() - touchStartTime;
    
    console.log('触摸结束:', { 
      index, 
      deltaX, 
      deltaY, 
      deltaTime,
      isMoving,
      currentState: this.data.swipeStates[index]
    });
    
    // 严格的滑动检测条件
    const isValidSwipe = 
      isMoving && // 确实有移动
      deltaTime < 500 && // 滑动时间不超过500ms
      deltaX < -100 && // 左滑距离至少100rpx
      Math.abs(deltaY) < 50 && // 垂直偏移不超过50rpx
      Math.abs(deltaX) > Math.abs(deltaY) * 2; // 水平距离是垂直距离的2倍以上
    
    if (isValidSwipe && !this.data.swipeStates[index]) {
      // 关闭其他所有菜单
      this.closeAllSwipeMenus();
      
      // 打开当前菜单
      const newSwipeStates = { ...this.data.swipeStates };
      newSwipeStates[index] = true;
      
      this.setData({
        swipeStates: newSwipeStates,
        currentSwipeIndex: index
      });
      
      console.log('有效左滑，打开菜单:', index);
    } else if (this.data.swipeStates[index] && deltaX > 40) {
      // 右滑关闭菜单
      const newSwipeStates = { ...this.data.swipeStates };
      newSwipeStates[index] = false;
      
      this.setData({
        swipeStates: newSwipeStates,
        currentSwipeIndex: -1
      });
      
      console.log('右滑关闭菜单:', index);
    }
  },

  /**
   * 关闭所有滑动菜单
   */
  closeAllSwipeMenus() {
    const hasOpenMenus = Object.values(this.data.swipeStates).some(state => state);
    
    if (hasOpenMenus) {
      this.setData({
        swipeStates: {},
        currentSwipeIndex: -1
      });
      console.log('关闭所有滑动菜单');
    }
  },


  /**
   * 页面点击事件 - 关闭滑动菜单
   */
  onPageTap(e) {
    // 检查点击目标是否在滑动菜单区域
    const { target } = e;
    if (target && target.dataset && (target.dataset.contact || target.dataset.index !== undefined)) {
      return; // 点击的是联系人项或操作按钮
    }
    
    // 关闭所有滑动菜单
    this.closeAllSwipeMenus();
  }
});